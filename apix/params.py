from typing import (
    Generic,
    TypeVar,
    ClassVar,
    Dict,
    Any,
    _SpecialForm,  # noqa
    _GenericAlias,  # noqa
)

T = TypeVar("T", covariant=True)


class _Param(str, Generic[T]):
    __apix_param_type__: ClassVar[str]
    __special_form__: _SpecialForm

    def __class_getitem__(cls, params):
        ty = _GenericAlias(cls.__special_form__, params)
        ty.__apix_param_type__ = cls.__apix_param_type__
        return ty


class Query(_Param):
    __apix_param_type__ = "Query"
    __special_form__ = _SpecialForm("Query", "")


class Header(_Param):
    __apix_param_type__ = "Header"
    __special_form__ = _SpecialForm("Header", "")


class Path(_Param):
    __apix_param_type__ = "Path"
    __special_form__ = _SpecialForm("Path", "")


class Cookie(_Param):
    __apix_param_type__ = "Cookie"
    __special_form__ = _SpecialForm("Cookie", "")


class _Body(Dict[str, Any], Generic[T]):
    __apix_param_type__: ClassVar[str]
    __special_form__: _SpecialForm

    def __class_getitem__(cls, params):
        ty = _GenericAlias(cls.__special_form__, params)
        ty.__apix_param_type__ = cls.__apix_param_type__
        return ty


class Body(_Body):
    __apix_param_type__ = "Body"
    __special_form__ = _SpecialForm("Body", "")


class Form(_Body):
    __apix_param_type__ = "Form"
    __special_form__ = _SpecialForm("Form", "")


__all__ = ["Query", "Header", "Path", "Cookie", "Body", "Form"]
