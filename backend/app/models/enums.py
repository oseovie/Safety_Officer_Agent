from enum import StrEnum


class RiskLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RecordStatus(StrEnum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    CLOSED = "closed"
    OVERDUE = "overdue"


class IncidentSeverity(StrEnum):
    NEAR_MISS = "near_miss"
    FIRST_AID = "first_aid"
    MEDICAL = "medical"
    LOST_TIME = "lost_time"
    FATALITY = "fatality"
