# common/enums.py
from enum import Enum


class Frequency(str, Enum):
    """Defines the supported frequency types for performance breakdowns."""

    DAILY = "daily"
    WEEKLY = "weekly"
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


class AttributionMode(str, Enum):
    """Defines the input modes for the attribution engine."""

    BY_INSTRUMENT = "by_instrument"
    BY_GROUP = "by_group"


class AttributionModel(str, Enum):
    """Defines the supported Brinson-style attribution models."""

    BRINSON_FACHLER = "BF"
    BRINSON_HOOD_BEEBOWER = "BHB"


class LinkingMethod(str, Enum):
    """Defines the supported methods for linking multi-period attribution effects."""

    CARINO = "carino"
    LOGARITHMIC = "log"
    NONE = "none"


class WeightingScheme(str, Enum):
    """Defines the supported weighting schemes for contribution analysis."""

    BOD = "BOD"
    AVG_CAPITAL = "AVG_CAPITAL"
    TWR_DENOM = "TWR_DENOM"