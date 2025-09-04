# common/enums.py
from enum import Enum


class Frequency(str, Enum):
    """Defines the supported frequency types for performance breakdowns."""
    DAILY = "daily"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"


class PeriodType(str, Enum):
    """Defines the supported period types for performance calculation."""
    MTD = "MTD"
    QTD = "QTD"
    YTD = "YTD"
    ITD = "ITD"
    Y1 = "Y1"
    Y3 = "Y3"
    Y5 = "Y5"
    EXPLICIT = "EXPLICIT"