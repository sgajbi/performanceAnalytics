# core/repro.py
import hashlib
import json
from typing import Any
from uuid import UUID
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel


def _json_default_serializer(obj: Any) -> str:
    """Custom JSON serializer for deterministic hashing."""
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if isinstance(obj, UUID):
        return str(obj)
    if isinstance(obj, Decimal):
        return str(obj)
    raise TypeError(f"Type {type(obj)} not serializable")


def generate_canonical_hash(request_model: BaseModel, engine_version: str) -> tuple[str, str]:
    """
    Generates a deterministic hash for a given request model and engine version.

    Returns a tuple of (input_fingerprint, calculation_hash).
    """
    # Create a canonical JSON string representation of the request
    request_json = request_model.model_dump_json(sort_keys=True, round_trip=True)
    
    # The `json` library is used for a final pass with the custom serializer
    # to handle types that Pydantic might not format deterministically.
    parsed_json = json.loads(request_json)
    canonical_string = json.dumps(
        parsed_json,
        sort_keys=True,
        ensure_ascii=False,
        separators=(',', ':'),
        default=_json_default_serializer,
    )

    input_fingerprint = f"sha256:{hashlib.sha256(canonical_string.encode('utf-8')).hexdigest()}"
    
    # The calculation_hash includes the engine version
    full_string_to_hash = canonical_string + engine_version
    calculation_hash = f"sha256:{hashlib.sha256(full_string_to_hash.encode('utf-8')).hexdigest()}"
    
    return input_fingerprint, calculation_hash