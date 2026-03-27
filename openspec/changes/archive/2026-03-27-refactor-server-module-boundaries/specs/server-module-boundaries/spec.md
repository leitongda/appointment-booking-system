## ADDED Requirements

### Requirement: Server 端必须按领域模块组织代码
系统 SHALL 将后端业务代码组织为按领域分包的模块化单体结构，以减少跨模块耦合并明确代码归属。

#### Scenario: 新增预约相关能力
- **WHEN** 开发者新增预约领域能力
- **THEN** 代码应放置在 `appointments` 领域模块下
- **AND** 不应继续将业务代码添加到全局扁平的 `api/v1` 或 `services` 大文件中

#### Scenario: 拆分现有超大文件
- **WHEN** 开发者重构现有超大 Router 或 Service
- **THEN** 应按领域职责拆分为多个较小文件
- **AND** 保持对外 API 行为不变

### Requirement: Router 层必须保持轻量
系统 SHALL 要求 Router 层仅负责 HTTP 协议适配、鉴权依赖、参数绑定与响应映射，不直接承担业务查询和业务 DTO 定义。

#### Scenario: 定义业务请求与响应模型
- **WHEN** 开发者为模块新增请求或响应结构
- **THEN** 应在模块 `schemas` 中定义 DTO
- **AND** 不应在 Router 文件中定义业务 `BaseModel`

#### Scenario: 处理复杂查询
- **WHEN** 接口需要执行复杂查询、聚合或报表逻辑
- **THEN** Router 应委托给 service 或 query 层
- **AND** Router 不应直接执行 `db.execute`、`db.scalar` 等 ORM 查询

### Requirement: 基础设施代码必须与领域逻辑分离
系统 SHALL 将邮件、微信、存储、Excel、Redis 等外部集成代码放置在基础设施层，避免与领域 Service 混杂。

#### Scenario: 新增对象存储能力
- **WHEN** 开发者实现新的上传或对象存储能力
- **THEN** 代码应放置于基础设施层
- **AND** 领域 Service 只能通过显式接口调用该能力

### Requirement: 运行期数据不得默认写入源码树
系统 SHALL 将日志、上传文件和其他运行期产物默认写入独立的运行时数据目录，而不是源码目录。

#### Scenario: 本地启动服务
- **WHEN** 开发者在本地启动 Server
- **THEN** 日志文件和上传文件应写入配置指定的运行时目录
- **AND** `apps/server` 源码目录不应成为默认运行期产物目录

### Requirement: 模块边界必须由自动化测试保护
系统 SHALL 提供自动化架构测试，防止 Router、Schema、Service、基础设施层职责再次漂移。

#### Scenario: 引入新的边界违规
- **WHEN** 开发者在 Router 文件中重新加入业务 DTO 或直接 ORM 查询
- **THEN** 架构测试应失败
- **AND** 阻止该边界违规进入主干
