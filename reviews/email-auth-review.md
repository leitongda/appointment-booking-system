# appointment-booking-system — 自适应多智能体研究画布

> 协作模式：集中调度
> 日期：2026-05-07
> 审查目标：邮箱认证功能设计（邮箱验证码登录、自动注册、绑定/解绑/换绑）

---

## 模式选择

**选定模式：** 集中调度

**选择理由：** 功能边界已由用户明确列出，三维权重均衡无主导领域，集中调度可快速收敛产出可执行方案。

---

## Round 1：事实层（只写事实，不评价）

### PM — 产品视角

**产品定位：**
- 当前系统为 SaaS 多租户医院预约挂号系统
- 邮箱在产品中的现有定位是"门店业务通知渠道"，非认证方式
- Account 主表无 email 字段，仅 AccountAdmin 扩展表有 email 字段（存储用，非认证用）
- 管理员 profile 中有邮箱字段但仅做格式校验，无验证码验证

**功能完成度：**
- 邮箱验证码登录：未实现
- 邮箱自动注册：未实现
- 邮箱绑定/解绑/换绑：未实现
- 手机换绑：不存在
- 微信绑定/解绑：已实现（微信→手机号、微信→用户信息）
- 短信验证码系统：已实现（6位数字、Redis存储、5分钟有效、60秒间隔限制）

**竞品功能对比：**
- 同赛道系统通常支持手机号+验证码登录，邮箱登录为差异化功能而非行业标配
- 邮箱绑定/解绑在 SaaS 系统中常见但非强制要求

**目标用户线索：**
- 三端用户：管理员（后台管理）、医生（工作台）、患者（H5/小程序）
- 管理员/医生不通过自助注册创建，由管理员后台操作
- 患者支持自助注册（手机号+密码）
- 多租户隔离：所有认证操作均带 tenant_id 维度

### Designer — 用户视角

**页面清单与结构：**
- admin 端登录页：3个Tab（微信扫码/手机号验证码/账号密码），使用 antd Tabs
- patient-h5 登录页：手机号+密码单一表单，底部有"忘记密码""注册账号"链接
- doctor 端登录页：账号+密码单一表单
- admin 个人设置页：已有邮箱字段（纯文本输入，无验证码）
- patient-h5 编辑资料页：手机号为 disabled 不可修改
- 不存在"安全设置"或"安全中心"独立页面
- 不存在邮箱绑定/解绑/换绑的独立 UI 页面

**交互模式统计：**
- 验证码交互：发送按钮（倒计时60秒）+ 6位输入框，各端独立实现无通用组件
- 倒计时逻辑：admin 端用 setTimeout 递归，patient-h5 端用 setInterval，实现不统一
- 确认操作：patient-h5 用 Dialog.confirm，admin 用 Modal.confirm
- 错误提示：admin 用 message.error，patient-h5 用 Toast.show，doctor 用 message.error

**响应式设计事实：**
- admin/doctor 端为桌面端布局
- patient-h5 端为移动端布局，使用 antd-mobile 组件

**组件一致性事实：**
- 各端 UI 组件库不同：admin用antd+ProComponents、patient-h5用antd-mobile、doctor用antd+ProComponents、admin-v2用shadcn/ui
- 表单验证方式不同：admin/doctor用antd rules、patient-h5用antd-mobile rules、admin-v2用zod
- Token 管理统一：所有端使用 localStorage + @hospital/shared 工具函数

### Engineer — 技术视角

**存储层事实：**
- Account 主表（accounts）：有 phone、username、password_hash，无 email 字段
- AccountAdmin 扩展表：有 email 字段（String(100)），仅存储
- AccountUser 扩展表：有 openid/unionid，无 email
- AccountDoctor 扩展表：无 email
- 唯一约束：UniqueConstraint(tenant_id, phone)、UniqueConstraint(tenant_id, username)
- PostgreSQL 中 NULL 不参与 UNIQUE 约束

**核心引擎事实：**
- 验证码生成：6位纯数字，random.choices（非密码学安全）
- 验证码存储：Redis，key 模式 `sms:{tenant_id}:{phone}:{code_type}`，值为 JSON `{"code":"123456","verified":false}`
- 有效期：300秒（5分钟）
- 发送间隔限制：60秒，通过 Redis TTL 控制
- 防重放：验证成功后标记 verified=True
- 多租户隔离：所有验证码操作均带 tenant_id

**API/协议事实：**
- 现有认证端点：/login、/register、/send-code、/forgot-password、/refresh、/change-password
- 微信认证端点：/wechat/login、/wechat/phone、/wechat/bind-phone、/wechat/bind-userinfo
- 管理员认证端点：/login、/phone-login、/sms/send、/sms/login、/wechat/*
- JWT Token：HS256，access_token 30分钟，refresh_token 7天
- 认证中间件：get_current_user、get_current_admin 等依赖注入函数

**安全机制事实：**
- 密码哈希：bcrypt
- 管理员登录支持 RSA 加密传输密码
- Token 黑名单机制（Redis）
- 管理员 session 存储在 Redis

**依赖和模块耦合事实：**
- 邮件发送基础设施已存在：EmailService（aiosmtplib异步）、email_hook_task（smtplib同步）
- SMTP 配置存储在 system_settings 表（category="email"），平台级统一配置
- 邮件模板系统已存在：EmailTemplate 模型，{{key}} 替换渲染
- 异步/同步两套邮件发送实现存在配置键命名不一致问题
- 验证码相关 Redis 操作封装在 core/redis.py 中（294-393行）
- SMS 发送有抽象接口 SmsProvider，支持 mock/aliyun
- 数据库迁移使用 Alembic，最新版本号 079
- 路由注册使用 RouterRegistration dataclass 集中管理

---

## Round 2：辩论层

### 交叉评论投票矩阵

#### 简化投票矩阵（集中调度模式）

| 议题 | 裁决者立场 | Critic 质询 | 最终裁决 |
|------|-----------|------------|---------|
| email 字段归属 | Account 主表新增 | A-主表 schema 变更是前置依赖 | Account 主表新增 email + 唯一约束 |
| 用户类型适用范围 | 按角色分层 | B-适用范围未定义 | 患者全功能，管理员/医生仅登录+绑定 |
| Redis 验证码方案 | 独立实现 | C-SMS 模式不可直接复用 | 新增 email 前缀 + 独立方法组 |
| 邮件发送路径 | 异步 EmailService | Q4-双轨问题 | 走 aiosmtplib 异步路径 |
| 验证码安全性 | 升级 secrets | Q5-风险未量化 | 改用 secrets 模块 |
| 组件统一策略 | 各端独立 | Q7-方向错误 | 仅统一交互逻辑，UI 库保持独立 |
| 微信绑定兼容 | 复用 bind-phone | Q8-流程冲突 | 邮箱用户绑定微信需先绑手机 |
| SMTP 配置策略 | 平台级统一 | Q9-租户隔离未定义 | 不按租户隔离，功能开关依赖 SMTP 可用 |
| 现有数据清洗 | 必须清洗 | Q10-安全隐患 | 上线前清洗 admin 邮箱数据 |

### 独到发现

1. **邮箱认证改变了 Account 模型的标识维度**：从 phone/username 二元标识扩展为 phone/username/email 三元标识，影响所有通过标识查找用户的代码路径
2. **邮箱自动注册与现有注册流程的差异**：手机号注册需要 password，邮箱自动注册可以无密码（首次登录后引导设置），需要决定密码策略
3. **邮箱登录入口的 Tab 设计**：admin 端已有 3 个 Tab，新增邮箱 Tab 会使登录页更复杂，需要评估是否合并手机号/邮箱为"验证码登录"统一入口

### Critic 质询

1. [Critic → 全体] 质询 1：Account 主表 email 字段的架构决策缺失
   - 论据：当前 Account 无 email 字段，邮箱认证必须先解决字段归属和约束策略
   - 要求回应：Engineer
   - 级别：普通

2. [Critic → 全体] 质询 2：Redis 邮箱验证码基础设施缺失
   - 论据：Redis 中只有 SMS 前缀，无 email 前缀，key 模式硬编码了手机号维度
   - 要求回应：Engineer
   - 级别：普通

3. [Critic → 全体] 质询 3：管理员/医生的邮箱认证适用性未分析
   - 论据：管理员/医生不通过自助注册创建，邮箱自动注册对其不适用
   - 要求回应：PM
   - 级别：普通

4. [Critic → 全体] 质询 4：异步/同步邮件发送双轨问题
   - 论据：EmailService（异步）和 email_hook_task（同步）配置键不一致
   - 要求回应：Engineer
   - 级别：普通

5. [Critic → 全体] 质询 5：random.choices 安全风险未量化
   - 论据：6 位数字验证码 + 5 分钟有效期 + 60 秒间隔，暴力破解风险需评估
   - 要求回应：Engineer
   - 级别：普通

6. [Critic → PM] 质询 6：竞品对比缺少数据支撑
   - 论据："部分支持""标准安全功能"缺乏具体数据
   - 要求回应：PM
   - 级别：普通

7. [Critic → Designer] 质询 7：组件一致性分析方向偏差
   - 论据：各端使用不同组件库是架构性合理差异，不应强行统一
   - 要求回应：Designer
   - 级别：普通

8. [Critic → 全体] 质询 8：邮箱注册用户与微信绑定流程的兼容性
   - 论据：现有微信绑定假设用户有手机号，邮箱注册用户可能无手机号
   - 要求回应：Engineer / PM
   - 级别：普通

9. [Critic → 全体] 质询 9：SMTP 可用性前提和租户隔离策略
   - 论据：邮箱认证依赖 SMTP 服务，多租户场景下配置策略未定义
   - 要求回应：PM / Engineer
   - 级别：普通

10. [Critic → 全体] 质询 10：现有 admin 邮箱数据安全隐患
    - 论据：AdminCreate/AdminUpdate 的 email 字段无格式校验和唯一性校验
    - 要求回应：Engineer / PM
    - 级别：普通

### 🚨 Critic 关键质询追踪

| # | 关键质询内容 | 三方回应摘要 | 回应是否充分 | 处置 |
|---|------------|------------|------------|------|
| A | Account 主表 schema 变更是邮箱认证的前置依赖 | 裁决：在 accounts 表新增 email 字段 + UniqueConstraint(tenant_id, email)，与 phone 模式一致。AccountAdmin 现有 email 数据需迁移。 | 是 | 纳入计划 |
| B | 邮箱认证功能的用户类型适用范围未定义 | 裁决：患者支持全部功能（登录+注册+绑定）；管理员/医生仅支持登录+绑定，不开放自动注册。 | 是 | 纳入计划 |
| C | Redis 验证码存储没有邮箱维度的实现 | 裁决：独立实现，新增 email:{tenant_id}:{email}:{code_type} 前缀和独立方法组，不泛化 SMS 方法。 | 是 | 纳入计划 |

---

## Round 3：共识层

### ✅ 共识项

1. **议题：Account 主表新增 email 字段**
   **结论：** 在 accounts 表新增 `email = Column(String(100), nullable=True)` + `UniqueConstraint("tenant_id", "email")`
   **建议行动：** 编写 Alembic 迁移脚本，迁移 AccountAdmin 现有 email 数据到 accounts 表
   **成本估算：** 4h（迁移脚本 + 数据清洗 + 测试）
   **优先级：** P0

2. **议题：Redis 邮箱验证码方法组**
   **结论：** 在 core/redis.py 新增 `set_email_code`、`get_email_code`、`verify_email_code`、`check_email_rate_limit` 方法，key 前缀 `email:`
   **建议行动：** 复用 SMS 的存储结构和校验逻辑，独立实现避免破坏现有接口
   **成本估算：** 2h
   **优先级：** P0

3. **议题：邮箱验证码发送服务**
   **结论：** 新增 `send_email_verification_code` 方法到 EmailService，使用 aiosmtplib 异步发送
   **建议行动：** 新增邮件验证码模板（含 6 位验证码、有效期提示）
   **成本估算：** 3h
   **优先级：** P0

4. **议题：邮箱认证 API 端点**
   **结论：** 新增 `/email/send-code`、`/email/login`、`/email/register` 端点到 auth router
   **建议行动：** 参照现有 SMS 验证码登录流程实现，邮箱登录支持自动注册（仅患者）
   **成本估算：** 8h
   **优先级：** P1

5. **议题：邮箱绑定/解绑/换绑 API**
   **结论：** 新增 `/email/bind`、`/email/unbind`、`/email/change` 端点，需要已登录状态 + 邮箱验证码
   **建议行动：** 绑定前校验邮箱唯一性，换绑需验证新旧邮箱
   **成本估算：** 6h
   **优先级：** P1

6. **议题：用户类型适用范围控制**
   **结论：** 邮箱自动注册仅对 AccountUser 类型开放，管理员/医生邮箱登录前提是邮箱已绑定
   **建议行动：** 在登录/注册逻辑中加入 account_type 判断
   **成本估算：** 2h
   **优先级：** P1

7. **议题：验证码生成安全性升级**
   **结论：** 将 `random.choices` 改为 `secrets.choice`，同时应用于 SMS 和 email 验证码
   **建议行动：** 修改 sms/service.py 的 generate_code 函数
   **成本估算：** 0.5h
   **优先级：** P0

### ⚡ 分歧项

1. **议题：admin 端邮箱登录入口设计**
   **各方立场：**
   - PM：应在 admin 端登录页新增邮箱 Tab
   - Designer：admin 端已有 3 个 Tab，新增第 4 个会使界面复杂
   - Engineer：可将手机号/邮箱合并为"验证码登录"Tab，通过下拉选择验证码类型
   **裁决/建议：** 合并为"验证码登录"Tab，输入框上方增加切换（手机号/邮箱），减少 Tab 数量
   **决策依据：** 保持登录页简洁，降低用户认知负担

2. **议题：邮箱注册是否强制设置密码**
   **各方立场：**
   - PM：邮箱自动注册后应引导用户设置密码，否则只能邮箱登录
   - Designer：首次登录后弹出设置密码引导，可跳过
   - Engineer：允许无密码（password_hash 为空），仅通过邮箱验证码登录
   **裁决/建议：** 允许无密码用户存在，首次邮箱登录后展示非强制的设置密码引导
   **决策依据：** 降低注册门槛，与微信注册（password 为空字符串）保持一致

---

## 被低估的优势

1. **邮件发送基础设施已完备**：EmailService + 邮件模板系统 + 通知日志已存在，邮箱认证可直接复用，不需要从零搭建邮件发送能力
2. **验证码模式可复用**：SMS 验证码的 Redis 存储、频率限制、防重放机制已成熟，邮箱验证码只需更换发送渠道和 key 前缀
3. **多租户隔离模式已建立**：tenant_id 维度的隔离贯穿整个认证体系，邮箱认证可直接继承

---

## 行动计划（按 ROI 排序）

| 优先级 | 行动 | 成本 | 价值 | 负责 | 状态 |
|--------|------|------|------|------|------|
| P0 | Account 主表新增 email 字段 + 迁移脚本 | 4h | 高 | Engineer | 待开始 |
| P0 | Redis 邮箱验证码方法组 | 2h | 高 | Engineer | 待开始 |
| P0 | 验证码安全性升级（secrets） | 0.5h | 高 | Engineer | 待开始 |
| P0 | EmailService 新增验证码发送方法 | 3h | 高 | Engineer | 待开始 |
| P1 | 邮箱认证 API 端点（send-code/login/register） | 8h | 高 | Engineer | 待开始 |
| P1 | 邮箱绑定/解绑/换绑 API | 6h | 高 | Engineer | 待开始 |
| P1 | 用户类型适用范围控制 | 2h | 高 | Engineer | 待开始 |
| P1 | patient-h5 端邮箱登录 UI | 6h | 高 | Designer | 待开始 |
| P1 | admin 端登录页合并验证码 Tab | 4h | 中 | Designer | 待开始 |
| P1 | admin 端个人设置页邮箱绑定/换绑 UI | 4h | 中 | Designer | 待开始 |
| P1 | patient-h5 端邮箱绑定/换绑 UI（个人中心） | 4h | 中 | Designer | 待开始 |
| P1 | packages/api 新增邮箱认证 API 封装 | 3h | 中 | Engineer | 待开始 |
| P1 | 前端 API 类型定义（TypeScript） | 2h | 中 | Engineer | 待开始 |
| P2 | admin 端邮箱登录 Tab UI | 3h | 中 | Designer | 待开始 |
| P2 | doctor 端邮箱绑定 UI | 3h | 低 | Designer | 待开始 |
| P2 | 邮箱验证码邮件模板设计（HTML） | 2h | 中 | Designer | 待开始 |
| P2 | 统一异步/同步邮件发送配置键 | 2h | 中 | Engineer | 待开始 |
| P2 | 现有 admin 邮箱数据清洗脚本 | 2h | 中 | Engineer | 待开始 |
| P2 | 单元测试（验证码、登录、注册、绑定） | 8h | 高 | Engineer | 待开始 |
| 待定 | 小程序端邮箱登录支持 | 4h | 低 | 待确认 | 需用户确认 |
| 待定 | 邮箱登录的"忘记密码"流程（邮箱重置密码） | 4h | 中 | 待确认 | 需用户确认 |

### P0：立即执行（高价值、低成本）

1. **Account 主表新增 email 字段 + Alembic 迁移**（4h）
   - accounts 表新增 `email = Column(String(100), nullable=True, index=True)`
   - 新增 `UniqueConstraint("tenant_id", "email", name="uq_accounts_tenant_email")`
   - 迁移脚本：从 account_admins 表迁移现有 email 数据
   - 处理重复邮箱冲突（保留最新注册，标记冲突记录）
   - 负责：Engineer

2. **Redis 邮箱验证码方法组**（2h）
   - core/redis.py 新增 `PREFIX_EMAIL = "email:"`
   - 新增方法：`set_email_code`、`get_email_code`、`verify_email_code`、`check_email_rate_limit`
   - key 格式：`email:{tenant_id}:{email}:{code_type}`
   - 复用 SMS 的 JSON 存储结构和 verified 标记逻辑
   - 负责：Engineer

3. **验证码安全性升级**（0.5h）
   - sms/service.py 的 `generate_code` 函数：`random.choices` → `secrets.choice`
   - 同时应用于 SMS 和 email 验证码（共用同一个生成函数）
   - 负责：Engineer

4. **EmailService 新增验证码发送方法**（3h）
   - 新增 `send_verification_code_email(to_email, code, code_type)` 方法
   - 使用 aiosmtplib 异步发送
   - 新增邮件验证码 HTML 模板（6 位验证码、5 分钟有效期、安全提示）
   - 负责：Engineer

### P1：本轮迭代（高价值、中等成本）

5. **邮箱认证 API 端点**（8h）
   - `POST /auth/email/send-code`：发送邮箱验证码（支持 login/register/reset 类型）
   - `POST /auth/email/login`：邮箱验证码登录（支持自动注册，仅患者类型）
   - `POST /auth/email/register`：邮箱注册（可选，与 login 合并更简洁）
   - Schema：`EmailSendCodeRequest(email, code_type)`、`EmailLoginRequest(email, code)`
   - 负责：Engineer

6. **邮箱绑定/解绑/换绑 API**（6h）
   - `POST /auth/email/bind`：绑定邮箱（需登录 + 验证码确认）
   - `POST /auth/email/unbind`：解绑邮箱（需登录 + 验证码确认）
   - `POST /auth/email/change`：换绑邮箱（需登录 + 旧邮箱验证码 + 新邮箱验证码）
   - 绑定前校验 email 唯一性
   - 负责：Engineer

7. **用户类型适用范围控制**（2h）
   - 邮箱登录逻辑中：查到 AccountUser 类型 → 支持自动注册；查到 AccountAdmin/AccountDoctor → 必须已绑定邮箱才能登录
   - 邮箱绑定逻辑中：所有类型均可绑定
   - 负责：Engineer

8. **前端 UI 实现**（17h）
   - patient-h5 登录页新增邮箱登录入口（6h）
   - admin 端登录页合并手机号/邮箱为"验证码登录"Tab（4h）
   - admin 端个人设置页邮箱绑定/换绑交互（4h）
   - patient-h5 端个人中心新增邮箱绑定入口（3h）
   - 负责：Designer（前端开发）

9. **API 封装和类型定义**（5h）
   - packages/api 新增 `email-auth.ts` 模块
   - TypeScript 类型定义
   - 负责：Engineer

### P2：下个周期规划（中等价值、较高成本）

10. **doctor 端邮箱绑定 UI**（3h）
11. **邮箱验证码邮件模板美化**（2h）
12. **统一异步/同步邮件发送配置键**（2h）— 修复 email_hook_task 与 service_views 的配置键命名不一致
13. **现有 admin 邮箱数据清洗**（2h）
14. **单元测试**（8h）— 覆盖验证码生成/校验、邮箱登录、自动注册、绑定/解绑/换绑

### 待定：需用户确认

1. **小程序端邮箱登录支持**（4h）— 当前小程序仅支持微信登录，是否需要新增邮箱入口？
2. **邮箱重置密码流程**（4h）— 当前仅支持手机号重置密码，是否需要新增邮箱重置密码？

---

## 摘要

**使用模式：** 集中调度

**关键共识：**
- 7 项达成共识（email 字段归属、Redis 方案、发送服务、API 端点、绑定管理、用户类型控制、安全性升级）

**关键分歧：**
- 2 项需要权衡（admin 登录页 Tab 设计、邮箱注册密码策略），已裁决

**Top 3 P0 行动：**
1. Account 主表新增 email 字段 + Alembic 迁移（4h）
2. Redis 邮箱验证码方法组 + 安全性升级（2.5h）
3. EmailService 验证码发送方法 + 邮件模板（3h）

**Critic 关键洞察：**
- Account 主表 schema 变更是所有后续工作的前置依赖，必须首先解决
- 用户类型适用范围必须明确定义，否则自动注册逻辑可能产生安全漏洞
- Redis 验证码存储需要独立实现而非泛化，避免破坏现有 SMS 接口契约

---

## 附录：模式切换日志

| 时间 | 从 | 到 | 原因 |
|------|-----|-----|------|
| 无切换 | | | |
