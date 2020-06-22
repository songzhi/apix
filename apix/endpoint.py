import asyncio
import inspect
from functools import wraps
from typing import Callable, Union, Tuple, Any, Dict

import typic
from httpx import Client, AsyncClient
from httpx import Request, Response

from .dependant import get_dependant
from .utils import is_coroutine_callable

AgnosticClient = Union[Client, AsyncClient]


def transmuter(call: Callable) -> Callable[..., Tuple[Tuple[..., Any], Dict[str, Any]]]:
    @wraps(call)
    def wrapped(*args, **kwargs):
        return args, kwargs

    return typic.al(wrapped)


class Endpoint:
    __is_endpoint__ = True
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
        self.transmuter = transmuter(call)
        self.raw_signature = inspect.signature(call)
        self.dependant = get_dependant(path=path, call=call, http_method=method)
        self.is_method = False
        self.is_classmethod = False

    def __call__(self, *args, **kwargs):
        from .service import Service
        args, kwargs = self.transmuter(*args, **kwargs)
        if self.is_classmethod:
            args = args[1:]
        elif self.is_method and len(args) != 0:
            first_param = next(iter(self.raw_signature.parameters.values()), None)
            if first_param is not None:
                name = first_param.name
                if name in kwargs:
                    kwargs.pop(name)
                elif isinstance(args[0], Service):
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
        self.dependant = get_dependant(path=self.path, call=self.call, http_method=self.method,
                                       is_method_or_classmethod=is_method or is_classmethod)

    def _prepare_request(self, args: Tuple[..., Any], kwargs: Dict[str, Any]) -> Request:
        dependant = self.dependant
        bound_args = dependant.bind(args, kwargs)
        path_values = bound_args.get('Path', {})
        queries = bound_args.get('Query', None)
        headers = bound_args.get('Header', None)
        cookies = bound_args.get('Cookie', None)
        body = bound_args.get('Body', None)
        form = bound_args.get('Form', None)
        url = self.client.base_url.join(self.path.format(**path_values))
        request = Request(self.method, url, params=queries, headers=headers, cookies=cookies, json=body, data=form)
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
        else:
            try:
                return typic.transmute(return_annotation, response.json())
            except ValueError:
                try:
                    return typic.transmute(return_annotation, response.text)
                except ValueError:
                    pass
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
