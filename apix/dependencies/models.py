from inspect import Signature
from typing import List, Callable

from pydantic.fields import ModelField

param_supported_types = (str, int, float, bool)


class Dependant:
    def __init__(
            self,
            *,
            path_params: List[ModelField] = None,
            query_params: List[ModelField] = None,
            header_params: List[ModelField] = None,
            cookie_params: List[ModelField] = None,
            body_params: List[ModelField] = None,
            name: str = None,
            call: Callable = None,
            path: str = None,
            signature: Signature = None
    ) -> None:
        self.path_params = path_params or []
        self.query_params = query_params or []
        self.header_params = header_params or []
        self.cookie_params = cookie_params or []
        self.body_params = body_params or []
        self.name = name
        self.call = call
        # Store the path to be able to re-generate a dependable from it in overrides
        self.path = path
        self.signature = signature
