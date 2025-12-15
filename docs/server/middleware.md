# 🔧 中间件

## 概述

中间件位于 `app/middleware/` 目录，包括：

| 中间件 | 文件 | 说明 |
|--------|------|------|
| 统一响应格式 | `response.py` | 包装 API 响应为统一格式 |
| 全局异常处理 | `exception.py` | 捕获并处理各类异常 |
| API 限流 | `rate_limit.py` | 防止接口被恶意调用 |
| 请求日志 | `request_log.py` | 记录请求详情和耗时 |

---

## 执行顺序

中间件按注册的**逆序**执行（洋葱模型）：

```
请求 → RequestLog → RateLimit → CORS → UnifiedResponse → 路由处理
响应 ← RequestLog ← RateLimit ← CORS ← UnifiedResponse ← 路由处理
```

---

## 统一响应格式

### 功能

将所有 API 响应包装为统一格式：

```json
{
  "code": 200,
  "message": "success",
  "data": { ... }
}
```

### 配置

已在 `main.py` 中注册：

```python
app.add_middleware(UnifiedResponseMiddleware)
```

### 响应示例

**成功响应**：
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "id": "123",
    "name": "张三"
  }
}
```

**错误响应**：
```json
{
  "code": 400,
  "message": "预约号源已满",
  "data": null
}
```

---

## API 限流

### 功能

- 基于 IP 的请求限流
- 支持每秒/每分钟限制
- 使用 Redis 存储计数

### 配置

```python
# main.py
app.add_middleware(
    RateLimitMiddleware,
    requests_per_minute=60,  # 每分钟最大请求数
    requests_per_second=10,  # 每秒最大请求数
    enabled=True             # 是否启用
)
```

环境变量：

```env
RATE_LIMIT_ENABLED=true
RATE_LIMIT_PER_MINUTE=60
RATE_LIMIT_PER_SECOND=10
```

### 白名单路径

以下路径不受限流：

- `/health`
- `/docs`
- `/redoc`
- `/openapi.json`

### 限流响应

```json
{
  "code": 429,
  "message": "请求过于频繁，请稍后再试",
  "data": {
    "retry_after": 45
  }
}
```

响应头：`Retry-After: 45`

### 接口级限流

对特定接口设置更严格的限制：

```python
from app.middleware.rate_limit import endpoint_limiter

@router.post("/send-code")
@endpoint_limiter.limit("5/minute")  # 每分钟最多 5 次
async def send_code(request: Request, phone: str):
    pass

@router.post("/login")
@endpoint_limiter.limit("10/minute")  # 每分钟最多 10 次
async def login(request: Request, data: LoginRequest):
    pass
```

限流规则格式：`次数/时间单位`

| 示例 | 说明 |
|------|------|
| `5/minute` | 每分钟 5 次 |
| `100/hour` | 每小时 100 次 |
| `10/second` | 每秒 10 次 |
| `1000/day` | 每天 1000 次 |

---

## 请求日志

### 功能

- 记录每个请求的方法、路径、耗时
- 生成请求 ID 用于追踪
- 在响应头中添加调试信息

### 配置

```python
# main.py
app.add_middleware(RequestLogMiddleware)
```

### 日志格式

```
[a1b2c3d4] --> GET /api/v1/doctors ?page=1 | IP: 192.168.1.100
[a1b2c3d4] <-- GET /api/v1/doctors | Status: 200 | Duration: 45.23ms
```

### 响应头

```
X-Request-ID: a1b2c3d4
X-Response-Time: 45.23ms
```

### 排除路径

以下路径不记录日志：

- `/health`
- `/docs`
- `/redoc`
- `/openapi.json`

---

## 自定义中间件

### 创建中间件

```python
# app/middleware/custom.py
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request

class CustomMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, some_option: str = "default"):
        super().__init__(app)
        self.some_option = some_option
    
    async def dispatch(self, request: Request, call_next):
        # 请求前处理
        print(f"Before request: {request.url.path}")
        
        # 调用下一个中间件/路由
        response = await call_next(request)
        
        # 响应后处理
        response.headers["X-Custom-Header"] = "value"
        
        return response
```

### 注册中间件

```python
# main.py
from app.middleware.custom import CustomMiddleware

app.add_middleware(CustomMiddleware, some_option="custom_value")
```

---

## 最佳实践

1. **顺序重要**：注意中间件的注册顺序
2. **性能考虑**：中间件应尽量轻量
3. **异常处理**：中间件中的异常应妥善处理
4. **日志记录**：重要操作记录日志便于排查
5. **配置化**：通过环境变量控制中间件行为

