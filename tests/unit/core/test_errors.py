# tests/unit/core/test_errors.py
import pytest
from fastapi import status
from core.errors import APIBadRequestError, APIUnprocessableEntityError, APIConflictError


def test_api_bad_request_error():
    """Tests the APIBadRequestError custom exception."""
    try:
        raise APIBadRequestError("Invalid field value")
    except APIBadRequestError as e:
        assert e.status_code == status.HTTP_400_BAD_REQUEST
        assert e.detail == "Invalid field value"


def test_api_unprocessable_entity_error():
    """Tests the APIUnprocessableEntityError custom exception."""
    try:
        raise APIUnprocessableEntityError("Calculation failed to converge")
    except APIUnprocessableEntityError as e:
        assert e.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert e.detail == "Calculation failed to converge"


def test_api_conflict_error():
    """Tests the APIConflictError custom exception."""
    try:
        raise APIConflictError("Resource already exists")
    except APIConflictError as e:
        assert e.status_code == status.HTTP_409_CONFLICT
        assert e.detail == "Resource already exists"