# appointment-booking-system — 支付/退款/多租户架构研究画布

> 协作模式：集中调度
> 日期：2026-04-10
> 审查目标：小程序支付流程、后台退款操作、多商户支付隔离机制的正确性与安全性

---

## 模式选择

**选定模式：** 集中调度

**选择理由：** 技术审计/验证任务，安全关键（涉及资金），需要单一权威做安全裁决，快速收敛。

---

## Round 1：事实层（只写事实，不评价）

### PM — 产品/业务视角

**支付业务流程现状：**
- 预约创建直接设为 CONFIRMED(1)，跳过待支付状态 (`service_booking.py:169`)
- 状态 0（待支付）仅存在于枚举定义，未被实际使用 (`appointment.py:20`)
- 无支付超时/过期处理、无待支付到已支付的状态流转逻辑
- 预约取消仅更新状态为 CANCELLED，无退款调用 (`service_booking.py:219-322`)
- **诊费模型已定义**：`ConsultationFeeType`/`StoreFeeTemplate`/`DoctorConsultationFee` 含 `initial_fee`/`follow_up_fee`（Numeric(10,2)），分初诊/复诊金额 (`consultation_fee.py`)

**退款业务流程现状：**
- 无退款状态枚举、无退款记录表、无退款金额字段
- 管理后台预约列表/详情页无退款操作入口 (`appointment/list.tsx`, `appointment/detail.tsx`)
- 无退款审核/审批流程、无部分退款场景支持
- 取消预约使用分布式锁 (`appointment:cancel:{schedule_id}`)，但无退款幂等性校验

**多商户业务隔离：**
- PaymentProfile 支持 direct（直连）和 service_provider（服务商）两种模式
- PaymentRoute 支持按门店/小程序实例维度路由到不同支付配置
- 预约表保存支付快照（payment_profile_id, payment_mode, payment_mch_id 等 7 个字段）
- 不同门店可使用不同支付账户（通过 PaymentRoute 优先级排序）

**资金安全现状：**
- 无退款金额与原支付金额校验
- 无退款限额或退款审核机制
- 无对账机制（无 reconciliation/settlement 代码）
- 无重复退款防护（无退款记录表）

**小程序端支付体验：**
- 预约流程无支付确认步骤，直接创建预约记录
- 预约结果页固定显示"预约成功"，无支付结果分支
- 无支付方式选择、支付金额展示

### Designer — 用户/UI 视角

**小程序端支付页面：**
- 预约列表定义了状态 0（待支付，橙色样式），但实际筛选逻辑未包含状态 0
- 预约详情页底部操作按钮：取消预约 + 扫码签到（仅状态 1），无支付按钮
- 预约确认页无支付确认步骤，直接提交
- 预约结果页固定"预约成功"，无支付成功/失败分支

**管理后台支付配置页面：**
- 支付配置列表完整：名称、编码、模式、AppID、商户号、状态、操作列
- 支付配置表单分三组：基本信息、微信支付配置、敏感信息配置
- 敏感信息使用 `env:变量名` 引用方式，非明文存储
- 小程序实例管理中支付配置为可选关联字段

**管理后台预约管理页面：**
- 预约列表有 9 种状态 Tag，包含状态 0（待支付，橙色）
- 操作列：详情、取消预约（状态 0）、标记爽约（状态 1）、取消签到（超管）
- **无退款相关操作按钮**
- 预约详情页无支付/退款信息展示

**多租户 UI 隔离：**
- 租户切换器仅平台管理员可见，位于顶部导航栏
- 切换逻辑：API 验证 → localStorage 存储 → 清除缓存 → 刷新页面
- 请求拦截器自动添加 `X-Tenant-ID` Header

**前端 API 调用层：**
- 预约创建/取消 API 无支付/退款参数
- 支付配置 CRUD API 完整定义
- 共享常量 `APPOINTMENT_STATUS` 未定义状态 0，与管理后台定义不一致

### Engineer — 技术架构视角

**支付配置解析与路由：**
- `PaymentConfigResolver.resolve()` 优先级链：payment_profile_id → store_id 路由 → miniapp_instance_id 默认 (`config_resolver.py:29-65`)
- **PaymentRoute 查询 WHERE 条件未包含 tenant_id** (`config_resolver.py:42-51`)
- 无缓存机制，每次查询直接访问数据库

**微信支付集成现状：**
- `requirements.txt` 中无 wechatpay-python 或类似 SDK 依赖
- `infrastructure/wechat/` 仅有小程序登录、获取手机号、订阅消息、access_token 管理
- 无签名/验签实现、无支付 API 调用代码

**多租户支付隔离风险：**
- TenantContextMiddleware 识别优先级：X-Tenant-ID → X-Tenant-Code → 子域名 → 路径前缀
- **PaymentConfigResolver 查询时未强制包含 tenant_id 过滤**
- 预约创建有租户校验（排班属于当前租户），但配置解析器本身无租户隔离
- Redis 微信 Token 缓存 key 包含 tenant_id

**退款技术实现：**
- 全局搜索无 refund 相关实现代码
- 无微信退款 API 调用、无退款回调处理、无退款幂等性保障
- 无退款与预约状态变更的事务一致性

**数据模型完整性：**
- Appointment 支付快照字段完整（7 个字段），但缺少 payment_amount 和 payment_transaction_id
- PaymentProfile 含 tenant_id + mode + mch_id/sub_mchid + 密钥引用
- **无独立 PaymentTransaction/PaymentOrder 表**
- **无退款记录表（RefundRecord）**
- **诊费模型完整**：`ConsultationFeeTemplate`(全局)、`StoreFeeTemplate`(门店级)、`DoctorConsultationFee`(医生级) 含金额字段

**安全机制：**
- 密钥存储：`env:VAR_NAME` 引用机制
- 支付回调签名验证：未实现
- 退款权限控制（RBAC）：未找到退款相关权限码
- 支付操作审计日志：未实现

**支付快照字段使用状态：**
- Appointment 的 7 个支付快照字段（payment_profile_id 等）在预约创建代码中**未被写入**
- 全局搜索 `service_booking.py` 中无 payment_profile_id 引用
- 这些字段目前始终为 NULL

---

## Round 2：辩论层

### 交叉评论投票矩阵（集中调度模式）

| # | 议题 | 裁决者立场 | Critic 质询 | 最终裁决 |
|---|------|-----------|------------|---------|
| 1 | ConfigResolver 缺少 tenant_id 过滤 | 安全风险属实，需修复 | 间接保护存在（外键链路），但应加纵深防御 | **确认风险，必须修复** |
| 2 | 支付/退款完全未实现 | 需要从零实现 | 系统有诊费模型（收费基础），非"无需支付" | **确认需实现，有业务基础** |
| 3 | Appointment 无 payment_amount 字段 | 数据模型需补充 | 正确，收费模型虽定义但未关联到预约 | **确认缺失，必须补充** |
| 4 | 支付快照字段未被写入 | 基础设施待激活 | 批评正确，字段存在但未使用 | **确认，需在支付流程中激活** |
| 5 | 支付配置"完整性"被夸大 | 配置管理完整 ≠ 支付系统完整 | 同意 Critic，"有配置页"不等于"能支付" | **确认区分** |
| 6 | 租户切换器数据隔离 | 切换后页面刷新，数据正确切换 | 需验证支付配置列表的隔离效果 | **基本完整，需验证边界** |

### Critic 质询回应

**质询 1（ConfigResolver tenant_id）：** 间接保护通过 `store → PaymentRoute → PaymentProfile` 外键链路存在，但防御纵深不足。如果 store_id 被恶意构造，可能绕过租户隔离。必须在查询中显式添加 `tenant_id` 过滤。

**质询 3（🚨关键 — 退款不实现是否是缺陷）：** 系统有诊费模型（`ConsultationFeeTemplate` 含 `initial_fee`/`follow_up_fee`），收费业务基础已存在。退款是对已收费预约取消时的必要流程，不是"不需要"，而是"未实现"。

**质询 5（🚨关键 — 无支付金额字段）：** Appointment 缺少 `payment_amount` 和 `payment_transaction_id` 字段。诊费金额在 `ConsultationFee*` 表中，但预约创建时未读取和快照。需在支付流程中读取诊费金额并写入预约快照。

**质询 9（🚨关键 — 支付快照未写入）：** 代码验证确认，`service_booking.py` 中无任何 payment_* 字段的赋值操作。这些字段在当前版本始终为 NULL，需在支付流程实现时激活。

### 独到发现

1. **诊费体系与支付体系脱节**：诊费模型（3 级：全局/门店/医生）定义了金额，PaymentProfile 定义了支付配置，但两者之间无任何代码连接。预约创建时既不读取诊费金额，也不调用支付配置解析器。

2. **多租户纵深防御缺口**：虽然数据模型层有 tenant_id，中间件层有 TenantContextMiddleware，但关键的支付配置解析器查询未包含租户过滤，形成纵深防御缺口。

---

## Round 3：共识层

### 共识项

1. **PaymentConfigResolver 必须添加 tenant_id 过滤**
   - 结论：安全纵深防御必需，虽然外键链路提供间接保护，但查询必须显式过滤
   - 修改文件：`config_resolver.py`
   - 成本：1h
   - 优先级：P0

2. **Appointment 模型需补充支付金额和交易号字段**
   - 结论：退款必须能追溯原支付金额和外部交易号
   - 需添加字段：`payment_amount`(Numeric)、`payment_transaction_id`(String)、`refund_status`(String)、`refund_amount`(Numeric)
   - 修改文件：`appointment.py` + 新增 Alembic 迁移
   - 成本：2h
   - 优先级：P0

3. **需新建 RefundRecord 独立退款记录表**
   - 结论：防止重复退款、支持退款审计、记录退款全生命周期
   - 字段：id, appointment_id, tenant_id, payment_profile_id, refund_no, out_trade_no, refund_amount, original_amount, refund_reason, status, wx_refund_id, callback_raw, created_by
   - 新增文件：`models/refund.py` + 迁移
   - 成本：3h
   - 优先级：P0

4. **需集成微信支付 SDK**
   - 结论：核心支付能力依赖微信支付 API
   - 添加依赖：`wechatpay-python`（官方 SDK）
   - 实现模块：`infrastructure/payments/wechat_pay.py`
   - 功能：创建支付订单、查询订单、申请退款、退款查询、回调验签
   - 成本：16h
   - 优先级：P1

5. **预约创建需接入支付流程**
   - 结论：创建预约时需读取诊费 → 调用 ConfigResolver 获取支付配置 → 快照到预约 → 调用微信统一下单 → 返回支付参数给前端
   - 状态流转改为：创建 → status=0(待支付) → 用户支付 → 回调 → status=1(已预约)
   - 修改文件：`service_booking.py`、前端预约确认页
   - 成本：16h
   - 优先级：P1

6. **退款流程实现（防退错核心）**
   - 结论：退款必须基于预约的支付快照，确保退到正确商户
   - 安全措施：
     a. 从预约支付快照获取 mch_id/sub_mchid，确保退款到原收款商户
     b. 校验退款金额 <= 原支付金额
     c. 创建 RefundRecord 记录，状态幂等控制
     d. 退款与预约状态变更在同一事务中
     e. 回调验签确认退款结果
   - 修改文件：`modules/appointments/service_booking.py`、新增 `modules/refunds/`
   - 成本：20h
   - 优先级：P1

7. **管理后台退款操作 UI**
   - 结论：管理员需能在预约详情页发起退款、查看退款记录
   - 功能：退款按钮、退款金额输入（默认全额，支持部分退款）、退款原因、退款记录列表
   - 修改文件：`apps/admin/src/pages/appointment/detail.tsx`、`list.tsx`
   - 成本：8h
   - 优先级：P1

8. **小程序端支付流程 UI**
   - 结论：用户需在预约确认页完成支付
   - 功能：诊费展示 → 确认支付 → 调用微信支付 → 结果页（成功/失败）
   - 修改文件：`packageBooking/pages/booking/index.tsx`、`result.tsx`
   - 成本：12h
   - 优先级：P1

---

## 行动计划（按 ROI 排序）

| 优先级 | 行动 | 成本 | 价值 | 负责 | 状态 |
|--------|------|------|------|------|------|
| P0 | ConfigResolver 添加 tenant_id 过滤 | 1h | 安全修复 | Engineer | 待执行 |
| P0 | Appointment 补充支付/退款字段 + 迁移 | 2h | 数据基础 | Engineer | 待执行 |
| P0 | 新建 RefundRecord 表 + 迁移 | 3h | 退款安全 | Engineer | 待执行 |
| P1 | 集成微信支付 SDK + 支付核心服务 | 16h | 核心能力 | Engineer | 待执行 |
| P1 | 预约创建接入支付流程（含诊费读取） | 16h | 支付闭环 | Engineer | 待执行 |
| P1 | 退款流程实现（防退错机制） | 20h | 资金安全 | Engineer | 待执行 |
| P1 | 管理后台退款 UI | 8h | 运营能力 | Designer | 待执行 |
| P1 | 小程序支付流程 UI | 12h | 用户体验 | Designer | 待执行 |
| P2 | 支付操作审计日志 | 4h | 合规审计 | Engineer | 待执行 |
| P2 | 对账系统 | 16h | 财务对齐 | Engineer | 待执行 |
| P2 | 支付路由管理 UI | 8h | 配置便利 | Designer | 待执行 |
| 待定 | 支付超时自动取消机制 | 4h | 体验优化 | Engineer | 需确认 |

### P0：立即执行（高价值、低成本）

1. **ConfigResolver 添加 tenant_id 过滤**（1h）
   - 文件：`apps/server/app/infrastructure/payments/config_resolver.py:42-51`
   - 在所有 PaymentRoute/PaymentProfile 查询中添加 `tenant_id` 条件
   - 获取当前租户：`from app.middleware.tenant_context import get_current_tenant_id`

2. **Appointment 补充支付/退款字段**（2h）
   - 文件：`apps/server/app/models/appointment.py`
   - 新增字段：`payment_amount`、`payment_transaction_id`、`refund_status`、`refund_amount`
   - 新增 Alembic 迁移

3. **新建 RefundRecord 表**（3h）
   - 新文件：`apps/server/app/models/refund.py`
   - 字段设计（防退错核心）：
     ```
     id, appointment_id, tenant_id  -- 租户隔离
     payment_profile_id             -- 关联支付配置（含 mch_id）
     refund_no                      -- 退款单号（幂等键）
     out_trade_no                   -- 原支付交易号
     refund_amount, original_amount -- 退款金额校验
     refund_reason, status          -- 退款原因和状态
     wx_refund_id, callback_raw     -- 微信退款结果
     ```
   - 唯一约束：`appointment_id` + `refund_no`（防重复退款）

### P1：本轮迭代（高价值、中等成本）

4. **微信支付 SDK 集成**（16h）
   - 添加依赖：`requirements.txt` 添加 `wechatpay-python`
   - 新文件：`apps/server/app/infrastructure/payments/wechat_pay_service.py`
   - 核心方法：`create_order()`, `query_order()`, `create_refund()`, `query_refund()`, `verify_callback()`
   - 密钥加载：从 `PaymentProfile` 读取 `api_v3_key_ref`/`private_key_ref`，通过 `secret_refs.py` 解析
   - 支持 direct 和 service_provider 两种模式

5. **预约创建接入支付流程**（16h）
   - 修改 `service_booking.py` 的 `create()` 方法
   - 流程：
     1. 读取诊费（`DoctorConsultationFee` → `StoreFeeTemplate` → `ConsultationFeeTemplate`，按优先级）
     2. 调用 `PaymentConfigResolver.resolve()` 获取支付配置
     3. 写入支付快照到 Appointment（包括 payment_amount）
     4. 调用微信统一下单 API
     5. 设置 status=0（待支付）
     6. 返回支付参数给前端
   - 新增支付回调路由：`/api/v1/payments/wechat/callback`

6. **退款流程实现 — 防退错核心**（20h）
   - 新模块：`apps/server/app/modules/refunds/`
   - **退款安全机制（确保不退错）：**
     a. **商户一致性校验**：退款时从 Appointment 支付快照读取 `payment_mch_id`/`payment_sub_mchid`，确保退款请求发往原收款商户
     b. **金额校验**：`refund_amount <= payment_amount`，累计退款不超过原支付金额
     c. **幂等性**：`RefundRecord.refund_no` 作为幂等键，同一 refund_no 不重复处理
     d. **事务一致性**：RefundRecord 创建 + Appointment.refund_status 更新在同一事务
     e. **回调验签**：微信退款回调必须验签后才更新状态
     f. **租户隔离**：退款查询强制过滤 `tenant_id`
   - RBAC 权限码：`appointment:refund`、`appointment:refund:partial`

7. **管理后台退款 UI**（8h）
   - 预约详情页增加退款按钮（需 `appointment:refund` 权限）
   - 退款表单：退款金额（默认全额）、退款原因
   - 退款记录 Tab：展示退款历史和状态

8. **小程序支付流程 UI**（12h）
   - 预约确认页增加诊费展示和"确认支付"按钮
   - 调用 `wx.requestPayment()` 发起微信支付
   - 支付结果页：成功（显示预约信息）、失败（重试/取消）
   - 预约列表支持"待支付"状态筛选和"去支付"操作

### P2：下个周期规划

9. **支付操作审计日志**（4h）
10. **对账系统**（16h）
11. **支付路由管理 UI**（8h）

### 已确认的业务规则（用户确认）

12. **支付超时自动取消**（4h）— 30 分钟未支付自动取消，释放号源。Celery 定时任务扫描 status=0 且创建时间超过 30 分钟的预约。
13. **免费预约跳过支付** — 诊费为 0 时直接 CONFIRMED，不走支付流程。
14. **支持部分退款** — 退款金额可小于原支付金额，但累计退款不超过原支付金额。

---

## 摘要

**使用模式：** 集中调度

**关键共识：** 8 项达成共识

**关键分歧：** 0 项（Critic 的关键质询已全部回应）

**Top 3 P0 行动：**
1. ConfigResolver 添加 tenant_id 过滤（1h）— 修复跨租户支付配置访问风险
2. Appointment 补充支付/退款字段 + 迁移（2h）— 支付金额和交易号是退款的基础
3. 新建 RefundRecord 退款记录表（3h）— 防重复退款、退款审计

**Critic 关键洞察：**
- 系统有诊费模型（收费基础），支付不是"不需要"，而是"未连接"
- "配置管理完整"不等于"支付系统完整" — 配置只是地基，上面没有建楼
- 支付快照字段已存在但从未被写入，需在支付流程中激活

**总成本估算：** P0=6h, P1=72h, P2=28h

---

## 核心结论：确保退款不退错的设计要点

1. **退款必须基于预约支付快照**：退款时从 `Appointment.payment_mch_id`/`payment_sub_mchid` 读取原收款商户号，不从 PaymentProfile 实时读取（避免配置变更后退款到错误商户）

2. **RefundRecord 作为幂等和审计基础**：每笔退款创建唯一记录，`refund_no` 防重复，`original_amount` 校验金额

3. **退款与预约状态的事务一致性**：退款记录创建和预约状态更新在同一个数据库事务中

4. **租户双重校验**：退款查询既过滤 `RefundRecord.tenant_id`，也校验 `Appointment.tenant_id`，确保跨租户无法操作

5. **微信退款回调验签**：回调必须验证签名后才更新退款状态，防止伪造退款成功通知

6. **部分退款累计校验**：每笔退款创建前，查询该预约的 `RefundRecord` 累计退款金额，确保 `累计退款 + 本次退款 <= payment_amount`

7. **支付超时自动取消**：Celery 定时任务（每5分钟）扫描 status=0 且创建超过30分钟的预约，自动取消并释放号源

8. **免费预约跳过支付**：创建预约时先计算诊费金额，为0则直接 CONFIRMED，不调用支付流程
