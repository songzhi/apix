from typing import Union, Generic, TypeVar, ClassVar, Dict, Any

T = TypeVar('T', covariant=True)


class _Param(str, Generic[T]):
    __apix_param_type__: ClassVar[str]

    def __class_getitem__(cls, params):
        ty = Union[params]
        ty.__apix_param_type__ = cls.__apix_param_type__
        return ty


class Query(_Param):
    __apix_param_type__ = 'Query'


class Header(_Param):
    __apix_param_type__ = 'Header'


class Path(_Param):
    __apix_param_type__ = 'Path'


class Cookie(_Param):
    __apix_param_type__ = 'Cookie'


class _Body(Dict[str, Any], Generic[T]):
    __apix_param_type__: ClassVar[str]

    def __class_getitem__(cls, params):
        ty = Union[params]
        ty.__apix_param_type__ = cls.__apix_param_type__
        return ty


class Body(_Body):
    __apix_param_type__ = 'Body'


class Form(_Body):
    __apix_param_type__ = 'Form'


__all__ = ['Query', 'Header', 'Path', 'Cookie', 'Body', 'Form']
