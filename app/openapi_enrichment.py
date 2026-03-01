"""OpenAPI enrichment helpers for RFC-0067 documentation completeness."""

from __future__ import annotations

import re
from typing import Any

ALLOWED_METHODS = {"get", "post", "put", "patch", "delete"}

EXAMPLE_BY_KEY = {
    "portfolio_id": "DEMO_DPM_EUR_001",
    "session_id": "SIM_0001",
    "calculation_id": "CALC_0001",
    "request_id": "REQ_0001",
    "correlation_id": "corr_123456789abc",
    "trace_id": "0123456789abcdef0123456789abcdef",
    "tenant_id": "default",
    "consumer_system": "lotus-gateway",
    "policy_version": "tenant-default-v1",
    "contract_version": "v1",
    "source_service": "lotus-performance",
    "as_of_date": "2026-02-27",
    "report_start_date": "2026-01-01",
    "report_end_date": "2026-01-31",
    "generated_at": "2026-02-27T10:30:00Z",
    "status": "ok",
    "currency": "USD",
    "base_currency": "USD",
}


def _to_snake_case(value: str) -> str:
    transformed = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", value)
    transformed = transformed.replace("-", "_").replace(" ", "_").replace(".", "_")
    return transformed.strip("_").lower()


def _humanize(value: str) -> str:
    return _to_snake_case(value).replace("_", " ").strip()


def _infer_example(prop_name: str, prop_schema: dict[str, Any]) -> Any:
    key = _to_snake_case(prop_name)
    if key in EXAMPLE_BY_KEY:
        return EXAMPLE_BY_KEY[key]

    enum_values = prop_schema.get("enum")
    if isinstance(enum_values, list) and enum_values:
        return enum_values[0]

    schema_type = prop_schema.get("type")
    schema_format = prop_schema.get("format")
    if schema_type == "array":
        item_schema = prop_schema.get("items", {})
        if isinstance(item_schema, dict):
            return [_infer_example(f"{prop_name}_item", item_schema)]
        return ["VALUE"]
    if schema_type == "object":
        return {"key": "value"}
    if schema_type == "boolean":
        return True
    if schema_type == "integer":
        return 1
    if schema_type == "number":
        return 0.1234
    if schema_format == "date":
        return "2026-02-27"
    if schema_format == "date-time":
        return "2026-02-27T10:30:00Z"
    if key.endswith("_id"):
        return f"{key[:-3].upper()}_001"
    if "date" in key:
        return "2026-02-27"
    if "time" in key or "timestamp" in key:
        return "2026-02-27T10:30:00Z"
    if "currency" in key:
        return "USD"
    return f"example_{key}"


def _infer_description(model_name: str, prop_name: str, prop_schema: dict[str, Any]) -> str:
    key = _to_snake_case(prop_name)
    text = _humanize(prop_name)
    if key.endswith("_id"):
        entity = key[: -len("_id")].replace("_", " ")
        return f"Unique {entity} identifier."
    if prop_schema.get("format") == "date":
        return f"Business date for {text}."
    if prop_schema.get("format") == "date-time":
        return f"Timestamp for {text}."
    if "currency" in key:
        return f"ISO currency code for {text}."
    if "return" in key or "rate" in key or "performance" in key:
        return f"Performance metric value for {text}."
    if "amount" in key or "value" in key:
        return f"Monetary value for {text}."
    return f"{_humanize(model_name)} field: {text}."


def _ensure_operation_documentation(schema: dict[str, Any]) -> None:
    paths = schema.get("paths", {})
    if not isinstance(paths, dict):
        return
    for path, methods in paths.items():
        if not isinstance(methods, dict):
            continue
        for method, operation in methods.items():
            if method.lower() not in ALLOWED_METHODS:
                continue
            if not isinstance(operation, dict):
                continue
            if not operation.get("summary"):
                operation["summary"] = f"{method.upper()} {path}"
            if not operation.get("description"):
                operation["description"] = f"{method.upper()} operation for {path} in lotus-performance."
            if not operation.get("tags"):
                if path.startswith("/health"):
                    operation["tags"] = ["Health"]
                elif path == "/metrics":
                    operation["tags"] = ["Monitoring"]
                else:
                    segment = path.strip("/").split("/", 1)[0] or "default"
                    operation["tags"] = [segment.replace("-", " ").title()]
            responses = operation.get("responses")
            if isinstance(responses, dict):
                has_error = any(
                    str(code).startswith("4") or str(code).startswith("5") or str(code) == "default"
                    for code in responses
                )
                if not has_error:
                    responses["default"] = {"description": "Unexpected error response."}


def _ensure_schema_documentation(schema: dict[str, Any]) -> None:
    components = schema.get("components", {})
    if not isinstance(components, dict):
        return
    schemas = components.get("schemas", {})
    if not isinstance(schemas, dict):
        return
    for model_name, model_schema in schemas.items():
        if not isinstance(model_schema, dict):
            continue
        properties = model_schema.get("properties", {})
        if not isinstance(properties, dict):
            continue
        for prop_name, prop_schema in properties.items():
            if not isinstance(prop_schema, dict):
                continue
            if not prop_schema.get("description"):
                prop_schema["description"] = _infer_description(model_name, prop_name, prop_schema)
            if "example" not in prop_schema and "examples" not in prop_schema:
                prop_schema["example"] = _infer_example(prop_name, prop_schema)


def enrich_openapi_schema(schema: dict[str, Any]) -> dict[str, Any]:
    """Mutates OpenAPI schema to meet RFC-0067 metadata minimums."""
    _ensure_operation_documentation(schema)
    _ensure_schema_documentation(schema)
    return schema
