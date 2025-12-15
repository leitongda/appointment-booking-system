# ⚠️ 异常处理

## 概述

异常处理模块位于 `app/middleware/exception.py`，提供：

- 统一的异常响应格式
- 自定义业务异常类
- 全局异常捕获

---

## 异常类型

### 业务异常 (BusinessError)

用于业务逻辑错误，返回 400 状态码：

```python
from app.middleware.exception import BusinessError

# 抛出业务异常
raise BusinessError("预约号源已满")
raise BusinessError("该时段已有预约", code=400)
```

响应：
```json
{
  "code": 400,
  "message": "预约号源已满",
  "data": null
}
```

### 认证异常 (AuthenticationError)

用于认证失败，返回 401 状态码：

```python
from app.middleware.exception import AuthenticationError

raise AuthenticationError("Token 已过期")
raise AuthenticationError("无效的登录凭证")
```

响应：
```json
{
  "code": 401,
  "message": "Token 已过期",
  "data": null
}
```

### 权限异常 (PermissionDeniedError)

用于权限不足，返回 403 状态码：

```python
from app.middleware.exception import PermissionDeniedError

raise PermissionDeniedError("无权访问该资源")
raise PermissionDeniedError("需要管理员权限")
```

响应：
```json
{
  "code": 403,
  "message": "无权访问该资源",
  "data": null
}
```

### 资源不存在 (NotFoundError)

用于资源未找到，返回 404 状态码：

```python
from app.middleware.exception import NotFoundError

raise NotFoundError("医生不存在")
raise NotFoundError("预约记录未找到")
```

响应：
```json
{
  "code": 404,
  "message": "医生不存在",
  "data": null
}
```

---

## 错误码规范

| 错误码 | 说明 | 对应异常 |
|--------|------|----------|
| 200 | 成功 | - |
| 400 | 业务错误 | BusinessError |
| 401 | 认证失败 | AuthenticationError |
| 403 | 权限不足 | PermissionDeniedError |
| 404 | 资源不存在 | NotFoundError |
| 422 | 参数验证失败 | RequestValidationError |
| 429 | 请求过于频繁 | 限流中间件 |
| 500 | 服务器错误 | Exception |

---

## 使用示例

### 在 Service 中使用

```python
# app/services/appointment_service.py
from app.middleware.exception import BusinessError, NotFoundError

class AppointmentService:
    async def create(self, user_id: str, data: dict):
        # 检查排班是否存在
        schedule = await self.get_schedule(data.schedule_id)
        if not schedule:
            raise NotFoundError("排班不存在")
        
        # 检查号源
        if schedule.booked >= schedule.max_patients:
            raise BusinessError("该时段号源已满")
        
        # 检查重复预约
        existing = await self.check_duplicate(user_id, data)
        if existing:
            raise BusinessError("您已预约该时段，请勿重复预约")
        
        # 创建预约
        return await self._do_create(data)
```

### 在 API 中使用

```python
# app/api/v1/appointments.py
from app.middleware.exception import BusinessError

@router.post("")
async def create_appointment(
    data: AppointmentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    service = AppointmentService(db)
    
    # 异常会被全局处理器捕获，无需 try-except
    appointment = await service.create(current_user["id"], data)
    
    return appointment
```

### 手动处理异常

```python
from fastapi import HTTPException

@router.get("/{id}")
async def get_item(id: str):
    item = await service.get_by_id(id)
    
    # 方式1: 使用自定义异常
    if not item:
        raise NotFoundError("资源不存在")
    
    # 方式2: 使用 FastAPI HTTPException（也会被统一处理）
    if not item:
        raise HTTPException(status_code=404, detail="资源不存在")
    
    return item
```

---

## 参数验证错误

Pydantic 验证失败时自动捕获：

请求：
```json
{
  "phone": "invalid",
  "age": "not_a_number"
}
```

响应：
```json
{
  "code": 422,
  "message": "body -> phone: 手机号格式不正确",
  "data": {
    "errors": [
      {
        "loc": ["body", "phone"],
        "msg": "手机号格式不正确",
        "type": "value_error"
      }
    ]
  }
}
```

---

## 数据库异常

自动捕获 SQLAlchemy 异常：

```python
# 唯一约束冲突
{
  "code": 400,
  "message": "数据已存在或违反约束条件",
  "data": null
}

# 其他数据库错误
{
  "code": 500,
  "message": "数据库操作失败",
  "data": null
}
```

---

## 全局异常兜底

未被其他处理器捕获的异常：

```json
{
  "code": 500,
  "message": "服务器内部错误",
  "data": null
}
```

**注意**：生产环境不会暴露详细错误信息，但会记录到日志。

---

## 自定义异常

```python
# app/middleware/exception.py

class RateLimitError(Exception):
    """限流异常"""
    def __init__(self, message: str = "请求过于频繁", retry_after: int = 60):
        self.message = message
        self.retry_after = retry_after
        super().__init__(message)

# 添加处理器
async def rate_limit_exception_handler(request: Request, exc: RateLimitError):
    return JSONResponse(
        status_code=429,
        content={
            "code": 429,
            "message": exc.message,
            "data": {"retry_after": exc.retry_after}
        },
        headers={"Retry-After": str(exc.retry_after)}
    )

# 注册处理器
def register_exception_handlers(app):
    # ... 其他处理器
    app.add_exception_handler(RateLimitError, rate_limit_exception_handler)
```

---

## 最佳实践

1. **使用自定义异常**：优先使用 `BusinessError` 等自定义异常，而非 `HTTPException`
2. **清晰的错误信息**：错误信息应该对用户友好，便于理解
3. **不暴露敏感信息**：生产环境不要返回堆栈信息
4. **日志记录**：所有异常都会自动记录日志
5. **异常分层**：Service 层抛出业务异常，API 层不需要 try-except

