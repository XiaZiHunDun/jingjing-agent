"""
告警通知发送器

支持多种通知渠道：钉钉、企业微信、邮件、控制台。
"""

import os
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional, Dict, Any
from datetime import datetime
from abc import ABC, abstractmethod

import httpx

from src.utils.logger import app_logger
from .rules import Alert, AlertLevel, AlertStatus


class NotificationChannel(ABC):
    """通知渠道基类"""
    
    @abstractmethod
    def send(self, title: str, content: str, level: AlertLevel) -> bool:
        pass


class ConsoleChannel(NotificationChannel):
    """控制台通知（用于测试）"""
    
    def send(self, title: str, content: str, level: AlertLevel) -> bool:
        level_emoji = {"info": "ℹ️", "warning": "⚠️", "critical": "🚨"}.get(level.value, "📢")
        app_logger.info(f"{level_emoji} [告警通知] {title}\n{content}")
        return True


class DingTalkChannel(NotificationChannel):
    """钉钉机器人通知"""
    
    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url
    
    def send(self, title: str, content: str, level: AlertLevel) -> bool:
        if not self.webhook_url:
            return False
        
        try:
            level_emoji = {"info": "ℹ️", "warning": "⚠️", "critical": "🚨"}.get(level.value, "📢")
            
            payload = {
                "msgtype": "markdown",
                "markdown": {
                    "title": f"{level_emoji} {title}",
                    "text": f"### {level_emoji} {title}\n\n{content}\n\n---\n*晶晶助手告警系统*"
                }
            }
            
            with httpx.Client(timeout=10) as client:
                response = client.post(self.webhook_url, json=payload)
                return response.status_code == 200
                
        except Exception as e:
            app_logger.error(f"钉钉通知发送失败: {str(e)}")
            return False


class WeChatWorkChannel(NotificationChannel):
    """企业微信机器人通知"""
    
    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url
    
    def send(self, title: str, content: str, level: AlertLevel) -> bool:
        if not self.webhook_url:
            return False
        
        try:
            level_emoji = {"info": "ℹ️", "warning": "⚠️", "critical": "🚨"}.get(level.value, "📢")
            
            payload = {
                "msgtype": "markdown",
                "markdown": {
                    "content": f"### {level_emoji} {title}\n\n{content}\n\n> 晶晶助手告警系统"
                }
            }
            
            with httpx.Client(timeout=10) as client:
                response = client.post(self.webhook_url, json=payload)
                return response.status_code == 200
                
        except Exception as e:
            app_logger.error(f"企业微信通知发送失败: {str(e)}")
            return False


class EmailChannel(NotificationChannel):
    """邮件通知"""
    
    def __init__(
        self,
        smtp_host: str,
        smtp_port: int,
        username: str,
        password: str,
        sender: str,
        recipients: list
    ):
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.username = username
        self.password = password
        self.sender = sender
        self.recipients = recipients
    
    def send(self, title: str, content: str, level: AlertLevel) -> bool:
        if not all([self.smtp_host, self.username, self.password, self.recipients]):
            return False
        
        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = f"[{level.value.upper()}] {title}"
            msg['From'] = self.sender
            msg['To'] = ', '.join(self.recipients)
            
            html_content = f"""
            <html>
            <body>
            <h2>{title}</h2>
            <pre>{content}</pre>
            <hr>
            <p><small>晶晶助手告警系统</small></p>
            </body>
            </html>
            """
            
            msg.attach(MIMEText(content, 'plain'))
            msg.attach(MIMEText(html_content, 'html'))
            
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.username, self.password)
                server.sendmail(self.sender, self.recipients, msg.as_string())
            
            return True
            
        except Exception as e:
            app_logger.error(f"邮件通知发送失败: {str(e)}")
            return False


class AlertNotifier:
    """告警通知器"""
    
    def __init__(self):
        self.channels: list[NotificationChannel] = []
        self._init_channels()
    
    def _init_channels(self):
        """初始化通知渠道"""
        # 始终添加控制台通知
        self.channels.append(ConsoleChannel())
        
        # 钉钉
        dingtalk_webhook = os.getenv("ALERT_DINGTALK_WEBHOOK")
        if dingtalk_webhook:
            self.channels.append(DingTalkChannel(dingtalk_webhook))
            app_logger.info("[✓] 钉钉告警通知已配置")
        
        # 企业微信
        wechat_webhook = os.getenv("ALERT_WECHAT_WEBHOOK")
        if wechat_webhook:
            self.channels.append(WeChatWorkChannel(wechat_webhook))
            app_logger.info("[✓] 企业微信告警通知已配置")
        
        # 邮件
        smtp_host = os.getenv("ALERT_SMTP_HOST")
        if smtp_host:
            self.channels.append(EmailChannel(
                smtp_host=smtp_host,
                smtp_port=int(os.getenv("ALERT_SMTP_PORT", "587")),
                username=os.getenv("ALERT_SMTP_USER", ""),
                password=os.getenv("ALERT_SMTP_PASSWORD", ""),
                sender=os.getenv("ALERT_SMTP_SENDER", ""),
                recipients=os.getenv("ALERT_SMTP_RECIPIENTS", "").split(",")
            ))
            app_logger.info("[✓] 邮件告警通知已配置")
    
    def send_alert(self, alert: Alert) -> bool:
        """发送告警通知"""
        title = f"告警: {alert.rule_name}"
        content = self._format_alert_content(alert)
        
        success = False
        for channel in self.channels:
            try:
                if channel.send(title, content, alert.level):
                    success = True
            except Exception as e:
                app_logger.error(f"通知发送失败: {str(e)}")
        
        return success
    
    def send_recovery(self, alert: Alert) -> bool:
        """发送恢复通知"""
        title = f"恢复: {alert.rule_name}"
        content = self._format_recovery_content(alert)
        
        success = False
        for channel in self.channels:
            try:
                if channel.send(title, content, AlertLevel.INFO):
                    success = True
            except Exception as e:
                app_logger.error(f"恢复通知发送失败: {str(e)}")
        
        return success
    
    def _format_alert_content(self, alert: Alert) -> str:
        """格式化告警内容"""
        return f"""
**告警级别**: {alert.level.value.upper()}
**告警规则**: {alert.rule_name}
**告警详情**: {alert.message}
**当前值**: {alert.value:.2f}
**阈值**: {alert.threshold}
**触发时间**: {alert.triggered_at.strftime('%Y-%m-%d %H:%M:%S')}
"""
    
    def _format_recovery_content(self, alert: Alert) -> str:
        """格式化恢复内容"""
        duration = ""
        if alert.resolved_at:
            delta = alert.resolved_at - alert.triggered_at
            duration = f"\n**持续时长**: {delta.total_seconds():.0f} 秒"
        
        return f"""
**状态**: 已恢复 ✅
**告警规则**: {alert.rule_name}
**触发时间**: {alert.triggered_at.strftime('%Y-%m-%d %H:%M:%S')}
**恢复时间**: {alert.resolved_at.strftime('%Y-%m-%d %H:%M:%S') if alert.resolved_at else 'N/A'}{duration}
"""
    
    def test_notification(self) -> Dict[str, bool]:
        """测试所有通知渠道"""
        results = {}
        
        test_alert = Alert(
            rule_name="test_alert",
            level=AlertLevel.INFO,
            status=AlertStatus.FIRING,
            message="这是一条测试告警",
            value=100.0,
            threshold=50.0
        )
        
        for channel in self.channels:
            channel_name = channel.__class__.__name__
            try:
                success = channel.send(
                    "测试告警",
                    self._format_alert_content(test_alert),
                    AlertLevel.INFO
                )
                results[channel_name] = success
            except Exception as e:
                results[channel_name] = False
                app_logger.error(f"{channel_name} 测试失败: {str(e)}")
        
        return results


_notifier: Optional[AlertNotifier] = None


def get_notifier() -> AlertNotifier:
    """获取全局通知器"""
    global _notifier
    
    if _notifier is None:
        _notifier = AlertNotifier()
    
    return _notifier
