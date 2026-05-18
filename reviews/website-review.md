# appointment-booking-system 官方网站 — 自适应多智能体研究画布

> 协作模式：集中调度
> 日期：2026-05-17
> 审查目标：实现官方营销网站（apps/website/），包含首页、产品、体验、定价、控制台、个人中心、注册登录

---

## 模式选择

**选定模式：** 集中调度

**选择理由：** 三个维度（设计/工程/产品）相对均衡，设计系统已前置降低领域主导必要性，集中调度收敛最快且输出完整度最高。

---

## Round 1：事实层（只写事实，不评价）

### PM — 产品视角

**产品定位：**
- 全栈医院预约挂号系统，SaaS 多租户架构，支持多门店/分院、多科室、多医生排班预约（CLAUDE.md:14）
- 一套完整的医院挂号系统解决方案，包含机构端、患者端（H5 + 小程序）、医生端三个平台（README.md:1）
- 技术栈：pnpm 10 + Turbo 2 / React 18/19 + TypeScript / FastAPI + SQLAlchemy / PostgreSQL 16 / Redis 7（CLAUDE.md:18-28）

**功能完成度：**
- 认证系统已完整实现：手机号+密码、手机号+短信验证码、微信 OAuth、邮箱验证码（auth/router.py:112-975）
- 订阅计划 CRUD 已实现，模型含 16 字段：plan_code/name/description/price_monthly/price_yearly/max_stores/max_admins/max_doctors/max_appointments_per_month/max_storage_mb/features/status/sort_order/is_default（models/tenant.py:16-46）
- 租户自助注册已实现：POST /tenants/register，创建试用租户（14天）+ 管理员账号（tenants/router.py:40-53）
- 功能开关系统已实现：14 个布尔开关（basic_appointment, wechat_integration, sso, online_payment 等）（tenants/schemas.py:41-76）
- 前端 API 封装已存在：packages/api/src/modules/auth.ts 和 tenant.ts

**定价系统现状：**
- GET /tenants/plans 需要 admin 认证（get_current_admin），无公开端点（tenants/router.py:368-371）
- 需要新增公开端点或前端使用静态数据展示定价
- SubscriptionPlanListResponse 返回：id, plan_code, name, price_monthly, price_yearly, max_stores, max_admins, max_doctors, max_appointments_per_month, status, is_default, sort_order（schemas.py:181-201）

**目标用户线索：**
- 官网面向机构管理者（租户管理员），非普通患者
- 租户注册需 6 个必填字段：tenant_code, name, contact_name, contact_phone, admin_username, admin_password（schemas.py:637-665）
- 多租户隔离：X-Tenant-ID/Code Header、子域名、路径前缀，ContextVar 异步隔离（middleware/tenant_context.py:1-17）

### Designer — 用户视角

**页面清单与结构：**
- apps/website/ 目录当前不存在，需从零创建
- patient-h5 已有完整的 Minimalist Modern 设计系统实现（tailwind.config.js + theme.css + global.css + 8 个 UI 组件）

**现有设计系统资产（patient-h5）：**
- 颜色系统：background #FAFAFA, foreground #0F172A, accent #0052FF, accent-secondary #4D7CFF（tailwind.config.js:6-17）
- 字体：Calistoga（display）、Inter（sans）、JetBrains Mono（mono）（tailwind.config.js:18-22）
- 阴影系统：sm/md/lg/xl/accent/accent-lg 六级（tailwind.config.js:23-30）
- 动画：pulse-dot 2s、float 5s、float-delayed 4s、rotate-slow 60s（tailwind.config.js:31-50）
- Google Fonts 加载：Calistoga、Inter 400-700、JetBrains Mono 400-500（global.css:2）
- 无障碍：prefers-reduced-motion 降级、sr-only 工具类（global.css:19-61）
- 点状纹理：bg-dot-pattern 32px 间距 3% 透明度（global.css:10-16）

**可复用 UI 组件（patient-h5/src/components/ui/）：**
- Button：4 variant（primary/secondary/ghost/outline），3 size，framer-motion 动画，loading 态
- Card：4 variant（default/elevated/gradient-border/flat），hoverable，fadeInUp 动画
- Input：2 variant，label/error/hint，leftIcon/rightIcon
- SectionLabel：圆角药丸徽章 + 脉冲圆点指示器
- GradientText/GradientHeading：Electric Blue 渐变文字，可选下划线
- InvertedSection：深色背景区域，点状纹理，径向光晕
- RadialGlow：装饰性径向渐变光晕
- animations.ts：20+ 预定义动画配置（fadeInUp/stagger/float/pulse/rotate 等）

**响应式设计事实：**
- patient-h5 无 @media 断点定义，依赖 Tailwind 响应式前缀（text-3xl md:text-4xl lg:text-5xl）
- 触摸目标最小 44px（theme.css:41-56）
- iOS safe-area-inset-bottom 处理（MainLayout/index.tsx:93）

**组件一致性事实：**
- admin-v2 使用 shadcn/ui 风格（radix-ui + cva），与 patient-h5 的自定义组件风格不同
- 共享包 packages/shared 仅导出 RegionSelector，无通用 UI 组件

### Engineer — 技术视角

**Monorepo 配置事实：**
- pnpm-workspace.yaml：`apps/*` 和 `packages/*`（第1-2行），新 website 自动被包含
- turbo.json：dev 任务 cache:false persistent:true，build 依赖 ^build（第1-39行）
- 根 package.json 已有 dev:admin-v2/build:admin-v2 模式可参考（第1-63行）
- 包命名约定：@hospital/admin-v2（新 website 应为 @hospital/website）

**admin-v2 技术栈详情（参考模板）：**
- React 19 + Vite 6 + Tailwind CSS 4（@tailwindcss/vite 插件）
- react-router-dom 7、@tanstack/react-query 5、zustand 5、zod、react-hook-form
- lucide-react 图标、sonner toast、next-themes 主题
- vite.config.ts：react() + tailwindcss() 插件，@ 路径别名，/api 代理到 localhost:9000（第1-28行）
- tsconfig.json：ES2020、bundler moduleResolution、strict true（第1-33行）
- App.tsx Provider 层级：QueryClientProvider -> ThemeProvider -> ThemePresetProvider -> RouterProvider

**后端 API 接口事实：**
- 公开端点：POST /auth/login, /auth/register, /auth/send-code, /auth/refresh, /auth/forgot-password
- 公开端点：POST /auth/email/send-code, /auth/email/login
- 公开端点：POST /tenants/register（租户自助注册）
- 需认证端点：GET /tenants/plans（需要 get_current_admin）
- 无公开的计划列表 API

**API 请求封装事实：**
- @hospital/api 基于 Axios，统一前缀 /api/v1（config.ts:1-43）
- 认证门控：失效后短路非白名单请求（request.ts:82-110）
- 自动重试：GET 请求最多 3 次指数退避（request.ts:82-110）
- 响应解析：code+data 格式自动提取 data 字段（request.ts:113-181）
- admin-v2 端拦截器：自动添加 Authorization + X-Tenant-ID header（interceptors.ts:1-209）
- tenantApi 无 registerTenant 方法封装

**安全机制事实：**
- JWT HS256，Access Token 30 分钟，Refresh Token 7 天（security.py:173-201）
- RSA 2048-bit 密码加密传输（security.py:25-157）
- bcrypt 密码哈希（security.py:159-171）
- CORS 默认允许 localhost:8002/8003/8005，新 website 端口需添加（config.py:91-94）
- 全局限流 300次/分钟、50次/秒（config.py:97-99）

---

## Round 2：辩论层

### 交叉评论投票矩阵（简化版 — 集中调度模式）

| 议题 | 裁决者立场 | Critic 质询 | 最终裁决 |
|------|-----------|------------|---------|
| 组件复用范围 | 复用设计 token，不复用组件 | 质询 1：组件为移动端设计，桌面营销网站无法直接复用 | **采纳 Critic**。复用颜色/字体/阴影/动画配置 token，组件需重新构建为桌面优先 |
| 定价页数据源 | 静态数据 | 质询 2：PM 回避决策，应明确选静态数据 | **采纳 Critic**。定价变更频率低（季度级），静态数据零成本零风险 |
| 注册安全 | 需要增强 | 质询 3（🚨关键）：公开端点无 CAPTCHA | **采纳**。前端加 hCaptcha/reCAPTCHA，后端加注册专用限流 |
| 控制台/个人中心定义 | 重定向到 admin-v2 | 质询 4：未定义这两个页面的本质 | **裁决**。"控制台"重定向到 admin-v2，"个人中心"为租户 profile 设置页（website 内） |
| SEO 策略 | 需要 SSG | 质询 5（🚨关键）：纯 SPA 无法被搜索引擎抓取 | **采纳**。使用 vite-ssg 或 react-snap 做预渲染，非全量 SSR |
| 品牌一致性 | website 与 admin-v2 可以不同 | 质询 6：三套 UI 体系伤害品牌 | **部分采纳**。website 是对外品牌展示，admin-v2 是内部工具，视觉语言可以不同。但核心品牌色（#0052FF）必须一致 |
| CORS 端口 | 分配 9102 | 质询 7：端口分配未指定 | **裁决**。website 开发端口设为 9102，需添加到 CORS 配置 |

### 独到发现

1. **设计系统复用的正确粒度是 token 而非组件** — patient-h5 的 UI 组件依赖 framer-motion 且为移动端设计，但其 Tailwind 配置（颜色、字体、阴影、动画关键帧）、CSS 变量、Google Fonts 加载方式、无障碍降级策略可以直接移植到 website
2. **定价页是 website 中唯一需要后端数据的公开页面，但静态数据方案消除了这个依赖** — 这意味着 website 的首页/产品/体验/定价页面可以完全静态部署，只有注册/登录/控制台需要后端连接
3. **website 的技术栈选择实际上是一个 SEO 决策而非工程偏好** — 如果选纯 Vite SPA，SEO 归零；如果选 vite-ssg 预渲染，增加约 2h 配置成本但获得完整 SEO

### Critic 质询

[Critic → 全体] 质询 1：patient-h5 设计系统"可直接复用"的结论是否经得起推敲？
- 论据：6 个 UI 组件全部依赖 framer-motion，为移动端设计，营销网站是桌面优先落地页
- 要求回应：Designer
- 级别：普通
- **Team Lead 回应：采纳。组件需重新构建，但设计 token（颜色/字体/阴影/动画配置）可直接复用**

[Critic → 全体] 质询 2：定价页方案被表面化处理
- 论据：定价变更频率低，静态数据零成本零风险，新建 API 成本高一个数量级
- 要求回应：PM + Engineer
- 级别：普通
- **Team Lead 回应：采纳。明确选择静态数据方案**

[Critic → 全体] 质询 3：注册流程存在安全隐患
- 论据：POST /tenants/register 无 CAPTCHA、无频率限制，全局限流 300/min 不足以防护
- 要求回应：Engineer + PM
- 级别：🚨 关键
- **Team Lead 回应：采纳。前端集成 hCaptcha，后端增加注册专用限流（10次/分钟/IP）**

[Critic → 全体] 质询 4："控制台"和"个人中心"页面的本质未被澄清
- 论据：未定义是重定向还是独立页面，影响技术方案和工作量
- 要求回应：PM
- 级别：普通
- **Team Lead 回应：裁决。控制台 = 重定向到 admin-v2，个人中心 = website 内的租户 profile 页**

[Critic → 全体] 质询 5：三方都忽略了 SEO 策略
- 论据：Vite SPA 无法被搜索引擎抓取，营销网站 SEO 是核心价值
- 要求回应：Engineer + PM
- 级别：🚨 关键
- **Team Lead 回应：采纳。使用 vite-ssg 预渲染关键页面（首页/产品/定价），动态页面（登录/控制台）保持 SPA**

[Critic → 全体] 质询 6：品牌一致性问题被系统性回避
- 论据：项目已有两套 UI 体系，新增第三套伤害品牌可信度
- 要求回应：Designer + PM
- 级别：普通
- **Team Lead 回应：部分采纳。website 是对外品牌展示，admin-v2 是内部工具，可以不同风格，但核心品牌色 #0052FF 必须一致**

[Critic → 全体] 质询 7：CORS 端口分配是阻塞性细节
- 论据：端口未指定，开发启动后会浪费排查时间
- 要求回应：Engineer
- 级别：普通
- **Team Lead 回应：采纳。website 端口设为 9102**

### 🚨 Critic 关键质询追踪

| # | 关键质询内容 | 三方回应摘要 | 回应是否充分 | 处置 |
|---|------------|------------|------------|------|
| 1 | 注册流程安全隐患：无 CAPTCHA、无专用限流 | Team Lead 裁决：前端 hCaptcha + 后端注册专用限流 10/min/IP | 是 | 纳入计划 |
| 2 | SEO 策略缺失：纯 SPA 无法被搜索引擎抓取 | Team Lead 裁决：vite-ssg 预渲染关键页面 | 是 | 纳入计划 |

---

## Round 3：共识层

### ✅ 共识项

1. **议题：技术栈选型**
   **结论：** React 19 + Vite 6 + Tailwind CSS 4（与 admin-v2 对齐），加 vite-ssg 预渲染
   **建议行动：** 以 admin-v2 的 vite.config.ts、tsconfig.json、App.tsx 为模板创建 website 脚手架
   **成本估算：** 4h（脚手架 + monorepo 集成 + CORS 配置 + turbo scripts）
   **优先级：** P0

2. **议题：设计系统移植**
   **结论：** 从 patient-h5 移植设计 token（颜色/字体/阴影/动画），重新构建桌面优先组件
   **建议行动：** 复制 tailwind.config.js 颜色/字体/阴影配置 + global.css 字体加载和无障碍样式 + animations.ts 动画配置，新建 Button/Card/Input/SectionLabel/GradientText 等桌面版组件
   **成本估算：** 8h（token 移植 2h + 6 个基础组件 6h）
   **优先级：** P0

3. **议题：定价页数据源**
   **结论：** 使用前端静态数据，不依赖后端 API
   **建议行动：** 在 website/src/data/pricing.ts 中定义计划数据，与 SubscriptionPlan 模型字段对齐
   **成本估算：** 1h
   **优先级：** P0

4. **议题：注册安全增强**
   **结论：** 前端集成 hCaptcha，后端增加注册专用限流
   **建议行动：** website 注册页面集成 hCaptcha；后端 tenants/register 端点增加 IP 级限流 10次/分钟
   **成本估算：** 4h（前端 hCaptcha 2h + 后端限流 2h）
   **优先级：** P0

5. **议题：控制台/个人中心定义**
   **结论：** 控制台 = 外部链接重定向到 admin-v2；个人中心 = website 内的租户 profile 设置页
   **建议行动：** 控制台路由做 302 重定向；个人中心实现基本信息展示和修改
   **成本估算：** 3h（重定向 0.5h + 个人中心页面 2.5h）
   **优先级：** P1

6. **议题：SEO 策略**
   **结论：** 使用 vite-ssg 预渲染首页、产品、定价等静态页面；登录/控制台保持 SPA
   **建议行动：** 安装 vite-ssg，配置预渲染路由列表，添加 meta tags 和 Open Graph
   **成本估算：** 3h（vite-ssg 配置 1h + meta/OG 标签 1h + sitemap 1h）
   **优先级：** P0

### ⚡ 分歧项

1. **议题：品牌一致性 — website 与 admin-v2 是否应保持视觉统一**
   **各方立场：**
   - PM：website 是品牌展示，admin-v2 是内部工具，定位不同可以风格不同
   - Designer：用户提供的设计系统明确要求 Minimalist Modern 风格，与 shadcn/ui 不同
   - Engineer：统一视觉需要额外工作量，且 admin-v2 已有成熟的 shadcn/ui 体系
   **裁决：** website 使用用户指定的 Minimalist Modern 设计系统，与 admin-v2 保持核心品牌色 #0052FF 一致即可。两者定位不同（对外营销 vs 内部管理），视觉语言可以不同
   **决策依据：** 用户已明确提供了设计系统规范，应尊重用户意图

---

## 被低估的优势

1. **patient-h5 的 animations.ts 是一个完整的动画库** — 20+ 预定义动画配置（fadeInUp/stagger/float/pulse/rotate/buttonHover/cardHover 等），可以直接移植到 website，省去动画设计和调试时间
2. **项目已有完整的认证和租户 API** — auth 模块支持手机号/邮箱/微信三种认证方式，tenant 模块支持自助注册，website 只需前端对接，无需后端开发（除注册限流外）
3. **monorepo 基础设施成熟** — pnpm workspace + Turbo 已配置好，新 app 自动被包含，dev/build scripts 模式已确立

---

## 行动计划（按 ROI 排序）

| 优先级 | 行动 | 成本 | 价值 | 负责 | 状态 |
|--------|------|------|------|------|------|
| P0 | 创建 website 脚手架（React 19 + Vite 6 + Tailwind 4 + vite-ssg） | 4h | 高 | Engineer | 待执行 |
| P0 | 移植设计 token 并构建 6 个桌面优先基础组件 | 8h | 高 | Designer + Engineer | 待执行 |
| P0 | 实现首页（Hero + Features + Stats + CTA） | 6h | 高 | Designer + Engineer | 待执行 |
| P0 | 实现定价页（静态数据 + 对比表格 + 渐变高亮） | 3h | 高 | PM + Engineer | 待执行 |
| P0 | 实现注册/登录页面（对接 auth API + hCaptcha） | 6h | 高 | Engineer | 待执行 |
| P0 | 后端注册限流增强（IP 级 10次/分钟） | 2h | 高 | Engineer | 待执行 |
| P0 | SEO 配置（vite-ssg + meta tags + OG + sitemap） | 3h | 高 | Engineer | 待执行 |
| P1 | 实现产品介绍页 | 4h | 中 | PM + Designer | 待执行 |
| P1 | 实现体验/Demo 页 | 4h | 中 | PM + Designer | 待执行 |
| P1 | 实现个人中心页面（租户 profile） | 3h | 中 | Engineer | 待执行 |
| P1 | 控制台重定向到 admin-v2 | 0.5h | 中 | Engineer | 待执行 |
| P1 | CORS 配置添加 website 端口 9102 | 0.5h | 中 | Engineer | 待执行 |
| P1 | 根 package.json 添加 dev:website / build:website scripts | 0.5h | 中 | Engineer | 待执行 |
| P2 | 暗色模式支持 | 4h | 低 | Designer | 待执行 |
| P2 | 多语言支持 | 8h | 低 | PM + Engineer | 待执行 |

### P0：立即执行（高价值、低成本）

1. **脚手架搭建** — 以 admin-v2 为模板，创建 apps/website/ 目录，配置 Vite + Tailwind 4 + vite-ssg + react-router-dom，添加 monorepo 集成（4h, Engineer）
2. **设计系统移植** — 从 patient-h5 移植颜色/字体/阴影/动画 token 到 website 的 tailwind.config.js 和 global.css，新建 6 个桌面优先组件（8h, Designer + Engineer）
3. **首页实现** — 按设计系统的 Hero（渐变文字 + 浮动动画）、Features（卡片网格 + 图标）、Stats（反转深色区域）、CTA（渐变按钮）四段式结构（6h, Designer + Engineer）
4. **定价页实现** — 静态数据 + 响应式对比表格 + 推荐计划渐变边框高亮 + 月/年付切换（3h, PM + Engineer）
5. **注册/登录页实现** — 对接 POST /tenants/register 和 POST /auth/login，集成 hCaptcha 防机器人（6h, Engineer）
6. **后端注册限流** — 在 tenants/register 端点增加 IP 级限流装饰器，10次/分钟（2h, Engineer）
7. **SEO 配置** — vite-ssg 预渲染 + 每页 meta/title/OG 标签 + sitemap.xml 生成（3h, Engineer）

### P1：本轮迭代（高价值、中等成本）

1. **产品介绍页** — 系统功能模块展示（多门店、排班、预约、统计等），使用 SectionLabel + Card 网格布局（4h, PM + Designer）
2. **体验/Demo 页** — 交互式功能演示或截图展示，使用 InvertedSection + 动画组合（4h, PM + Designer）
3. **个人中心页面** — 登录后展示租户基本信息、订阅状态、使用量统计，对接 GET /tenants/me（3h, Engineer）
4. **控制台重定向** — 登录后"进入控制台"按钮跳转 admin-v2（0.5h, Engineer）
5. **基础设施** — CORS 端口 9102 + 根 scripts（1h, Engineer）

### P2：下个周期规划（中等价值、较高成本）

1. 暗色模式支持（4h, Designer）
2. 多语言支持（8h, PM + Engineer）

### 待定：需用户确认

1. **网站域名和部署策略** — 是否使用独立域名？部署到 GCP 还是 Vercel/Netlify（SSG 更友好）？
2. **控制台重定向目标** — admin-v2 的线上地址是什么？是否需要根据环境动态切换？
3. **定价计划的实际数据** — 需要用户提供 basic/pro/enterprise 的具体价格和功能对比内容

---

## 摘要

**使用模式：** 集中调度

**关键共识：** 6 项达成共识
- 技术栈：React 19 + Vite 6 + Tailwind 4 + vite-ssg
- 设计系统：从 patient-h5 移植 token，重新构建桌面组件
- 定价页：静态数据方案
- 注册安全：hCaptcha + 专用限流
- 控制台/个人中心：重定向 vs 内部页面
- SEO：vite-ssg 预渲染

**关键分歧：** 1 项需决策者介入
- 品牌一致性：website 与 admin-v2 视觉语言是否统一 → 已裁决：可以不同，核心品牌色一致即可

**Top 3 P0 行动：**
1. 脚手架搭建 + monorepo 集成（4h, Engineer）
2. 设计系统移植 + 6 个基础组件（8h, Designer + Engineer）
3. 首页实现（6h, Designer + Engineer）

**Critic 关键洞察：**
- 注册安全是被三方遗漏的重大风险（公开端点无 CAPTCHA）
- SEO 策略是架构级决策，纯 SPA 对营销网站不可接受
- 组件复用的正确粒度是 token 而非组件本身
