# main.py
import logging

from fastapi import FastAPI

from app.api.endpoints import contribution, performance
from app.core.config import get_settings
from app.core.exceptions import PerformanceCalculatorError
from app.core.handlers import performance_calculator_exception_handler

settings = get_settings()

logging.basicConfig(level=settings.LOG_LEVEL, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

app = FastAPI(
    title=settings.APP_NAME,
    description=settings.APP_DESCRIPTION,
    version=settings.APP_VERSION,
)

app.add_exception_handler(PerformanceCalculatorError, performance_calculator_exception_handler)

# Add a prefix to group performance-related endpoints
app.include_router(performance.router, prefix="/performance")
app.include_router(contribution.router, prefix="/performance")


@app.get("/")
async def root():
    """Provides a welcome message and a link to the API documentation."""
    return {"message": "Welcome to the Portfolio Performance Analytics API. Access /docs for API documentation."}