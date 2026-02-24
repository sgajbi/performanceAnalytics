from datetime import date
from typing import Any

import httpx

from app.observability import propagation_headers


class PasSnapshotService:
    def __init__(self, base_url: str, timeout_seconds: float):
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout_seconds

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
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.post(url, json=payload, headers=headers)
            return response.status_code, self._response_payload(response)

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
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.post(url, json=payload, headers=headers)
            return response.status_code, self._response_payload(response)

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
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.post(url, json=payload, headers=headers)
            return response.status_code, self._response_payload(response)

    def _response_payload(self, response: httpx.Response) -> dict[str, Any]:
        try:
            payload = response.json()
        except ValueError:
            payload = {"detail": response.text}
        if isinstance(payload, dict):
            return payload
        return {"detail": payload}
