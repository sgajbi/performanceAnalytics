# tests/unit/services/test_lineage_service.py
import json
import os
from uuid import uuid4

import pandas as pd
from pydantic import BaseModel

from app.services.lineage_service import LineageService


class MockModel(BaseModel):
    key: str


def test_lineage_service_capture(tmp_path):
    """
    Tests that the lineage service correctly creates a directory and saves
    the request, response, manifest, and CSV artifacts.
    """
    # 1. Arrange
    service = LineageService(storage_path=str(tmp_path))
    calc_id = uuid4()
    req_model = MockModel(key="request")
    res_model = MockModel(key="response")
    details_df = pd.DataFrame([{"colA": 1, "colB": 2}])

    # 2. Act
    service.capture(
        calculation_id=calc_id,
        calculation_type="TEST",
        request_model=req_model,
        response_model=res_model,
        calculation_details={"details.csv": details_df},
    )

    # 3. Assert
    target_dir = os.path.join(tmp_path, str(calc_id))
    assert os.path.isdir(target_dir)

    # Check for all files
    req_path = os.path.join(target_dir, "request.json")
    res_path = os.path.join(target_dir, "response.json")
    csv_path = os.path.join(target_dir, "details.csv")
    manifest_path = os.path.join(target_dir, "manifest.json")

    assert os.path.exists(req_path)
    assert os.path.exists(res_path)
    assert os.path.exists(csv_path)
    assert os.path.exists(manifest_path)

    # Check manifest content
    with open(manifest_path, "r") as f:
        manifest_data = json.load(f)

    assert manifest_data["calculation_type"] == "TEST"
    assert "timestamp_utc" in manifest_data
