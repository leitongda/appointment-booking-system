"""
日志系统配置
支持控制台输出、文件输出、JSON 格式等
"""
import json
import logging
import logging.handlers
import os
import sys
from datetime import datetime


class JsonFormatter(logging.Formatter):
    """JSON 格式日志格式化器

    支持从 log record 的 extra 属性中提取结构化字段：
    trace_id, tenant_id, user_id, method, path, status_code,
    duration_ms, client_ip 等。
    """

    # 预定义的结构化字段名（从 record 中提取并提升为顶层字段）
    STRUCTURED_FIELDS = (
        "trace_id", "tenant_id", "user_id",
        "method", "path", "query", "status_code",
        "duration_ms", "client_ip", "error_type", "error_message",
    )

    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # 提取预定义的结构化字段到顶层
        for field in self.STRUCTURED_FIELDS:
            value = getattr(record, field, None)
            if value is not None:
                log_data[field] = value

        # 添加异常信息
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # 添加额外字段
        if hasattr(record, "extra_data"):
            log_data["extra"] = record.extra_data

        return json.dumps(log_data, ensure_ascii=False)


class _StructuredEnricher:
    """非 JSON 路径下的结构化字段条件富化 mixin。

    复用 JsonFormatter.STRUCTURED_FIELDS，对缺失/空字段安全：
    None / "" / 0 均跳过（0 跳过可避免 request_started 的 duration_ms=0 噪音），
    因此普通日志（无 extra）行字节级保持原样。

    注意：STRUCTURED_FIELDS 内禁止加入 levelname —— 它在 ColoredFormatter 中
    会被原地改写为带 ANSI 码的字符串，若纳入此处会把彩色转义符泄漏到文件日志。
    """

    def _append_structured(self, record: logging.LogRecord, base_line: str) -> str:
        parts = []
        for field in JsonFormatter.STRUCTURED_FIELDS:
            value = getattr(record, field, None)
            if value in (None, "", 0):
                continue
            if field == "duration_ms":
                parts.append(f"duration={value}ms")
            elif field == "trace_id":
                parts.append(f"trace={value}")
            else:
                parts.append(f"{field}={value}")
        if not parts:
            return base_line
        return f"{base_line}   | {' '.join(parts)}"


class ColoredFormatter(logging.Formatter, _StructuredEnricher):
    """彩色日志格式化器（用于控制台），并对请求日志做结构化富化。"""

    # ANSI 颜色代码
    COLORS = {
        "DEBUG": "\033[36m",     # 青色
        "INFO": "\033[32m",      # 绿色
        "WARNING": "\033[33m",   # 黄色
        "ERROR": "\033[31m",     # 红色
        "CRITICAL": "\033[35m",  # 紫色
    }
    RESET = "\033[0m"

    def __init__(self, fmt: str = None, datefmt: str = None, use_colors: bool = True):
        super().__init__(fmt, datefmt)
        self.use_colors = use_colors

    def format(self, record: logging.LogRecord) -> str:
        # 先备份 levelname，染色后调 super().format() 捕获彩色基础行，再立即还原。
        # 否则同一 record 被后续 file/error handler 复用时，会把 ANSI 转义码写进文件。
        # _append_structured 只读 STRUCTURED_FIELDS（不含 levelname），不会重复染色。
        original_levelname = record.levelname
        try:
            if self.use_colors and record.levelname in self.COLORS:
                record.levelname = f"{self.COLORS[record.levelname]}{record.levelname}{self.RESET}"
            base_line = super().format(record)
        finally:
            record.levelname = original_levelname
        return self._append_structured(record, base_line)


class _StructuredFileFormatter(logging.Formatter, _StructuredEnricher):
    """文件日志格式化器（非 JSON 分支），输出与控制台一致的结构化富化行。"""

    def format(self, record: logging.LogRecord) -> str:
        base_line = super().format(record)
        return self._append_structured(record, base_line)


def setup_logging(
    log_level: str = "INFO",
    log_dir: str = "logs",
    app_name: str = "hospital",
    json_format: bool = False,
    console_output: bool = True,
    file_output: bool = True,
    max_bytes: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5
):
    """
    配置日志系统
    
    Args:
        log_level: 日志级别 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_dir: 日志文件目录
        app_name: 应用名称（用于日志文件名）
        json_format: 是否使用 JSON 格式
        console_output: 是否输出到控制台
        file_output: 是否输出到文件
        max_bytes: 单个日志文件最大大小
        backup_count: 保留的日志文件数量
    """
    # 创建日志目录
    if file_output and not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # 获取根日志器
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))
    
    # 清除现有处理器
    root_logger.handlers.clear()
    
    # 日志格式
    log_format = "%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d | %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"
    
    # 控制台处理器
    if console_output:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.DEBUG)
        
        if json_format:
            console_handler.setFormatter(JsonFormatter())
        else:
            console_handler.setFormatter(ColoredFormatter(log_format, date_format))
        
        root_logger.addHandler(console_handler)
    
    # 文件处理器
    if file_output:
        # 普通日志文件（所有级别）
        file_handler = logging.handlers.RotatingFileHandler(
            filename=os.path.join(log_dir, f"{app_name}.log"),
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding="utf-8"
        )
        file_handler.setLevel(logging.DEBUG)
        
        if json_format:
            file_handler.setFormatter(JsonFormatter())
        else:
            file_handler.setFormatter(_StructuredFileFormatter(log_format, date_format))
        
        root_logger.addHandler(file_handler)
        
        # 错误日志文件（只记录 ERROR 及以上）
        error_handler = logging.handlers.RotatingFileHandler(
            filename=os.path.join(log_dir, f"{app_name}_error.log"),
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding="utf-8"
        )
        error_handler.setLevel(logging.ERROR)
        
        if json_format:
            error_handler.setFormatter(JsonFormatter())
        else:
            error_handler.setFormatter(_StructuredFileFormatter(log_format, date_format))
        
        root_logger.addHandler(error_handler)
    
    # 设置第三方库日志级别（减少噪音）
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    
    logger = logging.getLogger(__name__)
    logger.info(f"日志系统初始化完成: level={log_level}, dir={log_dir}, json={json_format}")


class RequestLogger:
    """请求日志记录器"""
    
    def __init__(self):
        self.logger = logging.getLogger("request")
    
    def log_request(
        self,
        method: str,
        path: str,
        status_code: int,
        duration_ms: float,
        client_ip: str = None,
        user_id: str = None,
        error: str = None
    ):
        """记录请求日志"""
        log_data = {
            "method": method,
            "path": path,
            "status": status_code,
            "duration_ms": round(duration_ms, 2),
            "client_ip": client_ip,
            "user_id": user_id,
        }
        
        if error:
            log_data["error"] = error
            self.logger.error(f"请求失败: {log_data}")
        elif status_code >= 400:
            self.logger.warning(f"请求异常: {log_data}")
        else:
            self.logger.info(f"请求完成: {log_data}")


# 全局请求日志记录器
request_logger = RequestLogger()

# 全局日志记录器（可以被其他模块导入使用）
logger = logging.getLogger(__name__)

