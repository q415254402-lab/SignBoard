"""时区工具"""

from datetime import datetime, timezone, timedelta

# 默认东八区
CST = timezone(timedelta(hours=8))


def now_utc() -> datetime:
    """获取当前 UTC 时间（带时区）"""
    return datetime.now(timezone.utc)


def now_local() -> datetime:
    """获取当前本地时间（带时区）"""
    return datetime.now(CST)


def utc_now_naive() -> datetime:
    """获取当前 UTC 时间（无时区信息，用于数据库）"""
    return datetime.now(timezone.utc).replace(tzinfo=None)
