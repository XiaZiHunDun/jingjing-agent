"""
告警 API 路由

提供告警管理和查询接口。
"""

from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from api.auth import verify_api_key
from src.alerts import get_alert_checker, get_notifier


router = APIRouter(prefix="/api/alerts", tags=["告警管理"])


class AlertRuleUpdate(BaseModel):
    """告警规则更新"""
    enabled: Optional[bool] = None
    threshold: Optional[float] = None


class AlertResponse(BaseModel):
    """告警响应"""
    rule_name: str
    level: str
    status: str
    message: str
    value: float
    threshold: float
    triggered_at: str
    resolved_at: Optional[str] = None
    notified: bool


class RuleResponse(BaseModel):
    """规则响应"""
    name: str
    description: str
    metric: str
    condition: str
    threshold: float
    level: str
    duration_minutes: int
    enabled: bool


@router.get("/active", response_model=List[AlertResponse])
async def get_active_alerts(
    api_key: Optional[str] = Depends(verify_api_key)
):
    """
    获取当前活跃告警
    
    返回所有正在触发的告警列表。
    """
    checker = get_alert_checker()
    return checker.get_active_alerts()


@router.get("/history", response_model=List[AlertResponse])
async def get_alert_history(
    limit: int = 100,
    api_key: Optional[str] = Depends(verify_api_key)
):
    """
    获取告警历史
    
    返回最近的告警记录（默认100条）。
    """
    checker = get_alert_checker()
    return checker.get_alert_history(limit=limit)


@router.get("/rules", response_model=List[RuleResponse])
async def get_alert_rules(
    api_key: Optional[str] = Depends(verify_api_key)
):
    """
    获取告警规则列表
    
    返回所有配置的告警规则。
    """
    checker = get_alert_checker()
    return checker.get_rules()


@router.put("/rules/{rule_name}")
async def update_alert_rule(
    rule_name: str,
    update: AlertRuleUpdate,
    api_key: Optional[str] = Depends(verify_api_key)
):
    """
    更新告警规则
    
    可以启用/禁用规则或修改阈值。
    """
    checker = get_alert_checker()
    
    success = checker.update_rule(
        name=rule_name,
        enabled=update.enabled,
        threshold=update.threshold
    )
    
    if not success:
        raise HTTPException(status_code=404, detail=f"规则 {rule_name} 不存在")
    
    return {"message": f"规则 {rule_name} 已更新", "success": True}


@router.post("/test")
async def test_alert_notification(
    api_key: Optional[str] = Depends(verify_api_key)
):
    """
    测试告警通知
    
    向所有配置的通知渠道发送测试消息。
    """
    notifier = get_notifier()
    results = notifier.test_notification()
    
    return {
        "message": "测试通知已发送",
        "channels": results
    }


@router.post("/check")
async def trigger_alert_check(
    api_key: Optional[str] = Depends(verify_api_key)
):
    """
    手动触发告警检查
    
    立即执行一次告警规则检查。
    """
    checker = get_alert_checker()
    checker.check_all_rules()
    
    return {
        "message": "告警检查已执行",
        "active_alerts": len(checker.get_active_alerts())
    }


@router.get("/status")
async def get_alert_status():
    """
    获取告警系统状态
    
    返回告警系统的运行状态（无需认证）。
    """
    checker = get_alert_checker()
    notifier = get_notifier()
    
    return {
        "enabled": True,
        "rules_count": len(checker.rules),
        "active_alerts_count": len(checker.get_active_alerts()),
        "notification_channels": [
            c.__class__.__name__ for c in notifier.channels
        ]
    }
