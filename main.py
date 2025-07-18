import logging
from fastapi import FastAPI
from app.api.endpoints import performance
from app.core.config import get_settings


settings = get_settings()

logging.basicConfig(level=settings.LOG_LEVEL,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

app = FastAPI(
    title=settings.APP_NAME,
    description=settings.APP_DESCRIPTION,
    version=settings.APP_VERSION,
)

app.include_router(performance.router)

@app.get("/")
async def root():
    return {"message": "Welcome to the Portfolio Performance Analytics API. Access /docs for API documentation."}