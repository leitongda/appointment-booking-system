# ⚙️ 配置管理

## 概述

配置管理模块位于 `app/core/config.py`，使用 Pydantic Settings 实现，支持环境变量和 `.env` 文件。

## 配置项说明

### 基础配置

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `PROJECT_NAME` | str | "医院挂号系统" | 项目名称 |
| `API_V1_STR` | str | "/api/v1" | API 前缀 |
| `DEBUG` | bool | false | 调试模式 |
| `ENVIRONMENT` | str | "development" | 环境：development/staging/production |

### 数据库配置

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `DATABASE_URL` | str | - | 异步数据库连接 URL |
| `DB_POOL_SIZE` | int | 10 | 连接池大小 |
| `DB_MAX_OVERFLOW` | int | 20 | 最大溢出连接数 |
| `DB_POOL_TIMEOUT` | int | 30 | 获取连接超时（秒） |
| `DB_POOL_RECYCLE` | int | 1800 | 连接回收时间（秒） |

### Redis 配置

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `REDIS_URL` | str | "redis://localhost:6379/0" | Redis 连接 URL |

### JWT 配置

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `SECRET_KEY` | str | - | JWT 密钥（生产环境必须修改） |
| `ALGORITHM` | str | "HS256" | JWT 算法 |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | int | 30 | Access Token 过期时间 |
| `REFRESH_TOKEN_EXPIRE_DAYS` | int | 7 | Refresh Token 过期时间 |

### 限流配置

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `RATE_LIMIT_ENABLED` | bool | true | 是否启用限流 |
| `RATE_LIMIT_PER_MINUTE` | int | 60 | 每分钟最大请求数 |
| `RATE_LIMIT_PER_SECOND` | int | 10 | 每秒最大请求数 |

### 日志配置

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `RUNTIME_DATA_DIR` | str | "var/server" | 运行期数据根目录 |
| `LOG_LEVEL` | str | "INFO" | 日志级别 |
| `LOG_DIR` | str | "var/server/logs" | 日志目录 |
| `LOG_JSON_FORMAT` | bool | false | 是否使用 JSON 格式 |

### 存储配置

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `STORAGE_TYPE` | str | "local" | 存储类型 |
| `LOCAL_UPLOAD_DIR` | str | "var/server/uploads" | 本地上传目录 |
| `LOCAL_PUBLIC_URL` | str | None | 本地上传的公网访问地址 |

### 微信配置

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `WECHAT_APP_ID` | str | None | 小程序 AppID |
| `WECHAT_APP_SECRET` | str | None | 小程序 Secret |

### 业务配置

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `APPOINTMENT_REMINDER_HOURS` | int | 24 | 就诊提醒提前小时数 |
| `SCHEDULE_AUTO_GENERATE_DAYS` | int | 14 | 自动生成排班天数 |

---

## 使用方式

### 导入配置

```python
from app.core.config import settings

# 使用配置
print(settings.PROJECT_NAME)
print(settings.DATABASE_URL)
print(settings.DEBUG)
```

### 环境变量文件

创建 `.env` 文件（不要提交到 Git）：

```env
# .env
ENVIRONMENT=production
DEBUG=false
SECRET_KEY=your-super-secret-key-here
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/dbname
REDIS_URL=redis://redis-host:6379/0
LOG_LEVEL=WARNING
LOG_JSON_FORMAT=true
RUNTIME_DATA_DIR=var/server
LOG_DIR=var/server/logs
LOCAL_UPLOAD_DIR=var/server/uploads
```

### 动态属性

配置类提供了一些动态计算的属性：

```python
# 同步数据库 URL（Celery 使用）
sync_url = settings.SYNC_DATABASE_URL

# Celery 配置
broker_url = settings.CELERY_BROKER_URL
result_backend = settings.CELERY_RESULT_BACKEND
```

---

## 环境区分

### 开发环境

```env
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=DEBUG
RATE_LIMIT_ENABLED=false
```

### 生产环境

```env
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=WARNING
LOG_JSON_FORMAT=true
RATE_LIMIT_ENABLED=true
RATE_LIMIT_PER_MINUTE=100
```

---

## 最佳实践

1. **敏感配置**：`SECRET_KEY`、数据库密码等必须通过环境变量配置
2. **不同环境**：使用不同的 `.env` 文件或环境变量
3. **配置验证**：Pydantic 会自动验证配置类型
4. **默认值**：为非敏感配置提供合理的默认值
5. **运行期数据隔离**：日志和上传文件应落在 `var/server/` 之类的运行期目录，而不是源码目录
