# Performance Analytics — Overview (Implementation-Aligned)

This service exposes portfolio analytics via FastAPI endpoints backed by an internal engine. The implementation is aligned with the files in your snapshot:

- API: `app/api/endpoints/performance.py`
- Requests/Responses: `app/models/*.py`
- Engine: `engine/*.py` (ror, mwr, contribution, attribution, breakdown, compute, rules, schema)
- Core/Envelope: `core/envelope.py`, `core/periods.py`
- Common Enums: `common/enums.py`
- Adapters: `adapters/api_adapter.py`

## Capabilities
- **TWR**: geometric time‑weighted returns with sign‑aware long/short compounding, resets (NCTRL_1..4), and NIP handling.
- **MWR**: XIRR with convergence reporting and automatic fallback to (Modified) Dietz.
- **Contribution**: per‑position/group contributions with BOP‑style weights, Carino smoothing, and residual distribution.
- **Attribution**: Brinson‑Fachler / Brinson‑Hood‑Beebower with top‑down linking to geometric active return.

## Response Envelope (as implemented)
All response models inherit from `core.envelope.BaseResponse` and include:
- `meta: Meta` → `calculation_id`, `engine_version`, `precision_mode`, `annualization`, `calendar`, `periods`
- `diagnostics: Diagnostics` → `nip_days`, `reset_days`, `effective_period_start`, `notes[]`
- `audit: Audit` → `sum_of_parts_vs_total_bp`, `residual_applied_bp`, `counts{}`

Endpoints also return endpoint‑specific `data` structures (see API Reference).

## Precision & Rounding
- `precision_mode`: `"FLOAT64"` (numpy/pandas) or `"DECIMAL_STRICT"` (decimal objects) as surfaced in requests.
- `rounding_precision`: integer; applied on float path at the end of `run_calculations` (Decimal path remains exact until emission).

## Periods & Calendars
- `calendar.type`: `"BUSINESS"` or `"NATURAL"`; `trading_calendar` default `"NYSE"`.
- `periods.type`: one of `"YTD" | "QTD" | "MTD" | "WTD" | "Y1" | "Y3" | "Y5" | "ITD" | "ROLLING" | "EXPLICIT"`.
  - `EXPLICIT` requires `periods.explicit = {start, end, frequency}`.
  - `ROLLING` requires `periods.rolling = {months|days}`.
- Resolution is performed by `core.periods.resolve_period` with strict validation (raises `APIBadRequestError` on invalid definitions).

## Resets, NIP, and Signs
- **NIP**: computed via rules in `engine.rules` (V2 rule: `begin_mv + bod_cf == 0` and `end_mv + eod_cf == 0`).
- **Resets**: initial reset rules + NCTRL‑4; legs zeroed on reset dates; blocks restart the next day.
- **Sign**: derived per day; emits `+1` long / `-1` short; affects compounding legs and `long_short` label.

See: `docs/guides/rules_and_diagnostics.md` and the implementation‑faithful methodology docs.
