"""短信重试辅助函数。"""
import asyncio
import json
import threading
from collections.abc import Awaitable, Mapping
from typing import Any


def coerce_extra_data(extra_data: Any) -> dict[str, Any]:
    """将 JSON 字符串或 dict extra_data 统一为 dict。"""
    if isinstance(extra_data, Mapping):
        return dict(extra_data)
    if isinstance(extra_data, str) and extra_data.strip():
        try:
            parsed = json.loads(extra_data)
        except json.JSONDecodeError:
            return {}
        return dict(parsed) if isinstance(parsed, Mapping) else {}
    return {}


def normalize_sms_result(result: Any) -> bool:
    """兼容 bool 或 (success, error) 返回值，避免失败 tuple 被误判为成功。"""
    if isinstance(result, tuple):
        return bool(result[0]) if result else False
    return bool(result)


def run_async_sms(coro: Awaitable[Any]) -> Any:
    """在同步重试任务中执行异步短信 provider 方法。"""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)

    result: dict[str, Any] = {}

    def runner() -> None:
        try:
            result["value"] = asyncio.run(coro)
        except Exception as exc:  # pragma: no cover - 由调用方统一记录日志
            result["error"] = exc

    thread = threading.Thread(target=runner, daemon=True)
    thread.start()
    thread.join()

    if "error" in result:
        raise result["error"]
    return result.get("value")


async def _send_sms_retry_async(
    provider: Any,
    phone: str,
    template_code: str | None,
    template_params: Any,
    content: str,
) -> Any:
    if template_code and hasattr(provider, "send_business_notification"):
        return await provider.send_business_notification(
            phone=phone,
            template_code=template_code,
            template_params=template_params or {},
        )
    if hasattr(provider, "send_notification"):
        return await provider.send_notification(phone, content)
    return False


def send_sms_retry(
    provider: Any,
    phone: str | None,
    extra_data: Any = None,
    content: str | None = None,
) -> bool:
    """按重试记录中的模板信息发送短信，缺少模板时降级为普通通知。"""
    if not phone:
        return False

    data = coerce_extra_data(extra_data)
    result = run_async_sms(
        _send_sms_retry_async(
            provider=provider,
            phone=phone,
            template_code=data.get("template_code"),
            template_params=data.get("template_params", {}),
            content=content or data.get("content") or "",
        )
    )
    return normalize_sms_result(result)
