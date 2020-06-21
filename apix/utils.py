import asyncio
import inspect
import re
from typing import (
    Any,
    Union,
    Tuple,
    Type,
    Set,
    Callable,
    Mapping,
    Optional,
    Sequence,
    List,
    cast,
)

from multidict import MultiDict

AnyType = Type[Any]


def get_path_param_names(path: str) -> Set[str]:
    return {item.strip("{}") for item in re.findall("{[^}]*}", path)}


def is_coroutine_callable(call: Callable) -> bool:
    if inspect.isroutine(call):
        return asyncio.iscoroutinefunction(call)
    if inspect.isclass(call):
        return False
    call = getattr(call, "__call__", None)
    return asyncio.iscoroutinefunction(call)


def lenient_issubclass(
        cls: Any, class_or_tuple: Union[AnyType, Tuple[AnyType, ...]]
) -> bool:
    return isinstance(cls, type) and issubclass(cls, class_or_tuple)


def is_scalar_type(type_: Any) -> bool:
    return lenient_issubclass(type_, (int, float, complex, bool, str, bytes))


def get_param_type(obj: Any) -> Optional[str]:
    return getattr(obj, "__apix_param_type__", None)


PrimitiveData = Optional[Union[str, int, float, bool]]
NestedArgs = Mapping[str, Union[PrimitiveData, Sequence[PrimitiveData], "NestedArgs"]]


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
