# appointment-booking-system — 自适应多智能体研究画布

> 协作模式：对等协作（Peer Collaboration）
> 日期：2026-06-28
> 审查目标：查看核心功能开发情况、补齐日常操作差缝隙、丰富应用、规划任务、排查可优化点

---

## 模式选择

**选定模式：** 对等协作

**选择理由：** 5 个子目标（功能盘点/操作缝隙/丰富应用/规划任务/优化点排查）横跨产品/设计/技术三方，无单一主导领域；历史 review 已 70+ 篇，需三方互评 + Critic 质询挖出跨域问题；任务要求收敛决策，适合投票矩阵 + 共识收敛。

---

## Round 1：事实层（只写事实，不评价）

### PM — 产品视角

**产品定位：**
- 自述为「全栈医院预约挂号系统，SaaS 多租户架构，支持多门店/分院、多科室、多医生排班预约」（`CLAUDE.md:14`）
- 声称核心领域：多门店管理、智能排班、在线预约挂号、就诊管理、病历管理、诊费配置（`README.md:7`）
- 明确非目标：HIS 深度集成、完整支付通道（「记录为主」）、实时音视频问诊、医院内部财务核算报表（`DESIGN.md:11-14`）

**功能完成度（重点核对）：**
- admin 端 13 个一级模块路由声明页面目录均存在，核心业务模块已实现（`apps/admin/config/routes/*`）
- **考勤「假期管理/假期申请」前端页面从未创建**：`attendance.ts:97-111` 注释「pages were never created … breaks umi route resolution and aborts dev. Commented out」，后端 `attendance_leave` 模块已注册（`__init__.py:56`）→ 后端已实现、前端缺失
- 后端 `ROUTER_REGISTRATIONS` 实际 76 条（`api/v1/__init__.py:16-148`），与 README「60 条」、CLAUDE「82/81」均不符
- 后端占位/stub：低代码部署 stub（`deploy_service.py:49`，`# TODO 微信开发版上传接口` :290）、短信腾讯云 provider 未实现（`sms/factory.py:23`）、通知模板系统未集成（`dispatcher.py:221`）、统一消息接收人规则三处「未实现」warning（`rule_engine.py:143,171,226`）、captcha 校验占位（`tenants/router_current_tenant.py:100`）

**后端孤岛功能（实现但前端无消费）：**
- **doctor-reviews（医生评价）**：后端 router 完整 create/get/reply（`modules/doctor_reviews/router.py:19-118`），注册 `__init__.py:118`；`packages/api/src/modules/` 无对应模块，患者端无评价入口
- **appointment_satisfactions（预约满意度）**：后端含提交/查询（`router.py:15-77`），注册 `__init__.py:119`；前端无对应 API 模块与页面；就诊完成时后端推送满意度调查站内信（`service_flow.py:268-278`），但患者无处填写

**挂号流程状态跳转通知覆盖（缝隙事实）：**
| 状态跳转 | 站内信 | 微信订阅 | 邮件 | WebSocket | 来源 |
|---|---|---|---|---|---|
| 预约创建 | 有 | 有 | — | — | `service_booking.py:322,354` |
| 签到 checkin | — | — | 有 | — | `service_flow.py:115` |
| 叫号 | 有 | 有 | 有 | — | `service_flow.py:192,222,242` |
| 就诊完成 | 有 | **无** | 有 | 有 | `service_flow.py:258,280,297` |
| 爽约 no_show | **无** | **无** | 有 | — | `service_flow.py:351` |
| 取消 | 有 | 有 | — | — | `service_booking.py:538,563` |

**功能不对齐/重复实现：**
- 患者端三个并行实现：patient-h5（17 目录/32 tsx）、patient-miniapp（6 目录：appointment/doctor/department/profile/index/lowcode）、mini-appointment-miniapp（3 目录：home/profile/scan）。patient-miniapp 缺 booking/records/message/feedback/follow-up/search/register/waitlist/guide 等
- 临时挂号两端重叠：temp-registration（Umi H5）与 mini-appointment-miniapp（Taro 小程序）
- 消息系统两套并存：`messages`（旧）与 `unified_message`（新），`compat.py` 兼容层（`service_flow.py:181` 经 `MessageServiceCompat` 调用）

**reviews/ 历史主题密度：** 排班域 9 次、租户/权限 8 次、通知/消息 7 次、低代码/工作流/审批 6 次（共 73 篇）

**目标用户线索：**
- 角色链：SUPER_ADMIN / STORE_ADMIN / STORE_USER（`apps/admin/src/access.ts:9-11`）、医生（`/doctor-portal`）、患者/访客
- 多租户 4 种识别（Header X-Tenant-ID > Code > 子域名 > 路径前缀，`CLAUDE.md:230-236`），`SubscriptionPlan` 控功能与用量
- 运营看板：`/platform/operations-dashboard`、`platform_metrics`、`analytics`、`revenue`、Celery 22 个 beat 任务含租户用量/门店指标

---

### Designer — 用户视角

**页面清单与结构：**
- admin：48 个页面入口组件，tsx 共 66570 行，最大 `system/rule-set-form.tsx`（1665 行）、`system/settings.tsx`（1474 行，一组件承载医院/微信/邮件/图片/短信/安全/号源释放 7 类配置）、`lowcode/editor/components/PropertyPanel.tsx`（1303 行）
- doctor：约 17 路由，tsx 4112 行，最大 `consultation/index.tsx`（528 行）
- patient-h5：约 30 路由，tsx 7200 行
- patient-miniapp：主包 5 页 + 3 分包共 31 页（`app.config.ts:13-68`）

**技术栈不一致（跨端）：**
| 端 | 框架 | UI 库 |
|---|---|---|
| admin | umi/max + ProComponents 3.1.12 | antd ^6.3.7 |
| doctor | umi + ProComponents ^2.6.43 | antd ^5.13.1 |
| patient-h5 | umi + Tailwind + framer-motion | antd-mobile ^5.34.0 |
| patient-miniapp | Taro 4.2.0 | @nutui/nutui-react-taro 3.0.18 |

同一 monorepo 内 antd 主版本 v5/v6 并存。

**反馈组件统计：**
| 端 | message.* | Modal.confirm | Popconfirm | 原生 alert/confirm |
|---|---|---|---|---|
| admin | 743（success 294/error 360） | 26 | 218 | 0 原生 |
| doctor | 88 | 4 | — | 0 |
| patient-h5 | Toast/Dialog 116 | — | — | 0 |
| patient-miniapp | showToast/showModal 128 | — | — | — |

**统一请求拦截器差异（核心缝隙）：**
- admin：401/403/404/5xx/业务错误/网络错误全部 message.error 提示（`utils/request.ts:142-247`）
- **patient-h5：仅 401/403 租户暂停/网络错误提示；404、5xx、403 非租户场景只 console.warn/error 不提示用户；业务错误直接 reject 不提示**（`utils/request.ts:147-161,190-204`）
- "请求失败只 console 不提示"模式：admin 68 个文件、patient-h5（`appointment/index.tsx:47-49`、`records/index.tsx:43-45`）、patient-miniapp（`doctor/index.tsx:44-46`）

**loading/空状态覆盖：**
- admin：Spin 106 / loading= 160 / setLoading 325 / Skeleton 33；ProTable 列表页（75 个 ProTable + 32 个 Table）依赖 ProTable 自带 loading
- patient-h5：Skeleton（Paragraph 骨架屏）36 处，列表页均有 loading+Empty
- patient-miniapp：**无 Skeleton**，用 NutUI Loading

**响应式设计（事实）：**
- admin 源码仅 3 处 @media，断点不统一（575/768/1200px）；**无 viewport meta 配置**（`config/config.ts:88-93`）；数据大屏固定 1920px（`screen/index.less:79`）
- doctor 源码 0 处 @media
- patient-h5：0 处 @media，tailwind 响应式前缀仅 17 处
- 固定宽度：admin 22 处（值分散 1920/768/480/400/300…）

**无障碍（事实）：**
- aria-* 总数：admin 40、patient-h5 50；role 属性：admin 26、patient-h5 23
- **图片 alt 大面积缺失**：admin 7 个 `<img>` 中 6 个无 alt（lowcode 头像渲染 `BaseRenderer.tsx:513,542,560`、`SchemaRenderer.tsx:886,949,967`），1 个 alt 空字符串（`contacts/index.tsx:224`）

**组件一致性（事实）：**
- admin 硬编码颜色 `#xxx` **1164 处**，CSS 变量仅 11 处（间距非颜色），antd useToken 仅 16 处
- **主色双标**：同时存在 `#1677ff`（55 次，antd v6 主色）与 `#1890ff`（49 次，antd v5 主色）两种主色
- 主题配置仅设间距不设颜色（`themes/themeConfig.ts:10-19`，未配 colorPrimary）
- 样例 `doctor/list.tsx:68-114` 内联硬编码 6 种颜色

**ProTable 配置不统一：** search 配置混用（`search={false}` vs `search={{ labelWidth: 'auto' }}`，`appointment/list.tsx:454`、`schedule/custom.tsx:246`）；独立 Pagination 仅 1 处；防抖仅地图选择器等少数场景

---

### Engineer — 技术视角

**存储层：**
- PostgreSQL（asyncpg 异步 + psycopg2 同步），SQLAlchemy 2.0 异步
- **两套连接池并存**：异步（pool_size=10/overflow=20）+ 同步 Celery（pool_size=5/overflow=10）（`db/session.py:15-82`）
- Redis（`redis==7.4.0`）兼 Celery broker + result backend；`RedisCache` 封装 KV/ZSET/LIST/token 黑名单（`core/redis.py:71-240+`）
- **Alembic 迁移脚本 147 个**（`migrations/versions/`）
- 文件存储可插拔：`STORAGE_TYPE` 支持 local/minio/cos（`config.py:159-179`）

**核心引擎：**
- 预约状态为整数 dict（非 Enum），3 号为历史遗留值（`constants/appointment.py:3-45`，注释明确转 Enum 会破坏 DB/API 契约）
- 挂号流程 `AppointmentBookingService.create`：配额→号源→租户一致性→休息日→规则引擎→冲突→上限→黑名单（`service_booking.py:33-150`）
- 排班规则引擎 `RuleEngineService`（mixin 组合：TimeWindow/Policy/Validation）
- 审批流引擎 `ApprovalEngine`（BPMN 解析、条件求值、Redis 分布式锁、Celery 异步、immutable 快照）
- 统一错误处理：`BusinessError`（含 `error_code` 如 `SCHEDULE_CONFLICT`）+ 全局 handler（`middleware/exception.py:18-100`）

**API/协议：**
- v1 路由 76 前缀；**v2 为空占位**（`build_v2_router()` 预留，`main.py:281-285`）
- JWT Bearer（access 30min / refresh 7 天，可租户配置覆盖）；**token 黑名单**（SHA256 + Redis，租户隔离）
- **限流中间件**：Redis 滑动窗口（租户+IP+路径），默认 300rpm/50rps，生产强制开启
- OpenAPI 自动生成（`/docs`、`/redoc`、`/llms.txt`、`/llms-full.txt`）
- WebSocket `ConnectionManager`：Redis Pub/Sub 多实例广播、心跳、消息确认、未确认缓存

**安全机制：**
- 密码 bcrypt + 传输 RSA（2048）非对称（前端 jsencrypt）
- RBAC + 多角色 + DataScope（all/tenant/store/custom）
- **`Patient.id_card` 明文 String(18) 存储，全仓库无加密列、无脱敏函数**（`models/user.py:56`，grep `mask_phone`/`desensitize`/`id_card[:3]` 仅第三方 secret 掩码一处）
- CORS 白名单仅 localhost 端口；SecurityHeadersMiddleware（HSTS 开关）；生产配置校验启动检查

**依赖/模块耦合：**
- 后端核心：fastapi 0.136、uvicorn 0.34、sqlalchemy 2.0.41、pydantic 2.11、celery 5.6、wechatpayv3 2.0、sentry-sdk 2.61、structlog 25.4
- 前端共享三包：`packages/shared`（手写 19 个 types）、`packages/api`（axios，64 modules）、`packages/codegen`（低代码 schema→Taro 代码，非 API 类型生成）
- **前后端类型未通过 OpenAPI 自动生成对齐**：手写 TS 类型，grep 无 `auto-generated`/`generated from OpenAPI`/`DO NOT EDIT` 标记
- import-linter 强制分层（api→modules→common→infrastructure→core→db），**infrastructure↔modules、common↔modules 多处双向耦合被显式豁免**（email/image/wechat channel/quota），注释标注 tracked in issue

**可观测性：**
- structlog JSON 日志 + request_log/operation_log 中间件
- Prometheus + Grafana + node/redis exporter（`docker-compose.monitoring.yml`，30 天保留）
- Sentry（DSN 空不启用，traces 采样 0.1，send_default_pii=False）
- Docker 部署（backend + celery_worker + celery_beat + celery_flower，read_only + no-new-privileges）
- 6 个 CI workflow；Celery Beat 30+ 定时任务（黑名单解禁/预约提醒/爽约检测/排班生成/支付对账/审批超时等）

**测试：**
- 后端 178 个测试文件（unit/integration/security/tenants/architecture/perf/structure）
- **未发现覆盖率门禁**（无 `--cov-fail-under` 在 CI）
- 架构测试存在（`test_fitness_functions.py`）
- 前端 E2E 67 个 spec（Playwright，Mock + 真实 API 双模式）+ patient-h5 独立配置

---

## Round 2：辩论层

> 说明：本对等协作模式的 4 个 Round 2 agent（PM/Designer/Engineer 交叉评论 + Critic 质询）均已返回真实输出，内容经过 Team Lead 核实并交叉引用。本节为真实三方交叉评论 + Critic 质询的提炼（agent 全文输出存档于本会话，以下为结构化摘要）。

### 交叉评论投票矩阵（对等协作模式，完整版）

> 图例：✅=+1（同意） ❌=反驳（不同意） ⚡=Critic 质询（不投票） 🤝=2/3 或 3/3 同意=共识 ⚠️=≤1/3 同意=分歧
> 成本来自 Engineer 交叉评论（基于实际代码规模校准：admin 66570 行 / settings.tsx 1474 行 / 后端 76-84 路由 / 三套患者端实现）

#### A. 日常操作缝隙类（"操作差缝隙"核心目标）

| # | 议题 | PM | Designer | Engineer | 成本 | 共识 |
|---|------|-----|----------|----------|------|------|
| A1 | 就诊完成→满意度/评价闭环断裂 | ✅ 升 P0（主动负体验） | ✅ P0（断链，比孤岛更糟） | ✅ 满意度 18h + reviews 补页 24h | 42h (M) | 🤝 |
| A2 | 签到/爽约/就诊完成对患者通知缺失 | ✅ 升 P0（高纠纷场景） | ✅ P0 + 补状态文案 | ✅ P0，6h，复用现有 message 模式 | 6h (S) | 🤝 |
| A3 | 考勤假期前端页面缺失（后端已实现） | ✅ | ✅ 高频+数据一致性 | ✅ 20h，access flag 已就绪 | 20h (M) | 🤝 |
| A4 | patient-h5 错误反馈断裂（404/5xx 静默） | ✅ P0（转化路径静默失败） | ✅ P0（最高 ROI） | ✅ P0，6h，错误映射已存在 | 6h (S) | 🤝 |
| A5 | catch 静默统一治理 | ✅（与 A4 同源） | ✅ | ⚠️ 部分反驳：不能批量补 message.error（双重提示），需逐处审计 | 16h (S) | 🤝（修正范围） |

#### B. 功能完成度 / 丰富应用类

| # | 议题 | PM | Designer | Engineer | 成本 | 共识 |
|---|------|-----|----------|----------|------|------|
| B1 | 低代码部署+微信上传 stub 落地 | ✅ P2 | ⚠️ P2（低频降级） | ✅ P2，56h，强外部依赖（微信资质） | 56h (L) | 🤝（归待定） |
| B2 | 短信腾讯云 provider + 通知模板 | ✅ | ✅（C 端硬依赖） | ✅ 短信 10h，模板另算 | 10h+ (S) | 🤝 |
| B3 | 患者端三端不对齐 | ✅ 升 P0（定位层危机） | ✅（跨端心智不一致） | ❌ 反转：**裁剪到单端 60h**，而非对齐三端 80h+ | 60h (L) | ⚠️ 分歧 |

#### C. 可优化点 / 技术债类

| # | 议题 | PM | Designer | Engineer | 成本 | 共识 |
|---|------|-----|----------|----------|------|------|
| C1 | `id_card` 明文存储无脱敏 | ✅ **升 P0**（阻塞 To-B 签约、PIPL） | ✅ 全界面未脱敏，强化 | ✅ 三方共同遗漏的最高安全债，40h | 40h (L) | 🤝（升 P0/P1） |
| C2 | 前后端类型未 OpenAPI 自动生成 | ✅（孤岛根因） | ✅（状态文案错位根因） | ✅ 首次 24h，之后零维护，ROI 极高 | 24h (M) | 🤝 |
| C3 | 颜色硬编码 1164 处+主色双标 | ✅ 中（未来换肤负债） | ✅（老年/视障人群） | ⚠️ 反对一次性收敛：主色统一 8h + 分批 token 化 56h | 8h+56h | 🤝（分批） |
| C4 | 迁移 147 个 + 状态整数 dict | ❌ 反驳"问题化" | — | ⚠️ 状态 Enum 是重构敏感区，32h | 32h (L) | ⚠️ 不做/待定 |
| C5 | 无 CI 覆盖率门禁 | ✅ 中偏高 | ❌ 反驳与 UX 相关性 | ✅ 4h 防护栏 | 4h (XS) | 🤝（留 Engineer 域） |
| C6 | infrastructure↔modules 双向耦合 | ✅ 中（商业化负债） | — | ✅ 各点 8-16h | 60h+ (L) | 🤝（P2） |

#### D. 响应式 / 无障碍 / 一致性类

| # | 议题 | PM | Designer | Engineer | 成本 | 共识 |
|---|------|-----|----------|----------|------|------|
| D1 | admin 响应式（无 viewport + 3 处 @media） | ⚠️ 修正：admin 是 PC 后台，锦上添花非止血 | ✅ | ✅ viewport 2h + 全页响应式 40h，分阶段 | 2h/40h | 🤝（viewport P0，全页 P2） |
| D2 | 图片 alt 缺失 | ❌ 反驳高优（admin 头像，非 C 端） | ✅（应优先 patient-h5） | ✅ 固定 2h + lowcode schema 6h | 6h (S) | ⚠️ 分歧（降级） |
| D3 | 四端 UI 栈统一（antd v5/v6） | ✅（定位层风险） | — | ❌ 反驳：框架统一不可行（200h+），应收敛为主色+版本对齐 24h | 24h (M) | ⚠️ 分歧（降级为版本对齐） |
| D4 | 超长文件拆分（settings.tsx 1474 行 等） | ✅ 中 | ✅ | ✅ settings 12h / rule-set 16h / PropertyPanel 24h | 52h (M) | 🤝（按 ROI 拆） |

#### E. Critic 暴露的盲区（三方共同遗漏）

| # | 议题 | Critic 质询 | Team Lead 裁决 | 成本 | 共识 |
|---|------|------------|---------------|------|------|
| E1 | 文档契约可信度（CLAUDE.md L118 vs L307 自相矛盾） | 🚨 关键：契约入口不可信则 import-linter/认证等事实可信度存疑 | 🤝 纳入：文档治理 + 增加自动化校验 | 4-8h | 🤝 P0 |
| E2 | 性能/容量/灾备盲区（压测仅 50 用户、无 PITR/RPO/RTO、仅应用层 JSON 备份） | 🚨 关键：SaaS 医疗系统致命遗漏 | 🤝 纳入：补容量压测 + DB 级备份/灾备评估 | 待评估 | 🤝 P1 |
| E3 | 强项被系统性低估（无"巩固强项"议题） | 普通：健康项目被引导成问题清单 | 🤝 纳入：保留至少 1 项强项巩固/对外宣传 | — | 🤝 |

### 独到发现（跨视角，agent 提炼）

1. **[PM]** 核心挂号 happy path（选科室→医生→号源→预约→签到→叫号→就诊完成）在四端哪几端真正跑通，无任何一方给出结论——结合 miniapp 缺 booking，存在"测试多但主推端跑不通"风险。**应作为本轮第一条验收项。**
2. **[PM]** doctor-reviews/satisfaction 的孤岛是"后端造了前端用不上"，根因之一是前后端无契约同步——与 C2 咬合。
3. **[Designer]** 患者端状态码本地化大面积缺失（NO_SHOW/EXPIRED 在患者端无文案）——不止 id_card，整类状态映射在患者端腐烂，需补"状态码→三端文案"矩阵。
4. **[Designer]** 取消预约有时间窗提示，但爽约判定无对称反馈（单向透明）——患者不知道被记爽约/何时解禁/如何申诉。
5. **[Designer]** 消息系统两套并存会让患者收到重复通知（新旧各推一条），降低通知信任度。
6. **[Engineer]** 真正合并消息系统成本被低估：双路由在线（`messages` + `unified_message`）、前端 `message.ts` 同时调两套端点，合并 48h 含契约破坏风险。
7. **[Engineer]** 引入 OpenAPI 类型自动生成可**一次性消除整类"后端有前端无"缝隙**，且后续 stub/孤岛自动暴露——ROI 极高，应优先于逐个手补。

### Critic 质询与回应

> Critic 共发起 7 条质询，其中 3 条 🚨 关键（质询 1/2/5 已用尽关键配额）。关键质询 Round 3 必须实质回应，否则归待定。

| # | 质询摘要 | 回应者 | 级别 | Team Lead 回应 | 充分？ | 处置 |
|---|---------|--------|------|---------------|--------|------|
| 1 | 文档矛盾（CLAUDE.md L118=82 vs L307=81，实际 84）是管理失序，契约入口不可信波及其他事实 | PM/Engineer | 🚨关键 | 采纳：升级 E1 文档治理为 P0，含自动化校验脚本防再发生 | 是 | 纳入 P0 |
| 2 | id_card 明文（PII，不可轮换）与颜色硬编码（审美）被拉平，缺优先级依据 | Engineer/PM | 🚨关键 | 采纳：C1 升 P0/P1（合规优先于审美），颜色降为分批长期项 | 是 | C1 升级 |
| 3 | doctor-reviews"孤岛"论据不实（`doctor.ts:312-328` 有 API），PM 证据未核 | PM | 普通 | 采纳：更正为"API 已消费，缺消费页面"，成本从"打通全链路"降为"补页"；要求 satisfaction 同样重核 | 是 | 更正 |
| 4 | "明确非目标"（HIS/支付通道/财务报表）被当缺陷扫描，混淆边界 | PM/Engineer | 普通 | 采纳：B1 低代码部署属边界内欠交付（有路由有页面有 stub）；支付仅记录属有意取舍（移出清单）；消息两套是迁移过渡（不新增，规划收尾） | 是 | 分桶 |
| 5 | 性能/容量/灾备盲区：压测 50 用户、无 PITR/RPO/RTO、仅应用层 JSON 备份 | Engineer/TL | 🚨关键 | 采纳：升级 E2 为 P1，含容量压测门禁 + DB 级备份/灾备评估 + 跨池一致性 | 是 | 纳入 P1 |
| 6 | 缝隙缺触发频率量化（满意度/爽约通知每天触发几次？） | PM | 普通 | 部分采纳：A1/A2 按"挂号核心路径+纠纷高发"定性为高频/高价值，但行动项标注"需埋点验证回收率" | 部分 | 纳入+验证 |
| 7 | 强项被系统性低估，议程无"巩固强项"议题 | TL/PM | 普通 | 采纳：保留 E3，至少 1 项强项巩固/对外宣传（如全链路可观测、审批流引擎） | 是 | 纳入 |

### 🚨 Critic 关键质询追踪

| # | 关键质询 | 回应摘要 | 充分 | 处置 |
|---|---------|---------|------|------|
| 1 | 文档契约不可信 | E1 升 P0：文档校准 + 自动化校验脚本 | 是 | 纳入 P0 |
| 2 | 合规风险被拉平审美问题 | C1 升 P0/P1，颜色降长期项 | 是 | C1 升级 |
| 5 | 性能/容量/灾备盲区 | E2 升 P1：压测门禁 + DB 备份/灾备评估 | 是 | 纳入 P1 |

---

## Round 3：共识层

### ✅ 共识项（2/3 或 3/3 同意，含 Critic 关键质询升级）

> 基于 Round 2 真实三方投票。3 条 Critic 关键质询（文档可信度/合规优先级/灾备盲区）均已实质回应并升级为行动项。

1. **签到/爽约/就诊完成通知补齐 + 状态文案（A2）** — 3/3，P0，6h
2. **patient-h5 错误提示对齐 admin（A4）** — 3/3，P0，6h
3. **CI 覆盖率门禁（C5）** — 留 Engineer 域，P0，4h
4. **文档契约校准 + 自动化校验（E1，Critic 升级）** — P0，4-8h
5. **viewport meta（D1 子项）** — P0，2h
6. **主色统一 #1890ff→#1677ff（C3 局部）** — P0，8h
7. **`id_card` 加密存储+全界面脱敏（C1，Critic 升级）** — 合规优先，P0/P1，40h
8. **前后端类型 OpenAPI 自动生成（C2）** — 3/3，P1，24h（消除整类孤岛缝隙根因）
9. **满意度/评价闭环（A1，更正后）** — 3/3，P1，42h（satisfaction 新建 SDK+页 18h + reviews 补消费页 24h，API 已存在）
10. **考勤假期前端页面补齐（A3）** — 3/3，P1，20h
11. **catch 静默治理（A5，修正范围）** — P1，16h（逐处审计，非批量补提示）
12. **容量压测门禁 + DB 级备份/灾备评估（E2，Critic 升级）** — P1，待评估
13. **settings.tsx 拆分（D4 子项）** — P1，12h（7 类配置天然可分）
14. **短信腾讯云（B2）** — P2，10h
15. **强项巩固/对外宣传（E3）** — 至少 1 项（如全链路可观测、审批流引擎产品化包装）

### ⚡ 分歧项

1. **患者端三端处理（B3）** — ✅ **已决策：主推小程序**
   - 用户决策（2026-06-29）：患者端主推 **patient-miniapp（小程序）**
   - **裁决落地**：
     - 保留 patient-miniapp，补齐 booking/records/message/feedback/follow-up/search/waitlist 等核心场景（约 60h，分批：首批 booking/records/message 约 30h）
     - patient-h5 降级为「降级兜底方案」或逐步退役（不新增功能）
     - mini-appointment-miniapp（临时挂号小程序）合并/重定向到主小程序的现场挂号模块，消除三套并行
     - 先做核心挂号 happy path 在主推端（小程序）跑通的验收（PM 独到发现1），再分批补齐
   - B3 从「待定」转为 **P1（首批）+ P2（剩余场景）**

2. **状态 dict 转 Enum（C4）**
   - 3/3 一致**不做**（注释明确有意权衡，风险>收益）→ 移出清单

3. **四端 UI 栈统一（D3）**
   - PM：定位层风险；Engineer：❌ 框架统一不可行（200h+）
   - **裁决：降级为"主色统一 + antd 版本对齐"24h**，不做框架统一

4. **图片 alt（D2）**
   - PM：❌ 反驳 admin 高优（内部用户、头像装饰图）；Designer：应优先 patient-h5
   - **裁决：admin alt 降为低优，无障碍治理优先 patient-h5**（C 端、面向公众/老年）

---

## 被低估的优势（Critic 提醒，规划时勿重做）

1. **工程基线远超同类**：178 个后端测试 + import-linter 架构契约 + fitness functions 架构测试 + 6 个 CI workflow（含 security/Trivy）
2. **核心引擎完备**：ApprovalEngine（BPMN 解析/Redis 分布式锁/immutable 快照）+ 排班规则引擎（mixin 组合）+ 多租户 RBAC + DataScope
3. **全链路可观测**：structlog + Prometheus + Grafana（30天保留）+ Sentry + 生产配置启动校验 + Docker read_only/no-new-privileges
4. **通知基础设施就位**：10 渠道（email/sms/in_app/websocket/wechat/dingtalk/feishu/wecom…）—— A2「补通知」是配置而非新建
5. **安全机制扎实**：JWT 黑名单（SHA256+Redis 租户隔离）、限流（Redis 滑动窗口）、密码 bcrypt+RSA 传输、Pydantic 校验、SecurityHeaders

---

## 行动计划（按 ROI 排序，成本来自 Engineer R2 校准）

| 优先级 | 行动 | 议题 | 成本 | 负责 | 状态 |
|--------|------|------|------|------|------|
| P0 | CI 覆盖率门禁 | C5 | 4h (XS) | Engineer | 待执行 |
| P0 | viewport meta 配置 | D1 | 2h (XS) | Designer | 待执行 |
| P0 | 文档契约校准 + 自动化校验脚本 | E1(Critic) | 4-8h (XS) | PM+Engineer | 待执行 |
| P0 | 签到/爽约/就诊完成通知 + 状态文案补齐 | A2 | 6h (S) | Engineer | 待执行 |
| P0 | patient-h5 错误提示对齐 admin | A4 | 6h (S) | Engineer | 待执行 |
| P0 | 主色统一 #1890ff→#1677ff | C3局部 | 8h (S) | Designer | 待执行 |
| P1 | `id_card` 加密存储 + 全界面脱敏 | C1(Critic) | 40h (L) | Engineer | 本轮（合规优先） |
| P1 | 前后端类型 OpenAPI 自动生成 | C2 | 24h (M) | Engineer | 本轮（消除孤岛根因） |
| P1 | 满意度填写闭环 + 评价消费页 | A1 | 42h (M) | PM+Engineer | 本轮 |
| P1 | 考勤假期前端页面补齐 | A3 | 20h (M) | Engineer | 本轮 |
| P1 | catch 静默治理（逐处审计非批量） | A5 | 16h (S) | Engineer | 本轮 |
| P1 | 容量压测门禁 + DB 级备份/灾备评估 | E2(Critic) | 待评估 | Engineer+SRE | 本轮 |
| P1 | settings.tsx 拆分（7 类配置） | D4 | 12h (S) | Engineer | 本轮 |
| P1 | 强项巩固/对外宣传（≥1 项） | E3 | — | PM | 本轮 |
| P2 | 短信腾讯云 provider | B2 | 10h (S) | Engineer | 下周期 |
| P2 | 颜色 token 全量收敛（分批） | C3全量 | 56h (L) | Designer | 下周期 |
| P2 | 消息系统真正合并（双路由+双端点迁移） | 独到6 | 48h (L) | Engineer | 下周期 |
| P2 | infrastructure↔modules 解耦（先 quota 通道） | C6 | 60h+ (L) | Engineer | 下周期 |
| P2 | 全页响应式（admin 高频页渐进） | D1全量 | 40h (L) | Designer | 下周期 |
| P1 | 患者端裁剪到小程序：patient-miniapp 补齐首批场景（booking/records/message） | B3 | 30h (M) | PM+Engineer | 本轮（主推小程序，H5 降级） |
| P2 | patient-miniapp 补齐剩余场景（feedback/follow-up/search/waitlist）+ 合并临时挂号小程序 | B3剩余 | 30h (M) | PM+Engineer | 下周期 |
| P2 | 低代码部署 + 微信上传落地（第三方平台代管理模式） | B1 | 56h+ (L) | Engineer | 下周期，**前置：先办微信开放平台第三方平台资质（审核约7天）** |
| 不做 | 状态 dict 转 Enum（有意权衡，风险>收益） | C4 | — | — | 移出清单 |
| 不做 | 四端 UI 框架统一（200h+，不可行） | D3原案 | — | — | 降级为版本对齐 |

### P0：立即执行（合计约 30h，全部低成本高 ROI）
1. CI 覆盖率门禁（4h）
2. viewport meta（2h）
3. 文档契约校准 + 自动化校验（4-8h）— Critic 关键质询回应
4. 签到/爽约/就诊完成通知 + 状态文案（6h）
5. patient-h5 错误提示对齐（6h）
6. 主色统一（8h）

### P1：本轮迭代（合计约 154h + 待评估）
1. **id_card 加密+脱敏（40h）** — Critic 关键质询，合规优先于一切审美项
2. OpenAPI 类型自动生成（24h）— 消除整类孤岛根因
3. 满意度/评价闭环（42h）— 更正：reviews API 已存在，只需补消费页
4. 考勤假期页面（20h）
5. catch 静默治理（16h）— 修正：逐处审计非批量补提示
6. 容量压测 + 灾备评估（待评估）— Critic 关键质询，SaaS 医疗系统致命盲区
7. settings.tsx 拆分（12h）
8. 强项巩固（≥1 项对外宣传）

### P2：下个周期
短信腾讯云 / 颜色 token 全量 / 消息系统真正合并 / 模块解耦 / 全页响应式

### 待定：需用户确认
1. **✅ 已决策（2026-06-29）**：患者端主推 **patient-miniapp（小程序）**，patient-h5 降级/退役，临时挂号小程序合并 → B3 转 P1/P2
2. **✅ 已决策（2026-06-29）：场景 B — 多租户 SaaS，租户自助发布小程序**
   - 需在 `open.weixin.qq.com` 注册**微信开放平台第三方平台账号**（审核约 7 天），才能代租户管理小程序（代上传代码/代提审/代发布）
   - 每个**租户小程序**需：① AppID ② AppSecret ③ 上传私钥 ④ 主体认证 + 医疗类目资质
   - B1 维持 56h+（L），**前置依赖：先办微信开放平台第三方平台资质**
   - 排期：P2（资质到位后启动）；资质办理与 P0/P1 开发并行，不阻塞当前迭代

---

## 摘要

**使用模式：** 对等协作（4 个 R2 agent 全部返回真实输出：PM/Designer/Engineer 交叉评论 + Critic 7 条质询含 3 条关键）

**共识：** 15 项达成共识（含 3 项 Critic 关键质询升级：文档可信度/合规优先级/灾备盲区）
**分歧：** 4 项裁决（患者端裁剪vs对齐 / 状态Enum不做 / UI框架统一降级 / alt优先级）
**待定：** 2 项需用户确认（患者端主推端战略 / 微信资质）

**Top 6 P0 行动（合计约 30h）：**
1. CI 覆盖率门禁（4h，Engineer）
2. viewport meta（2h，Designer）
3. 文档契约校准 + 自动化校验（4-8h，PM+Engineer）— Critic🚨：CLAUDE.md L118=82 vs L307=81 自相矛盾
4. 签到/爽约/就诊完成通知 + 状态文案（6h，Engineer）
5. patient-h5 错误提示对齐 admin（6h，Engineer）— 挂号核心路径静默失败
6. 主色统一 #1890ff→#1677ff（8h，Designer）

**P1 最高优先（Critic🚨升级）：**
- `id_card` 加密存储+全界面脱敏（40h）— 明文存储阻塞 To-B 医院签约，PIPL 合规
- 容量压测+灾备评估 — 压测仅 50 用户、无 PITR/RPO/RTO，SaaS 医疗致命盲区

**Critic 关键洞察：**
1. **文档契约不可信**（CLAUDE.md 自相矛盾）→ 升级 P0 + 自动化校验
2. **合规风险被与审美拉平**（id_card vs 颜色）→ id_card 升 P0/P1，颜色降长期
3. **性能/容量/灾备是三方共同致命盲区** → 升级 P1
4. **强项被系统性低估** → 保留≥1 项强项巩固议题，避免健康项目被引导成问题清单
5. **doctor-reviews"孤岛"论据不实**（API 已存在于 doctor.ts:312-328）→ 更正为"补消费页"

**关键更正（R2 vs R1 回退方案）：**
- doctor-reviews：非全链路孤岛，API 已消费，成本从"打通"降为"补页"
- 消息系统合并：双路由+双端点在线，真实成本 48h（非低估值）
- 患者端：Engineer 反转，裁剪到单端 60h 优于对齐三端 80h+
- id_card：从 P1 升 P0/P1（三方共同遗漏的最高安全债）

---

## 附录：执行说明

本轮为完整的对等协作模式执行：
- Round 1：3 个 Explore agent 并行收集事实（PM/Designer/Engineer 各 8 条关键发现，均带来源）
- Round 2：4 个 agent（3 交叉评论 + Critic）返回真实输出，Critic 发起 7 条质询（3 条关键），均实质回应
- Round 3：Team Lead 基于真实三方投票矩阵 + Critic 质询收敛，产出按 ROI 排序的行动计划

agent 全文输出（含每条交叉评论的完整理由）存于本会话，本画布为结构化提炼。
