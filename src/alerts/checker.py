"""
告警检查器

定期检查指标并触发告警。
"""

import os
import threading
import time
from typing import Dict, List, Optional
from datetime import datetime, timedelta

from src.utils.logger import app_logger
from src.metrics import get_metrics_client, metrics_enabled
from .rules import AlertRule, Alert, AlertLevel, AlertStatus, DEFAULT_RULES


class AlertChecker:
    """告警检查器"""
    
    def __init__(self, rules: Optional[List[AlertRule]] = None):
        self.rules = rules or DEFAULT_RULES
        self.active_alerts: Dict[str, Alert] = {}
        self.alert_history: List[Alert] = []
        self._lock = threading.Lock()
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._check_interval = int(os.getenv("ALERT_CHECK_INTERVAL", "60"))
        self._notifier = None
    
    def set_notifier(self, notifier):
        """设置通知器"""
        self._notifier = notifier
    
    def start(self):
        """启动告警检查"""
        if self._running:
            return
        
        self._running = True
        self._thread = threading.Thread(target=self._check_loop, daemon=True)
        self._thread.start()
        app_logger.info(f"[✓] 告警检查器已启动 (间隔: {self._check_interval}秒)")
    
    def stop(self):
        """停止告警检查"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
    
    def _check_loop(self):
        """检查循环"""
        while self._running:
            try:
                self.check_all_rules()
            except Exception as e:
                app_logger.error(f"告警检查异常: {str(e)}")
            
            time.sleep(self._check_interval)
    
    def check_all_rules(self):
        """检查所有规则"""
        if not metrics_enabled():
            return
        
        metrics = self._collect_metrics()
        
        for rule in self.rules:
            if not rule.enabled:
                continue
            
            metric_value = metrics.get(rule.metric)
            if metric_value is None:
                continue
            
            self._evaluate_rule(rule, metric_value)
    
    def _collect_metrics(self) -> Dict[str, float]:
        """收集当前指标"""
        metrics = {}
        
        client = get_metrics_client()
        if not client or not client.is_connected():
            return metrics
        
        try:
            # API 响应时间
            api_stats = client.query_api_stats(hours=1)
            metrics["api_response_time_avg"] = api_stats.get("avg_duration_ms", 0)
            metrics["api_request_count"] = api_stats.get("total", 0)
            
            # 错误率查询
            error_query = f'''
            from(bucket: "{client.bucket}")
            |> range(start: -1h)
            |> filter(fn: (r) => r._measurement == "api_requests")
            |> filter(fn: (r) => r._field == "success")
            '''
            results = client.query(error_query)
            
            total = len(results)
            errors = sum(1 for r in results if r.get("value") == 0)
            metrics["api_error_rate"] = errors / total if total > 0 else 0
            
            # 对话响应时间
            chat_query = f'''
            from(bucket: "{client.bucket}")
            |> range(start: -1h)
            |> filter(fn: (r) => r._measurement == "chat_metrics")
            |> filter(fn: (r) => r._field == "total_duration_ms")
            |> mean()
            '''
            chat_results = client.query(chat_query)
            if chat_results:
                metrics["chat_response_time_avg"] = chat_results[0].get("value", 0) or 0
            else:
                metrics["chat_response_time_avg"] = 0
                
        except Exception as e:
            app_logger.error(f"收集指标失败: {str(e)}")
        
        return metrics
    
    def _evaluate_rule(self, rule: AlertRule, value: float):
        """评估单个规则"""
        is_triggered = rule.evaluate(value)
        
        with self._lock:
            existing_alert = self.active_alerts.get(rule.name)
            
            if is_triggered:
                if existing_alert is None:
                    # 新告警
                    alert = Alert(
                        rule_name=rule.name,
                        level=rule.level,
                        status=AlertStatus.FIRING,
                        message=f"{rule.description}: 当前值 {value:.2f}, 阈值 {rule.threshold}",
                        value=value,
                        threshold=rule.threshold
                    )
                    self.active_alerts[rule.name] = alert
                    self.alert_history.append(alert)
                    
                    app_logger.warning(f"[告警触发] {rule.name}: {alert.message}")
                    
                    # 发送通知
                    if self._notifier and not alert.notified:
                        self._notifier.send_alert(alert)
                        alert.notified = True
            else:
                if existing_alert is not None:
                    # 告警恢复
                    existing_alert.status = AlertStatus.RESOLVED
                    existing_alert.resolved_at = datetime.now()
                    
                    app_logger.info(f"[告警恢复] {rule.name}: 已恢复正常")
                    
                    # 发送恢复通知
                    if self._notifier:
                        self._notifier.send_recovery(existing_alert)
                    
                    del self.active_alerts[rule.name]
    
    def get_active_alerts(self) -> List[Dict]:
        """获取当前活跃告警"""
        with self._lock:
            return [alert.to_dict() for alert in self.active_alerts.values()]
    
    def get_alert_history(self, limit: int = 100) -> List[Dict]:
        """获取告警历史"""
        with self._lock:
            return [alert.to_dict() for alert in self.alert_history[-limit:]]
    
    def get_rules(self) -> List[Dict]:
        """获取告警规则"""
        return [
            {
                "name": r.name,
                "description": r.description,
                "metric": r.metric,
                "condition": r.condition,
                "threshold": r.threshold,
                "level": r.level.value,
                "duration_minutes": r.duration_minutes,
                "enabled": r.enabled
            }
            for r in self.rules
        ]
    
    def update_rule(self, name: str, enabled: bool = None, threshold: float = None) -> bool:
        """更新告警规则"""
        for rule in self.rules:
            if rule.name == name:
                if enabled is not None:
                    rule.enabled = enabled
                if threshold is not None:
                    rule.threshold = threshold
                return True
        return False


_alert_checker: Optional[AlertChecker] = None


def get_alert_checker() -> AlertChecker:
    """获取全局告警检查器"""
    global _alert_checker
    
    if _alert_checker is None:
        _alert_checker = AlertChecker()
    
    return _alert_checker
