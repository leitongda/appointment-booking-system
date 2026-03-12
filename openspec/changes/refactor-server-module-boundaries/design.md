## Context

当前 Server 端仍遵循“Router / Service / Model / Schema”四层思路，但实际代码已经出现以下问题：
- Router 层同时承担 DTO 定义、ORM 查询和返回拼装
- Service 层同时承担领域逻辑、查询逻辑和基础设施编排
- 同一领域相关类型和服务分散在多个文件中，命名不稳定
- `admin.py`、`appointment_service.py`、`patient_service.py`、`import_export.py` 等核心文件体积已明显超出易维护范围
- 默认日志与上传目录位于 `apps/server` 源码树中，导致工作树容易被运行时产物污染

## Goals / Non-Goals

**Goals:**
- 建立清晰、稳定、可测试的后端模块边界
- 将后端组织方式调整为按领域分包的模块化单体
- 为后续功能迭代提供统一的放置规则
- 用自动化测试保证边界不再回退

**Non-Goals:**
- 不改公开 API 路径、请求字段、响应字段
- 不改数据库表结构和业务规则
- 不引入微服务、事件总线重构或大规模 DDD 仓储模式
- 不在本次变更中全面重写所有业务逻辑

## Decisions

### 1. 采用“模块化单体”作为目标结构

目标目录：

```text
apps/server/app/
  modules/
    admin/
      router.py
      schemas.py
      service.py
      queries.py
    appointments/
      router.py
      schemas.py
      service.py
      queries.py
    content/
    doctors/
    patients/
    scheduling/
    rules/
    settings/
  infrastructure/
    db/
    redis/
    storage/
    email/
    wechat/
  common/
    deps/
    responses/
    errors/
    utils/
  main.py
```

**理由：**
- 保留当前单体部署和事务模型，避免过度设计
- 让“代码放哪里”由业务领域决定，而不是由技术层目录决定
- 支持分阶段迁移，兼容现有 import 和 API 聚合方式

### 2. 明确每层职责

- `router.py`: HTTP 协议适配、鉴权依赖、参数绑定、响应模型声明
- `schemas.py`: 请求与响应 DTO
- `service.py`: 用例编排和业务规则
- `queries.py`: 复杂只读查询和报表查询
- `infrastructure/*`: 邮件、微信、存储、Redis、Excel 等外部集成

**约束：**
- Router 不直接 import ORM Model 进行业务查询
- Router 不直接执行 `db.execute` / `db.scalar`
- 业务 DTO 不再定义在 Router 文件中

### 3. 采用“兼容导出 + 渐进迁移”策略

- 第一阶段先建立新目录和约束测试
- 第二阶段迁移低风险模块作为模板
- 第三阶段拆分超大文件并按领域搬迁
- 过渡期允许旧路径文件保留兼容导入，直到模块迁移完成

**理由：**
- 降低一次性大改的回归风险
- 便于在有未提交分支变更的情况下并行推进

### 4. 运行期数据默认迁出源码树

新增明确配置项：
- `RUNTIME_DATA_DIR`
- `LOG_DIR`
- `LOCAL_UPLOAD_DIR`

默认目标：
- 日志：`<runtime-data-dir>/logs`
- 上传：`<runtime-data-dir>/uploads`

**理由：**
- 源码目录应只承载源文件与受版本控制的资源
- 便于容器挂载、部署和本地清理

### 5. 用架构测试固化边界

新增测试检查：
- `api` / `router` 文件中不得定义业务 `BaseModel`
- `api` / `router` 文件中不得直接调用 `db.execute`、`db.scalar`
- 新模块必须使用标准目录结构

**理由：**
- 没有自动化约束，目录会很快再次漂移

## Risks / Trade-offs

| 风险 | 缓解措施 |
|------|----------|
| 分阶段迁移期间会出现新旧结构并存 | 通过兼容导入和迁移清单控制范围 |
| 文件搬迁可能引入 import 错误 | 先补特征测试，再按模块迁移 |
| 结构重组短期内不直接产出业务价值 | 优先处理高耦合热点模块，降低后续迭代成本 |
| 与当前未提交规则引擎改动产生冲突 | 先避开已有脏文件，优先处理低风险模块 |

## Migration Plan

1. 建立 OpenSpec 变更、实施计划和架构约束测试
2. 迁移低风险模块作为模板：`content`、`booking_notices`、`store_email_recipients`
3. 拆分超大 Router：`admin`、`import_export`、`doctor_portal`
4. 拆分超大 Service：`appointment_service`、`patient_service`
5. 落地运行期目录配置并更新文档
6. 批量迁移剩余模块，删除兼容层

## Open Questions

- 统计报表类接口是否统一进入 `queries.py`，还是单独拆为 `read_service.py`
- `models/` 是否保留集中目录，还是后续按领域下沉到模块内部
