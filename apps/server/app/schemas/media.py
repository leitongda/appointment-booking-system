"""上传文件路径与公网基址的出口/入口转换。

背景：数据库只存相对路径（/uploads/<key>，见 local_storage.generate_url）。网页版
页面与 nginx 同源，<img src> 相对路径可直接加载；Tauri 桌面客户端运行在
tauri://localhost 自定义协议上，相对路径会打到本地资产协议，图片全部 404。

解法（配置 PUBLIC_MEDIA_BASE_URL 后生效，留空则以下全部为 no-op，现有客户端零影响）：
    出口 publicize_media  —— 响应序列化时给 /uploads/ 路径拼公网基址（中间件统一处理）；
    入口 normalize_media —— 请求体里客户端原样回写的「基址 + /uploads/」还原为相对路径
    （BaseRequestSchema 统一校验器 + 个别直连 BaseModel 请求模型显式校验器），
    保证无论客户端拿到的是哪种形态，入库的始终是相对路径。

规则刻意收窄：只处理以 /uploads/（或 uploads/）开头、且基址匹配的字符串；
外链（https://…）、非上传路径一律不动。
"""
import json

from app.core.config import settings

UPLOADS_PREFIX = "/uploads/"


def _base() -> str:
    return (settings.PUBLIC_MEDIA_BASE_URL or "").rstrip("/")


def to_public_url(value: str) -> str:
    """相对上传路径 → 公网绝对 URL；其余原样返回。"""
    base = _base()
    if not base:
        return value
    if value.startswith(UPLOADS_PREFIX):
        return base + value
    if value.startswith("uploads/"):
        return base + "/" + value
    return value


def to_storage_path(value: str) -> str:
    """「基址 + /uploads/」还原为相对路径；其余原样返回。"""
    base = _base()
    if not base:
        return value
    if value.startswith(base + UPLOADS_PREFIX):
        return value[len(base):]
    return value


def _walk(data, fn):
    """递归对 dict / list 中的字符串叶子应用 fn。

    特例：形如 JSON 编码的路径列表的字符串（如 department.intro_images，
    "[\"/uploads/a.png\",\"/uploads/b.png\"]"）解析后逐项处理再重新编码。
    仅当字符串以 "[" 开头且包含上传前缀时才尝试解析，避免对普通文本做无谓解析。
    """
    if isinstance(data, str):
        if data.startswith("[") and UPLOADS_PREFIX in data:
            try:
                parsed = json.loads(data)
            except ValueError:
                return fn(data)
            if isinstance(parsed, list):
                return json.dumps(_walk(parsed, fn), ensure_ascii=False)
            return fn(data)
        return fn(data)
    if isinstance(data, list):
        return [_walk(item, fn) for item in data]
    if isinstance(data, dict):
        return {key: _walk(value, fn) for key, value in data.items()}
    return data


def publicize_media(data):
    """响应出口：/uploads/ 相对路径 → 公网绝对 URL。基址未配置时原样返回。"""
    if not _base():
        return data
    return _walk(data, to_public_url)


def normalize_media(data):
    """请求入口：客户端回写的「基址 + /uploads/」→ 相对路径。基址未配置时原样返回。"""
    if not _base():
        return data
    return _walk(data, to_storage_path)
