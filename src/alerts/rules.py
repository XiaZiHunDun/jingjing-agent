"""
告警规则定义

定义告警级别、规则和状态。
"""

import os
from enum import Enum
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from datetime import datetime


class AlertLevel(Enum):
    """告警级别"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class AlertStatus(Enum):
    """告警状态"""
    OK = "ok"
    FIRING = "firing"
    RESOLVED = "resolved"


@dataclass
class AlertRule:
    """告警规则"""
    name: str
    description: str
    metric: str
    condition: str  # gt, lt, gte, lte, eq
    threshold: float
    level: AlertLevel = AlertLevel.WARNING
    duration_minutes: int = 5  # 持续多少分钟触发
    enabled: bool = True
    
    def evaluate(self, value: float) -> bool:
        """评估是否触发告警"""
        if self.condition == "gt":
            return value > self.threshold
        elif self.condition == "lt":
            return value < self.threshold
        elif self.condition == "gte":
            return value >= self.threshold
        elif self.condition == "lte":
            return value <= self.threshold
        elif self.condition == "eq":
            return value == self.threshold
        return False


@dataclass
class Alert:
    """告警实例"""
    rule_name: str
    level: AlertLevel
    status: AlertStatus
    message: str
    value: float
    threshold: float
    triggered_at: datetime = field(default_factory=datetime.now)
    resolved_at: Optional[datetime] = None
    notified: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule_name": self.rule_name,
            "level": self.level.value,
            "status": self.status.value,
            "message": self.message,
            "value": self.value,
            "threshold": self.threshold,
            "triggered_at": self.triggered_at.isoformat(),
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "notified": self.notified
        }


# 默认告警规则
DEFAULT_RULES: List[AlertRule] = [
    AlertRule(
        name="high_response_time",
        description="API 响应时间过高",
        metric="api_response_time_avg",
        condition="gt",
        threshold=float(os.getenv("ALERT_RESPONSE_TIME_MS", "5000")),
        level=AlertLevel.WARNING,
        duration_minutes=5
    ),
    AlertRule(
        name="high_error_rate",
        description="错误率过高",
        metric="api_error_rate",
        condition="gt",
        threshold=float(os.getenv("ALERT_ERROR_RATE", "0.1")),
        level=AlertLevel.CRITICAL,
        duration_minutes=5
    ),
    AlertRule(
        name="chat_timeout",
        description="对话响应超时",
        metric="chat_response_time_avg",
        condition="gt",
        threshold=float(os.getenv("ALERT_CHAT_TIMEOUT_MS", "30000")),
        level=AlertLevel.WARNING,
        duration_minutes=3
    ),
    AlertRule(
        name="service_down",
        description="服务不可用",
        metric="api_request_count",
        condition="eq",
        threshold=0,
        level=AlertLevel.CRITICAL,
        duration_minutes=2
    )
]
