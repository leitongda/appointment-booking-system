# 服务端开发指南

## 技术栈

| 类别 | 技术 | 说明 |
|------|------|------|
| Web | FastAPI | 主 HTTP / WebSocket 应用 |
| ORM | SQLAlchemy 2.x | 异步数据库访问 |
| DB | PostgreSQL | 主业务库 |
| Cache | Redis | Token、限流、分布式锁 |
| Task | Celery | 异步任务 |
| Validate | Pydantic v2 | 请求/响应模型 |

## 当前结构

`apps/server/app/` 现在按 3 层组织：

```text
app/
  api/
    v1/                  # 对外兼容入口，已迁移文件应保持薄 wrapper
  modules/               # 领域模块，放 router / service / schema / helper
  common/                # 通用依赖、错误、响应、工具
  infrastructure/        # 存储、邮件、短信、Excel、图片、微信等适配层
  core/                  # 配置、安全、日志、Redis、WebSocket
  db/                    # engine / session / base
  middleware/            # 统一响应、异常、限流、审计
  models/                # SQLAlchemy 模型
  schemas/               # 仍在使用的共享 Pydantic 模型
  tasks/                 # Celery / 异步任务
  main.py                # FastAPI 应用装配
```

详细分层说明见 [architecture.md](./architecture.md)。

## 关键约定

- `app/api/v1/*.py`：优先作为兼容入口，避免重新堆业务实现。
- `app/modules/<domain>/`：领域主代码入口，新增实现优先放这里。
- `app/services/*.py`：逐步收敛为兼容导出层；已迁移文件不应重新写业务逻辑。
- `app/infrastructure/*`：外部系统适配，不把邮件、短信、对象存储、Excel 直接塞回业务模块。
- 运行期数据默认写到 `apps/server/var/server/*`，不要再写回源码树。

## 本地启动

```bash
cd apps/server
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

常用地址：

- Swagger: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
- Health: `http://localhost:8000/health`

## 环境变量

参考：

- [config.md](./config.md)
- [architecture.md](./architecture.md)

重点变量：

```env
ENVIRONMENT=development
DEBUG=true
DATABASE_URL=postgresql+asyncpg://...
REDIS_URL=redis://localhost:6379/0
SECRET_KEY=...
LOG_LEVEL=INFO
LOG_DIR=var/server/logs
UPLOAD_DIR=var/server/uploads
```

## 相关文档

- [config.md](./config.md)
- [architecture.md](./architecture.md)
- [database.md](./database.md)
- [middleware.md](./middleware.md)
- [logging.md](./logging.md)
- [performance-monitoring.md](./performance-monitoring.md)
- [redis.md](./redis.md)
