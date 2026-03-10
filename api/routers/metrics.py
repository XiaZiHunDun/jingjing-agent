"""
指标查询 API 路由

提供时序指标的查询接口。
"""

from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from api.auth import verify_api_key
from src.metrics import get_metrics_client, metrics_enabled


router = APIRouter(prefix="/api/metrics", tags=["指标查询"])


class MetricsSummary(BaseModel):
    """指标概要"""
    enabled: bool
    connected: bool
    api_stats: Optional[dict] = None
    tool_usage: Optional[List[dict]] = None


class TimeSeriesData(BaseModel):
    """时序数据点"""
    time: Optional[str]
    value: Optional[float]


class TrendResponse(BaseModel):
    """趋势数据响应"""
    measurement: str
    field: str
    interval: str
    data: List[TimeSeriesData]


class RequestMetrics(BaseModel):
    """请求指标"""
    total: int
    avg_duration_ms: float
    max_duration_ms: float
    min_duration_ms: float
    by_endpoint: Optional[dict] = None
    by_status: Optional[dict] = None


class ToolMetrics(BaseModel):
    """工具使用指标"""
    tool: str
    count: int
    avg_duration_ms: Optional[float] = None
    success_rate: Optional[float] = None


@router.get("/summary", response_model=MetricsSummary)
async def get_metrics_summary(
    hours: int = Query(24, ge=1, le=168, description="查询时间范围（小时）"),
    api_key: Optional[str] = Depends(verify_api_key)
):
    """
    获取指标概要
    
    返回 API 统计和工具使用的概要信息。
    """
    client = get_metrics_client()
    
    if not metrics_enabled() or not client or not client.is_connected():
        return MetricsSummary(
            enabled=metrics_enabled(),
            connected=client.is_connected() if client else False
        )
    
    api_stats = client.query_api_stats(hours=hours)
    tool_usage = client.query_tool_usage(hours=hours)
    
    return MetricsSummary(
        enabled=True,
        connected=True,
        api_stats=api_stats,
        tool_usage=tool_usage
    )


@router.get("/requests", response_model=RequestMetrics)
async def get_request_metrics(
    hours: int = Query(24, ge=1, le=168, description="查询时间范围（小时）"),
    api_key: Optional[str] = Depends(verify_api_key)
):
    """
    获取 API 请求指标
    
    返回详细的 API 请求统计。
    """
    client = get_metrics_client()
    
    if not metrics_enabled() or not client or not client.is_connected():
        raise HTTPException(status_code=503, detail="指标服务不可用")
    
    stats = client.query_api_stats(hours=hours)
    
    endpoint_query = f'''
    from(bucket: "{client.bucket}")
    |> range(start: -{hours}h)
    |> filter(fn: (r) => r._measurement == "api_requests")
    |> filter(fn: (r) => r._field == "duration_ms")
    |> group(columns: ["endpoint"])
    |> count()
    '''
    
    endpoint_results = client.query(endpoint_query)
    by_endpoint = {}
    for r in endpoint_results:
        ep = r.get("endpoint", "unknown")
        by_endpoint[ep] = by_endpoint.get(ep, 0) + 1
    
    status_query = f'''
    from(bucket: "{client.bucket}")
    |> range(start: -{hours}h)
    |> filter(fn: (r) => r._measurement == "api_requests")
    |> filter(fn: (r) => r._field == "success")
    |> group(columns: ["status_code"])
    |> count()
    '''
    
    status_results = client.query(status_query)
    by_status = {}
    for r in status_results:
        status = r.get("status_code", "unknown")
        by_status[status] = by_status.get(status, 0) + 1
    
    return RequestMetrics(
        total=stats.get("total", 0),
        avg_duration_ms=stats.get("avg_duration_ms", 0),
        max_duration_ms=stats.get("max_duration_ms", 0),
        min_duration_ms=stats.get("min_duration_ms", 0),
        by_endpoint=by_endpoint,
        by_status=by_status
    )


@router.get("/tools", response_model=List[ToolMetrics])
async def get_tool_metrics(
    hours: int = Query(24, ge=1, le=168, description="查询时间范围（小时）"),
    api_key: Optional[str] = Depends(verify_api_key)
):
    """
    获取工具使用指标
    
    返回各工具的使用统计。
    """
    client = get_metrics_client()
    
    if not metrics_enabled() or not client or not client.is_connected():
        raise HTTPException(status_code=503, detail="指标服务不可用")
    
    tool_usage = client.query_tool_usage(hours=hours)
    
    return [
        ToolMetrics(tool=t["tool"], count=t["count"])
        for t in tool_usage
    ]


@router.get("/trends", response_model=TrendResponse)
async def get_trends(
    measurement: str = Query(..., description="测量名称"),
    field: str = Query("duration_ms", description="字段名称"),
    hours: int = Query(24, ge=1, le=168, description="查询时间范围（小时）"),
    interval: str = Query("1h", description="聚合间隔"),
    api_key: Optional[str] = Depends(verify_api_key)
):
    """
    获取趋势数据
    
    返回指定指标的时序趋势。
    """
    client = get_metrics_client()
    
    if not metrics_enabled() or not client or not client.is_connected():
        raise HTTPException(status_code=503, detail="指标服务不可用")
    
    allowed_measurements = ["api_requests", "chat_metrics", "tool_calls", "system_metrics"]
    if measurement not in allowed_measurements:
        raise HTTPException(status_code=400, detail=f"不支持的测量名称，可选: {allowed_measurements}")
    
    trends = client.query_trends(
        measurement=measurement,
        field=field,
        hours=hours,
        interval=interval
    )
    
    return TrendResponse(
        measurement=measurement,
        field=field,
        interval=interval,
        data=[TimeSeriesData(time=t["time"], value=t.get("value")) for t in trends]
    )


@router.get("/health")
async def metrics_health():
    """
    检查指标服务健康状态
    
    返回 InfluxDB 连接状态。
    """
    client = get_metrics_client()
    
    return {
        "enabled": metrics_enabled(),
        "connected": client.is_connected() if client else False,
        "url": client.url if client else None,
        "bucket": client.bucket if client else None
    }
