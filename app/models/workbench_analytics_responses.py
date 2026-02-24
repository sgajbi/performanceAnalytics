from pydantic import BaseModel, Field


class WorkbenchAnalyticsBucket(BaseModel):
    bucket_key: str = Field(alias="bucketKey")
    bucket_label: str = Field(alias="bucketLabel")
    current_quantity: float = Field(alias="currentQuantity")
    proposed_quantity: float = Field(alias="proposedQuantity")
    delta_quantity: float = Field(alias="deltaQuantity")
    current_weight_pct: float = Field(alias="currentWeightPct")
    proposed_weight_pct: float = Field(alias="proposedWeightPct")

    model_config = {"populate_by_name": True}


class WorkbenchTopChange(BaseModel):
    security_id: str = Field(alias="securityId")
    instrument_name: str = Field(alias="instrumentName")
    delta_quantity: float = Field(alias="deltaQuantity")
    direction: str

    model_config = {"populate_by_name": True}


class WorkbenchRiskProxy(BaseModel):
    hhi_current: float = Field(alias="hhiCurrent")
    hhi_proposed: float = Field(alias="hhiProposed")
    hhi_delta: float = Field(alias="hhiDelta")

    model_config = {"populate_by_name": True}


class WorkbenchAnalyticsResponse(BaseModel):
    source_mode: str = "pa_calc"
    source_service: str = Field("performance-analytics", alias="sourceService")
    portfolio_id: str = Field(alias="portfolioId")
    period: str
    group_by: str = Field(alias="groupBy")
    benchmark_code: str = Field(alias="benchmarkCode")
    portfolio_return_pct: float | None = Field(default=None, alias="portfolioReturnPct")
    benchmark_return_pct: float | None = Field(default=None, alias="benchmarkReturnPct")
    active_return_pct: float | None = Field(default=None, alias="activeReturnPct")
    allocation_buckets: list[WorkbenchAnalyticsBucket] = Field(default_factory=list, alias="allocationBuckets")
    top_changes: list[WorkbenchTopChange] = Field(default_factory=list, alias="topChanges")
    risk_proxy: WorkbenchRiskProxy = Field(alias="riskProxy")

    model_config = {"populate_by_name": True}
