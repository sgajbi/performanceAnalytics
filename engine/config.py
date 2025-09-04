# engine/config.py
from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Literal, Optional


class PrecisionMode(str, Enum):
    """
    Defines the calculation precision modes for the engine.
    - FLOAT64: Uses standard NumPy float64 for high performance.
    - DECIMAL_STRICT: Uses Python's Decimal type for auditable precision.
    """

    FLOAT64 = "float64"
    DECIMAL_STRICT = "decimal_strict"


@dataclass(frozen=True)
class FeatureFlags:
    """
    Container for feature flags to enable/disable experimental or alternative logic.
    """

    use_nip_v2_rule: bool = False


@dataclass(frozen=True)
class EngineConfig:
    """
    A comprehensive, immutable configuration object for the performance engine.
    This object encapsulates all settings required for a calculation run.
    """

    performance_start_date: date
    report_end_date: date
    metric_basis: Literal["NET", "GROSS"]
    period_type: Literal["MTD", "QTD", "YTD", "Explicit"]
    report_start_date: Optional[date] = None
    precision_mode: PrecisionMode = PrecisionMode.FLOAT64
    feature_flags: FeatureFlags = field(default_factory=FeatureFlags)