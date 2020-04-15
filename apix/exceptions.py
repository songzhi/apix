from typing import Sequence, Any

from fastapi.exceptions import RequestErrorModel
from pydantic import ValidationError
from pydantic.error_wrappers import ErrorList


class RequestValidationError(ValidationError):
    def __init__(self, errors: Sequence[ErrorList], *, body: Any = None) -> None:
        self.body = body
        super().__init__(errors, RequestErrorModel)
