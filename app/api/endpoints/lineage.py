# app/api/endpoints/lineage.py
import json
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
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Lineage data not found for the given calculation_id."
        )

    artifacts = {}
    try:
        manifest_path = os.path.join(lineage_dir, "manifest.json")
        if not os.path.exists(manifest_path):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lineage manifest not found.")

        with open(manifest_path, "r") as f:
            manifest_data = json.load(f)

        for filename in os.listdir(lineage_dir):
            if filename != "manifest.json":
                file_url = request.url_for("lineage_files", path=f"{calculation_id}/{filename}")
                artifacts[filename] = ArtifactLink(url=str(file_url))

        return LineageResponse(
            calculation_id=calculation_id,
            calculation_type=manifest_data.get("calculation_type", "UNKNOWN"),
            timestamp_utc=manifest_data.get("timestamp_utc", "N/A"),
            artifacts=artifacts,
        )
    except Exception as e:
        if isinstance(e, HTTPException):
            raise
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to retrieve lineage artifacts: {e}"
        )
