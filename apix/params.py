from typing import Union, Generic, TypeVar, ClassVar, Dict, Any

T = TypeVar('T', covariant=True)


class _Param(str, Generic[T]):
    _in: ClassVar[str]

    def __class_getitem__(cls, params):
        ty = Union[params]
        ty.__param_type__ = cls._in
        return ty


class Query(_Param):
    _in = 'Query'


class Header(_Param):
    _in = 'Header'


class Path(_Param):
    _in = 'Path'


class Cookie(_Param):
    _in = 'Cookie'


class _Body(Dict[str, Any], Generic[T]):
    _in: ClassVar[str]

    def __class_getitem__(cls, params):
        ty = Union[params]
        ty.__param_type__ = cls._in
        return ty


class Body(_Body):
    _in = 'Body'


class Form(_Body):
    _in = 'Form'


__all__ = ['Query', 'Header', 'Path', 'Cookie', 'Body', 'Form']
