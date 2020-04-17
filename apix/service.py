import inspect

from httpx import Client, AsyncClient
from httpx._auth import AuthTypes  # noqa

from .endpoint import Endpoint


class ServiceMeta(type):
    is_async: bool

    def __init__(cls, *args, **kwargs):
        # get all endpoints including wrapped by staticmethod or classmethod
        cls._end_points = inspect.getmembers(cls, lambda val: (isinstance(val, Endpoint) or
                                                               getattr(val, '__is_endpoint__', False)))
        if cls.is_async and not getattr(cls, 'client', None):
            cls.client = AsyncClient()
        else:
            cls.client = Client()
        for name, endpoint in cls._end_points:
            endpoint.service_cls = cls
            is_staticmethod = isinstance(cls.__dict__[name], staticmethod)
            is_classmethod = isinstance(cls.__dict__[name], classmethod)
            is_method = not (is_staticmethod or is_classmethod)
            if not is_staticmethod:
                endpoint.rebuild_dependant(is_method, is_classmethod)
                endpoint.client = cls.client
        super().__init__(*args, **kwargs)


class Service(metaclass=ServiceMeta):
    is_async = False

    def __init__(self, base_url: str = None, auth: AuthTypes = None):
        if self.is_async:
            self.client = AsyncClient(base_url=base_url, auth=auth)
        else:
            self.client = Client(base_url=base_url, auth=auth)


class AsyncService(Service):
    is_async = True


__all__ = [
    'Service',
    'AsyncService'
]
