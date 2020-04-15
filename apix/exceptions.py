from typing import Sequence, Any

from pydantic import ValidationError, create_model
from pydantic.error_wrappers import ErrorList

RequestErrorModel = create_model("Request")


class RequestValidationError(ValidationError):
    def __init__(self, errors: Sequence[ErrorList], *, body: Any = None) -> None:
        self.body = body
        super().__init__(errors, RequestErrorModel)
