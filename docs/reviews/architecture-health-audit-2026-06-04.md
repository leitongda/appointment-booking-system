# 架构健康度审计报告

**审计日期**: 2026-06-04
**项目**: appointment-booking-system (医院预约挂号系统)
**审计框架**: Well-Architected Framework + Tech Debt Analysis + Security Audit + Fitness Functions

---

## 总体评分

| 维度 | 评分 | 说明 |
|------|------|------|
| **整体架构设计** | B+ (78/100) | 模块化做得好，多租户设计成熟，但 God File 和循环依赖需要治理 |
| **代码质量** | C+ (65/100) | CRUD 重复严重，错误处理不一致，类型安全有缺口 |
| **安全性** | B (75/100) | 认证体系健全，但默认密码和 CORS 配置需加固 |
| **测试覆盖** | C+ (62/100) | 已有测试质量高，但 43% 模块零测试覆盖 |
| **文档** | D+ (50/100) | 文档严重滞后，仅 13% 模块有文档 |
| **运维成熟度** | B (77/100) | CI/CD 完善，监控到位，迁移管理需改进 |

---

## 1. 架构设计 — 关键发现

### 1.1 模块化架构（优势）

后端采用清晰的模块化设计：57 个业务模块，每个模块独立 `router.py` + `service.py`，复杂模块自动拆分为 `service_query.py` / `service_mutation.py`。路由注册使用声明式 `ROUTER_REGISTRATIONS` 列表 + 延迟导入，避免启动时循环依赖。中间件栈 10 层，职责分明，执行顺序合理。

**评分**: 优秀

### 1.2 God File 问题（需治理）

10 个文件超过 1000 行，职责过重：

| 文件 | 行数 | 问题 |
|------|------|------|
| `schedules/service_mutation.py` | 1,592 | 排班创建/修改/批量/通知/锁全在一个类 |
| `miniapp_platform/router.py` | 1,346 | 6 种资源类型的路由混在一个文件 |
| `tenants/router.py` | 1,189 | 租户 CRUD + 订阅 + 用量 + 通知 + 迁移 + 仪表盘 |
| `tenants/service.py` | 1,129 | 5 个独立 Service 类挤在一个文件 |
| `core/redis.py` | 1,140 | 缓存 + 分布式锁 + 限流 + 连接管理 |

**建议**: 按 SRP 拆分，每个 Service 类一个文件。

### 1.3 循环依赖（风险）

发现 5 组双向导入：

```
appointments <-> payments
appointments <-> refunds
appointments <-> waitlist
approval_flows <-> leave_requests
payments <-> refunds
```

部分通过函数内延迟导入缓解，但 `APPOINTMENT_STATUS` 常量从 `appointments/common.py` 被 `payments` 和 `refunds` 顶层导入，形成硬耦合。

**建议**: 将 `APPOINTMENT_STATUS` 等共享常量提取到 `constants/` 模块。

### 1.4 CRUD 代码重复（技术债务）

20+ 个模块独立实现了几乎相同的 `get_by_id` / `get_list` / `create` / `update` / `delete` 方法，没有 `BaseCRUDService` 或 Repository 模式。

**建议**: 引入泛型 `BaseCRUDService[Model, CreateSchema, UpdateSchema]`。

---

## 2. 代码质量 — 关键发现

### 2.1 错误处理不一致（严重）

三种错误机制并存：

| 机制 | 出现次数 | 问题 |
|------|---------|------|
| `BusinessError`（结构化） | 3 次 | 正确方式，但几乎没人用 |
| `HTTPException`（直抛） | 915 次 | 绕过统一错误信封 |
| `ValueError`（裸抛） | 322 次 | 未被捕获时变成 500 |

22 个模块的 router 完全没有 `try/except`。30+ 处使用 `except Exception` 吞掉错误。

### 2.2 错误码系统形同虚设

`ErrorCode` 定义了 16 个错误码，但仅在 3 个文件中使用。322 个 `ValueError` 携带的是中文字符串消息，前端无法做结构化分支。

**建议**: 逐步将 `ValueError` 替换为 `BusinessError(ErrorCode.XXX, message="...")`，制定迁移路线图。

### 2.3 类型安全缺口

- `lowcode` 模块 57 处 `Any` 类型
- 多个 service 方法的 `data` 参数无类型注解（`follow_up`, `patients`, `admin`）
- 删除策略不一致：部分软删除（`follow_up`），大部分硬删除，无基类统一

### 2.4 日志不一致

- 仅 `approval_flows` 使用 `structlog`
- 40 处使用 `logging.getLogger`
- 3 处仍用 `print()`
- 38/55 个模块完全没有日志

---

## 3. 安全性 — 关键发现

### 3.1 硬编码默认密码（HIGH）

**5 处使用 `"123456"` 作为默认密码**：

| 位置 | 场景 |
|------|------|
| `admin/service_admins.py:222` | 管理员创建 |
| `stores/service_mutation.py:30` | 门店创建 |
| `doctors/service_mutation.py:31` | 医生创建 |
| `import_export/router_import.py:133` | 批量导入用户 |
| `core/config.py:174` | `DEFAULT_USER_PASSWORD = "Hospital@2024"` |

密码策略验证器 (`password_policy.py`) 存在但未在这些路径调用。

### 3.2 CORS 配置（MEDIUM）

```python
allow_methods=["*"],  # 允许所有方法
allow_headers=["*"],  # 允许所有头
allow_credentials=True  # 允许凭证
```

`allow_credentials=True` + `allow_methods=["*"]` 组合在安全扫描中会被标记。

### 3.3 监控端口暴露（MEDIUM）

`docker-compose.monitoring.yml` 将 Prometheus (9090)、Grafana (3000)、Node Exporter (9100) 端口暴露到宿主机。Grafana 默认凭据可通过环境变量 `GF_ADMIN_USER` / `GF_ADMIN_PASSWORD` 覆盖。

### 3.4 限流可被静默禁用（MEDIUM）

`.env` 中 `RATE_LIMIT_ENABLED=false`，生产环境启动时仅警告不阻止。

### 3.5 良好实践

- 认证体系健全：JWT + Redis 黑名单 + 租户校验 + 角色路由
- SQL 注入：全部使用参数化查询，ORM 自动参数化
- Docker：非 root 用户、最小基础镜像、健康检查
- 依赖扫描：Trivy + Dependabot 周期性扫描

---

## 4. 前端架构 — 关键发现

### 4.1 依赖版本漂移（严重）

| 依赖 | admin | doctor | website |
|------|-------|--------|---------|
| React | 18 | 18 | **19** |
| Ant Design | **v6** | **v5** | - |
| pro-components | **v3 (预发布)** | **v2** | - |
| TypeScript | 5.6 | 5.3 | 5.7 |

- doctor 和 patient-h5 声明了 `zustand` 和 `@tanstack/react-query` 依赖但从未导入（死依赖）
- doctor app 存在**双重请求拦截器栈**（`@hospital/api` initApiConfig + umi 内置 request），可能是 bug 来源

### 4.2 组件重复

| 组件 | 重复次数 | 位置 |
|------|---------|------|
| EmailBindingModal | 3 次 | admin, doctor, patient-h5 |
| UI 组件库 (Button, Card, animations) | 3 次 | patient-h5, website, temp-registration |
| request.ts 拦截器逻辑 | 3 次 | admin, doctor, patient-h5 |

`animations.ts` 在三个应用中几乎完全相同（相同缓动曲线、相同变体名）。

### 4.3 测试覆盖极不均衡

| 应用 | 单元测试 | E2E 测试 |
|------|---------|---------|
| admin | 1 | **39 spec** |
| doctor | **0** | **0** |
| patient-h5 | **0** | 3 spec |
| miniapp-instance | **0** | **0** |
| temp-registration | **0** | **0** |

doctor 应用（118 个源文件）零测试。

---

## 5. 测试与文档 — 关键发现

### 5.1 后端测试

**已有测试质量高**（appointments, payments, lowcode 等模块测试深入），但覆盖面不足：

- **43% 的模块（27/62）零单元测试**
- `appointments` 有 9 个测试文件（优秀），`tenants` 仅 1 个 schema 测试
- 测试基础设施完善：内存 SQLite + mock Redis + factories

### 5.2 文档严重滞后

- `docs/server/architecture.md` 仍列出 16 个模块（实际 62 个）
- `docs/architecture.md` 引用了不存在的 Elasticsearch
- 62 个模块中仅 8 个有模块文档（13%）
- OpenAPI/Swagger 自动生成，保持最新

### 5.3 数据库迁移

- 126 个迁移文件，其中一个达 **6,492 行**（应拆分）
- 编号冲突：多个文件以 `004`、`007`、`058` 开头
- 命名风格不一致：部分用序号，部分用 Alembic hash

---

## 6. 枚举与常量治理

### 6.1 缺失枚举

| 领域 | 使用硬编码字符串 | 应有枚举 |
|------|----------------|---------|
| 退款状态 | `"pending"`, `"success"`, `"failed"` | `RefundStatus` |
| 审批流状态 | `"pending"` | `ApprovalInstanceStatus` |
| 支付状态 | `"pending"`, `"paid"` | `PaymentStatus` |
| 排班暂停处理 | `"pending"`, `"processing"` | `SuspensionProcessingStatus` |

### 6.2 枚举重复

- `ChannelType` 和 `NotificationChannel` 定义相同值（IN_APP, SMS, EMAIL...）
- `NotificationLogStatus` 和 `DeliveryStatus` 值重叠

---

## 优先级行动建议

### P0 — 必须修复（安全 / 稳定性）

| # | 行动 | 影响 |
|---|------|------|
| 1 | 消除硬编码默认密码 `"123456"`，统一使用密码策略验证器 | 5 处 |
| 2 | CORS 配置显式指定 `allow_methods` 和 `allow_headers` | main.py |
| 3 | Grafana 默认密码改为环境变量注入 | docker-compose.monitoring.yml |
| 4 | 生产环境限流禁用时拒绝启动（warning -> error） | main.py |

### P1 — 高优先级（技术债务治理）

| # | 行动 | 预期收益 |
|---|------|---------|
| 5 | 引入 `BaseCRUDService` 泛型基类，消除 20+ 模块的 CRUD 重复 | 减少 ~2000 行重复代码 |
| 6 | 将 `APPOINTMENT_STATUS` 等共享常量提取到 `constants/` | 打破循环依赖 |
| 7 | 统一错误处理：服务层用 `BusinessError`，router 层捕获 `ValueError` 转 `BusinessError` | 消除 322 处裸 ValueError |
| 8 | 拆分 God File（tenants/router.py, miniapp_platform/router.py, tenants/service.py） | 降低单文件复杂度 |

### P2 — 中优先级（质量提升）

| # | 行动 | 预期收益 |
|---|------|---------|
| 9 | doctor app 升级 antd v5 -> v6，移除双重拦截器 | 消除潜在 bug |
| 10 | 统一 React 版本（website 降级到 18 或其他升级到 19） | 消除 peer dependency 冲突 |
| 11 | 提取 `EmailBindingModal` 和 UI 组件库到 `@hospital/ui` 包 | 消除 3 处重复 |
| 12 | 为 27 个零测试模块补充基础单元测试 | 覆盖率提升到 80%+ |
| 13 | 更新 `docs/server/architecture.md` 和模块文档 | 文档与代码同步 |

### P3 — 低优先级（长期改进）

| # | 行动 | 预期收益 |
|---|------|---------|
| 14 | 统一日志方案（推荐 structlog） | 可观测性提升 |
| 15 | 补充缺失枚举（RefundStatus, PaymentStatus 等） | 类型安全提升 |
| 16 | 拆分 6492 行大迁移文件 | 迁移可维护性 |
| 17 | 移除未使用的 passlib 依赖 | 依赖清理 |
| 18 | Docker 容器启用 `read_only: true` + `cap_drop: ALL` | 安全加固 |
| 19 | 监控端口不暴露到宿主机（改用 Docker network） | 安全加固 |

---

## 架构 Fitness Functions 建议

可自动化的架构守护规则：

```python
# 1. 禁止模块间顶层循环导入
# 检查: modules/A/*.py 中 from modules/B import X 是否在 B 中反向导入

# 2. God File 阈值
# 规则: 单文件不超过 500 行（service）/ 300 行（router）

# 3. 错误处理一致性
# 规则: router.py 中不应有裸 HTTPException raise，应使用 BusinessError

# 4. 新模块必须有测试
# 规则: modules/X/ 存在时，tests/ 中必须有对应 test_X_*.py

# 5. API 路由必须有认证依赖
# 规则: 除 /public/* 和 /auth/* 外，所有路由需 get_current_account
```

---

## 结论

项目整体架构设计合理，模块化程度高，多租户体系成熟。主要技术债务集中在：

1. **CRUD 代码重复** — 缺少泛型基类，20+ 模块各自实现相同的增删改查
2. **错误处理碎片化** — 322 个裸 ValueError vs 仅 3 个结构化 BusinessError
3. **前端版本漂移** — React 18/19 混用、antd 5/6 混用、doctor app 零测试
4. **文档滞后** — 仅 13% 模块有文档，架构文档引用不存在的组件

建议按 P0 -> P1 -> P2 -> P3 优先级逐步治理，每轮聚焦 2-3 个改进项，避免一次性大规模重构带来的风险。
