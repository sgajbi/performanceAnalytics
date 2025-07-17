from fastapi import FastAPI
from app.api.endpoints import performance

app = FastAPI(
    title="Portfolio Performance Analytics API",
    description="API for calculating portfolio performance metrics.",
    version="0.1.0",
)

app.include_router(performance.router)

# You can add root endpoint or other global configurations here if needed
@app.get("/")
async def root():
    return {"message": "Welcome to the Portfolio Performance Analytics API. Access /docs for API documentation."}