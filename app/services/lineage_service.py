# app/services/lineage_service.py
import json
import logging
import os
from typing import Dict
from uuid import UUID

import pandas as pd
from pydantic import BaseModel

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

class LineageService:
    def __init__(self, storage_path: str):
        self.storage_path = storage_path
        if not os.path.exists(self.storage_path):
            os.makedirs(self.storage_path)
            logger.info(f"Created lineage storage directory at: {self.storage_path}")

    def capture(
        self,
        calculation_id: UUID,
        calculation_type: str,
        request_model: BaseModel,
        response_model: BaseModel,
        calculation_details: Dict[str, pd.DataFrame],
    ):
        """Captures all artifacts for a calculation and saves them to storage."""
        try:
            target_dir = os.path.join(self.storage_path, str(calculation_id))
            if not os.path.exists(target_dir):
                os.makedirs(target_dir)

            # Save request and response JSON
            with open(os.path.join(target_dir, "request.json"), "w") as f:
                f.write(request_model.model_dump_json(indent=2))
            
            with open(os.path.join(target_dir, "response.json"), "w") as f:
                f.write(response_model.model_dump_json(indent=2))

            # Save detailed calculation CSVs
            for filename, df in calculation_details.items():
                df.to_csv(os.path.join(target_dir, filename), index=False)
            
            logger.info(f"Successfully captured lineage data for calculation_id: {calculation_id}")

        except Exception as e:
            logger.error(f"Failed to capture lineage data for {calculation_id}: {e}", exc_info=True)


lineage_service = LineageService(storage_path=settings.LINEAGE_STORAGE_PATH)