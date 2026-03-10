"""
InfluxDB 客户端模块

提供时序数据库的连接和基础操作。
"""

import os
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from functools import lru_cache

from src.utils.logger import app_logger


INFLUXDB_URL = os.getenv("INFLUXDB_URL", "http://localhost:8086")
INFLUXDB_TOKEN = os.getenv("INFLUXDB_TOKEN", "")
INFLUXDB_ORG = os.getenv("INFLUXDB_ORG", "jingjing")
INFLUXDB_BUCKET = os.getenv("INFLUXDB_BUCKET", "metrics")
INFLUXDB_ENABLED = os.getenv("INFLUXDB_ENABLED", "false").lower() == "true"


def metrics_enabled() -> bool:
    """检查指标收集是否启用"""
    return INFLUXDB_ENABLED and bool(INFLUXDB_TOKEN)


class MetricsClient:
    """InfluxDB 指标客户端"""
    
    def __init__(
        self,
        url: str = INFLUXDB_URL,
        token: str = INFLUXDB_TOKEN,
        org: str = INFLUXDB_ORG,
        bucket: str = INFLUXDB_BUCKET
    ):
        self.url = url
        self.token = token
        self.org = org
        self.bucket = bucket
        self._client = None
        self._write_api = None
        self._query_api = None
        self._connected = False
    
    def connect(self) -> bool:
        """连接到 InfluxDB"""
        if not self.token:
            app_logger.warning("InfluxDB Token 未配置，跳过连接")
            return False
        
        try:
            from influxdb_client import InfluxDBClient
            from influxdb_client.client.write_api import SYNCHRONOUS
            
            self._client = InfluxDBClient(
                url=self.url,
                token=self.token,
                org=self.org
            )
            
            health = self._client.health()
            if health.status == "pass":
                self._write_api = self._client.write_api(write_options=SYNCHRONOUS)
                self._query_api = self._client.query_api()
                self._connected = True
                app_logger.info(f"InfluxDB 连接成功: {self.url}")
                return True
            else:
                app_logger.error(f"InfluxDB 健康检查失败: {health.message}")
                return False
                
        except ImportError:
            app_logger.warning("influxdb-client 未安装，跳过 InfluxDB 连接")
            return False
        except Exception as e:
            app_logger.error(f"InfluxDB 连接失败: {str(e)}")
            return False
    
    def is_connected(self) -> bool:
        """检查是否已连接"""
        return self._connected
    
    def close(self):
        """关闭连接"""
        if self._client:
            self._client.close()
            self._connected = False
    
    def write_point(
        self,
        measurement: str,
        tags: Dict[str, str],
        fields: Dict[str, Any],
        time: Optional[datetime] = None
    ) -> bool:
        """
        写入单个数据点
        
        Args:
            measurement: 测量名称（表名）
            tags: 标签（索引字段）
            fields: 字段（数值字段）
            time: 时间戳（可选）
        """
        if not self._connected:
            return False
        
        try:
            from influxdb_client import Point
            
            point = Point(measurement)
            
            for key, value in tags.items():
                point = point.tag(key, str(value))
            
            for key, value in fields.items():
                point = point.field(key, value)
            
            if time:
                point = point.time(time)
            
            self._write_api.write(bucket=self.bucket, record=point)
            return True
            
        except Exception as e:
            app_logger.error(f"写入指标失败: {str(e)}")
            return False
    
    def query(self, flux_query: str) -> List[Dict]:
        """
        执行 Flux 查询
        
        Args:
            flux_query: Flux 查询语句
            
        Returns:
            查询结果列表
        """
        if not self._connected:
            return []
        
        try:
            tables = self._query_api.query(flux_query, org=self.org)
            
            results = []
            for table in tables:
                for record in table.records:
                    results.append({
                        "time": record.get_time(),
                        "measurement": record.get_measurement(),
                        "field": record.get_field(),
                        "value": record.get_value(),
                        **{k: v for k, v in record.values.items() 
                           if k not in ["_time", "_measurement", "_field", "_value", "result", "table"]}
                    })
            
            return results
            
        except Exception as e:
            app_logger.error(f"查询指标失败: {str(e)}")
            return []
    
    def query_api_stats(self, hours: int = 24) -> Dict:
        """查询 API 统计"""
        query = f'''
        from(bucket: "{self.bucket}")
        |> range(start: -{hours}h)
        |> filter(fn: (r) => r._measurement == "api_requests")
        |> filter(fn: (r) => r._field == "duration_ms")
        '''
        
        results = self.query(query)
        
        if not results:
            return {"total": 0, "avg_duration_ms": 0}
        
        durations = [r["value"] for r in results if r.get("value") is not None]
        
        return {
            "total": len(durations),
            "avg_duration_ms": sum(durations) / len(durations) if durations else 0,
            "max_duration_ms": max(durations) if durations else 0,
            "min_duration_ms": min(durations) if durations else 0
        }
    
    def query_tool_usage(self, hours: int = 24) -> List[Dict]:
        """查询工具使用统计"""
        query = f'''
        from(bucket: "{self.bucket}")
        |> range(start: -{hours}h)
        |> filter(fn: (r) => r._measurement == "tool_calls")
        |> filter(fn: (r) => r._field == "duration_ms")
        |> group(columns: ["tool_name"])
        |> count()
        '''
        
        results = self.query(query)
        
        tool_counts = {}
        for r in results:
            tool_name = r.get("tool_name", "unknown")
            tool_counts[tool_name] = tool_counts.get(tool_name, 0) + 1
        
        return [
            {"tool": name, "count": count}
            for name, count in sorted(tool_counts.items(), key=lambda x: -x[1])
        ]
    
    def query_trends(
        self,
        measurement: str,
        field: str,
        hours: int = 24,
        interval: str = "1h"
    ) -> List[Dict]:
        """查询趋势数据"""
        query = f'''
        from(bucket: "{self.bucket}")
        |> range(start: -{hours}h)
        |> filter(fn: (r) => r._measurement == "{measurement}")
        |> filter(fn: (r) => r._field == "{field}")
        |> aggregateWindow(every: {interval}, fn: mean, createEmpty: false)
        |> yield(name: "mean")
        '''
        
        results = self.query(query)
        
        return [
            {"time": r["time"].isoformat() if r.get("time") else None, "value": r.get("value")}
            for r in results
        ]


_metrics_client: Optional[MetricsClient] = None


def get_metrics_client() -> Optional[MetricsClient]:
    """获取全局指标客户端实例"""
    global _metrics_client
    
    if not metrics_enabled():
        return None
    
    if _metrics_client is None:
        _metrics_client = MetricsClient()
        _metrics_client.connect()
    
    return _metrics_client


def init_metrics():
    """初始化指标系统"""
    if metrics_enabled():
        client = get_metrics_client()
        if client and client.is_connected():
            app_logger.info("[✓] InfluxDB 指标系统已启用")
        else:
            app_logger.warning("[!] InfluxDB 连接失败，指标系统已禁用")
    else:
        app_logger.info("[!] InfluxDB 指标系统未启用")
