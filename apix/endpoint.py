import asyncio
import inspect
import json
from typing import Callable, Union, Optional

from httpx import Client, AsyncClient
from httpx import Request, Response
from pydantic import BaseModel

from . import params
from .dependencies.utils import get_dependant, request_params_to_args, request_body_to_args
from .exceptions import RequestValidationError
from .utils import is_coroutine_callable, is_scalar_type, flatten_args

AgnosticClient = Union[Client, AsyncClient]


class Endpoint:
    __is_endpoint__ = True
    client: AgnosticClient = Client()
    _async_client = AsyncClient()
    service_cls: Optional['Service'] = None

    def __init__(self, *, path: str, method: str, call: Callable, client: AgnosticClient = None):
        self.path = path
        self.method = method.strip().upper()
        self.is_async = is_coroutine_callable(call)
        if client is not None:
            assert self.is_async == isinstance(client, AsyncClient), "async function should use `AsyncClient`"
            self.client = client
        elif self.is_async:
            self.client = self._async_client
        self.call = call
        self.raw_signature = inspect.signature(call)
        self.dependant = get_dependant(path=path, call=call)
        self.is_method = False
        self.is_classmethod = False

    def __call__(self, *args, **kwargs):
        if self.is_classmethod:
            args = args[1:]
        elif self.is_method and len(args) != 0:
            first_param = next(iter(self.raw_signature.parameters.values()), None)
            if first_param is not None:
                name = first_param.name
                if name in kwargs:
                    kwargs.pop(name)
                elif isinstance(args[0], self.service_cls):
                    args = args[1:]

        request = self._prepare_request(*args, **kwargs)
        if self.is_async and isinstance(self.client, AsyncClient):
            async def send_request():
                return self._response_to_return(await self.client.send(request))

            return asyncio.ensure_future(send_request())
        elif self.is_async:
            async def send_request():
                return self._response_to_return(self.client.send(request))

            return asyncio.ensure_future(send_request())
        else:
            return self._response_to_return(self.client.send(request))

    def __get__(self, instance, owner):
        if instance is not None:
            self.client = getattr(instance, 'client', self.client)
        return self

    def rebuild_dependant(self, is_method: bool, is_classmethod: bool):
        self.is_method = is_method
        self.is_classmethod = is_classmethod
        self.dependant = get_dependant(path=self.path, call=self.call,
                                       is_method_or_classmethod=is_method or is_classmethod)

    def _prepare_request(self, *args, **kwargs) -> Request:
        bound_arguments = self.dependant.signature.bind(*args, **kwargs).arguments
        dependant = self.dependant
        errors = []
        path_values, path_errors = request_params_to_args(dependant.path_params, bound_arguments)
        query_values, query_errors = request_params_to_args(dependant.query_params, bound_arguments)
        header_values, header_errors = request_params_to_args(dependant.header_params, bound_arguments)
        cookie_values, cookie_errors = request_params_to_args(dependant.cookie_params, bound_arguments)
        body_values, body_errors = request_body_to_args(dependant.body_params, bound_arguments)

        errors += path_errors + query_errors + header_errors + cookie_errors + body_errors
        if errors:
            raise RequestValidationError(errors)

        is_body_form = any(isinstance(f.field_info, params.Form) for f in dependant.body_params)
        data_arg = body_values if is_body_form else None
        json_arg = None if is_body_form else body_values
        url = self.client.base_url.join(self.path.format(**path_values))
        request = Request(self.method, url, params=flatten_args(query_values),
                          headers=flatten_args(header_values),
                          cookies=dict(flatten_args(cookie_values)), json=json_arg, data=data_arg)

        return request

    def _response_to_return(self, response: Response):
        return_annotation = self.dependant.signature.return_annotation

        if return_annotation is inspect.Parameter.empty or return_annotation is Response:
            return response
        elif return_annotation is None:
            return None
        elif return_annotation is str:
            return response.text
        elif return_annotation is bytes:
            return response.content
        elif issubclass(return_annotation, BaseModel):
            return_annotation.update_forward_refs(**getattr(self.call, "__globals__", {}))
            return return_annotation(**response.json())
        elif is_scalar_type(return_annotation):
            try:
                return return_annotation(response.json())
            except json.JSONDecodeError:
                return return_annotation(response.text)
        elif inspect.isclass(return_annotation):
            try:
                return return_annotation(**response.json())
            except json.JSONDecodeError:
                return response
        else:
            return response


def endpoint(path: str, method: str, client: AgnosticClient = None):
    def decorator(call: Callable):
        # print(getattr(call, "__locals__", {}))
        return Endpoint(path=path, method=method, call=call, client=client)

    return decorator


def options(path: str, client: AgnosticClient = None):
    return endpoint(path, method='OPTIONS', client=client)


def head(path: str, client: AgnosticClient = None):
    return endpoint(path, method='HEAD', client=client)


def get(path: str, client: AgnosticClient = None):
    return endpoint(path, method='GET', client=client)


def post(path: str, client: AgnosticClient = None):
    return endpoint(path, method='POST', client=client)


def put(path: str, client: AgnosticClient = None):
    return endpoint(path, method='PUT', client=client)


def patch(path: str, client: AgnosticClient = None):
    return endpoint(path, method='PATCH', client=client)


def delete(path: str, client: AgnosticClient = None):
    return endpoint(path, method='DELETE', client=client)


__all__ = [
    'Endpoint',
    'options',
    'head',
    'get',
    'post',
    'put',
    'patch',
    'delete'
]
