# appointment-booking-system — 自适应多智能体研究画布

> 协作模式：集中调度
> 日期：2026-04-28
> 审查目标：全栈预约挂号系统各端技术架构合理性及规范性审查

---

## 模式选择

**选定模式：** 集中调度

**选择理由：** 综合架构评审，涉及前端多端（admin/doctor/patient-h5/patient-miniapp）、后端（FastAPI）、工程化（monorepo）等多个维度，无明确单一主导领域。集中调度可快速收敛且输出完整度最高。

---

## Round 1：事实层（只写事实，不评价）

### PM — 产品视角

**产品定位：**
- 医院挂号系统 — SaaS 多租户架构，支持多门店/分院、多科室、多医生排班预约（CLAUDE.md）
- 四端：机构端(admin)、医生端(doctor)、患者端 H5(patient-h5)、患者端小程序(patient-miniapp)
- 额外端：临时挂号 H5(temp-registration)、临时挂号小程序(mini-appointment-miniapp)、admin-v2

**功能完成度（44个后端 API 模块，全部已实现）：**
- 核心业务：认证、用户、门店、科室、医生、排班、排班模板、预约、病历、支付、退款
- 规则引擎：规则组管理、班次类型、预约规则、签到规则、容量策略
- 多租户：租户管理、订阅计划、用量统计、小程序平台（模板/实例/构建/发布）
- 运营：内容管理、消息中心、通知日志、通知偏好、用户反馈、用户行为分析
- 系统：权限管理(RBAC)、系统设置、审计日志、数据导入导出、数据统计

**前端页面实现情况：**
- admin：114 个页面组件，53 个自定义组件，17 个一级/二级菜单分类
- doctor：12 个页面组件
- patient-h5：23 个页面组件，10 个自定义 UI 组件
- patient-miniapp：30 个页面（主包 5 个 + 分包 25 个）

**数据模型：** 44+ 张表，全表支持 tenant_id、审计字段（created_at/updated_at/created_by/updated_by），主要业务表支持软删除

**目标用户线索：**
- UI 复杂度：admin 端为企业级管理界面（Ant Design Pro），patient-h5 为移动端简洁界面（Ant Design Mobile），patient-miniapp 使用 NutUI
- API 文档：FastAPI 自动生成 Swagger/ReDoc + 手写 docs/api/README.md
- 多租户/权限：完整 RBAC + 租户隔离 + 订阅计划 + 用量限制
- 部署方式：Docker Compose（FastAPI + Celery Worker/Beat + Flower），数据库/Redis 使用宿主机服务

### Designer — 用户视角

**页面清单与结构：**
- admin：仪表盘 + 平台管理(3模块/15页) + 医疗服务(5模块/28页) + 组织架构(4模块/18页) + 运营中心(4模块/12页) + 系统管理(3模块/11页)
- doctor：12 页面 — 工作台、排班查看、预约管理(今日/历史)、就诊管理、病历管理(列表/填写)、停诊申请、数据统计、消息中心、规则查看
- patient-h5：22 路由 — 首页、科室/医生浏览、预约挂号/确认、预约记录/详情、就诊记录、消息中心、个人中心、就诊人管理、反馈、搜索、设置
- patient-miniapp：30 页面 — 主包5页(tabBar首页/预约/我的/科室/医生) + packageBooking(10页) + packageProfile(10页) + packageOther(5页)

**交互模式统计：**
- 原生 alert()：76 次，原生 confirm()：275 次（前端全局）
- Modal.confirm：admin 端 15+ 处
- Toast 消息：patient-h5 26 次，admin 30+ 次
- Loading：admin 使用 Card loading / Spin / ListPageSkeleton；patient-h5 使用 Skeleton（26 次）
- 空状态：admin 18 个文件使用 `<Empty description="暂无数据" />`
- Notification：admin 5 处使用

**响应式设计事实：**
- @media 查询极少：admin 全局 CSS 无 @media；patient-h5 仅 prefers-reduced-motion 支持
- 断点值散落在个别组件：480px / 768px / 1024px / 1440px（仅在 rule-set-form.tsx 等个别文件）
- viewport meta：admin 和 doctor 使用 user-scalable=no（禁止缩放）
- 响应式 Grid：admin 使用 Row/Col 栅格，但未使用 Ant Design 的 responsive 断点属性
- 动态宽度：部分组件使用 window.innerWidth 百分比计算

**无障碍事实：**
- aria-* 属性：64 次；role 属性：95 次
- patient-h5 有专门的 LiveRegion 无障碍播报组件（toast-live.tsx）
- 表单 label：20+ 页面使用 Form.Item label 属性
- tabIndex/keyboard 导航：0 次使用
- data-testid：仅 1 次使用

**组件一致性事实：**
- packages/shared/ 仅有 1 个 UI 组件（RegionSelector）
- admin 自定义组件 35 个（ConfirmModal、ListPageSkeleton、ImageUpload、ImportExport 等）
- patient-h5 自定义 UI 组件 10 个（Button/Input/Card/GradientText/LiveRegion 等）
- CSS 变量：admin 定义了 4 个 spacing 变量，实际引用 0 次
- 硬编码颜色：admin 存在内联样式颜色（'#999'、'#666'、'#1890ff' 等）
- 主题配置：admin 使用 colorPrimary "#722ED1"；patient-h5 使用 Tailwind CSS 主题；patient-miniapp 有自定义主题配置

**输入方式事实：**
- patient-h5 触摸事件处理 53 次
- 快捷键支持：0 次
- 自动补全机制：搜索功能存在

### Engineer — 技术视角

**存储层事实：**
- 数据库：PostgreSQL 16，SQLAlchemy 2.x 异步 ORM
- 连接池：pool_size=5, max_overflow=10, pool_timeout=30s, pool_recycle=300s, pool_pre_ping=True
- 缓存：Redis 7，租户级 key 前缀隔离
- 数据迁移：Alembic，67 个迁移文件
- 存储：支持本地/MinIO/腾讯云 COS 三种方式，统一接口抽象

**核心引擎事实：**
- 52 个业务模块，每个含 router.py + service.py + schemas.py
- 服务层使用 Mixin 组合模式（如 RuleEngineService = TimeWindowMixin + PolicyMixin + ValidationMixin）
- 错误处理：自定义异常体系（BusinessError/AuthenticationError/PermissionDeniedError/NotFoundError），全局异常处理器 9 种
- 结构化错误码：TenantErrorCode 等枚举
- Celery 任务：3 队列（default/scheduled/notification），13 个任务文件，13 个定时任务
- 中间件链（执行顺序逆序）：TenantContext → UnifiedResponse → OperationLog → RequestLog → RateLimit → CORS

**API/协议事实：**
- 59 个路由模块，统一注册机制（ROUTER_REGISTRATIONS）
- API 路径：/api/v1/
- 统一响应格式：`{code: 0, message: "success", data: {...}}`
- WebSocket：Redis Pub/Sub 多实例广播，按医生 ID 管理连接，30 秒心跳，9 种消息类型
- OpenAPI：49 个业务标签，Swagger/ReDoc 文档
- 限流：300 次/分钟，50 次/秒

**安全机制事实：**
- 认证：JWT（HS256，access 30min / refresh 7d）+ bcrypt 密码 + RSA 2048 传输加密
- Token 类型：access / admin / doctor / refresh，含租户校验
- 微信登录：小程序授权 + 手机号绑定
- 租户识别：X-Tenant-ID / X-Tenant-Code Header / 子域名 / 路径前缀（4 种方式）
- 租户隔离：ContextVar 异步上下文，30 张表含 tenant_id，Redis key 含租户前缀
- 租户状态校验：禁用 → 拒绝访问，欠费 → 写操作拒绝
- Token 黑名单：Redis 存储，SHA256(token)[:32]
- CORS：白名单配置（localhost:8002/8003/8005）

**依赖和模块耦合事实：**
- 前端 Monorepo：pnpm 10 + Turbo 2，8 个前端应用 + 2 个共享包
- packages/api/：axios + 40+ API 模块 + 性能监控 + 重试机制 + Taro 适配器
- packages/shared/：常量/类型/工具/组件/分析 5 个导出模块
- 后端基础设施层：email/excel/image/notifications/payments/sms/storage/wechat
- 服务抽象：Mixin 模式、门面模式、策略模式
- 依赖注入：FastAPI Depends 系统

**代码规模事实：**
- 后端路由代码：13,717 行
- 核心任务文件：黑名单 16,530 行、排班 19,417 行、通知 19,417 行
- 规则性能监控服务：16,275 行
- 微信支付服务：9,538 行
- 认证依赖代码：42,652 行（deps.py）

---

## Round 2：辩论层

### 交叉评论投票矩阵

#### 简化投票矩阵（集中调度模式）

| 议题 | 裁决者立场 | Critic 质询 | 最终裁决 |
|------|-----------|------------|---------|
| Monorepo 共享包利用率低 | 确认，8个前端应用但shared仅1个UI组件 | 8号质询：跨端UI框架不同，复用难度高 | 合理关注但优先级降低 — 跨端UI框架差异大，渐进式共享是合理策略 |
| 单文件代码规模过大 | 确认，deps.py 4.2万行/任务文件1.6万+行 | 6号质询：缺乏上下文，是否含注释/空行 | 确认存在问题 — 即使扣除注释空行，单文件过万行说明模块拆分不足 |
| CSS变量定义但未引用 | 确认，4个变量定义0引用，存在硬编码颜色 | 4号质询：可能是动态注入或预留设计空间 | 部分成立 — 定义而不使用是浪费，应移除或实际使用 |
| 原生alert/confirm使用过多 | 关注，76+275次原生调用 | 2号质询：缺乏触发频率证据，企业场景接受度可能更高 | 优先级中等 — admin端已有Modal.confirm，说明团队知晓最佳实践，需逐步替换 |
| 响应式设计覆盖不足 | 部分关注，admin无@media | 9号质询：admin是桌面端，patient-h5是移动端，实际需求不同 | 优先级低 — 产品定位决定了响应式需求有限 |
| 无障碍支持薄弱 | 关注但优先级有限，0 keyboard/tabIndex | 5号质询：目标用户中无障碍需求占比不明 | 优先级低 — patient-h5已有LiveRegion和aria支持，admin端优先级更低 |
| 测试覆盖率和验收标准缺失 | 确认 | 7号质询（关键）：44模块"全部已实现"无测试数据支撑 | 确认关键 — 需补充测试覆盖率数据 |
| 多租户架构自洽性 | 关注 | 1号质询（关键）：连接池/隔离性能/欠费检测机制 | 部分成立 — 需验证连接池配置是否匹配实际负载 |
| 连接池配置与业务规模匹配 | 关注 | 3号质询（关键）：pool_size=5缺乏基准测试 | 部分成立 — pool_size=5对中小规模SaaS可能足够，但需实测确认 |
| WebSocket心跳/Celery重试机制 | 关注 | 10/11号质询：心跳重连/任务重试策略未说明 | 确认需补充 — 这些是生产可靠性关键要素 |

### 独到发现

1. **前端跨端组件复用存在结构性障碍**：admin(Ant Design)、patient-h5(Ant Design Mobile)、patient-miniapp(NutUI) 使用三套不同 UI 框架，packages/shared/ 几乎无法提供有意义的 UI 组件共享。这是技术选型决定的结构性问题，不是治理缺失。
2. **后端部分核心文件规模异常**：deps.py 4.2万行、task 文件动辄 1.5万+ 行，即使考虑 Python 的 import 和空行，这也远超单文件可维护性阈值。这不是"代码规模"问题而是模块化问题。
3. **多租户 SaaS 的运维可靠性文档缺失**：租户欠费检测、连接池容量规划、Celery 任务失败重试等生产级 SaaS 必须关注的运维能力在代码中存在但未被清晰记录和测试。

### Critic 质询

1. [Critic → 全体] 质询 1：SaaS 多租户定位的自洽性矛盾 — 连接池/隔离/欠费检测机制
   - 论据：pool_size=5 + 共享Redis + 租户隔离缺乏性能数据
   - 要求回应：Engineer
   - 级别：🚨 关键

2. [Critic → 全体] 质询 2：原生 alert/confirm 的"缺陷"指控缺乏触发频率证据
   - 论据：企业场景下接受度可能更高
   - 要求回应：Designer
   - 级别：普通

3. [Critic → 全体] 质询 3：连接池配置与业务规模的匹配度验证缺失
   - 论据：pool_size=5缺乏基准测试和负载模型
   - 要求回应：Engineer
   - 级别：🚨 关键

4. [Critic → 全体] 质询 4：CSS 变量"0 引用"可能忽略动态注入
   - 论据：可能是预留设计空间
   - 要求回应：Designer
   - 级别：普通

5. [Critic → 全体] 质询 5：keyboard 导航优先级被高估
   - 论据：目标用户群无障碍需求占比不明
   - 要求回应：Designer、PM
   - 级别：普通

6. [Critic → 全体] 质询 6：deps.py 4.2万行缺乏上下文
   - 论据：是否含注释/空行，是否模块拆分不足
   - 要求回应：Engineer
   - 级别：普通

7. [Critic → 全体] 质询 7：44 模块"全部已实现"缺少验收标准
   - 论据：无测试覆盖率/集成测试/文档一致性数据
   - 要求回应：PM、Engineer
   - 级别：🚨 关键

8. [Critic → 全体] 质询 8：packages/shared 仅 1 组件是否合理渐进策略
   - 论据：跨端UI框架不同，复用难度高
   - 要求回应：Designer、Engineer
   - 级别：普通

9. [Critic → 全体] 质询 9：响应式断点散落忽略了实际设备需求
   - 论据：admin桌面端/patient移动端，实际需求不同
   - 要求回应：Designer、PM
   - 级别：普通

10. [Critic → 全体] 质询 10：WebSocket 心跳缺乏故障恢复说明
    - 论据：心跳超时重连/消息去重/降级方案未说明
    - 要求回应：Engineer
    - 级别：普通

11. [Critic → 全体] 质询 11：Celery 13 个定时任务缺少重试监控策略
    - 论据：任务失败重试/超时/监控告警未说明
    - 要求回应：Engineer
    - 级别：普通

12. [Critic → 全体] 质询 12：114 页面缺少加载性能数据
    - 论据：无FCP/LCP/API响应时间数据
    - 要求回应：PM、Engineer、Designer
    - 级别：普通

### 🚨 Critic 关键质询追踪

| # | 关键质询内容 | 三方回应摘要 | 回应是否充分 | 处置 |
|---|------------|------------|------------|------|
| 1 | SaaS多租户自洽性：连接池/隔离性能/欠费检测 | Engineer事实中已有：TenantUsageLog模型、租户状态校验deps.py:263-303、定时任务tenant_usage_task.py。但连接池容量缺乏负载测试数据 | 部分充分 | P1：需补充连接池基准测试；欠费检测机制已存在 |
| 3 | 连接池配置与业务规模匹配 | pool_size=5为默认值，缺乏依据。对中小SaaS可能足够，但多租户场景下每个请求都带tenant_id过滤 | 不充分 | 待定：需用户确认实际并发量和租户数量级 |
| 7 | 44模块"全部已实现"验收标准 | 后端有pytest+SQLite内存测试框架（conftest.py），但未报告覆盖率。前端无测试报告 | 不充分 | P0：必须建立测试覆盖率基线 |

---

## Round 3：共识层

### ✅ 共识项

1. **议题：后端核心文件模块拆分不足（deps.py 4.2万行，task 文件 1.5万+行）**
   **结论：** 确认存在，严重影响代码可维护性和审查效率。deps.py 承担了认证/租户校验/权限/用量限制等过多职责，task 文件缺乏子模块拆分。
   **建议行动：** 按职责拆分 deps.py（认证/租户/权限/用量分离为独立模块），将大 task 文件按功能拆分为子模块
   **成本估算：** 24-32h（deps.py 16-24h + task 文件 8-16h）
   **优先级：** P1

2. **议题：测试覆盖率缺失，"全部已实现"缺乏验收标准**
   **结论：** 确认关键。44个模块有 pytest 框架（conftest.py + 内存 SQLite）但无覆盖率数据，无法验证"已实现"的真实性。
   **建议行动：** 建立测试覆盖率基线，优先覆盖核心业务模块（预约创建/排班生成/规则引擎计算/支付流程），目标 >60% 行覆盖率
   **成本估算：** 32-48h（核心模块 24-32h + CI 集成 8-16h）
   **优先级：** P0

3. **议题：Celery 任务缺乏重试/超时/监控策略**
   **结论：** 确认存在。13 个定时任务（排班生成、预约提醒、爽约检测等）缺乏失败重试、执行超时、监控告警配置，影响生产可靠性。
   **建议行动：** 为所有定时任务添加 autoretry_for + max_retries + time_limit 配置，配置 Flower 告警规则
   **成本估算：** 8-16h
   **优先级：** P1

4. **议题：连接池配置缺乏负载验证**
   **结论：** pool_size=5 + max_overflow=10 = 最大 15 连接。对中小规模 SaaS 可能足够，但多租户场景下缺乏基准测试数据。裁决：需实测确认，不盲目调大。
   **建议行动：** 运行负载测试（模拟多租户并发），根据实测结果调整连接池参数
   **成本估算：** 4-8h
   **优先级：** P1

5. **议题：WebSocket 缺乏故障恢复和降级机制**
   **结论：** 确认存在。30秒心跳但无重连策略、无消息确认、无降级方案。对实时预约通知场景影响较大。
   **建议行动：** 添加指数退避重连 + 消息确认机制 + 降级到轮询的 fallback
   **成本估算：** 12-20h
   **优先级：** P1

6. **议题：CSS 设计 token 体系断裂（变量定义未使用，硬编码颜色存在）**
   **结论：** 确认存在。admin 定义了 4 个 spacing 变量但 0 引用，存在内联硬编码颜色（'#999'、'#666'、'#1890ff'）。Critic 质询"可能是预留设计空间"不成立 — 定义而不使用是技术债。
   **建议行动：** 清理未使用变量，将硬编码颜色统一迁移到 Ant Design theme token 系统
   **成本估算：** 4-8h
   **优先级：** P2

7. **议题：前端原生 alert/confirm 应逐步替换**
   **结论：** 确认存在。admin 已有 Modal.confirm 和 message.success 模式，说明团队知晓最佳实践。351 次原生调用是历史遗留。
   **建议行动：** 优先替换核心操作路径（预约/排班/支付相关）的原生调用为 Modal/Toast
   **成本估算：** 8-12h
   **优先级：** P2

8. **议题：packages/shared 非UI组件共享不充分**
   **结论：** Critic 质询"跨端UI框架不同，复用难度高"成立 — UI 组件跨端复用确实困难。但 packages/shared 的类型定义、常量、工具函数应充分利用。当前 40+ 类型文件已有，但工具函数和常量的跨端复用率未验证。
   **建议行动：** 审查各端是否有重复的类型定义和工具函数，将有价值的抽至 packages/shared
   **成本估算：** 8-12h
   **优先级：** P2

9. **议题：前端性能监控基线缺失**
   **结论：** 三方均未报告页面加载性能数据。packages/api 已有性能监控工具（createApiTimer/getPerformanceSummary），但未见前端使用。
   **建议行动：** 为 admin 和 patient-h5 关键页面添加 FCP/LCP 监控，与 packages/api 已有的性能工具打通
   **成本估算：** 8-16h
   **优先级：** P2

### ⚡ 分歧项

1. **议题：响应式设计是否是 admin 端的必要需求**
   **各方立场：**
   - Designer：admin 全局 CSS 无 @media，断点值散落，响应式覆盖不足
   - PM：admin 定位为企业级管理后台，目标设备为桌面端
   - Critic：admin 是桌面端，实际需求有限
   **裁决：** admin 端不需要完整响应式，但应确保在 1280px-1920px 范围内布局合理。当前 rule-set-form.tsx 的 768px/1024px/1440px 断点是合理实践，应推广到其他复杂表单。
   **决策依据：** 产品定位决定响应式需求有限，但不代表布局可以不受控

2. **议题：无障碍（keyboard 导航/ tabIndex）的优先级**
   **各方立场：**
   - Designer：0 tabIndex，0 keyboard 导航，1 data-testid
   - Critic：目标用户无障碍需求占比不明，投入产出比存疑
   - PM：patient-h5 已有 LiveRegion 和 aria 支持
   **裁决：** 当前阶段不作为优先行动。patient-h5 的无障碍支持（LiveRegion + aria）已超过同类产品平均水平。admin/doctor 端的键盘导航可在后续迭代中逐步添加。
   **决策依据：** ROI 不支持当前阶段投入大量无障碍改进

---

## 被低估的优势

1. **完整的多租户 SaaS 架构**：4 种租户识别方式（Header/子域名/路径/编码）+ 订阅计划 + 用量统计 + 审计日志 + 状态校验（禁用/欠费/到期），这在同类项目中是相当完备的实现
2. **规则引擎设计成熟**：Mixin 组合模式（TimeWindow + Policy + Validation）+ 规则快照机制 + 审计日志 + 性能监控服务，是业务复杂度管理的优秀实践
3. **前端 API 包工程化水平高**：packages/api 包含 axios 封装 + 性能监控（createApiTimer）+ 重试机制（withRetry）+ Taro 适配器，40+ 模块统一管理
4. **统一的错误处理体系**：结构化错误码（error_code）+ 9 种全局异常处理器 + 业务异常类，前端可精确分支处理
5. **WebSocket 多实例支持**：Redis Pub/Sub 广播机制，支持水平扩展，非单实例局限

---

## 行动计划（按 ROI 排序）

| 优先级 | 行动 | 成本 | 价值 | 负责 | 状态 |
|--------|------|------|------|------|------|
| P0 | 建立测试覆盖率基线 | 32-48h | 高 | Engineer | 待执行 |
| P1 | 拆分 deps.py 核心文件 | 24-32h | 高 | Engineer | 待执行 |
| P1 | Celery 任务重试/超时/监控 | 8-16h | 高 | Engineer | 待执行 |
| P1 | 连接池负载测试验证 | 4-8h | 高 | Engineer | 待执行 |
| P1 | WebSocket 故障恢复机制 | 12-20h | 高 | Engineer | 待执行 |
| P2 | CSS 设计 token 统一 | 4-8h | 中 | Designer | 待执行 |
| P2 | 原生 alert/confirm 替换 | 8-12h | 中 | Designer | 待执行 |
| P2 | packages/shared 跨端共享审查 | 8-12h | 中 | Engineer | 待执行 |
| P2 | 前端性能监控基线 | 8-16h | 中 | Engineer + Designer | 待执行 |
| 待定 | 连接池规模调优 | 4-8h | 待定 | Engineer | 需用户确认实际并发量 |

### P0：立即执行（高价值、低成本）

1. **建立测试覆盖率基线**
   - 为核心业务模块（预约创建/排班生成/规则引擎/支付流程）编写单元测试和集成测试
   - 配置 pytest-cov 覆盖率报告，CI 集成
   - 目标：核心模块 >60% 行覆盖率
   - 成本：32-48h | 负责：Engineer
   - 理由：Critic 关键质询 #7，没有测试覆盖率就无法验证"已实现"的真实性

### P1：本轮迭代（高价值、中等成本）

1. **拆分 deps.py 核心文件**
   - 将 deps.py（4.2 万行）按职责拆分：认证(get_current_user/get_current_doctor) → auth_deps.py，租户校验 → tenant_deps.py，权限/用量 → permission_deps.py
   - 将 1.5万+ 行的 task 文件按功能拆分子模块
   - 成本：24-32h | 负责：Engineer

2. **Celery 任务可靠性加固**
   - 为所有定时任务添加 autoretry_for + max_retries + time_limit 配置
   - 配置 Flower 告警规则（任务失败率 >5% 告警）
   - 成本：8-16h | 负责：Engineer

3. **连接池负载测试**
   - 编写负载测试脚本，模拟多租户并发场景
   - 根据 P99 延迟和连接池使用率调整 pool_size
   - 成本：4-8h | 负责：Engineer

4. **WebSocket 故障恢复机制**
   - 添加指数退避重连策略
   - 添加消息确认/去重机制
   - 添加降级到轮询的 fallback
   - 成本：12-20h | 负责：Engineer

### P2：下个周期规划（中等价值、较高成本）

1. **CSS 设计 token 统一**
   - 清理 admin 中未使用的 CSS 变量
   - 将硬编码颜色迁移到 Ant Design theme token
   - 成本：4-8h | 负责：Designer

2. **原生 alert/confirm 替换**
   - 优先替换核心操作路径（预约/排班/支付）的原生调用
   - 统一使用 Modal.confirm / message.success
   - 成本：8-12h | 负责：Designer

3. **packages/shared 跨端共享审查**
   - 审查各端是否有重复的类型定义和工具函数
   - 将高复用率的代码抽至 packages/shared
   - 成本：8-12h | 负责：Engineer

4. **前端性能监控基线**
   - 为 admin 和 patient-h5 关键页面添加 FCP/LCP 监控
   - 与 packages/api 已有的性能监控工具打通
   - 成本：8-16h | 负责：Engineer + Designer

### 待定：需用户确认

1. **连接池规模调优**
   - 当前 pool_size=5，Critic 质疑与多租户 SaaS 规模匹配度
   - 需用户确认：当前实际并发量和租户数量级
   - 若并发量 >50 或租户数 >20，建议 pool_size 调至 10-20
   - 成本：4-8h（调优后） | 负责：Engineer

---

## 摘要

**使用模式：** 集中调度

**关键共识：**
- 9 项达成共识（2 项分歧已裁决）

**关键分歧：**
- 2 项需要决策者介入（响应式设计优先级、无障碍优先级 — 均已裁决为低优先级）

**Top 3 P0 行动：**
1. 建立测试覆盖率基线（32-48h，核心模块 >60%） — Critic 关键质询：无验收标准
2. 拆分 deps.py 核心文件（24-32h） — 单文件 4.2 万行影响可维护性
3. Celery 任务可靠性加固（8-16h） — 13 个定时任务缺乏重试/超时/监控

**Critic 关键洞察：**
- Critic 质询 #7（🚨关键）：44 模块"全部已实现"声明缺乏测试覆盖率支撑 — 已纳入 P0
- Critic 质询 #3（🚨关键）：连接池 pool_size=5 缺乏基准测试 — 已纳入待定（需用户确认实际规模）
- Critic 质询 #1（🚨关键）：多租户架构自洽性 — 部分充分，欠费检测机制已存在，连接池需验证

---

## 附录：模式切换日志

| 时间 | 从 | 到 | 原因 |
|------|-----|-----|------|
| | | | |
