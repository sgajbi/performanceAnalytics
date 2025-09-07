# Performance Analytics — Overview

## Purpose
This service provides portfolio performance analytics with four primary capabilities:
- **TWR** (Time-Weighted Return)
- **MWR** (Money-Weighted Return / IRR)
- **Contribution** (security/group return contribution with optional smoothing)
- **Attribution** (Brinson-style active return decomposition)

It exposes HTTP APIs, enforces consistent snake_case payloads, and returns results with diagnostics suitable for audit, QA, and client reporting.

## Audience
- **Developers**: integrate APIs, extend engines, ensure reliability and tests.
- **Business/Quants**: understand methodology and configuration options.
- **Product/Support/Ops**: operate, troubleshoot, and validate results end‑to‑end.

## Design Principles
- **Deterministic & auditable**: inputs → outputs with reproducible settings.
- **Booking/location agnostic**: consistent schema across portfolios, instruments, and books.
- **Configurable**: explicit engine flags (precision, rounding, periodization, linking).
- **Separation of concerns**: API adapter ↔ engine calculators ↔ common utilities.
- **Observability-first**: diagnostics and notes shipped with every response.

## Surface Area
- REST endpoints under `/performance/*`.
- Request/response models in `app/models` (snake_case only).
- Engines in `engine/*` for reusable calculations.
- Common core in `core/*` for periods, annualization, envelopes, errors.

## Quickstart
```bash
# 1) Create and activate virtualenv (example)
python -m venv .venv && . .venv/bin/activate  # Windows: .venv\Scripts\activate

# 2) Install
pip install -U pip
pip install -e .

# 3) Run (adjust if using uvicorn/gunicorn wrapper)
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# 4) Health check
curl -s http://localhost:8000/health
```

## Choose the Right API
- **TWR** → manager skill/time-series comparability; insensitive to cash flow timing.
- **MWR** → investor experience; sensitive to cash flow amounts and timing.
- **Contribution** → which assets/groups drove the portfolio return.
- **Attribution** → why the portfolio out/under-performed a benchmark (allocation/selection/interaction).

## Directory Map (high level)
```
app/
  api/endpoints/           # HTTP routes
  models/                  # Pydantic models (req/resp)
core/
  periods.py               # Period resolution & calendars
  annualize.py             # Annualization utilities
  envelope.py              # Response wrapper, meta/diagnostics
engine/
  ror.py                   # TWR return construction
  mwr.py                   # XIRR/Dietz family
  contribution.py          # Contribution & smoothing
  attribution.py           # Brinson effects & linking
docs/
  guides/                  # You are here
  examples/                # JSON requests & captured responses
```

## Response Envelope (standard)
Every endpoint returns:
```json
{
  "data": { "...endpoint specific..." },
  "meta": {
    "request_id": "uuid",
    "as_of": "2025-09-07",
    "config": { "precision_mode": "DECIMAL_STRICT", "rounding": 6 }
  },
  "diagnostics": {
    "notes": ["string"],
    "counts": { "rows": 123, "positions": 12 },
    "residuals": { "bp_difference": 0.1 }
  }
}
```

## Precision & Rounding
- Modes: `FLOAT64` (faster) and `DECIMAL_STRICT` (deterministic).
- Default rounding: 6–8 decimals for rates/weights; configurable per endpoint.

## Non‑Goals
- No inference of booking rules from raw bank data.
- No portfolio accounting; inputs must already be pre‑accounted MV and CF series.

## Next Steps
- Read **Data Model** for field names & enums.
- See **API Reference** for contracts and examples.
- Dive into **Methodology** guides for TWR, MWR, Contribution, Attribution.
