# Server 架构说明

## 目标

当前服务端采用“模块化单体”结构，不做微服务拆分。目标是把业务实现从历史平铺目录收敛到稳定边界：

- `modules` 放领域代码
- `common` 放通用能力
- `infrastructure` 放外部适配
- `api/v1` 保留对外兼容入口

## 分层

### 1. `app/modules/*`

领域主代码位置。一个模块通常包含：

```text
modules/<domain>/
  router.py
  service.py / service_*.py
  schemas.py
  helpers.py
```

已迁移的核心领域包括：

- `admin`
- `appointments`
- `audit_logs`
- `auth`
- `content`
- `doctor_portal`
- `doctors`
- `messages`
- `patients`
- `rule_sets`
- `schedule_templates`
- `schedules`
- `settings`
- `statistics`
- `stores`
- `websocket`

### 2. `app/common/*`

放跨领域复用能力：

- `deps.py`
- `responses.py`
- `errors.py`
- `utils/`

原则：

- 可以被多个模块直接依赖
- 不承载具体业务语义

### 3. `app/infrastructure/*`

放外部系统适配层：

- `storage`
- `email`
- `sms`
- `excel`
- `image`
- `notification`
- `wechat`

原则：

- 业务模块依赖抽象适配，不直接知道实现细节
- 与第三方 SDK / 文件系统 / 对象存储 / 外部 API 的耦合尽量停在这里

### 4. `app/api/v1/*`

对外兼容入口。

对于已经迁移的资源，这里应保持“薄 wrapper”：

```python
from app.modules.<domain>.router import router
```

不应再继续放：

- 新的业务 DTO
- 直接 ORM 查询
- 复杂业务流程编排

## 服务层现状

`app/services/*` 目前处于过渡期：

- 已迁移文件优先作为兼容导出层
- 少数文件仍保留未完全收敛的历史实现

典型兼容导出示例：

- `rule_engine_service.py`
- `schedule_service.py`
- `schedule_template_service.py`
- `rule_set_service.py`
- `admin_service.py`
- `settings_service.py`
- `doctor_service.py`
- `message_service.py`
- `store_service.py`

## 运行期目录

运行期数据默认放在：

```text
apps/server/var/server/
  logs/
  uploads/
```

目的：

- 避免 `logs/`、`uploads/` 污染源码目录
- 让本地与部署环境的目录语义更明确

## 当前护栏

自动化测试已经覆盖：

- `api/v1` 已迁移 wrapper 保持薄层
- 已迁移 `services/*.py` 保持兼容导出，不重新塞回业务实现
- 关键模块兼容 smoke tests
- 全量 `pytest` 回归基线

## 兼容层删除标准

兼容层分两类：

### 1. 纯 wrapper

典型位置：

- `app/api/v1/*.py`
- 一部分 `app/services/*.py`

删除前必须同时满足：

1. 新实现已经稳定落在 `app/modules/*` 或 `app/infrastructure/*`
2. 工作区内不再有业务代码依赖旧路径
3. 自动化测试已经覆盖新路径的行为
4. 删除旧入口后，`pytest` 全量回归通过

### 2. facade

典型位置：

- `app/services/appointment_service.py`
- `app/services/patient_service.py`

这类文件允许暂时保留类名，但删除门槛更高：

1. 所有调用方已经切到模块内新 service
2. 测试里的 patch 点已经切到新路径，或有明确替代
3. 不再承担兼容 monkeypatch / import side effect 的职责
4. 删除后不会破坏历史 API 或测试基线

## 推荐删除顺序

建议按风险从低到高：

1. `app/services/storage/*`
2. 已迁移到 `infrastructure` 的适配层 wrapper
3. 已迁移到 `modules` 的简单 service wrapper
4. `app/services/appointment_service.py` / `app/services/patient_service.py` 这类 facade
5. `app/api/v1/*` 薄 wrapper

## 删除前检查

建议最少执行：

```bash
cd apps/server
rg "app\\.api\\.v1\\.|app\\.services\\." app tests
pytest -q
```

如果旧路径仍被引用，就不应删除对应兼容层。

## 后续方向

- 继续缩小 `admin` / `doctor_portal` / `import_export` 内部 router 文件
- 明确兼容层删除标准
- 在文档、OpenSpec、代码结构三者之间保持同步
