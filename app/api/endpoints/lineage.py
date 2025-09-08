# app/api/endpoints/lineage.py
import os
from typing import Dict
from uuid import UUID
from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel

from app.core.config import get_settings

router = APIRouter()
settings = get_settings()

class ArtifactLink(BaseModel):
    url: str

class LineageResponse(BaseModel):
    calculation_id: UUID
    calculation_type: str
    timestamp_utc: str
    artifacts: Dict[str, ArtifactLink]


@router.get("/lineage/{calculation_id}", response_model=LineageResponse, summary="Retrieve Data Lineage Artifacts")
async def get_lineage_data(calculation_id: UUID, request: Request):
    """
    Retrieves the download URLs for all data lineage artifacts associated with a calculation_id.
    """
    lineage_dir = os.path.join(settings.LINEAGE_STORAGE_PATH, str(calculation_id))
    if not os.path.isdir(lineage_dir):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lineage data not found for the given calculation_id.")

    artifacts = {}
    try:
        for filename in os.listdir(lineage_dir):
            # Construct a relative URL that the static file server can handle
            file_url = request.url_for("lineage_files", path=f"{calculation_id}/{filename}")
            artifacts[filename] = ArtifactLink(url=str(file_url))

        # We need to get metadata like calc_type and timestamp from a manifest file
        # For now, we'll use placeholder values.
        return LineageResponse(
            calculation_id=calculation_id,
            calculation_type="UNKNOWN",
            timestamp_utc="N/A",
            artifacts=artifacts,
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to retrieve lineage artifacts: {e}")