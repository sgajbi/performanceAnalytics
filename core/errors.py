# core/errors.py
from fastapi import HTTPException, status

if hasattr(status, "HTTP_422_UNPROCESSABLE_CONTENT"):
    HTTP_422_UNPROCESSABLE = status.HTTP_422_UNPROCESSABLE_CONTENT
else:
    HTTP_422_UNPROCESSABLE = status.HTTP_422_UNPROCESSABLE_ENTITY


class APIError(HTTPException):
    """Base class for custom API exceptions for consistent error handling."""

    def __init__(self, status_code: int, detail: str):
        super().__init__(status_code=status_code, detail=detail)


class APIBadRequestError(APIError):
    """To be used for 400 Bad Request errors (validation, schema issues)."""

    def __init__(self, detail: str = "Bad Request"):
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


class APIUnprocessableEntityError(APIError):
    """To be used for 422 Unprocessable Entity errors (valid request, but data is insufficient)."""

    def __init__(self, detail: str = "Unprocessable Entity"):
        super().__init__(status_code=HTTP_422_UNPROCESSABLE, detail=detail)


class APIConflictError(APIError):
    """To be used for 409 Conflict errors (e.g., overlapping hierarchies)."""

    def __init__(self, detail: str = "Conflict"):
        super().__init__(status_code=status.HTTP_409_CONFLICT, detail=detail)
