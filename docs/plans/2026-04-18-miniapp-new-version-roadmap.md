# 小程序新版本实施规划文档

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 基于现有患者端小程序能力，梳理现状模块与业务逻辑，形成可执行的新版本分阶段实施路线。

**Architecture:** 当前主版本以 `apps/patient-miniapp` 为核心，已经具备预约、支付、签到、消息、就诊人、主题与租户门店上下文等能力；新版本不建议推倒重做，而应以“业务链路稳定化 + 模板实例化平台升级 + 发布运营闭环”作为主线演进。仓库中已有 `OpenSpec` 变更草案，适合作为新版本的平台化方向基线。

**Tech Stack:** Taro 4.x、React 18、TypeScript、`@hospital/api` / `@hospital/shared`、FastAPI、OpenSpec

---

## 1. 版本现状结论

当前仓库里与小程序相关的实现可以分成三层：

1. `apps/patient-miniapp`
当前主版本，业务能力最完整，已经覆盖预约挂号主链路、微信登录、支付、签到、就诊人、消息、反馈、设置、主题与租户门店上下文。

2. `apps/mini-appointment-miniapp`
较早期或简化版实现，保留了首页/扫码/个人中心等基础结构，但在登录守卫、支付闭环、模块完整度、平台化能力上明显弱于当前主版本，更适合做历史参考，不适合作为新版本主基线。

3. `apps/temp-registration`
更偏临时登记/单场景流程样例，不适合作为患者端新版本母版。

结论：
新版本应以 `apps/patient-miniapp` 为功能基线，以 `openspec/changes/add-template-driven-miniapp-platform/` 为平台化方向基线，而不是重新从旧版小程序起盘。

## 2. 当前功能模块梳理

### 2.1 启动与全局基础能力

核心文件：
- `apps/patient-miniapp/src/app.tsx`
- `apps/patient-miniapp/src/app.config.ts`
- `apps/patient-miniapp/src/utils/auth.ts`
- `apps/patient-miniapp/src/utils/store.ts`
- `apps/patient-miniapp/src/utils/theme.ts`
- `apps/patient-miniapp/src/hooks/useTenantGuard.ts`

现有职责：
- 初始化 API 适配器、请求拦截器、401 自动刷新与统一退登
- 根据 `storeCode/storeId` 拉取门店上下文，写入本地缓存
- 初始化门店主题、字体模式、页面埋点
- 在全局请求层自动附加 `store_id`
- 在写操作前增加租户暂停保护，避免订阅过期机构继续预约/支付

这部分说明当前小程序已经不是单纯“页面集合”，而是具备“门店上下文 + 租户状态 + 登录会话 + 主题风格”四层运行时能力。

### 2.2 首页与导流模块

核心文件：
- `apps/patient-miniapp/src/pages/index/index.tsx`
- `apps/patient-miniapp/src/pages/department/index.tsx`
- `apps/patient-miniapp/src/pages/doctor/index.tsx`
- `apps/patient-miniapp/src/packageOther/pages/search/index.tsx`

现有能力：
- 首页轮播图、推荐医生、快捷入口
- 科室树展示，支持单层/多层结构自动适配
- 医生列表展示、号源状态提示
- 科室/医生搜索
- 首页直接触发“预约记录”“扫码签到”“反馈”等导流动作

业务价值：
- 承担预约前的流量分发入口
- 负责把用户从“浏览医院能力”引导到“选科室/选医生/发起预约”

### 2.3 预约挂号主链路

核心文件：
- `apps/patient-miniapp/src/packageBooking/pages/doctor/detail.tsx`
- `apps/patient-miniapp/src/packageBooking/pages/booking/index.tsx`
- `apps/patient-miniapp/src/packageBooking/pages/booking/result.tsx`
- `apps/patient-miniapp/src/pages/appointment/index.tsx`
- `apps/patient-miniapp/src/packageBooking/pages/appointment/detail.tsx`
- `apps/patient-miniapp/src/utils/payment.ts`

现有能力：
- 医生详情、排班可用性、预约截止时间、剩余号源、收藏
- 预约确认页选择就诊人、病情描述、预约须知、医院信息、诊费
- 重复预约校验
- 创建预约后自动分支到“直接成功 / 待支付 / 支付失败 / 支付取消 / 支付暂不可用”
- 微信支付拉起与支付结果二次确认
- 预约列表、预约详情、取消预约、重新支付

核心逻辑：
- 预约流程已从“下单”扩展为“下单 + 支付 + 结果回跳 + 详情兜底”
- 支付失败并不直接丢单，而是保留订单，允许从预约详情重试
- 这是一个已经接近生产闭环的流程，说明新版本更需要“增强与平台化”，而不是重写页面

### 2.4 签到与到院链路

核心文件：
- `apps/patient-miniapp/src/utils/checkin.ts`
- `apps/patient-miniapp/src/packageBooking/pages/checkin/select.tsx`
- `apps/patient-miniapp/src/packageBooking/pages/checkin/scan.tsx`
- `apps/patient-miniapp/src/packageBooking/components/CheckinSuccessModal.tsx`

现有能力：
- 首页和预约页都可发起扫码签到
- 扫码内容识别 `store-checkin:{storeId}`
- 按门店拉取可签到预约
- 支持签到成功后反馈排队结果

业务价值：
- 把“线上预约”与“到院就诊”衔接起来
- 是患者端区别于纯预约展示型小程序的重要模块

### 2.5 个人中心与用户资产模块

核心文件：
- `apps/patient-miniapp/src/pages/profile/index.tsx`
- `apps/patient-miniapp/src/packageProfile/pages/profile/edit.tsx`
- `apps/patient-miniapp/src/packageProfile/pages/patient/index.tsx`
- `apps/patient-miniapp/src/packageProfile/pages/patient/edit.tsx`
- `apps/patient-miniapp/src/packageProfile/pages/favorite/index.tsx`
- `apps/patient-miniapp/src/packageProfile/pages/records/index.tsx`
- `apps/patient-miniapp/src/packageProfile/pages/message/index.tsx`
- `apps/patient-miniapp/src/packageProfile/pages/feedback/index.tsx`
- `apps/patient-miniapp/src/packageProfile/pages/feedback/history.tsx`
- `apps/patient-miniapp/src/packageProfile/pages/settings/index.tsx`

现有能力：
- 微信登录、用户资料展示与编辑
- 就诊人管理
- 我的收藏
- 就诊记录
- 消息中心与已读处理
- 意见反馈与反馈回复历史
- 设置中心：通知偏好、主题、字体模式、修改密码、绑定手机号、清缓存、退出登录

业务意义：
- 这部分已经具备“患者账户中心”特征，不再只是附属页面
- 新版本需要把这里提升为患者长期留存与服务运营的主阵地

### 2.6 平台与后台配置能力

核心文件：
- `packages/api/src/modules/miniapp-platform.ts`
- `apps/server/app/modules/miniapp_platform/router.py`
- `apps/server/app/modules/miniapp_platform/service.py`
- `openspec/changes/add-template-driven-miniapp-platform/*`

现有方向：
- 已有“小程序平台管理”接口模型：公司主体、支付配置、小程序实例
- 已有 OpenSpec 变更草案：模板、实例、支付路由、构建发布任务

结论：
- 后台平台化方向已经起步，但还没有和患者端版本演进完整闭环
- 新版本要做的不只是 UI 改版，而是把“患者端模板化 + 实例化配置 + 发布流程”真正打通

## 3. 当前核心业务逻辑梳理

### 3.1 启动逻辑

链路：
`小程序启动 -> 读取 storeCode/storeId -> 拉取门店信息 -> 初始化主题/租户状态 -> 初始化请求层 -> 页面开始访问 API`

意义：
- 当前是“门店驱动型启动”
- 新版本如果做多实例，启动逻辑需要从“门店驱动”升级为“实例 + 门店双上下文驱动”

### 3.2 登录逻辑

链路：
`触发登录 -> Taro.login -> authApi.wechatLogin -> 判断是否新用户 -> 绑定昵称/头像 -> 写入 accessToken/refreshToken -> 统一广播登录事件 -> 受保护页面自动恢复`

意义：
- 当前登录体验已经支持登录后续动作恢复
- 新版本可以继续复用，不应再回退成分散式页面登录

### 3.3 预约支付逻辑

链路：
`医生详情选排班 -> 预约页选就诊人 -> 重复预约校验 -> 创建预约 -> 需要支付则拉起微信支付 -> 失败时二次确认支付状态 -> 结果页/详情页兜底`

意义：
- 这是当前最成熟的主交易链路
- 新版本应优先保护这条链路的稳定性，再做平台化与体验升级

### 3.4 签到逻辑

链路：
`扫码二维码 -> 识别 store-checkin -> 获取门店待签到预约 -> 选择预约 -> 执行签到 -> 反馈排队信息`

意义：
- 当前签到依赖门店二维码与门店上下文
- 若未来支持多实例/多门店/多模板，需要明确签到码归属与实例归属关系

### 3.5 平台配置逻辑

规划中的目标链路：
`模板 -> 模板版本 -> 小程序实例 -> 默认门店 -> 支付配置 -> 构建任务 -> 发布任务`

意义：
- 这是“新增小程序版本”真正要解决的中后台问题
- 没有这一层，后续每次增加一个客户小程序都会重复人工改配置、改 AppID、手工发版

## 4. 当前版本的主要问题

### 4.1 业务能力完整，但版本治理能力不足

当前患者端已经有较完整业务功能，但“哪个版本给哪个客户、绑定哪个 AppID、如何发布、如何升级、如何回滚”仍缺少统一治理体系。

### 4.2 门店上下文强，实例上下文弱

当前逻辑大量围绕 `storeId/storeCode` 展开，适合单店或单实例场景；要支持多个客户、多个小程序号时，需要补上实例层。

### 4.3 功能模块已经够多，但缺少清晰的版本边界

目前代码里既有成熟业务模块，也有历史实现、试验应用和平台化草案。新版本如果没有明确“基线版本”和“新增边界”，后续容易边做边散。

### 4.4 发布流程仍未平台化

OpenSpec 已明确提出要做模板驱动、实例驱动、发布任务化，但这部分尚未形成真正的实施闭环。

## 5. 新版本总体实施目标

建议把“小程序新版本”定义为以下三件事的组合，而不是单纯的页面改版：

1. 以 `apps/patient-miniapp` 为基线，稳定并补齐患者端核心业务能力。
2. 以模板/实例/支付配置/发布任务为核心，建立小程序平台化能力。
3. 形成“一个模板，多实例、多客户、可升级、可发布、可回滚”的版本治理机制。

## 6. 分阶段实施目标与核心方案

### 阶段一：现状基线固化与新版本范围冻结

**阶段目标**
- 明确新版本以 `apps/patient-miniapp` 为唯一业务基线
- 输出模块地图、业务主链路图、版本边界、遗留代码处置策略
- 明确哪些能力属于 V1 必做，哪些属于后续增强

**核心实施方案**
- 以当前文档为基础，补充页面清单、接口依赖清单、关键状态流转清单
- 把 `apps/mini-appointment-miniapp`、`apps/temp-registration` 定位为历史参考，不再作为新版本主分支
- 抽出“预约/支付/签到/用户中心/消息/反馈/设置/主题/租户上下文”八大模块作为主版本能力树
- 形成产品、研发、测试共用的版本范围说明，避免后续边做边改目标

**阶段产出**
- 新版本功能范围文档
- 模块地图与业务流程图
- V1 功能边界清单

### 阶段二：平台化底座建设

**阶段目标**
- 建立模板、模板版本、小程序实例、支付配置、支付路由、构建任务、发布任务的核心模型
- 让“新增一个小程序版本/实例”从人工改配置变成后台可管理流程

**核心实施方案**
- 以 `openspec/changes/add-template-driven-miniapp-platform/` 为基线推进数据模型与接口设计
- 先建设后台配置中心：公司主体、支付配置、小程序实例
- 患者端保持兼容读取，优先支持“实例配置存在时走实例，缺省时回退门店旧配置”
- 把构建参数从“手写 project.config.json + 环境变量”升级成“实例级配置生成”

**阶段产出**
- 小程序实例管理后台
- 支付配置中心
- 实例级配置读取兼容层
- OpenSpec 规格与设计文档定稿

### 阶段三：患者端业务链路升级

**阶段目标**
- 在不破坏当前主交易链路的前提下，把患者端升级为“模板可复用、实例可注入、业务更稳定”的版本
- 把登录、预约、支付、签到等链路和实例配置真正打通

**核心实施方案**
- 启动阶段从“门店初始化”升级为“实例 + 门店联合初始化”
- 微信登录、支付参数读取、主题配置逐步切到实例优先
- 预约与支付链路增加更明确的配置校验、异常分流、兜底页面
- 统一收敛个人中心模块的数据统计与消息联动，避免各页面分散拼接
- 对首页、个人中心、预约列表等高频页面做模块拆分，降低后续多模板扩展成本

**阶段产出**
- 新版本患者端运行时配置框架
- 实例优先的登录/支付接入逻辑
- 更稳定的预约支付闭环
- 可扩展的页面模块结构

### 阶段四：构建发布与运营闭环

**阶段目标**
- 让“小程序新版本上线”成为标准化发布动作，而不是依赖人工操作
- 支持版本构建、上传、提审、发布、回滚与审计

**核心实施方案**
- 基于实例生成构建参数与 `project.config.json`
- 建立构建任务、发布任务、产物归档和状态追踪
- 后台增加实例版本记录、历史版本列表、回滚入口
- 建立灰度验证、验收清单、上线 checklist

**阶段产出**
- 发布任务流
- 构建产物与版本记录
- 回滚与审计机制
- 上线验收流程

### 阶段五：模板化扩展与商业化复制

**阶段目标**
- 支持多个客户复用同一模板并做差异化配置
- 让新客户接入、模板升级、版本复制形成标准交付模式

**核心实施方案**
- 抽离模板差异点：主题、首页模块、医院介绍、支付配置、默认门店、客服与协议内容
- 建立模板版本管理和实例升级策略
- 明确“模板通用能力”和“实例业务配置”的边界
- 对接客户 onboarding 流程，形成标准配置模板

**阶段产出**
- 模板版本管理机制
- 多客户实例复制流程
- 标准化交付手册

## 7. 阶段优先级建议

建议优先顺序如下：

1. 先做阶段一，冻结基线和范围。
2. 紧接着做阶段二，先把平台化底座立住。
3. 再做阶段三，把患者端切到新底座上运行。
4. 然后做阶段四，补齐发布运营闭环。
5. 最后做阶段五，支撑规模复制。

原因：
- 如果先做 UI 或新页面，后面仍会被实例化和发布问题反复打断。
- 如果不先冻结基线，团队会在多个旧版本之间来回摇摆。
- 如果没有发布闭环，新增版本越多，后续运维成本越高。

## 8. 建议的 V1 核心落地范围

如果要尽快启动“小程序新版本”并控制范围，建议 V1 只覆盖以下内容：

1. 确认 `apps/patient-miniapp` 为唯一新版本基线。
2. 完成模板/实例/支付配置的数据模型与后台基础页面。
3. 打通实例级配置注入。
4. 完成登录、预约、支付、签到四条主链路对实例配置的兼容切换。
5. 建立最小可用的构建发布记录机制。

这五项做完后，新版本就具备“可持续交付”的基础；后续再做模板扩展、页面美化和更多商业化复制能力，会更稳。

## 9. 后续实施建议

从推进顺序看，下一步最适合先补两份文档：

1. 一份更细的“患者端模块与接口依赖清单”
2. 一份正式的 OpenSpec 变更实施 proposal / tasks 拆解

前者帮助团队统一认知，后者帮助真正进入研发排期与实施。
