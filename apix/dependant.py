import inspect
from collections import defaultdict
from typing import Dict, Any, Callable, Type, List, DefaultDict

from .utils import get_path_param_names, is_scalar_type, get_param_type

try:
    from typing import ForwardRef  # noqa


    def evaluate_forwardref(
            type_: ForwardRef, globalns: Any, localns: Any
    ) -> Type[Any]:
        return type_._evaluate(globalns, localns)  # noqa


except ImportError:
    # python 3.6
    from typing import _ForwardRef as ForwardRef  # noqa


    def evaluate_forwardref(
            type_: ForwardRef, globalns: Any, localns: Any
    ) -> Type[Any]:
        return type_._eval_type(globalns, localns)  # noqa


def get_typed_annotation(param: inspect.Parameter, globalns: Dict[str, Any]) -> Any:
    annotation = param.annotation
    if isinstance(annotation, str):
        annotation = ForwardRef(annotation)
        annotation = evaluate_forwardref(annotation, globalns, globalns)
    return annotation


def get_typed_signature(
        call: Callable, is_method_or_classmethod=False
) -> inspect.Signature:
    signature = inspect.signature(call)

    globalns = getattr(call, "__globals__", {})
    raw_params = list(signature.parameters.values())
    if is_method_or_classmethod:
        raw_params = raw_params[1:]
    typed_params = [
        inspect.Parameter(
            name=param.name,
            kind=param.kind,
            default=param.default,
            annotation=get_typed_annotation(param, globalns),
        )
        for param in raw_params
    ]
    typed_signature = inspect.Signature(
        typed_params, return_annotation=signature.return_annotation
    )
    return typed_signature


class Dependant:
    def __init__(
            self,
            *,
            params_map: DefaultDict[str, List[str]] = None,
            name: str = None,
            call: Callable = None,
            path: str = None,
            signature: inspect.Signature = None,
    ) -> None:
        self.params_map = params_map or defaultdict(list)
        self.name = name
        self.call = call
        # Store the path to be able to re-generate a dependable from it in overrides
        self.path = path
        self.signature = signature

    def add_param(self, param_name: str, param: inspect.Parameter) -> bool:
        param_type = get_param_type(param.annotation)
        if param_type is None:
            return False
        self.params_map[param_type].append(param_name)
        return True


def get_dependant(
        *,
        path: str,
        call: Callable,
        http_method: str,
        name: str = None,
        is_method_or_classmethod=False,
) -> Dependant:
    path_param_names = get_path_param_names(path)
    endpoint_signature = get_typed_signature(call, is_method_or_classmethod)
    signature_params = endpoint_signature.parameters
    dependant = Dependant(call=call, name=name, path=path, signature=endpoint_signature)
    for param_name, param in signature_params.items():
        if param_name in path_param_names:
            assert is_scalar_type(
                param.annotation
            ), f"Path params must be of one of the supported types"
            dependant.params_map['Path'].append(param_name)
        elif not dependant.add_param(param_name, param):
            if http_method in ("POST", "PUT", "PATCH") and not is_scalar_type(
                    param.annotation
            ):
                dependant.params_map['Body'].append(param_name)
            else:
                dependant.params_map['Query'].append(param_name)

    return dependant
