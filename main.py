import logging

from fastapi import FastAPI

from app.api.endpoints import performance
from app.core.config import get_settings
from app.core.exceptions import PerformanceCalculatorError  # Import the base exception
from app.core.handlers import performance_calculator_exception_handler  # Import the handler

settings = get_settings()

logging.basicConfig(level=settings.LOG_LEVEL, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

app = FastAPI(
    title=settings.APP_NAME,
    description=settings.APP_DESCRIPTION,
    version=settings.APP_VERSION,
)

# Register the custom exception handler
app.add_exception_handler(PerformanceCalculatorError, performance_calculator_exception_handler)

app.include_router(performance.router)


@app.get("/")
async def root():
    return {"message": "Welcome to the Portfolio Performance Analytics API. Access /docs for API documentation."}
