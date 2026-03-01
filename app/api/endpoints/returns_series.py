from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Iterable

import pandas as pd
from fastapi import APIRouter, HTTPException, status

from app.models.returns_series import (
    CalendarPolicy,
    FillMethod,
    InputMode,
    MissingDataPolicy,
    ResolvedWindow,
    ReturnPoint,
    ReturnsDiagnostics,
    ReturnsFrequency,
    ReturnsMetadata,
    ReturnsProvenance,
    ReturnsRelativePeriod,
    ReturnsSeriesPayload,
    ReturnsSeriesRequest,
    ReturnsSeriesResponse,
    SeriesCoverage,
    SeriesGap,
    UpstreamSourceRef,
)
from app.observability import correlation_id_var, request_id_var, trace_id_var
from core.repro import generate_canonical_hash

router = APIRouter(tags=["Integration"])


def _period_start(as_of_date: date, period: ReturnsRelativePeriod, year: int | None) -> date:
    as_of = pd.Timestamp(as_of_date)
    if period == ReturnsRelativePeriod.MTD:
        return as_of.to_period("M").start_time.date()
    if period == ReturnsRelativePeriod.QTD:
        return as_of.to_period("Q").start_time.date()
    if period == ReturnsRelativePeriod.YTD:
        return as_of.to_period("Y").start_time.date()
    if period == ReturnsRelativePeriod.ONE_YEAR:
        return (as_of - pd.DateOffset(years=1) + pd.Timedelta(days=1)).date()
    if period == ReturnsRelativePeriod.THREE_YEAR:
        return (as_of - pd.DateOffset(years=3) + pd.Timedelta(days=1)).date()
    if period == ReturnsRelativePeriod.FIVE_YEAR:
        return (as_of - pd.DateOffset(years=5) + pd.Timedelta(days=1)).date()
    if period == ReturnsRelativePeriod.SI:
        return date(1900, 1, 1)
    if period == ReturnsRelativePeriod.YEAR:
        if year is None:
            raise ValueError("year is required when period=YEAR")
        return date(year, 1, 1)
    raise ValueError(f"Unsupported period: {period}")


def _resolve_window(request: ReturnsSeriesRequest) -> ResolvedWindow:
    if request.window.mode.value == "EXPLICIT":
        return ResolvedWindow(
            start_date=request.window.from_date,
            end_date=request.window.to_date,
            resolved_period_label=None,
        )
    if request.window.period is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "INVALID_REQUEST", "message": "window.period is required when mode=RELATIVE"},
        )
    start_date = _period_start(request.as_of_date, request.window.period, request.window.year)
    return ResolvedWindow(
        start_date=start_date,
        end_date=request.as_of_date,
        resolved_period_label=request.window.period.value,
    )


def _to_dataframe(points: Iterable[ReturnPoint], *, series_type: str) -> pd.DataFrame:
    data = [{"date": p.date, "return_value": Decimal(str(p.return_value))} for p in points]
    df = pd.DataFrame(data)
    if df.empty:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "INSUFFICIENT_DATA", "message": f"{series_type} series is empty."},
        )
    if df["date"].duplicated().any():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "INVALID_REQUEST", "message": f"{series_type} series contains duplicate dates."},
        )
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date")
    return df


def _filter_window(df: pd.DataFrame, *, resolved_window: ResolvedWindow) -> pd.DataFrame:
    mask = (df["date"].dt.date >= resolved_window.start_date) & (df["date"].dt.date <= resolved_window.end_date)
    window_df = df[mask].copy()
    if window_df.empty:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "INSUFFICIENT_DATA", "message": "No observations in resolved window."},
        )
    return window_df


def _resample_returns(df: pd.DataFrame, *, frequency: ReturnsFrequency) -> pd.DataFrame:
    if frequency == ReturnsFrequency.DAILY:
        return df
    indexed = df.set_index("date")
    if frequency == ReturnsFrequency.WEEKLY:
        grouped = indexed["return_value"].resample("W-FRI").apply(lambda x: (1 + x).prod() - 1)
    else:
        grouped = indexed["return_value"].resample("ME").apply(lambda x: (1 + x).prod() - 1)
    out = grouped.dropna().reset_index()
    return out


def _date_range_count(
    resolved_window: ResolvedWindow, *, frequency: ReturnsFrequency, calendar_policy: CalendarPolicy
) -> int:
    start = pd.Timestamp(resolved_window.start_date)
    end = pd.Timestamp(resolved_window.end_date)
    if frequency == ReturnsFrequency.DAILY:
        if calendar_policy == CalendarPolicy.CALENDAR:
            return len(pd.date_range(start, end, freq="D"))
        return len(pd.bdate_range(start, end))
    if frequency == ReturnsFrequency.WEEKLY:
        return len(pd.date_range(start, end, freq="W-FRI"))
    return len(pd.date_range(start, end, freq="ME"))


def _detect_gaps(df: pd.DataFrame, *, frequency: ReturnsFrequency, series_type: str) -> list[SeriesGap]:
    if len(df) < 2:
        return []
    expected_days = 1 if frequency == ReturnsFrequency.DAILY else (7 if frequency == ReturnsFrequency.WEEKLY else 31)
    gaps: list[SeriesGap] = []
    dates = list(df["date"].dt.date)
    for prev, curr in zip(dates, dates[1:]):
        delta = (curr - prev).days
        if delta > expected_days + 1:
            gaps.append(
                SeriesGap(
                    series_type=series_type,
                    from_date=prev,
                    to_date=curr,
                    gap_days=delta - 1,
                )
            )
    return gaps


def _points_from_df(df: pd.DataFrame) -> list[ReturnPoint]:
    out: list[ReturnPoint] = []
    for _, row in df.iterrows():
        value = Decimal(str(row["return_value"])).quantize(Decimal("0.000000000001"))
        out.append(
            ReturnPoint(
                date=row["date"].date(),
                return_value=value,
            )
        )
    return out


@router.post(
    "/returns/series",
    response_model=ReturnsSeriesResponse,
    summary="Get canonical return series for downstream analytics",
    description=(
        "Returns canonical portfolio/benchmark/risk-free return time series for stateful analytics consumers. "
        "Current implementation supports inline_bundle source mode; core_api_ref wiring is reserved for future integration."
    ),
)
async def get_returns_series(request: ReturnsSeriesRequest) -> ReturnsSeriesResponse:
    if request.source.input_mode == InputMode.CORE_API_REF:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "SOURCE_UNAVAILABLE",
                "message": "core_api_ref source mode is not available yet. Use inline_bundle until lotus-core integration is enabled.",
            },
        )

    resolved_window = _resolve_window(request)
    bundle = request.source.inline_bundle
    if bundle is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "INVALID_REQUEST", "message": "source.inline_bundle is required in inline_bundle mode."},
        )

    portfolio_df = _resample_returns(
        _filter_window(
            _to_dataframe(bundle.portfolio_returns, series_type="portfolio"), resolved_window=resolved_window
        ),
        frequency=request.frequency,
    )
    benchmark_df = None
    risk_free_df = None

    if request.series_selection.include_benchmark:
        benchmark_df = _resample_returns(
            _filter_window(
                _to_dataframe(bundle.benchmark_returns or [], series_type="benchmark"),
                resolved_window=resolved_window,
            ),
            frequency=request.frequency,
        )
    if request.series_selection.include_risk_free:
        risk_free_df = _resample_returns(
            _filter_window(
                _to_dataframe(bundle.risk_free_returns or [], series_type="risk_free"),
                resolved_window=resolved_window,
            ),
            frequency=request.frequency,
        )

    if request.data_policy.missing_data_policy == MissingDataPolicy.STRICT_INTERSECTION:
        common_dates = set(portfolio_df["date"])
        if benchmark_df is not None:
            common_dates &= set(benchmark_df["date"])
        if risk_free_df is not None:
            common_dates &= set(risk_free_df["date"])
        if not common_dates:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={"code": "INSUFFICIENT_DATA", "message": "No overlapping dates across selected series."},
            )
        portfolio_df = portfolio_df[portfolio_df["date"].isin(common_dates)].sort_values("date")
        if benchmark_df is not None:
            benchmark_df = benchmark_df[benchmark_df["date"].isin(common_dates)].sort_values("date")
        if risk_free_df is not None:
            risk_free_df = risk_free_df[risk_free_df["date"].isin(common_dates)].sort_values("date")

    if request.data_policy.fill_method == FillMethod.FORWARD_FILL:
        if benchmark_df is not None:
            benchmark_df = benchmark_df.set_index("date").reindex(portfolio_df["date"]).ffill().reset_index()
        if risk_free_df is not None:
            risk_free_df = risk_free_df.set_index("date").reindex(portfolio_df["date"]).ffill().reset_index()
    elif request.data_policy.fill_method == FillMethod.ZERO_FILL:
        if benchmark_df is not None:
            benchmark_df = benchmark_df.set_index("date").reindex(portfolio_df["date"]).fillna(0.0).reset_index()
        if risk_free_df is not None:
            risk_free_df = risk_free_df.set_index("date").reindex(portfolio_df["date"]).fillna(0.0).reset_index()

    requested_points = _date_range_count(
        resolved_window, frequency=request.frequency, calendar_policy=request.data_policy.calendar_policy
    )
    returned_points = len(portfolio_df)
    missing_points = max(requested_points - returned_points, 0)
    if request.data_policy.missing_data_policy == MissingDataPolicy.FAIL_FAST and missing_points > 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "INSUFFICIENT_DATA",
                "message": f"Missing {missing_points} required points under FAIL_FAST policy.",
            },
        )

    warnings: list[str] = []
    if request.data_policy.calendar_policy == CalendarPolicy.MARKET:
        warnings.append("MARKET calendar policy currently uses business-day approximation.")

    input_fingerprint, calculation_hash = generate_canonical_hash(request, "returns-series-v1")
    diagnostics = ReturnsDiagnostics(
        coverage=SeriesCoverage(
            requested_points=requested_points,
            returned_points=returned_points,
            missing_points=missing_points,
            coverage_ratio=Decimal(str(round(returned_points / requested_points, 8)))
            if requested_points
            else Decimal("1"),
        ),
        gaps=[
            *_detect_gaps(portfolio_df, frequency=request.frequency, series_type="portfolio"),
            *(
                _detect_gaps(benchmark_df, frequency=request.frequency, series_type="benchmark")
                if benchmark_df is not None
                else []
            ),
            *(
                _detect_gaps(risk_free_df, frequency=request.frequency, series_type="risk_free")
                if risk_free_df is not None
                else []
            ),
        ],
        policy_applied=request.data_policy,
        warnings=warnings,
    )

    return ReturnsSeriesResponse(
        portfolio_id=request.portfolio_id,
        as_of_date=request.as_of_date,
        frequency=request.frequency,
        metric_basis=request.metric_basis,
        resolved_window=resolved_window,
        series=ReturnsSeriesPayload(
            portfolio_returns=_points_from_df(portfolio_df),
            benchmark_returns=_points_from_df(benchmark_df) if benchmark_df is not None else None,
            risk_free_returns=_points_from_df(risk_free_df) if risk_free_df is not None else None,
        ),
        provenance=ReturnsProvenance(
            input_mode=request.source.input_mode,
            upstream_sources=[
                UpstreamSourceRef(
                    service="inline_bundle",
                    endpoint="request.source.inline_bundle",
                    contract_version="v1",
                )
            ],
            input_fingerprint=input_fingerprint,
            calculation_hash=calculation_hash,
        ),
        diagnostics=diagnostics,
        metadata=ReturnsMetadata(
            generated_at=datetime.now(UTC),
            correlation_id=correlation_id_var.get() or None,
            request_id=request_id_var.get() or None,
            trace_id=trace_id_var.get() or None,
        ),
    )
