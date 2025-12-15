# 🖥️ 服务端开发指南

本文档详细介绍服务端各模块的使用方式和开发规范。

## 📚 目录

- [技术栈概览](#技术栈概览)
- [项目结构](#项目结构)
- [核心模块](#核心模块)
  - [配置管理](./config.md)
  - [Redis 缓存](./redis.md)
  - [日志系统](./logging.md)
  - [中间件](./middleware.md)
  - [异常处理](./exception.md)
  - [数据库操作](./database.md)
- [快速开始](#快速开始)

---

## 技术栈概览

| 类别 | 技术 | 版本 | 说明 |
|------|------|------|------|
| Web 框架 | FastAPI | 0.109.0 | 异步高性能框架 |
| ASGI 服务器 | Uvicorn | 0.27.0 | 支持异步 |
| 数据库 | PostgreSQL | 16 | 主数据库 |
| ORM | SQLAlchemy | 2.0.25 | 异步模式 |
| 缓存 | Redis | 7 | 验证码、Token 缓存 |
| 任务队列 | Celery | 5.3.6 | 异步任务 |
| 数据验证 | Pydantic | 2.5.3 | 请求/响应模型 |

---

## 项目结构

```
apps/server/
├── app/
│   ├── api/                    # API 路由
│   │   ├── deps.py             # 依赖注入
│   │   └── v1/                 # v1 版本 API
│   │       ├── __init__.py     # 路由注册
│   │       ├── auth.py         # 认证接口
│   │       ├── appointments.py # 预约接口
│   │       └── ...
│   ├── core/                   # 核心模块
│   │   ├── config.py           # 配置管理
│   │   ├── security.py         # 安全工具
│   │   ├── redis.py            # Redis 客户端
│   │   └── logging.py          # 日志配置
│   ├── db/                     # 数据库
│   │   ├── base.py             # 基础模型
│   │   └── session.py          # 会话管理
│   ├── middleware/             # 中间件
│   │   ├── response.py         # 统一响应
│   │   ├── exception.py        # 异常处理
│   │   ├── rate_limit.py       # 限流
│   │   └── request_log.py      # 请求日志
│   ├── models/                 # 数据模型
│   ├── schemas/                # Pydantic 模式
│   ├── services/               # 业务逻辑
│   ├── tasks/                  # Celery 任务
│   └── main.py                 # 应用入口
├── migrations/                 # 数据库迁移
├── logs/                       # 日志文件
├── requirements.txt            # 依赖
└── .env                        # 环境变量
```

---

## 快速开始

### 1. 环境准备

```bash
# 安装依赖
cd apps/server
pip install -r requirements.txt

# 启动 PostgreSQL 和 Redis
docker-compose up -d postgres redis
```

### 2. 配置环境变量

创建 `.env` 文件：

```env
# 环境
ENVIRONMENT=development
DEBUG=true

# 数据库
DATABASE_URL=postgresql+asyncpg://hospital:hospital123@localhost:5432/hospital_booking

# Redis
REDIS_URL=redis://localhost:6379/0

# JWT
SECRET_KEY=your-secret-key-change-in-production

# 日志
LOG_LEVEL=INFO
LOG_DIR=logs
```

### 3. 启动服务

```bash
# 开发模式
uvicorn app.main:app --reload --port 8000

# 生产模式
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### 4. 访问文档

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- 健康检查: http://localhost:8000/health

---

## 核心模块文档

| 文档 | 说明 |
|------|------|
| [配置管理](./config.md) | 环境变量、配置项说明 |
| [Redis 缓存](./redis.md) | 缓存操作、验证码、Token |
| [日志系统](./logging.md) | 日志配置、使用方式 |
| [中间件](./middleware.md) | 限流、请求日志、响应格式 |
| [异常处理](./exception.md) | 异常类型、错误码 |
| [数据库操作](./database.md) | ORM 使用、连接池 |

---

## 开发规范

### API 开发流程

1. 在 `schemas/` 定义请求/响应模型
2. 在 `services/` 实现业务逻辑
3. 在 `api/v1/` 创建路由
4. 在 `api/v1/__init__.py` 注册路由

### 代码风格

- 使用 `async/await` 异步编程
- 类型注解完整
- 函数/类添加文档字符串
- 使用 `logging` 记录日志，不用 `print`

---

**版本**: v1.0.0  
**更新日期**: 2024年

