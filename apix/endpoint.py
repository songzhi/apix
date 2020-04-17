import asyncio
import inspect
import json
from typing import Callable, Union

from httpx import Client, AsyncClient
from httpx import Request, Response
from pydantic import BaseModel

from . import params
from .dependencies.utils import get_dependant, request_params_to_args, request_body_to_args, get_body_field
from .exceptions import RequestValidationError
from .utils import is_coroutine_callable, is_scalar_type, flatten_args

AgnosticClient = Union[Client, AsyncClient]


class Endpoint:
    client: AgnosticClient = Client()
    _async_client = AsyncClient()

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
        self.dependant = get_dependant(path=path, call=call)
        self.body_field = get_body_field(dependant=self.dependant, name=call.__name__)

    def __call__(self, *args, **kwargs):
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

        body_field = self.body_field
        is_body_form = body_field and isinstance(body_field.field_info, params.Form)
        data_arg = body_values if is_body_form else None
        json_arg = None if is_body_form else body_values
        request = Request(self.method, self.path.format(**path_values), params=flatten_args(query_values),
                          headers=flatten_args(header_values),
                          cookies=dict(flatten_args(cookie_values)), json=json_arg, data=data_arg)

        return request

    def _response_to_return(self, response: Response):
        # TODO: more accurate
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
