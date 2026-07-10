from datetime import datetime, timedelta


def today():
    """返回当前年月日字符串 2025-08-29"""
    return datetime.now().strftime("%Y-%m-%d")


def todayTime():
    """返回当前年月日时分秒字符串 20250829142235"""
    return datetime.now().strftime("%Y%m%d%H%M%S")


def todayTimeStandard():
    """返回当前年月日时分秒字符串 2025-08-29 14:22:35"""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def yesterday():
    """返回前一天日期字符串，格式 2025-08-28"""
    return (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")


def nowTimeStamp():
    """返回当前时间戳，精确到毫秒级"""
    return int(datetime.now().timestamp() * 1000)


def year():
    """返回当前年份"""
    return datetime.now().year


def month():
    """返回当前月份"""
    return datetime.now().month


def day():
    """返回当前几号"""
    return datetime.now().day