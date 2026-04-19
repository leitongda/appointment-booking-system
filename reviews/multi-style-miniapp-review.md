# 多风格小程序模板生成 — 自适应多智能体研究画布

> 协作模式：集中调度
> 日期：2026-04-18
> 审查目标：将 5 套模板细化到页面级定义，拆出分阶段可开发任务清单

---

## 模式选择

**选定模式：** 集中调度

**选择理由：** 目标是产出页面级设计文档和任务清单，需要三视角事实支撑但最终由 Team Lead 综合裁决产出，集中调度最快收敛。

---

## Round 1：事实层

### PM — 产品视角

**现有页面清单（24个页面）：**

主包 5 个：首页、预约列表、个人中心、科室列表、医生列表

分包 packageBooking 6 个：医生详情、预约确认、预约结果、预约详情、扫码签到、选择预约签到

分包 packageProfile 9 个：个人信息编辑、就诊人列表、就诊人编辑、我的收藏、就诊记录列表、就诊记录详情、消息中心、意见反馈、反馈历史、设置

分包 packageOther 4 个：搜索、关于我们、网页容器、协议页面

**导航结构：**
- 自定义 TabBar（3栏）：首页 / 预约 / 我的
- 主题色动态切换，未选中灰色 #9CA3AF

**首页模块（从上到下）：**
1. Banner 轮播（营销）
2. 功能菜单 4 宫格（预约挂号、预约记录、扫码签到、我的客服）
3. 就诊卡快捷入口
4. 推荐医生列表

**个人中心结构：**
- 顶部：头像 + 昵称 + 手机号 + 统计卡片（预约/就诊人/消息）
- 业务组：就诊人管理、我的收藏、就诊记录、消息通知
- 服务组：意见反馈、联系我们、关于我们、用户协议、隐私政策、退出登录

**预约完整链路：**
首页 → 科室列表 → 医生列表 → 医生详情 → 预约确认 → 预约结果

**现有模板/主题：**
- 仅 4 套颜色主题（red/yellow/blue/green），无页面级模板
- 环境变量已预留：TARO_APP_TEMPLATE_CODE、TARO_APP_TEMPLATE_VERSION、TARO_APP_MINIAPP_INSTANCE_ID

### Designer — 设计视角

**UI 组件库：** NutUI React Taro 3.0.18

**自定义组件（3个）：** Icons（45+ SVG 图标）、PageContainer（页面容器+字体模式）、LoginPopup（登录弹窗）

**设计 Token 系统：**
- 4 套颜色主题（blue/red/yellow/green），CSS 变量动态切换
- 完整变量体系：颜色（功能色/背景/文字/边框）、字号（26~60rpx，9级）、间距（8rpx 基础）、圆角（6级）、阴影、动画、层级
- 长辈模式：字体+20%，通过 .font-mode-elder 类激活

**卡片样式：**
- 医生卡片：头像+姓名职称+科室+擅长+有号标签
- 科室卡片：图标+名称+箭头
- 预约卡片：单号+状态+医生时间+操作按钮（7种状态色）

**文案风格：** "您"/"就诊人"称呼，中文硬编码，无 i18n

**无障碍：** 无 aria-* 属性，触摸目标尺寸符合标准，支持长辈模式

### Engineer — 技术视角

**技术栈：** Taro 4.1.9 + React 18.2.0 + TypeScript 5.3.3 + Webpack 5

**状态管理：** 无全局状态库，使用 Hooks + Taro.Storage + eventCenter

**组件架构：**
- 无业务容器/展示组件分离模式
- 共享逻辑通过 hooks（useProtectedPage、useTenantGuard）和 utils（auth、theme、navigate、payment）抽取
- 页面标准结构：函数组件 + useDidShow + PageContainer 包装

**后端实例化支持：**
- miniapp_platform 模块已建立：AppTemplate、TemplateVersion、MiniappInstance、BuildJob、ReleaseJob
- MiniappInstance 已关联 template_id、template_version_id
- 构建时环境变量注入机制已就绪

**构建配置：**
- 支持 defineConstants 注入环境变量
- 后处理脚本 fix-wxml.js 修复 Taro 编译问题
- 无 CI/CD 配置

**代码规模：** ~10,166 行 TS/TSX，31 个页面组件

---

## Round 2：辩论层

### 交叉评论投票矩阵（集中调度简化版）

| 议题 | 裁决者立场 | Critic 质询 | 最终裁决 |
|------|-----------|------------|---------|
| 页面壳层拆分边界 | 见下方详述 | | |
| 5 套模板差异化深度 | | | |
| 前端架构改造策略 | | | |
| 分阶段实施顺序 | | | |

### Critic 质询

1. [Critic → Designer+PM] 🚨 关键质询 1：模板差异化深度不足
   - 论据：TabBar 硬编码、首页模块顺序固定、长辈模式仅字体+20%
   - 要求回应：如何不重写 30+ 页面实现真正的体验差异
   - 级别：🚨 关键

2. [Critic → Engineer] 🚨 关键质询 2：架构改造成本被低估
   - 论据：31 个页面无展示组件层、状态管理碎片化、构建时 vs 运行时矛盾
   - 要求回应：壳层拆分方案和成本估算
   - 级别：🚨 关键

3. [Critic → Engineer+PM] 🚨 关键质询 3：后端能力与前端需求脱节
   - 论据：环境变量预留但未使用、配置下发机制缺失、版本管理形同虚设
   - 要求回应：配置 JSON Schema 设计和下发机制
   - 级别：🚨 关键

---

## Round 3：共识层

### Critic 关键质询回应

| # | 质询 | 回应 | 处置 |
|---|------|------|------|
| 1 | 差异化深度不足 | 裁决：模板差异通过 3 层实现 — (1) TabBar 动态配置 (2) 首页模块配置驱动 (3) 页面壳层组件替换。不需要重写业务逻辑，只需抽壳层。长辈模板不仅改字体，还改布局（超大按钮、简化模块、大卡片） | 纳入 Phase 0 + Phase 1 |
| 2 | 架构改造成本被低估 | 裁决：采用渐进式拆分 — Phase 0 建壳层规范 + hooks 抽取业务逻辑，Phase 1 先做 2 套模板验证，确认可行后再扩展。构建时注入模板配置，运行时不需要动态切换。 | 纳入 Phase 0 |
| 3 | 后端能力未使用 | 裁决：第一阶段前端用静态配置文件（不依赖后端），Phase 3 再接入后端 API。JSON Schema 已在模板定义文档中设计完成。 | Phase 3 接入 |

### ✅ 共识项

1. **模板差异化通过壳层替换而非重写实现** — 6 个可替换页面 × 5 种壳层变体
2. **首页模块必须配置驱动** — 支持 5 种完全不同的首页编排
3. **TabBar 必须动态配置** — 支持 3/4 栏切换
4. **交易链路页面固定不变** — 预约确认/支付/签到不可模板化
5. **第一阶段前端不依赖后端模板 API** — 使用静态配置文件
6. **5 阶段实施：基建→双模板验证→补齐→集成→打磨**

---

## 行动计划

完整实施计划见 `docs/templates/implementation-plan.md`

| 优先级 | 行动 | 成本 | 负责 | 阶段 |
|--------|------|------|------|------|
| P0 | 模板类型定义 + 加载机制 | 16h | Engineer | Phase 0 |
| P0 | 动态 TabBar + 首页模块渲染器 | 16h | Engineer+Designer | Phase 0 |
| P0 | 页面壳层规范 + hooks 抽取 | 8h | Engineer | Phase 0 |
| P1 | 现代综合医疗模板（基准验证） | 20h | Designer+Engineer | Phase 1 |
| P1 | 长辈友好/中医康养模板（强差异验证） | 28h | Designer+Engineer | Phase 1 |
| P1 | 高端专科门诊模板 | 28h | Designer+Engineer | Phase 2 |
| P1 | 亲子儿科模板 | 28h | Designer+Engineer | Phase 2 |
| P1 | 女性健康模板 | 24h | Designer+Engineer | Phase 2 |
| P2 | 后端模板管理 API + 管理后台 | 20h | 后端+前端 | Phase 3 |
| P2 | 构建流程模板注入 + 发布追踪 | 20h | Engineer | Phase 3 |
| P2 | 无障碍增强 + 性能优化 + 全面测试 | 30h | 全员 | Phase 4 |

---

## 摘要

**使用模式：** 集中调度

**关键共识：** 6 项达成共识

**Top 3 P0 行动：**
1. 模板类型定义 + 加载机制（16h）— 建立模板化基础设施
2. 动态 TabBar + 首页模块渲染器（16h）— 解锁模板差异化核心
3. 页面壳层规范 + hooks 抽取（8h）— 建立业务/展示分离规范

**Critic 关键洞察：** 当前代码架构（31 个页面无分离、TabBar 硬编码、首页模块固定）距离"多风格"目标差距大，但通过渐进式改造（先基建、后验证、再扩展）可控风险。

**产出物：**
- `docs/templates/template-modern-general.md` — 现代综合医疗页面级定义
- `docs/templates/template-premium-specialty.md` — 高端专科门诊页面级定义
- `docs/templates/template-family-pediatrics.md` — 亲子儿科页面级定义
- `docs/templates/template-womens-health.md` — 女性健康页面级定义
- `docs/templates/template-elderly-tcm.md` — 长辈友好/中医康养页面级定义
- `docs/templates/template-comparison-matrix.md` — 跨模板对比矩阵
- `docs/templates/implementation-plan.md` — 5 阶段实施计划 + 任务清单
