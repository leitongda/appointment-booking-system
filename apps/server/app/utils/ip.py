"""
IP 地址工具函数
用于获取客户端真实 IP 地址
"""
from fastapi import Request
from typing import Tuple, Optional
import re


# 私有 IP 地址范围正则表达式
PRIVATE_IP_PATTERNS = [
    re.compile(r'^10\.'),                          # 10.0.0.0/8
    re.compile(r'^172\.(1[6-9]|2[0-9]|3[0-1])\.'), # 172.16.0.0/12
    re.compile(r'^192\.168\.'),                    # 192.168.0.0/16
    re.compile(r'^127\.'),                         # 127.0.0.0/8 (loopback)
    re.compile(r'^169\.254\.'),                    # 169.254.0.0/16 (link-local)
    re.compile(r'^::1$'),                          # IPv6 loopback
    re.compile(r'^fc00:'),                         # IPv6 unique local
    re.compile(r'^fe80:'),                         # IPv6 link-local
]


def is_private_ip(ip: str) -> bool:
    """
    判断 IP 是否是私有/内网 IP
    
    Args:
        ip: IP 地址字符串
    
    Returns:
        True 如果是私有 IP，False 如果是公网 IP
    """
    if not ip:
        return True
    
    for pattern in PRIVATE_IP_PATTERNS:
        if pattern.match(ip):
            return True
    return False


def get_client_ip(request: Request) -> str:
    """
    获取客户端真实 IP（优先获取公网 IP）
    
    通过以下顺序获取：
    1. X-Forwarded-For 头部（取第一个非私有 IP）
    2. X-Real-IP 头部
    3. request.client.host（直连 IP）
    
    Args:
        request: FastAPI Request 对象
    
    Returns:
        客户端 IP 地址字符串
    """
    # 1. 尝试从 X-Forwarded-For 获取
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        # X-Forwarded-For 格式: client, proxy1, proxy2, ...
        ips = [ip.strip() for ip in forwarded.split(",")]
        # 优先返回第一个公网 IP
        for ip in ips:
            if ip and not is_private_ip(ip):
                return ip
        # 如果全是私有 IP，返回第一个
        if ips:
            return ips[0]
    
    # 2. 尝试从 X-Real-IP 获取
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()
    
    # 3. 使用直连 IP
    return request.client.host if request.client else "unknown"


def get_client_ips(request: Request) -> Tuple[str, Optional[str]]:
    """
    获取客户端的公网 IP 和内网 IP
    
    Args:
        request: FastAPI Request 对象
    
    Returns:
        (public_ip, private_ip) 元组
        - public_ip: 公网 IP（如果没有则返回内网 IP）
        - private_ip: 内网 IP（如果公网 IP 和内网 IP 相同则为 None）
    """
    public_ip = None
    private_ip = None
    all_ips = []
    
    # 从 X-Forwarded-For 收集所有 IP
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        all_ips.extend([ip.strip() for ip in forwarded.split(",")])
    
    # X-Real-IP
    real_ip = request.headers.get("X-Real-IP")
    if real_ip and real_ip.strip() not in all_ips:
        all_ips.append(real_ip.strip())
    
    # 直连 IP
    direct_ip = request.client.host if request.client else None
    if direct_ip and direct_ip not in all_ips:
        all_ips.append(direct_ip)
    
    # 分类 IP
    for ip in all_ips:
        if not ip:
            continue
        if is_private_ip(ip):
            if not private_ip:
                private_ip = ip
        else:
            if not public_ip:
                public_ip = ip
    
    # 如果没有公网 IP，使用私有 IP 作为主 IP
    if not public_ip:
        public_ip = private_ip or "unknown"
        private_ip = None
    elif public_ip == private_ip:
        private_ip = None
    
    return public_ip, private_ip


def format_client_ip(request: Request, include_private: bool = True) -> str:
    """
    格式化客户端 IP 字符串
    
    Args:
        request: FastAPI Request 对象
        include_private: 是否包含私有 IP
    
    Returns:
        格式化的 IP 字符串，例如 "203.0.113.50" 或 "203.0.113.50 (内网: 192.168.1.100)"
    """
    if not include_private:
        return get_client_ip(request)
    
    public_ip, private_ip = get_client_ips(request)
    
    if private_ip:
        return f"{public_ip} (内网: {private_ip})"
    return public_ip

