import os
from datetime import UTC, date, datetime
from typing import Literal

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

router = APIRouter()

ConsumerSystem = Literal["BFF", "PA", "DPM", "UI", "UNKNOWN"]


class FeatureCapability(BaseModel):
    key: str = Field(description="Canonical feature key.")
    enabled: bool = Field(description="Whether this feature is enabled.")
    owner_service: str = Field(description="Owning service for this feature.")
    description: str = Field(description="Human-readable capability summary.")


class WorkflowCapability(BaseModel):
    workflow_key: str = Field(description="Workflow key for feature orchestration.")
    enabled: bool = Field(description="Whether workflow is enabled.")
    required_features: list[str] = Field(
        default_factory=list,
        description="Feature keys required for this workflow.",
    )


class IntegrationCapabilitiesResponse(BaseModel):
    contract_version: str = Field(alias="contractVersion")
    source_service: str = Field(alias="sourceService")
    consumer_system: ConsumerSystem = Field(alias="consumerSystem")
    tenant_id: str = Field(alias="tenantId")
    generated_at: datetime = Field(alias="generatedAt")
    as_of_date: date = Field(alias="asOfDate")
    policy_version: str = Field(alias="policyVersion")
    supported_input_modes: list[str] = Field(alias="supportedInputModes")
    features: list[FeatureCapability]
    workflows: list[WorkflowCapability]

    model_config = {"populate_by_name": True}


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@router.get(
    "/capabilities",
    response_model=IntegrationCapabilitiesResponse,
    summary="Get PA Integration Capabilities",
    description=("Returns backend-governed PA capability/workflow controls for BFF, PAS, and DPM integration."),
)
async def get_integration_capabilities(
    consumer_system: ConsumerSystem = Query("BFF", alias="consumerSystem"),
    tenant_id: str = Query("default", alias="tenantId"),
) -> IntegrationCapabilitiesResponse:
    twr_enabled = _env_bool("PA_CAP_TWR_ENABLED", True)
    mwr_enabled = _env_bool("PA_CAP_MWR_ENABLED", True)
    contribution_enabled = _env_bool("PA_CAP_CONTRIBUTION_ENABLED", True)
    attribution_enabled = _env_bool("PA_CAP_ATTRIBUTION_ENABLED", True)

    features = [
        FeatureCapability(
            key="pa.analytics.twr",
            enabled=twr_enabled,
            owner_service="PA",
            description="Time-weighted return analytics APIs.",
        ),
        FeatureCapability(
            key="pa.analytics.mwr",
            enabled=mwr_enabled,
            owner_service="PA",
            description="Money-weighted return analytics APIs.",
        ),
        FeatureCapability(
            key="pa.analytics.contribution",
            enabled=contribution_enabled,
            owner_service="PA",
            description="Contribution analytics APIs.",
        ),
        FeatureCapability(
            key="pa.analytics.attribution",
            enabled=attribution_enabled,
            owner_service="PA",
            description="Attribution analytics APIs.",
        ),
    ]

    workflows = [
        WorkflowCapability(
            workflow_key="performance_snapshot",
            enabled=twr_enabled and mwr_enabled,
            required_features=["pa.analytics.twr", "pa.analytics.mwr"],
        ),
        WorkflowCapability(
            workflow_key="performance_explainability",
            enabled=contribution_enabled and attribution_enabled,
            required_features=["pa.analytics.contribution", "pa.analytics.attribution"],
        ),
    ]

    return IntegrationCapabilitiesResponse(
        contractVersion="v1",
        sourceService="performance-analytics",
        consumerSystem=consumer_system,
        tenantId=tenant_id,
        generatedAt=datetime.now(UTC),
        asOfDate=date.today(),
        policyVersion=os.getenv("PA_POLICY_VERSION", "tenant-default-v1"),
        supportedInputModes=["pas_ref", "inline_bundle"],
        features=features,
        workflows=workflows,
    )
