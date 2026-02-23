# core/repro.py
import hashlib
import json

from pydantic import BaseModel


def generate_canonical_hash(request_model: BaseModel, engine_version: str) -> tuple[str, str]:
    """
    Generates a deterministic hash for a given request model and engine version.

    Returns a tuple of (input_fingerprint, calculation_hash).
    """
    # For Pydantic V2, dump the model to a dictionary, letting Pydantic's 'json'
    # mode handle serialization of special types like dates, UUIDs, and Decimals.
    request_dict = request_model.model_dump(mode="json")

    # Use the standard json library to create a canonical string with sorted keys.
    canonical_string = json.dumps(request_dict, sort_keys=True, ensure_ascii=False, separators=(",", ":"))

    input_fingerprint = f"sha256:{hashlib.sha256(canonical_string.encode('utf-8')).hexdigest()}"

    # The calculation_hash includes the engine version
    full_string_to_hash = canonical_string + engine_version
    calculation_hash = f"sha256:{hashlib.sha256(full_string_to_hash.encode('utf-8')).hexdigest()}"

    return input_fingerprint, calculation_hash
