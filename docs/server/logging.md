# 📝 日志系统

## 概述

日志系统位于 `app/core/logging.py`，提供：

- 彩色控制台输出（开发环境）
- 文件日志（自动轮转）
- JSON 格式日志（生产环境）
- 请求日志中间件

---

## 配置

### 环境变量

```env
LOG_LEVEL=INFO          # 日志级别: DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_DIR=logs            # 日志目录
LOG_JSON_FORMAT=false   # 是否使用 JSON 格式
```

### 初始化

日志系统在 `main.py` 启动时自动初始化：

```python
from app.core.logging import setup_logging
from app.core.config import settings

setup_logging(
    log_level=settings.LOG_LEVEL,
    log_dir=settings.LOG_DIR,
    app_name="hospital",
    json_format=settings.LOG_JSON_FORMAT,
    console_output=True,
    file_output=True
)
```

---

## 日志文件

```
logs/
├── hospital.log         # 所有级别日志
└── hospital_error.log   # 仅 ERROR 及以上
```

### 轮转策略

- 单文件最大：10MB
- 保留文件数：5
- 自动压缩归档

---

## 使用方式

### 基础用法

```python
import logging

# 获取 logger（使用模块名）
logger = logging.getLogger(__name__)

# 记录日志
logger.debug("调试信息")
logger.info("普通信息")
logger.warning("警告信息")
logger.error("错误信息")
logger.critical("严重错误")
```

### 在服务中使用

```python
# app/services/appointment_service.py
import logging

logger = logging.getLogger(__name__)

class AppointmentService:
    async def create(self, user_id: str, data: dict):
        logger.info(f"创建预约: user_id={user_id}, data={data}")
        
        try:
            # 业务逻辑
            appointment = await self._do_create(data)
            logger.info(f"预约创建成功: appointment_id={appointment.id}")
            return appointment
        except Exception as e:
            logger.error(f"预约创建失败: {e}", exc_info=True)
            raise
```

### 记录异常

```python
try:
    result = await some_operation()
except Exception as e:
    # 记录完整堆栈
    logger.error(f"操作失败: {e}", exc_info=True)
    
    # 或者使用 exception 方法（自动包含堆栈）
    logger.exception(f"操作失败: {e}")
```

### 添加上下文信息

```python
# 使用 extra 参数
logger.info("用户登录", extra={
    "extra_data": {
        "user_id": "123",
        "ip": "192.168.1.1",
        "device": "iPhone"
    }
})
```

---

## 日志格式

### 控制台格式（彩色）

```
2024-01-15 10:30:45 | INFO     | app.services.auth:login:42 | 用户登录成功
2024-01-15 10:30:46 | WARNING  | app.middleware.rate_limit:check:85 | 请求被限流
2024-01-15 10:30:47 | ERROR    | app.services.sms:send:33 | 短信发送失败
```

### JSON 格式（生产环境）

```json
{
  "timestamp": "2024-01-15T10:30:45.123456Z",
  "level": "INFO",
  "logger": "app.services.auth",
  "message": "用户登录成功",
  "module": "auth",
  "function": "login",
  "line": 42,
  "extra": {
    "user_id": "123",
    "ip": "192.168.1.1"
  }
}
```

---

## 请求日志

请求日志中间件自动记录每个请求：

### 请求开始

```
[a1b2c3d4] --> GET /api/v1/doctors ?page=1 | IP: 192.168.1.100
```

### 请求结束

```
[a1b2c3d4] <-- GET /api/v1/doctors | Status: 200 | Duration: 45.23ms
```

### 响应头

每个响应自动添加：

- `X-Request-ID`: 请求唯一标识
- `X-Response-Time`: 响应耗时

---

## 日志级别建议

| 级别 | 使用场景 |
|------|----------|
| `DEBUG` | 开发调试信息，详细的执行过程 |
| `INFO` | 重要业务操作，如登录、预约创建 |
| `WARNING` | 异常情况但不影响功能，如限流触发 |
| `ERROR` | 错误但可恢复，如第三方接口失败 |
| `CRITICAL` | 严重错误，系统无法正常工作 |

### 环境配置建议

| 环境 | 日志级别 | JSON 格式 |
|------|----------|-----------|
| 开发 | DEBUG | 否 |
| 测试 | INFO | 否 |
| 生产 | WARNING | 是 |

---

## 第三方库日志

已自动降低噪音库的日志级别：

```python
logging.getLogger("uvicorn").setLevel(logging.WARNING)
logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
```

如需查看 SQL 语句：

```python
logging.getLogger("sqlalchemy.engine").setLevel(logging.DEBUG)
```

---

## 最佳实践

1. **使用 `__name__`**：`logger = logging.getLogger(__name__)` 自动使用模块路径
2. **结构化日志**：使用 f-string 和 extra 参数记录上下文
3. **不要 print**：使用 logger 代替 print，便于统一管理
4. **异常堆栈**：使用 `exc_info=True` 或 `logger.exception()`
5. **敏感信息**：不要记录密码、Token 等敏感信息
6. **性能考虑**：避免在日志中执行复杂计算

