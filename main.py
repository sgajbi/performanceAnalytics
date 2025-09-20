# main.py
import logging
import os
from typing import Any

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from starlette.responses import JSONResponse
import orjson

from app.api.endpoints import contribution, performance, lineage
from app.core.config import get_settings
from app.core.exceptions import PerformanceCalculatorError
from app.core.handlers import performance_calculator_exception_handler

# --- FIX START: Create a custom JSON response class to exclude nulls ---
class ORJSONResponseExcludeNull(JSONResponse):
    def render(self, content: Any) -> bytes:
        # Use orjson for high-performance JSON serialization
        # option=orjson.OPT_OMIT_NULL removes keys with None values.
        return orjson.dumps(content, option=orjson.OPT_OMIT_NULL)
# --- FIX END ---


settings = get_settings()

logging.basicConfig(level=settings.LOG_LEVEL, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

app = FastAPI(
    title=settings.APP_NAME,
    description=settings.APP_DESCRIPTION,
    version=settings.APP_VERSION,
    default_response_class=ORJSONResponseExcludeNull, # Set as the default for the app
)

# Create lineage directory if it doesn't exist
if not os.path.exists(settings.LINEAGE_STORAGE_PATH):
    os.makedirs(settings.LINEAGE_STORAGE_PATH)

app.mount("/lineage", StaticFiles(directory=settings.LINEAGE_STORAGE_PATH), name="lineage_files")

app.add_exception_handler(PerformanceCalculatorError, performance_calculator_exception_handler)

# Add a prefix to group performance-related endpoints
app.include_router(performance.router, prefix="/performance")
app.include_router(contribution.router, prefix="/performance")
app.include_router(lineage.router, prefix="/performance")


@app.get("/")
async def root():
    """Provides a welcome message and a link to the API documentation."""
    return {"message": "Welcome to the Portfolio Performance Analytics API. Access /docs for API documentation."}