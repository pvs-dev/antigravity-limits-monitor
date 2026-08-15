import math
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any


@dataclass
class ModelQuota:
    label: str
    remaining_fraction: float  # 0.0 to 1.0
    reset_time: Optional[str] = None  # ISO timestamp
    model_id: Optional[str] = None
    tag_title: Optional[str] = None
    is_recommended: bool = False

    @property
    def percentage(self) -> int:
        if self.remaining_fraction is None:
            return 0
        return int(round(self.remaining_fraction * 100))

    @property
    def reset_countdown(self) -> str:
        """Returns human-readable countdown string e.g. '42m', '1h 15m' or 'Сброшен'."""
        if not self.reset_time:
            return ""
        try:
            iso_str = self.reset_time.replace("Z", "+00:00")
            dt_reset = datetime.fromisoformat(iso_str)
            now = datetime.now(timezone.utc)
            delta = dt_reset - now
            total_seconds = int(delta.total_seconds())

            if total_seconds <= 0:
                return "сброшен"

            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60

            if hours > 0:
                return f"{hours}ч {minutes}м"
            return f"{minutes}м"
        except Exception:
            return ""


@dataclass
class PlanStatus:
    plan_name: str = "Unknown"
    teams_tier: str = ""
    monthly_prompt_credits: int = 0
    monthly_flow_credits: int = 0
    available_prompt_credits: int = 0
    available_flow_credits: int = 0


@dataclass
class AccountStatus:
    is_connected: bool = False
    name: str = ""
    email: str = ""
    plan: PlanStatus = field(default_factory=PlanStatus)
    models: List[ModelQuota] = field(default_factory=list)
    last_updated: Optional[datetime] = None
    error_message: Optional[str] = None
    pid: Optional[int] = None
    port: Optional[int] = None
    csrf_token: Optional[str] = None
