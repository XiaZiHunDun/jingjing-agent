"""
API 认证模块

提供 API Key 认证机制。
"""

import os
from typing import Optional
from fastapi import HTTPException, Security, Depends
from fastapi.security import APIKeyHeader, APIKeyQuery
from starlette.status import HTTP_401_UNAUTHORIZED, HTTP_403_FORBIDDEN


API_KEY_HEADER_NAME = "X-API-Key"
API_KEY_QUERY_NAME = "api_key"

api_key_header = APIKeyHeader(name=API_KEY_HEADER_NAME, auto_error=False)
api_key_query = APIKeyQuery(name=API_KEY_QUERY_NAME, auto_error=False)


def get_api_keys() -> list:
    """
    从环境变量获取有效的 API Keys
    
    支持多个 key，用逗号分隔：API_KEYS=key1,key2,key3
    如果未配置，返回空列表（禁用认证）
    """
    keys_str = os.getenv("API_KEYS", "").strip()
    if not keys_str:
        return []
    return [k.strip() for k in keys_str.split(",") if k.strip()]


def is_auth_enabled() -> bool:
    """检查是否启用了认证"""
    return len(get_api_keys()) > 0


async def verify_api_key(
    api_key_header: Optional[str] = Security(api_key_header),
    api_key_query: Optional[str] = Security(api_key_query)
) -> Optional[str]:
    """
    验证 API Key
    
    支持两种传递方式：
    1. Header: X-API-Key: your-api-key
    2. Query: ?api_key=your-api-key
    
    如果未配置 API_KEYS 环境变量，则跳过认证（开发模式）
    """
    valid_keys = get_api_keys()
    
    if not valid_keys:
        return None
    
    api_key = api_key_header or api_key_query
    
    if not api_key:
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail="缺少 API Key，请在 Header 中添加 X-API-Key 或在 URL 中添加 api_key 参数",
            headers={"WWW-Authenticate": "ApiKey"}
        )
    
    if api_key not in valid_keys:
        raise HTTPException(
            status_code=HTTP_403_FORBIDDEN,
            detail="无效的 API Key"
        )
    
    return api_key


def get_optional_api_key(
    api_key_header: Optional[str] = Security(api_key_header),
    api_key_query: Optional[str] = Security(api_key_query)
) -> Optional[str]:
    """
    可选的 API Key 验证（用于公开接口，但记录调用者）
    """
    return api_key_header or api_key_query
