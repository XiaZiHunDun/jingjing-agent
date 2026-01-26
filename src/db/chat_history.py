"""
对话历史数据库模块

使用 SQLite 存储对话历史，支持：
- 会话管理
- 消息存储
- 历史查询
"""

import sqlite3
import json
from typing import List, Dict, Optional
from datetime import datetime

from src.utils.config import Config


def get_db_connection():
    """获取数据库连接"""
    Config.ensure_dirs()
    return sqlite3.connect(str(Config.DB_PATH))


def init_database():
    """初始化数据库，创建表结构"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 创建会话表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS chat_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT UNIQUE NOT NULL,
            title TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 创建消息表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS chat_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            thinking_steps TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES chat_sessions(session_id)
        )
    ''')
    
    conn.commit()
    conn.close()


def save_session(session_id: str, messages: List[Dict], title: Optional[str] = None):
    """
    保存对话到数据库
    
    Args:
        session_id: 会话 ID
        messages: 消息列表，每条消息包含 role, content, 可选 thinking_steps
        title: 会话标题，如果不提供则自动生成
    """
    if not messages:
        return
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 自动生成标题（取第一条用户消息的前20字）
    if not title:
        for msg in messages:
            if msg.get("role") == "user":
                content = msg["content"]
                title = content[:20] + ("..." if len(content) > 20 else "")
                break
        title = title or f"对话 {session_id}"
    
    # 更新或插入会话
    cursor.execute('''
        INSERT OR REPLACE INTO chat_sessions (session_id, title, updated_at)
        VALUES (?, ?, CURRENT_TIMESTAMP)
    ''', (session_id, title))
    
    # 删除旧消息，重新插入
    cursor.execute('DELETE FROM chat_messages WHERE session_id = ?', (session_id,))
    
    for msg in messages:
        thinking_steps = None
        if msg.get("thinking_steps"):
            thinking_steps = json.dumps(msg["thinking_steps"], ensure_ascii=False)
        
        cursor.execute('''
            INSERT INTO chat_messages (session_id, role, content, thinking_steps)
            VALUES (?, ?, ?, ?)
        ''', (session_id, msg["role"], msg["content"], thinking_steps))
    
    conn.commit()
    conn.close()


def load_session(session_id: str) -> List[Dict]:
    """
    从数据库加载对话
    
    Args:
        session_id: 会话 ID
        
    Returns:
        消息列表
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT role, content, thinking_steps FROM chat_messages
        WHERE session_id = ? ORDER BY id
    ''', (session_id,))
    
    messages = []
    for row in cursor.fetchall():
        msg = {"role": row[0], "content": row[1]}
        if row[2]:
            msg["thinking_steps"] = json.loads(row[2])
        messages.append(msg)
    
    conn.close()
    return messages


def get_all_sessions(limit: int = 20) -> List[Dict]:
    """
    获取所有对话会话列表
    
    Args:
        limit: 返回数量限制
        
    Returns:
        会话列表
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT session_id, title, updated_at,
               (SELECT COUNT(*) FROM chat_messages 
                WHERE chat_messages.session_id = chat_sessions.session_id) as msg_count
        FROM chat_sessions
        ORDER BY updated_at DESC
        LIMIT ?
    ''', (limit,))
    
    sessions = []
    for row in cursor.fetchall():
        sessions.append({
            "session_id": row[0],
            "title": row[1],
            "updated_at": row[2],
            "msg_count": row[3]
        })
    
    conn.close()
    return sessions


def delete_session(session_id: str):
    """
    删除对话会话
    
    Args:
        session_id: 会话 ID
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('DELETE FROM chat_messages WHERE session_id = ?', (session_id,))
    cursor.execute('DELETE FROM chat_sessions WHERE session_id = ?', (session_id,))
    
    conn.commit()
    conn.close()


def get_session_count() -> int:
    """获取会话总数"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT COUNT(*) FROM chat_sessions')
    count = cursor.fetchone()[0]
    
    conn.close()
    return count


def get_message_count(session_id: Optional[str] = None) -> int:
    """
    获取消息总数
    
    Args:
        session_id: 如果指定，只统计该会话的消息数
        
    Returns:
        消息数量
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if session_id:
        cursor.execute(
            'SELECT COUNT(*) FROM chat_messages WHERE session_id = ?', 
            (session_id,)
        )
    else:
        cursor.execute('SELECT COUNT(*) FROM chat_messages')
    
    count = cursor.fetchone()[0]
    
    conn.close()
    return count
