from datetime import date
from typing import Any

import httpx

from app.observability import propagation_headers
from app.services.http_resilience import post_with_retry, response_payload


class PasInputService:
    def __init__(
        self,
        base_url: str,
        timeout_seconds: float,
        max_retries: int = 2,
        retry_backoff_seconds: float = 0.2,
    ):
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout_seconds
        self._max_retries = max_retries
        self._retry_backoff_seconds = retry_backoff_seconds

    async def get_core_snapshot(
        self,
        portfolio_id: str,
        as_of_date: date,
        include_sections: list[str],
        consumer_system: str,
    ) -> tuple[int, dict[str, Any]]:
        url = f"{self._base_url}/integration/portfolios/{portfolio_id}/core-snapshot"
        payload = {
            "asOfDate": str(as_of_date),
            "includeSections": include_sections,
            "consumerSystem": consumer_system,
        }
        headers = propagation_headers()
        return await post_with_retry(
            url=url,
            timeout_seconds=self._timeout,
            json_body=payload,
            headers=headers,
            max_retries=self._max_retries,
            backoff_seconds=self._retry_backoff_seconds,
        )

    def _response_payload(self, response: httpx.Response) -> dict[str, Any]:
        return response_payload(response)

    async def get_performance_input(
        self,
        portfolio_id: str,
        as_of_date: date,
        lookback_days: int,
        consumer_system: str,
    ) -> tuple[int, dict[str, Any]]:
        url = f"{self._base_url}/integration/portfolios/{portfolio_id}/performance-input"
        payload = {
            "asOfDate": str(as_of_date),
            "lookbackDays": lookback_days,
            "consumerSystem": consumer_system,
        }
        headers = propagation_headers()
        return await post_with_retry(
            url=url,
            timeout_seconds=self._timeout,
            json_body=payload,
            headers=headers,
            max_retries=self._max_retries,
            backoff_seconds=self._retry_backoff_seconds,
        )

    async def get_positions_analytics(
        self,
        portfolio_id: str,
        as_of_date: date,
        sections: list[str],
        performance_periods: list[str] | None,
    ) -> tuple[int, dict[str, Any]]:
        url = f"{self._base_url}/portfolios/{portfolio_id}/positions-analytics"
        payload: dict[str, Any] = {"asOfDate": str(as_of_date), "sections": sections}
        if performance_periods:
            payload["performanceOptions"] = {"periods": performance_periods}
        headers = propagation_headers()
        return await post_with_retry(
            url=url,
            timeout_seconds=self._timeout,
            json_body=payload,
            headers=headers,
            max_retries=self._max_retries,
            backoff_seconds=self._retry_backoff_seconds,
        )
