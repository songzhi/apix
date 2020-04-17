import asyncio
import functools
import inspect
import re
from typing import Set, Dict, Type, Any, Optional, Union, Callable, Mapping, Sequence, cast, List, Tuple

from multidict import MultiDict
from pydantic import BaseConfig
from pydantic.class_validators import Validator
from pydantic.fields import UndefinedType, FieldInfo, ModelField
from pydantic.utils import lenient_issubclass


def get_path_param_names(path: str) -> Set[str]:
    return {item.strip("{}") for item in re.findall("{[^}]*}", path)}


def create_response_field(
        name: str,
        type_: Type[Any],
        class_validators: Optional[Dict[str, Validator]] = None,
        default: Optional[Any] = None,
        required: Union[bool, UndefinedType] = False,
        model_config: Type[BaseConfig] = BaseConfig,
        field_info: Optional[FieldInfo] = None,
        alias: Optional[str] = None,
) -> ModelField:
    """
    Create a new response field. Raises if type_ is invalid.
    """
    class_validators = class_validators or {}
    field_info = field_info or FieldInfo(None)

    response_field = functools.partial(
        ModelField,
        name=name,
        type_=type_,
        class_validators=class_validators,
        default=default,
        required=required,
        model_config=model_config,
        alias=alias,
    )

    return response_field(field_info=field_info)


def is_coroutine_callable(call: Callable) -> bool:
    if inspect.isroutine(call):
        return asyncio.iscoroutinefunction(call)
    if inspect.isclass(call):
        return False
    call = getattr(call, "__call__", None)
    return asyncio.iscoroutinefunction(call)


sequence_types = (list, set, tuple)


def is_scalar_type(type_: Any) -> bool:
    return lenient_issubclass(type_, (int, float, complex, bool, str, bytes))


PrimitiveData = Optional[Union[str, int, float, bool]]
NestedArgs = Mapping[str, Union[PrimitiveData, Sequence[PrimitiveData], 'NestedArgs']]


def flatten_args(args: NestedArgs) -> List[Tuple[str, PrimitiveData]]:
    """
    flatten nested args ignoring the key of nested mapping

    Example:
    >>> flatten_args({"tag": ["python", "dev"], "foo": {"tag": ["math"]}})
    [('tag', 'python'), ('tag', 'dev'), ('tag', 'math')]

    """
    flattened_args = MultiDict()
    for k, v in args.items():
        if isinstance(v, Sequence) and not isinstance(v, (str, bytes)):
            for u in v:
                flattened_args.add(k, u)
        elif isinstance(v, Mapping):
            flattened_args.extend(flatten_args(v))
        else:
            flattened_args.add(k, cast("PrimitiveData", v))
    return list(flattened_args.items())
