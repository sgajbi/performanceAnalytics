# main.py
import logging
import os
from typing import Any

from fastapi import FastAPI
from fastapi.encoders import jsonable_encoder
from fastapi.staticfiles import StaticFiles
from starlette.responses import JSONResponse
import orjson

from app.api.endpoints import contribution, integration_capabilities, lineage, performance
from app.core.config import get_settings
from app.core.exceptions import PerformanceCalculatorError
from app.core.handlers import performance_calculator_exception_handler

# --- FIX START: Create a robust custom JSON response class ---
def _clean_none_from_dict(d: dict) -> dict:
    """Recursively removes keys with None values from a dictionary."""
    out = {}
    for k, v in d.items():
        if v is not None:
            if isinstance(v, dict):
                out[k] = _clean_none_from_dict(v)
            elif isinstance(v, list):
                out[k] = _clean_none_from_list(v)
            else:
                out[k] = v
    return out

def _clean_none_from_list(l: list) -> list:
    """Recursively removes None values from lists and dicts within lists."""
    out = []
    for v in l:
        if v is not None:
            if isinstance(v, dict):
                out.append(_clean_none_from_dict(v))
            elif isinstance(v, list):
                out.append(_clean_none_from_list(v))
            else:
                out.append(v)
    return out

class ORJSONResponseExcludeNull(JSONResponse):
    def render(self, content: Any) -> bytes:
        """
        Serializes content to JSON using orjson, after removing null values.
        """
        # jsonable_encoder handles Pydantic models, datetimes, etc.
        encoded_content = jsonable_encoder(content)
        
        # Recursively remove None values
        if isinstance(encoded_content, dict):
            cleaned_content = _clean_none_from_dict(encoded_content)
        elif isinstance(encoded_content, list):
            cleaned_content = _clean_none_from_list(encoded_content)
        else:
            cleaned_content = encoded_content

        return orjson.dumps(cleaned_content)
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
app.include_router(integration_capabilities.router, prefix="/integration")


@app.get("/")
async def root():
    """Provides a welcome message and a link to the API documentation."""
    return {"message": "Welcome to the Portfolio Performance Analytics API. Access /docs for API documentation."}
