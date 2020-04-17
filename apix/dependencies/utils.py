import inspect
from copy import deepcopy
from typing import Callable, Dict, Any, Type, List, Optional, cast, Sequence, Mapping, Tuple

from pydantic import BaseModel, MissingError, create_model  # noqa
from pydantic.error_wrappers import ErrorWrapper
from pydantic.fields import ModelField, FieldInfo, SHAPE_SINGLETON, SHAPE_LIST, SHAPE_SET, SHAPE_TUPLE, \
    SHAPE_SEQUENCE, SHAPE_TUPLE_ELLIPSIS, Required
from pydantic.schema import get_annotation_from_field_info
from pydantic.typing import ForwardRef, evaluate_forwardref  # noqa
from pydantic.utils import lenient_issubclass

from .models import Dependant
from .. import params
from ..encoder import jsonable_encoder
from ..utils import get_path_param_names, create_response_field

sequence_shapes = {
    SHAPE_LIST,
    SHAPE_SET,
    SHAPE_TUPLE,
    SHAPE_SEQUENCE,
    SHAPE_TUPLE_ELLIPSIS,
}
sequence_types = (list, set, tuple)
sequence_shape_to_type = {
    SHAPE_LIST: list,
    SHAPE_SET: set,
    SHAPE_TUPLE: tuple,
    SHAPE_SEQUENCE: list,
    SHAPE_TUPLE_ELLIPSIS: list,
}


def get_typed_annotation(param: inspect.Parameter, globalns: Dict[str, Any]) -> Any:
    annotation = param.annotation
    if isinstance(annotation, str):
        annotation = ForwardRef(annotation)
        annotation = evaluate_forwardref(annotation, globalns, globalns)
    return annotation


def get_typed_signature(call: Callable, is_method_or_classmethod=False) -> inspect.Signature:
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
    typed_signature = inspect.Signature(typed_params, return_annotation=signature.return_annotation)
    return typed_signature


def get_dependant(
        *,
        path: str,
        call: Callable,
        name: str = None,
        is_method_or_classmethod=False
) -> Dependant:
    path_param_names = get_path_param_names(path)
    endpoint_signature = get_typed_signature(call, is_method_or_classmethod)
    signature_params = endpoint_signature.parameters
    dependant = Dependant(call=call, name=name, path=path, signature=endpoint_signature)
    for param_name, param in signature_params.items():
        param_field = get_param_field(
            param=param, default_field_info=params.Query, param_name=param_name
        )
        if param_name in path_param_names:
            assert is_scalar_field(
                field=param_field
            ), f"Path params must be of one of the supported types"
            if isinstance(param.default, params.Path):
                ignore_default = False
            else:
                ignore_default = True
            param_field = get_param_field(
                param=param,
                param_name=param_name,
                default_field_info=params.Path,
                force_type=params.ParamTypes.path,
                ignore_default=ignore_default,
            )
            add_param_to_fields(field=param_field, dependant=dependant)
        elif isinstance(param.default, params.Body):
            dependant.body_params.append(param_field)
        else:
            add_param_to_fields(field=param_field, dependant=dependant)

    return dependant


def add_param_to_fields(*, field: ModelField, dependant: Dependant) -> None:
    field_info = cast(params.Param, get_field_info(field))
    if field_info.in_ == params.ParamTypes.path:
        dependant.path_params.append(field)
    elif field_info.in_ == params.ParamTypes.query:
        dependant.query_params.append(field)
    elif field_info.in_ == params.ParamTypes.header:
        dependant.header_params.append(field)
    else:
        assert (
                field_info.in_ == params.ParamTypes.cookie
        ), f"non-body parameters must be in path, query, header or cookie: {field.name}"
        dependant.cookie_params.append(field)


def get_param_field(
        *,
        param: inspect.Parameter,
        param_name: str,
        default_field_info: Type[params.Param] = params.Param,
        force_type: params.ParamTypes = None,
        ignore_default: bool = False,
) -> ModelField:
    default_value = Required
    had_schema = False
    if not param.default == param.empty and ignore_default is False:
        default_value = param.default
    if isinstance(default_value, FieldInfo):
        had_schema = True
        field_info = default_value
        default_value = field_info.default
        if (
                isinstance(field_info, params.Param)
                and getattr(field_info, "in_", None) is None
        ):
            field_info.in_ = default_field_info.in_
        if force_type:
            field_info.in_ = force_type  # noqa
    else:
        field_info = default_field_info(default_value)
    required = default_value == Required
    annotation: Any = Any
    if not param.annotation == param.empty:
        annotation = param.annotation
    annotation = get_annotation_from_field_info(annotation, field_info, param_name)
    if not field_info.alias and getattr(field_info, "convert_underscores", None):
        alias = param.name.replace("_", "-")
    else:
        alias = field_info.alias or param.name
    field = create_response_field(
        name=param.name,
        type_=annotation,
        default=None if required else default_value,
        alias=alias,
        required=required,
        field_info=field_info,
    )
    field.required = required
    if not had_schema and not is_scalar_field(field=field):
        field.field_info = params.Body(field_info.default)

    return field


def is_scalar_field(field: ModelField) -> bool:
    field_info = get_field_info(field)
    if not (
            field.shape == SHAPE_SINGLETON
            and not lenient_issubclass(field.type_, BaseModel)
            and not lenient_issubclass(field.type_, sequence_types + (dict,))  # noqa
            and not isinstance(field_info, params.Body)
    ):
        return False
    if field.sub_fields:
        if not all(is_scalar_field(f) for f in field.sub_fields):
            return False
    return True


def is_scalar_sequence_field(field: ModelField) -> bool:
    if (field.shape in sequence_shapes) and not lenient_issubclass(
            field.type_, BaseModel
    ):
        if field.sub_fields is not None:
            for sub_field in field.sub_fields:
                if not is_scalar_field(sub_field):
                    return False
        return True
    if lenient_issubclass(field.type_, sequence_types):
        return True
    return False


def get_field_info(field: ModelField) -> FieldInfo:
    return field.field_info


def get_missing_field_error(field_alias: str) -> ErrorWrapper:
    missing_field_error = ErrorWrapper(MissingError(), loc=("body", field_alias))
    return missing_field_error


def request_params_to_args(
        required_params: Sequence[ModelField],
        received_params: Mapping[str, Any],
) -> Tuple[Dict[str, Any], List[ErrorWrapper]]:
    values = {}
    errors = []
    for field in required_params:
        value = received_params.get(field.name)
        field_info = get_field_info(field)
        assert isinstance(
            field_info, params.Param
        ), "Params must be subclasses of Param"
        if value is None:
            if field.required:
                errors.append(
                    ErrorWrapper(
                        MissingError(), loc=(field_info.in_.value, field.alias)
                    )
                )
            else:
                values[field.alias] = deepcopy(field.default)
            continue
        v_, errors_ = field.validate(
            value, values, loc=(field_info.in_.value, field.alias)
        )
        if isinstance(errors_, ErrorWrapper):
            errors.append(errors_)
        elif isinstance(errors_, list):
            errors.extend(errors_)
        else:
            values[field.alias] = v_
    return values, errors


def request_body_to_args(
        required_params: List[ModelField],
        received_body: Optional[Dict[str, Any]],
) -> Tuple[Dict[str, Any], List[ErrorWrapper]]:
    values = {}
    errors = []
    if required_params:
        field = required_params[0]
        field_info = get_field_info(field)
        embed = getattr(field_info, "embed", None)
        if len(required_params) == 1 and not embed:
            values = jsonable_encoder(received_body.get(field.name))
            return values, errors
        for field in required_params:
            value: Any = None
            if received_body is not None:
                try:
                    value = received_body.get(field.name)
                except AttributeError:
                    errors.append(get_missing_field_error(field.name))
                    continue

            if (
                    value is None
                    or (isinstance(field_info, params.Form) and value == "")
                    or (isinstance(field_info, params.Form)
                        and field.shape in sequence_shapes
                        and len(value) == 0)
            ):
                if field.required:
                    errors.append(get_missing_field_error(field.name))
                else:
                    values[field.alias] = deepcopy(field.default)
                continue
            v_, errors_ = field.validate(value, values, loc=("body", field.name))
            if isinstance(errors_, ErrorWrapper):
                errors.append(errors_)
            elif isinstance(errors_, list):
                errors.extend(errors_)
            else:
                values[field.alias] = v_
    return jsonable_encoder(values), errors
