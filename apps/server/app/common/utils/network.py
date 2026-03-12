"""Network-related utility helpers."""

import re
from typing import Optional, Tuple

from fastapi import Request


PRIVATE_IP_PATTERNS = [
    re.compile(r"^10\."),
    re.compile(r"^172\.(1[6-9]|2[0-9]|3[0-1])\."),
    re.compile(r"^192\.168\."),
    re.compile(r"^127\."),
    re.compile(r"^169\.254\."),
    re.compile(r"^::1$"),
    re.compile(r"^fc00:"),
    re.compile(r"^fe80:"),
]


def is_private_ip(ip: str) -> bool:
    if not ip:
        return True
    return any(pattern.match(ip) for pattern in PRIVATE_IP_PATTERNS)


def get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        ips = [ip.strip() for ip in forwarded.split(",")]
        for ip in ips:
            if ip and not is_private_ip(ip):
                return ip
        if ips:
            return ips[0]

    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()

    return request.client.host if request.client else "unknown"


def get_client_ips(request: Request) -> Tuple[str, Optional[str]]:
    public_ip = None
    private_ip = None
    all_ips = []

    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        all_ips.extend([ip.strip() for ip in forwarded.split(",")])

    real_ip = request.headers.get("X-Real-IP")
    if real_ip and real_ip.strip() not in all_ips:
        all_ips.append(real_ip.strip())

    direct_ip = request.client.host if request.client else None
    if direct_ip and direct_ip not in all_ips:
        all_ips.append(direct_ip)

    for ip in all_ips:
        if not ip:
            continue
        if is_private_ip(ip):
            if not private_ip:
                private_ip = ip
        elif not public_ip:
            public_ip = ip

    if not public_ip:
        public_ip = private_ip or "unknown"
        private_ip = None
    elif public_ip == private_ip:
        private_ip = None

    return public_ip, private_ip


def format_client_ip(request: Request, include_private: bool = True) -> str:
    if not include_private:
        return get_client_ip(request)

    public_ip, private_ip = get_client_ips(request)
    if private_ip:
        return f"{public_ip} (内网: {private_ip})"
    return public_ip
