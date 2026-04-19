# 多风格小程序模板生成 — 分阶段实施计划

> **核心原则：** 新建独立项目 `apps/miniapp-instance`，不修改现有 `apps/patient-miniapp`。

---

## 架构决策

### 为什么新建项目而非改造现有项目

1. **零风险：** 现有 patient-miniapp 继续运行，不受任何影响
2. **从零设计：** 新项目原生支持"业务内核 + 页面壳层"分离，无需逆向拆分
3. **并行开发：** 新项目开发期间旧项目正常迭代
4. **构建隔离：** 每个模板实例独立构建，互不干扰

### 新项目结构

```
apps/miniapp-instance/           # 新建项目（多模板生成器）
├── config/                      # Taro 构建配置
├── src/
│   ├── app.tsx                  # 入口，加载模板配置
│   ├── app.config.ts            # 页面注册 + 分包 + TabBar 基础配置
│   ├── custom-tab-bar/          # 动态 TabBar（从模板配置驱动）
│   ├── components/              # 通用组件
│   │   ├── PageContainer.tsx    # 页面容器
│   │   ├── LoginPopup.tsx       # 登录弹窗
│   │   └── Icons.tsx            # 图标库
│   ├── shells/                  # 页面壳层（按模板变体组织）
│   │   ├── home/
│   │   │   ├── HomeStandard.tsx
│   │   │   ├── HomePremium.tsx
│   │   │   ├── HomeFamily.tsx
│   │   │   ├── HomeWomens.tsx
│   │   │   └── HomeElderly.tsx
│   │   ├── department/
│   │   ├── doctor/
│   │   ├── appointment/
│   │   └── profile/
│   ├── modules/                 # 首页可配置模块组件
│   │   ├── BannerSwiper.tsx
│   │   ├── QuickMenu.tsx
│   │   ├── PatientCard.tsx
│   │   ├── RecommendDoctor.tsx
│   │   ├── FeaturedDoctorCarousel.tsx
│   │   ├── ServiceShowcase.tsx
│   │   └── ...                  # 其他模块
│   ├── hooks/                   # 业务 hooks
│   │   ├── useProtectedPage.ts
│   │   ├── useTenantGuard.ts
│   │   ├── useHomePageData.ts
│   │   ├── useDeptPageData.ts
│   │   └── ...
│   ├── utils/                   # 工具函数
│   ├── templates/               # 5 套模板配置
│   │   ├── modern-general.ts
│   │   ├── premium-specialty.ts
│   │   ├── family-pediatrics.ts
│   │   ├── womens-health.ts
│   │   └── elderly-tcm.ts
│   ├── styles/                  # 全局样式 + Token
│   │   ├── variables.less
│   │   ├── themes.less
│   │   └── templates/           # 模板专属样式覆盖
│   ├── pages/                   # 主包页面（入口页，选择壳层）
│   ├── packageBooking/          # 预约分包
│   ├── packageProfile/          # 个人中心分包
│   └── packageOther/            # 其他分包
├── project.config.json
└── package.json                 # name: @hospital/miniapp-instance
```

### 复用策略

| 层 | 复用来源 | 方式 |
|----|---------|------|
| API 请求 | `@hospital/api` | workspace 依赖，直接 import |
| 共享类型/常量 | `@hospital/shared` | workspace 依赖，直接 import |
| 业务 hooks | patient-miniapp → 新项目 | 复制后改造（抽取业务逻辑为 hooks） |
| 工具函数 | patient-miniapp → 新项目 | 复制 auth.ts、navigate.ts、payment.ts 等 |
| 页面布局 | patient-miniapp 作为参考 | 重写壳层组件（不是复制粘贴） |
| 固定业务页面 | patient-miniapp 作为参考 | 复制预约确认/支付/签到等交易页面 |

---

## 阶段总览

| 阶段 | 名称 | 目标 | 预估工时 | 依赖 |
|------|------|------|---------|------|
| Phase 0 | 项目初始化 + 架构 | 新建项目，建立模板系统基础设施 | 48h | 无 |
| Phase 1 | 双模板验证 | 实现现代综合 + 长辈友好，验证架构 | 56h | Phase 0 |
| Phase 2 | 补齐剩余模板 | 实现高端专科 + 亲子儿科 + 女性健康 | 72h | Phase 1 |
| Phase 3 | 实例化集成 | 接入后台模板选择 + 构建注入 + 发布追踪 | 40h | Phase 2 |
| Phase 4 | 打磨优化 | 无障碍增强 + 性能优化 + 回归测试 | 30h | Phase 3 |

总计约 **246h**（约 6 周，2 人前端 + 1 人后端并行）

---

## Phase 0：项目初始化 + 架构（48h）

### 目标
从零创建 `apps/miniapp-instance`，搭建模板系统基础设施，确保与 patient-miniapp 功能对等。

### 任务清单

#### 0.1 项目脚手架（8h，Engineer）

- [ ] 在 `apps/` 下初始化 Taro 4.x 项目 `miniapp-instance`
- [ ] 配置 package.json：name、workspace 依赖（@hospital/api、@hospital/shared）
- [ ] 配置构建脚本：dev:weapp、build:weapp、clean 等
- [ ] 配置 defineConstants 环境变量注入：
  - TARO_APP_API_URL
  - TARO_APP_TEMPLATE_CODE（模板代码）
  - TARO_APP_TEMPLATE_VERSION（模板版本）
  - TARO_APP_MINIAPP_INSTANCE_ID（实例 ID）
  - TARO_APP_STORE_ID / STORE_CODE / STORE_NAME
- [ ] 配置 babel-plugin-import（NutUI 按需加载）
- [ ] 配置 Webpack 模块替换（axios/jsencrypt/antd 空模块）
- [ ] 验证：`pnpm dev:miniapp-instance` 能正常启动

**产出物：** 可运行的空项目骨架

#### 0.2 模板定义类型系统（8h，Engineer）

- [ ] 创建 `packages/shared/src/types/miniapp-template.ts`
- [ ] 定义 `MiniappStyleTemplate` 接口：
  - code, name, description, category, supportedAudience
  - navSchema: NavSchema（TabBar 配置）
  - homeSchema: HomeModuleSchema[]（首页模块树）
  - pageShells: Record<string, string>（页面 → 壳层映射）
  - designTokens: DesignTokenSet（色彩、字号、圆角、间距覆盖）
  - copyTone: CopyToneConfig（文案覆盖表）
  - constraints: TemplateConstraints（约束声明）
- [ ] 定义所有子类型：NavSchema、HomeModuleSchema、DesignTokenSet 等
- [ ] 导出并发布到 @hospital/shared

**产出物：** `packages/shared/src/types/miniapp-template.ts`

#### 0.3 模板配置加载 + Context（8h，Engineer）

- [ ] 创建 `src/templates/` 目录
- [ ] 创建 `src/templates/index.ts`：导出所有模板配置 + 加载器
- [ ] 创建 `src/templates/loader.ts`：
  - 根据 `TARO_APP_TEMPLATE_CODE` 加载对应模板
  - 回退机制：指定模板不存在 → modern-general
- [ ] 创建 `src/contexts/TemplateContext.tsx`：
  - TemplateProvider：在 app.tsx 包裹，注入模板配置
  - useTemplate() hook：获取当前模板配置
  - useTemplateTokens() hook：获取设计 Token
- [ ] 在 app.tsx 启动时初始化模板配置
- [ ] 应用模板 Token 到 CSS 变量（动态注入 :root 变量）

**产出物：** 模板加载器 + TemplateProvider + useTemplate hooks

#### 0.4 动态 TabBar（8h，Engineer）

- [ ] 创建 `src/custom-tab-bar/index.tsx`
- [ ] 从 useTemplate() 读取 navSchema 配置
- [ ] 动态渲染 Tab 数量（支持 3 栏和 4 栏）
- [ ] 动态渲染 Tab 名称、图标（通过图标映射表）、颜色
- [ ] 支持 TabBar 高度的模板化配置（默认 100rpx，长辈模板 120rpx）
- [ ] 创建图标映射表：模板配置中的 iconKey → 实际图标组件

**产出物：** 动态 TabBar 组件

#### 0.5 页面壳层系统 + 业务 hooks（8h，Engineer）

- [ ] 创建 `src/shells/` 目录结构（home/department/doctor/appointment/profile/）
- [ ] 创建 `src/shells/registry.ts`：壳层注册表
  - registerShell(pagePath, variantId, ShellComponent)
  - resolveShell(pagePath, templateCode) → ShellComponent
- [ ] 创建页面入口组件模式：
  ```tsx
  // pages/index/index.tsx（入口页）
  const HomePage = () => {
    const { pageShells } = useTemplate();
    const Shell = resolveShell('home', pageShells.home);
    return <Shell />;
  };
  ```
- [ ] 创建 `src/hooks/` 目录，从 patient-miniapp 复制并改造：
  - useProtectedPage.ts（登录保护）
  - useTenantGuard.ts（租户检查）
  - 新增 useHomePageData.ts（首页数据获取）
  - 新增 useDeptPageData.ts（科室数据获取）
- [ ] 创建 `src/utils/` 目录，从 patient-miniapp 复制：
  - auth.ts、navigate.ts、payment.ts、store.ts、theme.ts、wechatAuth.ts

**产出物：** 壳层注册系统 + 业务 hooks + 工具函数

#### 0.6 基础组件 + 样式体系（8h，Designer + Engineer）

- [ ] 复制并改造基础组件：
  - PageContainer.tsx（页面容器，支持模板 Token 注入）
  - LoginPopup.tsx（登录弹窗）
  - Icons.tsx（图标库，保留 45+ 图标）
- [ ] 创建 `src/styles/variables.less`：基础 Token（从 patient-miniapp 适配）
- [ ] 创建 `src/styles/themes.less`：模板驱动的 CSS 变量覆盖机制
- [ ] 创建 `src/styles/global.less`：全局样式（NutUI 覆盖、通用样式）
- [ ] 建立 Token 应用链：模板配置 → CSS 变量 → 组件样式

**产出物：** 基础组件 + 样式 Token 体系

#### 0.7 首页模块化渲染器（8h，Engineer）

- [ ] 创建 `src/modules/` 目录
- [ ] 实现 HomeModuleRenderer 组件：
  - 接收 homeSchema 配置
  - 按顺序渲染模块，支持 visible/order/config 控制
- [ ] 实现基础模块组件（从 patient-miniapp 适配）：
  - BannerSwiper：Banner 轮播
  - QuickMenu：快捷入口宫格（支持 4/6 格）
  - PatientCard：就诊卡入口
  - RecommendDoctor：推荐医生列表
- [ ] 模块组件只负责展示，数据通过 props 传入（由壳层组件的 hooks 获取）

**产出物：** HomeModuleRenderer + 4 个基础模块组件

---

## Phase 1：双模板验证（56h）

### 目标
实现现代综合医疗 + 长辈友好/中医康养两套模板，验证完整链路。

### 任务清单

#### 1.1 现代综合医疗模板（24h）

**配置（4h）：**
- [ ] 创建 `src/templates/modern-general.ts`
- [ ] 定义完整配置（TabBar 3栏、首页4模块、6 页面壳层绑定、蓝色 Token）
- [ ] 验证配置符合 MiniappStyleTemplate 类型

**壳层组件（16h）：**
- [ ] `HomeStandard`：Banner → 4宫格 → 就诊卡 → 推荐医生（标准纵向滚动）
- [ ] `DeptSidebar`：搜索栏 + 左右分栏科室选择
- [ ] `DoctorCards`：标准医生卡片列表（头像+信息+有号标签）
- [ ] `DoctorDetailStandard`：医生信息 + 排班选择 + 收藏
- [ ] `AppointTabs`：Tab 分类（5个 Tab）+ 预约卡片列表
- [ ] `ProfileStandard`：头像统计 + 分组菜单列表

**固定业务页面迁移（4h）：**
- [ ] 预约确认页（从 patient-miniapp 适配）
- [ ] 预约结果页
- [ ] 签到页面（scan + select）
- [ ] 个人信息编辑、就诊人管理、收藏、记录、消息、反馈、设置

#### 1.2 长辈友好/中医康养模板（20h）

**配置（4h）：**
- [ ] 创建 `src/templates/elderly-tcm.ts`
- [ ] TabBar 3栏 + 高度 120rpx + 大图标
- [ ] 首页 3 模块：超大按钮 → 公告 → 常看医生
- [ ] 暖棕色 Token + 大字号 + 大圆角 + 大触摸目标

**壳层组件（16h）：**
- [ ] `HomeElderly`：4 超大按钮 + 单条公告 + 常看医生
- [ ] `DeptLargeGrid`：2 列大尺寸科室卡片
- [ ] `DoctorLargeCards`：大卡片（240rpx 高）+ 大字号
- [ ] `DoctorDetailElderly`：超大头像 + 简化排班 + 超大按钮
- [ ] `AppointSimple`：单列表（无 Tab 分类）
- [ ] `ProfileElderly`：大头像 + 大菜单项（120rpx）

**新增模块（已包含在壳层中）：**
- BigActionButton、SimpleNotice、RecentDoctorList、ConfirmDialog（大字版）

#### 1.3 双模板验证（12h）

- [ ] `TARO_APP_TEMPLATE_CODE=modern-general` 构建运行，验证完整预约流程
- [ ] `TARO_APP_TEMPLATE_CODE=elderly-tcm` 构建运行，验证完整预约流程
- [ ] 对比两套模板的视觉差异截图
- [ ] 回归测试：登录、预约、支付、签到、消息
- [ ] 修复验证中发现的问题

**产出物：** 2 套可运行的完整模板 + 验证报告

---

## Phase 2：补齐剩余模板（72h）

### 目标
实现高端专科门诊、亲子儿科、女性健康三套模板。

### 任务清单

#### 2.1 高端专科门诊模板（28h）

**配置（4h）：**
- [ ] `src/templates/premium-specialty.ts`
- [ ] TabBar 4 栏：首页/专家/预约/我的
- [ ] 首页 5 模块：品牌Banner → 明星专家 → 特色项目 → 快捷入口 → 机构介绍

**壳层（20h）：**
- [ ] `HomePremium` + `DeptMinimal` + `DoctorShowcase` + `DoctorDetailPremium` + `ProfilePremium`

**新增模块（4h）：**
- [ ] FeaturedDoctorCarousel、ServiceShowcase、BrandStoryCard

#### 2.2 亲子儿科模板（24h）

**配置（4h）：**
- [ ] `src/templates/family-pediatrics.ts`
- [ ] TabBar 3 栏：首页/预约/成长
- [ ] 首页 5 模块：家庭成员切换 → Banner → 6宫格 → 常见服务 → 推荐医生

**壳层（16h）：**
- [ ] `HomeFamily` + `DeptColorful` + `DoctorDetailFamily` + `ProfileFamily`

**新增模块（4h）：**
- [ ] FamilyMemberSwitcher、AgeGroupService、PediatricQuickMenu

#### 2.3 女性健康模板（20h）

**配置（4h）：**
- [ ] `src/templates/womens-health.ts`
- [ ] TabBar 3 栏：首页/预约/我的
- [ ] 首页 5 模块：Banner → 健康服务 → 快捷入口 → 健康提醒 → 推荐医生

**壳层（12h）：**
- [ ] `HomeWomens` + `DeptSoft` + `DoctorCardsSoft` + `DoctorDetailWomens` + `ProfileWomens`

**新增模块（4h）：**
- [ ] HealthServiceEntry、HealthReminderCard

---

## Phase 3：实例化集成（40h）

### 目标
接入后台管理、构建流程和发布追踪。

### 任务清单

#### 3.1 后端模板管理 API（12h，后端）

- [ ] 扩展 `AppTemplate` 模型：增加 `template_config` JSON 字段
- [ ] 实现 5 套模板 seed 数据脚本
- [ ] 新增 API：模板列表 + 模板详情
- [ ] 修改实例创建 API：template_code 必填
- [ ] 修改实例查询 API：返回关联模板配置

#### 3.2 管理后台模板选择界面（8h，前端）

- [ ] 实例创建/编辑中增加模板选择步骤
- [ ] 模板选择 UI：卡片式展示 5 套模板 + 预览
- [ ] 模板选择保存到实例配置

#### 3.3 构建流程模板注入（12h，Engineer）

- [ ] 构建脚本从实例配置读取模板代码
- [ ] 模板配置 JSON 注入构建环境变量
- [ ] 构建时按模板 tree-shake 未使用壳层
- [ ] 构建产物记录模板版本和实例 ID
- [ ] 支持本地指定模板代码开发模式

#### 3.4 发布追踪模板来源（8h，Engineer）

- [ ] BuildJob 记录模板代码和版本
- [ ] ReleaseArtifact 包含模板来源元数据
- [ ] 发布详情页展示模板信息
- [ ] 支持按模板筛选发布历史

---

## Phase 4：打磨优化（30h）

### 目标
无障碍增强、性能优化、全面回归测试。

### 任务清单

#### 4.1 无障碍增强（8h）
- [ ] 长辈模板 aria-label 属性
- [ ] 色彩对比度 WCAG AA
- [ ] 表单 label 关联 + 图片 alt

#### 4.2 长辈模板专项优化（8h）
- [ ] 触摸目标 >= 88rpx 全面检查
- [ ] 按钮二次确认统一
- [ ] 文案口语化审查
- [ ] 骨架屏适配

#### 4.3 性能优化（6h）
- [ ] 按模板 tree-shake 未使用壳层
- [ ] 模板配置压缩（仅差异部分）
- [ ] 壳层组件 React.lazy
- [ ] 主包体积 < 2MB 检查

#### 4.4 全面回归测试（8h）
- [ ] 5 套模板 × 核心流程矩阵测试
- [ ] 真机测试（iOS/Android）
- [ ] 边界场景（无网络、弱网、切后台）

---

## 任务依赖关系图

```
Phase 0（项目初始化 + 架构）
  0.1 脚手架 ──────→ 0.2 类型定义 ──→ 0.3 模板加载
  0.1 脚手架 ──────→ 0.4 动态 TabBar ──→ 依赖 0.2
  0.1 脚手架 ──────→ 0.5 壳层系统 ──→ 依赖 0.2 + 0.3
  0.1 脚手架 ──────→ 0.6 基础组件 ──→ 依赖 0.3
  0.1 脚手架 ──────→ 0.7 首页渲染器 ──→ 依赖 0.3 + 0.6

Phase 1（双模板验证）──→ 依赖 Phase 0
  1.1 现代综合 ──────→ 可并行
  1.2 长辈友好 ──────→ 可并行
  1.3 验证 ──────────→ 依赖 1.1 + 1.2

Phase 2（剩余模板）──→ 依赖 Phase 1
  2.1 高端专科 ──────→ 可并行
  2.2 亲子儿科 ──────→ 可并行
  2.3 女性健康 ──────→ 可并行

Phase 3（实例化集成）──→ 依赖 Phase 2
  3.1-3.4 顺序依赖

Phase 4（打磨优化）──→ 依赖 Phase 3
```

---

## 里程碑与交付物

| 里程碑 | 交付物 | 验收标准 |
|--------|-------|---------|
| M0: 项目就绪 | 新项目 + 模板系统基础 | `pnpm dev:miniapp-instance` 启动成功，模板配置可加载 |
| M1: 双模板验证 | 2 套完整模板可运行 | 切换 TEMPLATE_CODE，首页/科室/医生/预约/个人中心完全不同 |
| M2: 五模板齐备 | 5 套模板全部可运行 | 5 套模板各通过核心流程回归测试 |
| M3: 平台集成 | 后台选择 + 构建 + 发布 | 后台选模板创建实例，构建发布为独立小程序 |
| M4: 生产就绪 | 全面优化 + 测试报告 | 5 套模板通过真机验证 |

---

## 风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| 业务逻辑迁移遗漏 | 功能缺失 | 逐页面对比 patient-miniapp，核心流程列 checklist |
| Taro 4 栏 TabBar 适配 | 高端专科受阻 | Phase 1 先验证 3 栏，Phase 2 再引入 4 栏 |
| 主包体积超标 | 发布受限 | 按模板 tree-shake；固定页面不分模板复用 |
| 5 套壳层样式冲突 | 视觉异常 | 壳层组件使用 CSS Modules + BEM 命名 |
| 后端接口拖延 | Phase 3 受阻 | 第一阶段用静态配置文件，不依赖后端 |
| 新项目与旧项目维护双份代码 | 长期维护成本 | 最大化复用 @hospital/api 和 @hospital/shared；hooks/utils 纳入共享包 |

---

## 开发命令规划

```bash
# 新增到根 package.json scripts
pnpm dev:miniapp-instance                    # 开发（默认 modern-general 模板）
TEMPLATE_CODE=elderly-tcm pnpm dev:miniapp-instance  # 指定模板开发
TEMPLATE_CODE=premium-specialty pnpm build:miniapp-instance  # 指定模板构建
```

## Turbo 配置

```json
// turbo.json 新增
{
  "miniapp-instance#dev": {
    "cache": false,
    "persistent": true
  },
  "miniapp-instance#build": {
    "dependsOn": ["^build"],
    "outputs": ["dist/**"]
  }
}
```
