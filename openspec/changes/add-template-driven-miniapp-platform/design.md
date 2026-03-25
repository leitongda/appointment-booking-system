## Context

当前仓库已有以下基础：
- 后端存在 `Tenant` 与 `Store` 模型，门店已带 `tenant_id`
- `Store` 上内嵌了 `wechat_app_id`、`wechat_app_secret`、`wechat_mch_id`、`wechat_api_key`、`wechat_notify_url`
- 患者端小程序通过构建时环境变量注入 `storeId/storeCode/storeName`
- 患者端 `project.config.json` 中的 `appid` 仍为单实例固定值

这说明系统已经具备“门店维度切微信配置”的雏形，但还没有形成“模板 -> 实例 -> 发布 -> 支付路由”的平台能力。

## Goals / Non-Goals

**Goals:**
- 支持多个模板服务多个客户，每个客户可生成一个或多个小程序实例
- 将实例配置与业务门店配置解耦
- 将支付主体与门店配置解耦，支持未来多主体结算
- 为构建、上传、发布建立可审计、可回滚的任务链路
- 为后续自动化发布和模板升级留出稳定模型

**Non-Goals:**
- 本次不直接实现完整微信支付 API 接入
- 本次不直接实现自动提审、自动发布的全部脚本细节
- 本次不重写患者端页面结构，只定义模板化边界
- 本次不要求一次性移除现有 `stores.wechat_*` 字段

## Decisions

### 1. 采用五层模型：模板、租户、实例、门店、支付配置

核心关系：

```text
Template
  -> MiniappInstance
Tenant
  -> Store
  -> Company / LegalEntity
  -> MiniappInstance
Company / LegalEntity
  -> PaymentProfile
MiniappInstance / Store
  -> PaymentRoute
```

说明：
- `Template` 负责页面结构、模块组合和默认主题
- `MiniappInstance` 负责具体小程序账号和发布信息
- `Store` 负责业务数据归属，不再直接承担全部微信和支付配置
- `PaymentProfile` 负责收款主体与支付参数

### 2. 模板与实例严格解耦

新增概念：
- `app_templates`: 模板定义
- `template_versions`: 模板版本
- `miniapp_instances`: 租户的小程序实例

约束：
- 一个模板可被多个租户复用
- 一个租户可创建多个实例
- 一个实例在任一时刻只使用一个模板版本
- 模板升级通过“实例选择目标版本 + 构建发布”完成

### 3. 支付配置独立建模，门店只做路由入口

新增概念：
- `companies` 或 `legal_entities`: 客户的公司主体
- `payment_profiles`: 支付配置
- `payment_routes`: 路由规则

建议字段：

```text
payment_profiles
- id
- tenant_id
- company_id
- mode                 # direct / service_provider
- app_id
- mch_id
- sub_mchid
- notify_url
- api_v3_key_ref
- cert_serial_no
- private_key_ref
- status
```

路由规则优先级：
1. 订单显式指定
2. 实例级默认支付配置
3. 门店级覆盖支付配置
4. 公司主体默认支付配置
5. 租户默认支付配置

订单创建时必须写入支付快照，避免回调时读取到被变更后的配置。

### 4. 构建与发布采用任务模型，而非手工修改配置文件

新增概念：
- `build_jobs`
- `release_jobs`
- `release_artifacts`

输入参数：
- `template_code`
- `template_version`
- `tenant_id`
- `miniapp_instance_id`
- 构建时环境变量集合

输出结果：
- 构建产物
- 目标 `appid`
- 上传版本号
- 提审状态
- 发布状态
- 回滚来源版本

### 5. 患者端改为“模板入口 + 实例注入”，不再仅依赖门店构建

患者端构建时配置改为至少包含：
- `TARO_APP_TEMPLATE_CODE`
- `TARO_APP_TEMPLATE_VERSION`
- `TARO_APP_TENANT_CODE`
- `TARO_APP_MINIAPP_INSTANCE_ID`
- `TARO_APP_STORE_ID` 或默认门店
- `TARO_APP_API_URL`

`project.config.json` 不再作为手工维护的最终真相，而由发布脚本或模板文件生成。

### 6. 采用兼容迁移策略

迁移分三阶段：

1. 新模型落库，但保留 `stores.wechat_*`
2. 管理后台支持配置模板、实例、支付配置和路由
3. 微信登录、支付、发布任务逐步改为读取新模型

兼容规则：
- 若实例级微信配置存在，优先使用实例级
- 否则回退到当前 `stores.wechat_*`
- 支付配置读取优先走 `payment_profiles/payment_routes`
- 若未配置则回退到 `stores.wechat_*`

## Data Model Sketch

```text
app_templates
- id
- code
- name
- description
- status
- default_config

template_versions
- id
- template_id
- version
- source_ref
- schema_version
- changelog
- status

miniapp_instances
- id
- tenant_id
- template_id
- template_version_id
- name
- app_id
- app_secret_ref
- default_store_id
- default_payment_profile_id
- upload_private_key_ref
- app_config
- status

payment_profiles
- id
- tenant_id
- company_id
- mode
- app_id
- mch_id
- sub_mchid
- notify_url
- api_v3_key_ref
- cert_serial_no
- private_key_ref
- status

payment_routes
- id
- tenant_id
- store_id
- miniapp_instance_id
- payment_profile_id
- priority
- status

build_jobs
- id
- tenant_id
- miniapp_instance_id
- template_version_id
- trigger_source
- build_params
- status
- started_at
- finished_at
- artifact_id

release_artifacts
- id
- build_job_id
- file_path
- checksum
- metadata

release_jobs
- id
- miniapp_instance_id
- artifact_id
- action           # upload / submit_audit / publish / rollback
- target_version
- result
- status
```

## Risks / Trade-offs

| 风险 | 缓解措施 |
|------|----------|
| 模型引入后初期概念增多 | 在后台按“模板 / 实例 / 支付”三个中心组织信息架构 |
| 与现有门店级微信配置并存，短期可能双写 | 通过兼容层和迁移任务控制写入优先级 |
| 模板化过早导致前端结构复杂 | 第一阶段只抽配置与构建边界，不一次性做完全插件化 |
| 发布任务依赖外部工具与凭证 | 先定义任务模型与状态机，后续再接真实 CI |
| 支付主体路由错误会带来财务风险 | 路由结果写入订单快照，支付回调按订单快照校验 |

## Rollout Plan

### Phase 1: 模型与配置中心
- 新增模板、实例、支付配置、发布任务相关表
- 搭建管理端最小配置页面
- 建立读取兼容层

### Phase 2: 构建发布流水线
- 新增模板化构建脚本
- 生成实例级 `project.config.json`
- 打通上传任务与状态跟踪

### Phase 3: 业务链路切换
- 微信登录改为以实例配置为主
- 支付下单改为走支付路由
- 发布、回滚、版本对比进入后台

## Open Questions

- 模板版本的来源是 Git ref、制品包还是工作区目录快照
- 是否允许一个租户的多个实例共享同一支付配置
- 管理端是否需要“从现有门店配置一键生成实例/支付配置”的初始化工具
