# 🔴 Redis 缓存

## 概述

Redis 缓存模块位于 `app/core/redis.py`，提供统一的缓存操作接口，支持：

- 短信验证码存储与验证
- 微信 access_token 缓存
- 扫码登录状态管理
- 通用键值缓存

---

## 快速使用

### 导入

```python
from app.core.redis import cache, get_redis, RedisCache
```

### 基础操作

```python
# 设置缓存（自动 JSON 序列化）
await cache.set("user:123", {"name": "张三", "age": 30}, expire=3600)

# 获取缓存（自动 JSON 反序列化）
data = await cache.get("user:123")
# {"name": "张三", "age": 30}

# 获取缓存（带默认值）
data = await cache.get("not_exists", default={})

# 删除缓存
await cache.delete("user:123")

# 检查是否存在
exists = await cache.exists("user:123")

# 获取剩余过期时间
ttl = await cache.ttl("user:123")  # 返回秒数

# 自增
count = await cache.incr("counter:visits")
```

---

## 短信验证码

### 发送验证码

```python
from app.services.sms_service import SmsService

# 发送验证码（自动存储到 Redis）
code = await SmsService.send_code("13800138000", code_type="login")
# 返回验证码（开发环境调试用）
```

### 验证验证码

```python
# 验证验证码
is_valid = await SmsService.verify_code("13800138000", "123456", code_type="login")
# True / False
```

### 底层 API

```python
from app.core.redis import cache

# 存储验证码（5分钟过期）
await cache.set_sms_code("13800138000", "123456", code_type="login", expire=300)

# 获取验证码
data = await cache.get_sms_code("13800138000", code_type="login")
# {"code": "123456", "verified": False}

# 验证验证码（验证后标记为已使用）
is_valid = await cache.verify_sms_code("13800138000", "123456", code_type="login")

# 检查发送频率（60秒内只能发送一次）
can_send, remaining = await cache.check_sms_rate_limit("13800138000", "login", interval=60)
if not can_send:
    raise ValueError(f"请 {remaining} 秒后重试")
```

### 验证码类型

| 类型 | 说明 |
|------|------|
| `login` | 登录验证码 |
| `register` | 注册验证码 |
| `reset` | 重置密码验证码 |
| `bindPhone` | 绑定手机验证码 |

---

## 微信 Token 缓存

```python
from app.core.redis import cache

# 缓存 access_token（7000秒，接近 7200 秒有效期）
await cache.set_wechat_token("wx_appid_xxx", "access_token_xxx", expire=7000)

# 获取缓存的 token
token = await cache.get_wechat_token("wx_appid_xxx")
# 返回 token 或 None
```

### 在微信服务中的使用

`WechatService` 已自动集成缓存：

```python
from app.services.wechat_service import WechatService

service = WechatService(db)

# 自动使用缓存，缓存未命中时调用微信 API
token = await service._get_access_token()
```

---

## 扫码登录

```python
from app.core.redis import cache
import uuid

# 生成扫码 ID
scan_id = str(uuid.uuid4())

# 设置扫码状态（5分钟过期）
await cache.set_scan_login(scan_id, {
    "status": "pending",  # pending / scanned / confirmed / expired
    "created_at": "2024-01-01T12:00:00"
}, expire=300)

# 获取扫码状态
data = await cache.get_scan_login(scan_id)

# 更新状态（用户扫码后）
await cache.set_scan_login(scan_id, {
    "status": "scanned",
    "user_id": "user_123"
}, expire=300)

# 确认登录后删除
await cache.delete_scan_login(scan_id)
```

---

## 通用缓存

### 缓存热点数据

```python
# 缓存科室列表（1小时）
departments = await department_service.get_all()
await cache.set("cache:departments:all", departments, expire=3600)

# 读取缓存
cached = await cache.get("cache:departments:all")
if cached:
    return cached

# 缓存未命中，查询数据库
departments = await department_service.get_all()
await cache.set("cache:departments:all", departments, expire=3600)
return departments
```

### 缓存装饰器（示例）

```python
from functools import wraps
from app.core.redis import cache

def cached(key_prefix: str, expire: int = 3600):
    """缓存装饰器"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 构建缓存键
            cache_key = f"{key_prefix}:{hash(str(args) + str(kwargs))}"
            
            # 尝试从缓存获取
            cached_result = await cache.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            # 执行函数
            result = await func(*args, **kwargs)
            
            # 存入缓存
            await cache.set(cache_key, result, expire)
            return result
        return wrapper
    return decorator

# 使用
@cached("departments", expire=3600)
async def get_departments():
    # 查询数据库
    pass
```

---

## 键前缀规范

| 前缀 | 说明 | 示例 |
|------|------|------|
| `sms:` | 短信验证码 | `sms:13800138000:login` |
| `wechat:token:` | 微信 Token | `wechat:token:wx_appid` |
| `scan:login:` | 扫码登录 | `scan:login:uuid` |
| `session:` | 用户会话 | `session:user_123` |
| `cache:` | 通用缓存 | `cache:departments:all` |
| `ratelimit:` | 限流计数 | `ratelimit:ip:second:123` |

---

## 直接使用 Redis 客户端

```python
from app.core.redis import get_redis

redis = await get_redis()

# 原生 Redis 操作
await redis.set("key", "value")
await redis.get("key")
await redis.hset("hash", "field", "value")
await redis.lpush("list", "item")
await redis.sadd("set", "member")
```

---

## 注意事项

1. **连接管理**：使用 `get_redis()` 获取共享连接，不要手动创建
2. **序列化**：`cache.set/get` 自动处理 JSON 序列化
3. **过期时间**：建议所有缓存都设置过期时间
4. **异常处理**：Redis 不可用时，缓存操作会记录日志但不会抛出异常
5. **键命名**：使用统一的前缀规范，便于管理和清理

