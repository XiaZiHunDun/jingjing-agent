"""
数据库模块

提供对话历史的持久化存储。
"""

from src.db.chat_history import (
    init_database,
    save_session,
    load_session,
    get_all_sessions,
    delete_session,
)

__all__ = [
    "init_database",
    "save_session",
    "load_session",
    "get_all_sessions",
    "delete_session",
]
