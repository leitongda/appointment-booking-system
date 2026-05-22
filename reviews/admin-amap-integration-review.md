# admin-amap-integration — 自适应多智能体研究画布

> 协作模式：集中调度
> 日期：2026-05-22
> 审查目标：Admin 端高德地图集成方案规划（地图选点标注、地址搜索功能）

---

## 模式选择

**选定模式：** 集中调度

**选择理由：** 目标明确（添加地图支持），不需要某个领域特别深入。涉及 PM/Designer/Engineer 三方视角但无跨职能复杂权衡，集中调度可快速收敛。

---

## Round 1：事实层（只写事实，不评价）

### PM — 产品视角

**产品定位：**
- 项目定位为"医院挂号系统"，SaaS 多租户架构，支持多门店/分院、多科室、多医生排班预约
- 来源：CLAUDE.md:14
- Admin 端技术栈：React 18 + TypeScript + Umi 4 + Ant Design 5 + ProComponents
- 来源：CLAUDE.md:20-22

**功能完成度（地址相关）：**

| 场景 | 模型层 | Schema 层 | API 层 | Admin UI 层 | 完成度 |
|------|--------|-----------|--------|-------------|--------|
| 门店地址 | address+province+city+district+lat+lng (VARCHAR) | 全部声明 | 全部字段可传 | 仅 address 文本域 | 部分实现 |
| 患者地址 | province+city+district+street+address（无经纬度） | 全部声明 | 全部字段可传 | 全部文本字段可编辑 | 已实现（纯文本） |
| 租户地址 | address | 已声明 | 可传 | 文本输入 | 已实现（纯文本） |
| 科室位置 | location（楼层语义） | 已声明 | 可传 | 有字段 | 已实现（纯文本） |
| 医院地址（设置） | key-value store | N/A | 可读写 | 文本输入 | 已实现（纯文本） |
| 签到位置 | location_info | N/A | 字段存在 | 无采集 UI | 未实现 |
| 地图展示/选点 | N/A | N/A | N/A | 类型声明就绪，无组件 | 未实现 |
| 后端地图代理 | N/A | N/A | 无路由 | N/A | 未实现 |

**竞品功能对比：**

| 功能 | 微医/好大夫/挂号网 | 本项目 |
|------|---------------------|--------|
| 医院/门店地址展示 | 有（含地图卡片） | 有（纯文本） |
| 院内导航/地图 | 有 | 无 |
| 到院路线规划 | 有 | 无 |
| 附近医院搜索 | 有 | 无 |
| 地址自动补全/POI 选择 | 有 | 无 |
| 地理编码 | 有 | 无（模型字段存在但未使用） |
| 地址级联选择（省市区） | 有 | 无 |

**目标用户线索：**
- Admin 端 14 个一级业务模块，路由按 5 个业务域拆分
- 无任何地图 npm 依赖，仅有 TypeScript 类型声明预留
- 多租户场景下地址数据通过 tenant_id 隔离
- 来源：CLAUDE.md:150-151

### Designer — 用户视角

**地址相关页面清单：**

| 页面 | 路由 | 组件路径 | 行数 | 地址字段 |
|------|------|----------|------|----------|
| 门店表单 | /organization/store/create 或 /:id/edit | apps/admin/src/pages/store/form.tsx | 417 | address (ProFormTextArea) |
| 门店列表 | /organization/store/list | apps/admin/src/pages/store/index.tsx | 551 | city、address 列 |
| 租户表单 | /platform/tenant/create 或 /:id/edit | apps/admin/src/pages/tenant/form.tsx | 279 | address (ProFormTextArea) |
| 租户详情 | /platform/tenant/:id | apps/admin/src/pages/tenant/detail.tsx | 567 | address (Descriptions) |
| 就诊卡详情(用户) | /medical-services/patient/:id | apps/admin/src/pages/user/detail.tsx | 539 | province/city/district/street/address (ModalForm) |
| 就诊卡详情(患者) | /medical-services/patient/card/:id | apps/admin/src/pages/patient/detail.tsx | 864 | province/city/district/street/address |
| 系统设置-医院信息 | /system/config/hospital-info | apps/admin/src/pages/system/settings.tsx | 1185 | address (ProFormText) |
| 科室表单 | 路由未直接包含地址 | apps/admin/src/pages/department/form.tsx | 371 | location (ProFormText, 楼层语义) |

**地址输入交互模式：**
- 门店表单：ProFormTextArea, rows=3, 无省市区分拆, placeholder="请输入完整地址"
- 租户表单：ProFormTextArea, rows=2, 无省市区分拆
- 就诊卡表单：5 个独立 ProFormText（province/city/district/street/address）
- 系统设置：单个 ProFormText
- 科室表单：单个 ProFormText, placeholder="门诊楼3楼"

**地址验证规则：**
- 门店地址：required + stringLengthRules(1, 255)
- 其他地址字段：全部无验证规则（非必填）
- 无地址专用正则

**组件一致性事实：**
- MapLocationPicker 组件：名为"地图选点"，实际为纯文本 Input 组件（apps/admin/src/components/MapLocationPicker/index.tsx, 52 行）
- MapLocationPickerModal：Modal 包装上述 Input 组件（86 行）
- 自定义表单控件先例：formFields/ 目录有 PasswordField、SwitchGroup、ImageUploadCard
- 第三方库集成方式：全部通过 npm 安装，无 <script> 标签加载先例

**输入方式事实：**
- 无地址 autocomplete 或 POI 搜索功能
- 无省市区级联选择器（Cascader）
- 仅有 fieldProps={{ autoComplete: 'off' }} 关闭浏览器原生补全

### Engineer — 技术视角

**存储层事实：**
- stores 表：latitude VARCHAR(20), longitude VARCHAR(20), address VARCHAR(255), province VARCHAR(50), city VARCHAR(50), district VARCHAR(50) — 来源：models/store.py:16-21
- patients 表：province/city/district/street/address（无经纬度） — 来源：models/user.py:61-67
- departments 表：location VARCHAR(100)（楼层语义） — 来源：models/department.py:42
- tenants 表：address VARCHAR(255) — 来源：models/tenant.py:95
- 未使用 PostGIS，latitude/longitude 为普通字符串类型
- latitude/longitude 在初始建表时即存在，非后续迁移添加

**前端构建与依赖事实：**
- Umi 4（@umijs/max ^4.6.0）支持 headScripts/externals 配置项注入外部 JS SDK
- 当前 config/config.ts 中无 headScripts、scripts、externals 配置
- 无任何地图 npm 依赖（@amap/amap-jsapi-loader 等）
- 代码分割策略：depPerChunk，大于 50KB 单独打包
- 浏览器目标：Chrome 80+

**高德地图集成现状（已有基础设施）：**

| 项目 | 状态 | 来源 |
|------|------|------|
| AMap TypeScript 类型声明 | 已完成（Map, LngLat, Marker, Geocoder, PlaceSearch, AutoComplete） | apps/admin/typings.d.ts:14-148 |
| 开发环境代理配置 | 已完成（/_AMapService 代理到后端） | apps/admin/config/proxy/index.ts:6-29 |
| 生产环境 Nginx 代理文档 | 已完成（/_AMapService/ 代理到 restapi.amap.com） | docs/github-actions-secrets.md:141-148 |
| AMAP_KEY 环境变量 | 已配置（.env.local + .env.production） | apps/admin/.env.local:9 |
| AMAP_SERVICE_HOST 代理地址 | 已配置 | apps/admin/.env.local:10 |

**未完成的部分：**
- 后端 AMap API 代理路由（apps/server 无任何 amap 相关代码）
- Admin 端地图组件（无任何 AMap 组件实际使用）
- 门店表单地图选点（仅有文本地址域）
- 地理编码/逆地理编码/POI 搜索
- AMAP_KEY 未通过 define 暴露给前端运行时
- AMAP_KEY 未通过 headScripts 注入到 HTML

**安全机制事实：**
- AMAP_KEY 已在 .env.local 和 .env.production 中配置（同一 Key）
- 后端 config.py 中无 AMAP_KEY 配置项
- proxy 配置已预留 _AMapService 路径，但后端无对应路由实现

**依赖和模块耦合事实：**
- MapLocationPicker 组件 LocationInfo 接口仅包含 address: string，无经纬度
- typings.d.ts 中 AMap 类型声明完整但未被实际使用
- 所有第三方库通过 npm 管理，无 CDN script 注入先例

---

## Round 2：辩论层

### 交叉评论投票矩阵（简化版）

| 议题 | 裁决者立场 | Critic 质询 | 最终裁决 |
|------|-----------|------------|---------|
| API Key 安全模型（前端直连 vs 后端代理） | 后端代理更安全 | 🚨 关键：安全架构决策必须在编码前确定 | 采用后端代理模式 |
| 基础设施就绪度 | 实际为断裂状态，需逐项接通 | 🚨 关键：半成品脚手架，成本估算会偏低 | 承认断裂，纳入 P0 行动计划 |
| 竞品对比范围 | 混淆了患者端与 Admin 端功能 | 正确：仅 1-2 项与 Admin 端相关 | 裁决接受：重新定义 Admin 端竞品范围 |
| MapLocationPicker 死代码 | 设计债务，需清理 | 正确：误导性命名 + 死代码 | 删除旧组件，新建真实组件 |
| 使用频率（门店地址地图选点） | 低频操作，ROI 待验证 | 正确：一年可能只用几次 | 裁决接受：分阶段实施，P1 而非 P0 |
| latitude/longitude VARCHAR(20) 类型 | 当前无需地理计算，暂不迁移 | 正确：未来做附近搜索时会有技术债 | 裁决：暂不迁移，但文档标注为已知限制 |
| 多租户 Key 管理 | 当前阶段共享 Key 足够 | 正确：共享 Key 有配额风险 | 裁决：先共享 Key，文档化配额监控方案 |
| 自定义表单控件先例论证力 | 不足，地图组件复杂度远超 PasswordField | 正确：需单独评估 | 裁决接受：不以简单组件类比 |

### 独到发现

1. **后端代理架构已有半成品基础**：proxy 配置已预留 `/_AMapService` 路径，Nginx 代理文档已写好。选择后端代理模式可复用这些基础设施，而非从零开始。
2. **门店表单的 province/city/district 字段在模型中已存在但 UI 未使用**：这意味着即使不做地图功能，门店表单的地址录入体验也有改进空间（省市区分拆 + 级联选择器）。
3. **MapLocationPickerModal 实际未被任何页面引用**：不仅是"死代码"，还暗示当初可能有集成地图的意图但未完成。

### Critic 质询

1. [Critic -> 全体] 质询 1：基础设施实际处于断裂状态，类型声明/proxy/env 未接通
   - 论据：类型声明未被引用、proxy 目标不存在、AMAP_KEY 未暴露给运行时、headScripts 未配置
   - 要求回应：Engineer
   - 级别：🚨 关键

2. [Critic -> 全体] 质询 2：竞品对比将患者端功能与 Admin 端功能混为一谈
   - 论据：7 项竞品功能中仅 1-2 项与 Admin 端数据录入相关
   - 要求回应：PM
   - 级别：普通

3. [Critic -> 全体] 质询 3：MapLocationPicker 组件是误导性命名的死代码
   - 论据：组件名暗示地图功能但实为纯文本 Input，且未被任何页面引用
   - 要求回应：Designer + Engineer
   - 级别：普通

4. [Critic -> 全体] 质询 4：API Key 安全问题是最被低估的风险
   - 论据：前端直连 vs 后端代理两种安全模型完全不同，决定整个架构方向
   - 要求回应：Engineer + PM
   - 级别：🚨 关键

5. [Critic -> 全体] 质询 5：门店地址地图选点的使用频率缺少数据支撑
   - 论据：门店数量少、地址编辑极低频，省市区级联选择器可能是更低成本替代方案
   - 要求回应：PM
   - 级别：普通

6. [Critic -> 全体] 质询 6：latitude/longitude VARCHAR(20) 是否构成技术债
   - 论据：无法做地理距离计算和空间索引，未来可能需要数据迁移
   - 要求回应：Engineer
   - 级别：普通

7. [Critic -> 全体] 质询 7：多租户场景下 Key 管理问题
   - 论据：共享 Key 有配额滥用风险，开发和生产共用同一 Key
   - 要求回应：PM + Engineer
   - 级别：普通

8. [Critic -> 全体] 质询 8：自定义表单控件先例论证力不足
   - 论据：地图组件复杂度（SDK 加载、异步初始化、容器尺寸计算）远超 PasswordField
   - 要求回应：Designer
   - 级别：普通

### Critic 关键质询追踪

| # | 关键质询内容 | 三方回应摘要 | 回应是否充分 | 处置 |
|---|------------|------------|------------|------|
| 1 | 基础设施实际处于断裂状态 | Team Lead 裁决：承认断裂，需逐项接通（类型声明已有、proxy 配置已有、需补充 headScripts + 后端代理路由 + define 暴露 Key） | 是 | 纳入 P0 行动计划 |
| 4 | API Key 安全模型未确定 | Team Lead 裁决：采用后端代理模式。理由：proxy 和 Nginx 配置已有半成品基础、Key 不暴露在浏览器、高德 Web 服务 API Key 需服务端保护 | 是 | 纳入 P0 行动计划 |

---

## Round 3：共识层

### 共识项

1. **议题：采用后端代理模式保护 API Key**
   **结论：** 高德地图 API 请求通过后端代理转发，Key 留在服务端，不暴露给浏览器。复用已有的 `/_AMapService` proxy 配置和 Nginx 代理文档。
   **建议行动：** 后端新增 AMap 代理模块，config.py 新增 AMAP_KEY 配置，前端通过后端代理调用高德 API。
   **成本估算：** 8h（后端代理路由 4h + 前端调用适配 4h）
   **优先级：** P0

2. **议题：接通已有的断裂基础设施**
   **结论：** 类型声明和 proxy 配置已有，需补充：config.ts 的 headScripts 加载 AMap JS SDK、config.ts 的 define 暴露 AMAP_KEY（如果前端需要 Key 用于 JS API）、后端代理路由。
   **建议行动：** 逐步接通 headScripts → 后端代理 → 前端组件加载验证。
   **成本估算：** 4h
   **优先级：** P0

3. **议题：清理 MapLocationPicker 死代码，新建真实地图选点组件**
   **结论：** 删除现有的 MapLocationPicker/MapLocationPickerModal（纯文本 Input，未被引用），新建基于 AMap JS SDK 的真实地图选点组件。新组件放在 `src/components/MapLocationPicker/`（复用路径）。
   **建议行动：** 删除旧组件 → 实现新 MapLocationPicker（地图 + POI 搜索 + 选点回调）→ 集成到门店表单。
   **成本估算：** 16h（地图组件 8h + POI 搜索/地理编码 4h + 门店表单集成 4h）
   **优先级：** P1

4. **议题：门店表单地址录入增强（省市区分拆 + 经纬度）**
   **结论：** 门店表单当前仅有一个 address 文本域。应分拆为 province/city/district 级联选择器 + 详细地址文本域 + 地图选点（可选）。后端模型字段已存在，只需 UI 层补全。
   **建议行动：** 门店表单新增省市区字段、latitude/longitude 隐藏字段（地图选点自动填充）。
   **成本估算：** 6h（省市区级联 4h + 表单字段联动 2h）
   **优先级：** P1

5. **议题：后端 AMap 代理模块实现**
   **结论：** 后端新增 `/api/v1/amap/` 模块，代理高德地图 Web 服务 API（地理编码、逆地理编码、POI 搜索）。Key 从 Settings 配置读取。
   **建议行动：** 新建 modules/amap/（router.py + service.py），config.py 新增 AMAP_KEY，代理 3 个核心 API。
   **成本估算：** 8h（代理路由 4h + 错误处理/限流 2h + 配置管理 2h）
   **优先级：** P0

6. **议题：多租户 Key 管理策略**
   **结论：** 当前阶段采用平台级共享 Key，所有租户共用。在系统设置中增加"地图服务配置"项，允许平台管理员替换 Key。不做租户级独立 Key（过度设计）。
   **建议行动：** Settings 模型新增 amap_key 字段，系统设置页面新增地图配置区域。
   **成本估算：** 3h
   **优先级：** P2

### 分歧项

1. **议题：latitude/longitude 数据类型是否需要迁移为 Numeric/Float**
   **各方立场：**
   - PM：当前无地理计算需求，暂不迁移
   - Designer：不影响前端地图选点功能
   - Engineer：VARCHAR(20) 可存储高德返回的经纬度字符串，但未来做"附近门店"查询时需要迁移
   **裁决/建议：** 暂不迁移。当前阶段地图选点只需存储和回显经纬度，不涉及距离计算。VARCHAR(20) 足够存储 `116.397428,39.90923` 格式。在文档中标注为"已知限制"。
   **决策依据：** 迁移需要 Alembic 迁移脚本 + 数据清洗 + 前端适配，成本约 4h，且当前无实际使用场景。推迟到需要"附近门店"功能时再处理。

2. **议题：是否需要省市区级联选择器作为独立功能先行交付**
   **各方立场：**
   - PM：级联选择器可独立于地图功能交付，提升所有地址表单的体验
   - Designer：患者端已有省市区文本字段，级联选择器可统一交互
   - Engineer：需引入 antd Cascader + 省市区数据源，额外依赖
   **裁决/建议：** 作为 P1 与门店表单地图选点一起交付，不单独拆分。理由：省市区级联主要服务于门店表单，患者端已有独立字段且交互模式不同。
   **决策依据：** 单独交付级联选择器需要额外测试和集成成本，与地图选点一起交付可共享省市区数据源。

---

## 被低估的优势

1. **已有基础设施价值被 Critic 纠正为"半成品脚手架"**：虽然断裂，但类型声明（148 行完整 AMap 类型）、proxy 规则、Nginx 代理文档、环境变量配置都是可直接复用的工作量。从"半成品"到"可用"的真实工作量约 12h，远低于从零开始（约 30h+）。
2. **后端模型字段完整度高**：stores 表的 address/province/city/district/latitude/longitude 字段全部已存在且 Schema 已声明，前端只需补全 UI，无需后端改动。
3. **Umi 4 的 headScripts 机制成熟**：无需自定义 Webpack 配置，config.ts 加一行 headScripts 即可注入 AMap JS SDK。

---

## 行动计划（按 ROI 排序）

| 优先级 | 行动 | 成本 | 价值 | 负责 | 状态 |
|--------|------|------|------|------|------|
| P0 | 后端 AMap 代理模块（geocoding/reverse geocoding/POI search） | 8h | 高 | Engineer | 待执行 |
| P0 | 接通前端基础设施（headScripts + define + 后端路由验证） | 4h | 高 | Engineer | 待执行 |
| P0 | API Key 安全模型确认 + config.py 新增 AMAP_KEY 配置 | 2h | 高 | Engineer | 待执行 |
| P1 | 清理 MapLocationPicker 死代码 + 新建真实地图选点组件 | 16h | 高 | Engineer | 待执行 |
| P1 | 门店表单地址录入增强（省市区分拆 + 经纬度隐藏字段） | 6h | 高 | Engineer | 待执行 |
| P2 | 系统设置新增地图服务配置（Key 管理） | 3h | 中 | Engineer | 待执行 |
| P2 | 租户/医院地址表单集成地图选点（可选） | 4h | 中 | Engineer | 待执行 |
| 待定 | latitude/longitude 类型迁移为 Numeric（需"附近门店"功能时） | 4h | 待定 | Engineer | 需用户确认 |
| 待定 | 患者地址模型新增经纬度字段（需患者端地图功能时） | 6h | 待定 | PM + Engineer | 需用户确认 |

### P0：立即执行（高价值、低成本）

1. **后端 AMap 代理模块** — 新建 `apps/server/app/modules/amap/`，代理高德 Web 服务 API 的 3 个核心接口：地理编码（地址→经纬度）、逆地理编码（经纬度→地址）、POI 搜索（关键词→地点列表）。Key 从 Settings 读取，限流按租户隔离。成本：8h。
2. **接通前端基础设施** — `config/config.ts` 新增 `headScripts` 注入 AMap JS SDK 2.0，`define` 暴露 `AMAP_SERVICE_HOST`。验证 proxy `/_AMapService` 路由到后端代理可通。成本：4h。
3. **API Key 安全配置** — `apps/server/app/core/config.py` 新增 `AMAP_KEY` 字段，`.env.example` 补充说明。成本：2h。

### P1：本轮迭代（高价值、中等成本）

1. **真实地图选点组件** — 删除旧 MapLocationPicker，新建基于 AMap JS SDK 的 React 组件：地图容器 + Marker 拖拽 + POI 搜索输入框 + 选点回调（返回 address/province/city/district/lng/lat）。封装为 ProForm 兼容的自定义表单控件。成本：16h。
2. **门店表单地址增强** — 门店表单（store/form.tsx）地址区域重构：新增 province/city/district 字段（可手动输入或地图选点自动填充）、latitude/longitude 隐藏字段、地图选点按钮触发 MapLocationPickerModal。成本：6h。

### P2：下个周期规划（中等价值，较高成本）

1. **系统设置地图配置** — Settings 模型新增 amap_key/amap_secret 字段，系统设置页面新增"地图服务"配置区域，允许平台管理员管理 Key。成本：3h。
2. **其他表单集成** — 租户表单、医院地址（系统设置）可选集成地图选点。成本：4h。

### 待定：需用户确认

1. **latitude/longitude 类型迁移** — 将 VARCHAR(20) 迁移为 NUMERIC(10,7)，需 Alembic 迁移 + 数据清洗。仅在需要"附近门店"距离查询时执行。成本：4h。
2. **患者地址新增经纬度** — patients 表新增 latitude/longitude 字段，患者端表单集成地图选点。仅在患者端需要地图功能时执行。成本：6h。

---

## 摘要

**使用模式：** 集中调度

**关键共识：**
- 6 项达成共识（后端代理模式、基础设施接通、组件清理重建、门店表单增强、后端代理模块、Key 管理策略）

**关键分歧：**
- 2 项需要决策者介入（经纬度数据类型迁移时机、省市区级联选择器交付节奏）

**Top 3 P0 行动：**
1. 后端 AMap 代理模块（8h）— 安全基础，阻塞所有前端地图功能
2. 接通前端基础设施（4h）— headScripts + define + proxy 验证
3. API Key 安全配置（2h）— config.py 新增 AMAP_KEY

**Critic 关键洞察：**
- "基础设施就绪"是误判，实际为断裂状态（类型声明未引用、proxy 目标不存在、Key 未暴露给运行时）
- 竞品对比混淆了患者端与 Admin 端功能，仅 POI 搜索/地址自动补全与 Admin 端相关
- MapLocationPicker 是误导性命名的死代码，需清理后重建

---

## 附录：模式切换日志

| 时间 | 从 | 到 | 原因 |
|------|-----|-----|------|
| 无切换 | | | |
