import logging

from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse

from app.core.exceptions import PerformanceCalculatorError

logger = logging.getLogger(__name__)


async def performance_calculator_exception_handler(request: Request, exc: PerformanceCalculatorError):
    """
    Handles PerformanceCalculatorError and its subclasses, returning a 500 or 400 HTTP response.
    """
    logger.error(f"PerformanceCalculatorError caught: {exc.message}", exc_info=True)

    # Customize status codes based on the specific exception type if needed
    # For now, treating all as internal server error unless explicitly designed for client error
    if isinstance(exc, (InvalidInputDataError, MissingConfigurationError)):
        status_code = status.HTTP_400_BAD_REQUEST
    else:
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR

    return JSONResponse(status_code=status_code, content={"detail": f"Calculation Error: {exc.message}"})
