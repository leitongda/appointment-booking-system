## Context

当前 Admin 导航的主要问题有四类：
- 左侧菜单把 `租户管理`、`系统设置`、`门店管理`、`预约管理` 等不同层级能力并列，SaaS 平台端与租户运营端边界不清晰
- `system/settings` 聚合了预约规则、建卡名称、黑名单、微信配置、邮件配置、图片处理等多类能力，导致配置归属不明确
- 头部门店快捷入口中承载了签到二维码、诊费设置、复诊规则等操作，但这些能力在左侧导航中没有稳定入口
- 后端已正式提供病历、租户订阅、租户用量日志等能力，但前台缺少与其复杂度相匹配的导航表达

## Goals / Non-Goals

**Goals:**
- 建立适合多租户 SaaS 后台的 Admin 导航层级
- 让菜单可见性与角色权限边界保持一致
- 提升高频配置能力与关键业务能力的可发现性
- 为旧菜单遗留功能建立清晰迁移结论，避免“文档还在、入口消失”的认知偏差

**Non-Goals:**
- 不在本次变更中重做业务页面视觉设计
- 不改变既有后端 API 路径、请求字段或核心业务规则
- 不一次性补齐所有遗留页面实现，仅先约束哪些能力必须有入口、哪些允许继续隐藏
- 不在本次变更中处理医生端、患者端的信息架构

## Decisions

### 0. 菜单命名与结构（团队对齐后确认）

**关键命名调整：**
- 组织与权限 → **组织管理** [Organization Management]
- 经营配置 → **配置中心** [Configuration Center]
- 内容与触达 → **内容运营** [Content Operations]
- 新增独立一级菜单：**系统监控** [System Monitoring]

### 1. 采用分域导航而不是继续按历史模块平铺

目标导航域：

```text
仪表盘 (保持不变)
│
├── 平台管理 [Platform Management] - 仅超级管理员可见
│   ├── 租户管理
│   │   ├── 租户列表
│   │   ├── 租户详情 (包含订阅管理、用量统计)
│   │   └── ...
│   └── 订阅计划
│
├── 组织管理 [Organization Management]
│   ├── 门店管理
│   │   ├── 门店列表
│   │   └── 编辑门店（保留诊费类型、诊费模板、复诊规则作为关联入口）
│   ├── 科室管理
│   ├── 角色权限
│   └── 后台用户
│
├── 医疗业务 [Medical Services]
│   ├── 医生管理
│   ├── 排班管理
│   ├── 预约管理
│   ├── 患者管理
│   ├── 就诊卡管理
│   ├── 病历管理 (补充详情/编辑页)
│   └── 停诊审核
│
├── 配置中心 [Configuration Center]
│   ├── 预约规则 (从 settings/booking 提升)
│   ├── 黑名单管理 (从 settings/blacklist 提升)
│   ├── 微信配置 (从 settings/wechat 提升)
│   ├── 预约选项 (从 settings 的 bookingFields 提升)
│   ├── 就诊卡配置 (从 settings 的 patientCard 提升)
│   ├── 医院信息 (从 settings 的 hospital 提升)
│   ├── 邮件配置 (从 settings 的 email 提升)
│   ├── 图片配置 (从 settings 的 image 提升)
│   ├── 班次类型
│   ├── 规则组管理
│   ├── 诊费类型
│   ├── 诊费模板
│   └── 预约须知
│
├── 内容运营 [Content Operations]
│   ├── 内容管理（新闻/公告/Banner）
│   ├── 消息管理
│   └── 用户反馈
│
└── 系统监控 [System Monitoring] - 独立一级菜单
    ├── 操作日志
    ├── 签到审计
    ├── 在线用户
    └── 行为分析
```

**理由：**
- 菜单先表达"业务域"和"管理边界"，再表达页面实现
- 平台管理员与租户管理员看到的是同一产品，但不是同一套运营责任
- 把"业务操作"和"业务配置"拆开后，权限模型更稳定
- 系统监控作为独立域，从组织管理中拆分，使职责更清晰

### 2. 平台能力与租户能力必须显式隔离

- `租户管理` 仅对平台管理员可见，且保持独立导航域
- 租户订阅变更、订阅记录、用量概览、用量日志归属于租户管理上下文，不下沉到普通租户后台导航
- 普通租户管理员不应通过宽泛的父级菜单权限看见平台级菜单壳

**理由：**
- 这是 SaaS 产品最核心的认知边界
- 当前通过较粗的父级 `access` 控制存在“父菜单可见但子能力无权限”的灰区

### 3. settings 全部拆分：所有配置 Tab 提升为独立菜单

**拆分策略调整**：从"仅拆高频配置"改为"全部拆分"

| 原 Tab | 新路径 | 新组件路径 | 说明 |
|--------|--------|------------|------|
| 规则配置 (booking) | `/booking-rules` | `pages/configuration/booking-rules.tsx` | 预约规则配置 |
| 爽约黑名单 (blacklist) | `/blacklist` | `pages/configuration/blacklist.tsx` | 黑名单管理 |
| 微信配置 (wechat) | `/wechat-config` | `pages/configuration/wechat-config.tsx` | 微信配置 |
| 预约选项 (bookingFields) | `/booking-fields` | `pages/configuration/booking-fields.tsx` | 预约选项配置 |
| 就诊卡配置 (patientCard) | `/patient-card-config` | `pages/configuration/patient-card-config.tsx` | 就诊卡配置 |
| 医院信息 (hospital) | `/hospital-info` | `pages/configuration/hospital-info.tsx` | 医院信息配置 |
| 邮件配置 (email) | `/email-config` | `pages/configuration/email-config.tsx` | 邮件配置 |
| 图片配置 (image) | `/image-config` | `pages/configuration/image-config.tsx` | 图片配置 |

**理由：**
- 不同配置由不同岗位负责，全部拆分可避免权限冲突
- 独立菜单更便于后续扩展和维护
- 提升可发现性，降低配置查找成本
- 为后续细粒度权限控制奠定基础

**兼容性处理：**
- 保留 `system/settings` 页面作为过渡期兼容入口
- 添加 deprecation warning，引导用户使用新菜单
- 配置旧路由到新路由的自动重定向

### 4. 头部快捷入口保留，但不能成为唯一入口

- 门店切换器中的 `签到二维码`、`诊费设置`、`复诊规则` 继续保留
- 同时必须在左侧菜单或其上下文页面中提供可发现的正式入口
- 快捷入口的命名和跳转目标必须与正式菜单一致，避免同一能力多种叫法

**理由：**
- 快捷入口适合提高效率，不适合承担信息架构职责
- 否则新用户、低频用户、权限调试都很困难

### 5. 已存在的后台能力必须有清晰导航承接策略

必须补充导航承接的现有能力：
- 病历管理：作为医疗业务域的一部分提供正式入口
- 租户订阅管理：至少在租户详情中提供显式二级入口和操作区
- 租户用量日志：至少在租户详情中提供显式二级入口，不再只停留在 API 层

允许继续不做独立左侧菜单，但必须写明处理结论的遗留能力：
- 首页菜单
- 底部菜单
- 新闻分类
- 弹框管理

**理由：**
- 能力存在而入口缺失，会让团队误判系统实际能力边界
- 遗留功能不一定要恢复，但必须有清晰处置结论

### 6. 菜单可见性需要从“粗父级权限”升级为“父子一致的访问模型”

- 父级菜单的可见性应由其有效子项或明确的父级首页决定
- 子路由需要更细粒度的 `access` 约束，而不是依赖父级大类兜底
- 菜单重构时同步建立“角色 -> 导航域 -> 页面”的映射表

**理由：**
- 当前 `canSystem` 一类的粗放判断不利于长期扩展
- 后续若继续增加配置页，父级菜单会越来越失真

## 新增权限点

```typescript
// 租户用量
tenant:usage:view - 查看租户用量统计

// 病历详情/编辑
medical-record:detail - 查看病历详情
medical-record:create - 创建病历
medical-record:update - 编辑病历
medical-record:delete - 删除病历

// 配置中心（新增细分权限）
configuration:booking-rules - 预约规则配置
configuration:blacklist - 黑名单管理
configuration:wechat - 微信配置
configuration:booking-fields - 预约选项配置
configuration:patient-card - 就诊卡配置
configuration:hospital-info - 医院信息配置
configuration:email - 邮件配置
configuration:image - 图片配置

// 系统监控（独立域）
monitor:logs - 操作日志
monitor:checkin-audit - 签到审计
monitor:online-users - 在线用户
monitor:analytics - 行为分析
```

## 权限分组调整

```typescript
// 新的权限分组
canPlatformManagement = canTenant || canTenantPlans || canTenantUsage
canOrganizationManagement = canStore || canDepartment || canRoleManagement || canUserManagement
canMedicalServices = canDoctor || canSchedule || canAppointment || canPatient || canMedicalRecord || canLeaveRequest
canConfigurationCenter = canBookingRules || canBlacklist || canWechat || canBookingFields || canPatientCard || canHospitalInfo || canEmail || canImage || canShiftType || canRuleGroup || canFeeType || canFeeTemplate || canBookingNotice
canContentOperations = canContent || canMessage || canFeedback
canSystemMonitoring = canSystemLogs || canCheckinAuditLogs || canOnlineUsers || canAnalytics
```

## 角色可见性矩阵

| 角色 | 平台管理 | 组织管理 | 医疗业务 | 配置中心 | 内容运营 | 系统监控 |
|------|----------|----------|----------|----------|----------|----------|
| 超级管理员 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| 租户管理员 | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ |
| 门店管理员 | ❌ | 部分 | ✅ | 部分 | ❌ | ❌ |
| 医生 | ❌ | ❌ | 部分 | ❌ | ❌ | ❌ |
| 普通后台用户 | ❌ | ❌ | 部分 | ❌ | ❌ | ❌ |

**说明：**
- "部分" 表示仅可见特定子项（如门店管理员仅可见自己门店的相关功能）
- 门店管理员的配置中心权限仅限其门店相关配置
- 系统监控域通常仅对管理审计需求的角色开放
- 医生的"部分"医疗业务权限通常仅包括：查看自己的排班、查看自己的预约记录、查看患者信息（限自己接诊的患者）

## 完整菜单树与权限映射

```typescript
// 导航域与权限点映射
const navigationDomains = {
  platform: {
    name: '平台管理',
    icon: 'CloudServerOutlined',
    access: 'canPlatformManagement',
    routes: [
      { path: '/tenant', name: '租户管理', access: 'canTenant' },
      { path: '/tenant/plans', name: '订阅计划', access: 'canTenantPlans' },
    ]
  },
  organization: {
    name: '组织管理',
    icon: 'ApartmentOutlined',
    access: 'canOrganizationManagement',
    routes: [
      { path: '/store', name: '门店管理', access: 'canStore' },
      { path: '/department', name: '科室管理', access: 'canDepartment' },
      { path: '/role', name: '角色权限', access: 'canRoleManagement' },
      { path: '/user', name: '后台用户', access: 'canUserManagement' },
    ]
  },
  medical: {
    name: '医疗业务',
    icon: 'MedicineBoxOutlined',
    access: 'canMedicalServices',
    routes: [
      { path: '/doctor', name: '医生管理', access: 'canDoctor' },
      { path: '/schedule', name: '排班管理', access: 'canSchedule' },
      { path: '/appointment', name: '预约管理', access: 'canAppointment' },
      { path: '/patient', name: '患者管理', access: 'canPatient' },
      { path: '/patient-card', name: '就诊卡管理', access: 'canPatientCard' },
      { path: '/medical-record', name: '病历管理', access: 'canMedicalRecord' },
      { path: '/leave-request', name: '停诊审核', access: 'canLeaveRequest' },
    ]
  },
  configuration: {
    name: '配置中心',
    icon: 'SettingOutlined',
    access: 'canConfigurationCenter',
    routes: [
      { path: '/booking-rules', name: '预约规则', access: 'canBookingRules', from: 'settings.booking' },
      { path: '/blacklist', name: '黑名单管理', access: 'canBlacklist', from: 'settings.blacklist' },
      { path: '/wechat-config', name: '微信配置', access: 'canWechat', from: 'settings.wechat' },
      { path: '/booking-fields', name: '预约选项', access: 'canBookingFields', from: 'settings.bookingFields' },
      { path: '/patient-card-config', name: '就诊卡配置', access: 'canPatientCardConfig', from: 'settings.patientCard' },
      { path: '/hospital-info', name: '医院信息', access: 'canHospitalInfo', from: 'settings.hospital' },
      { path: '/email-config', name: '邮件配置', access: 'canEmail', from: 'settings.email' },
      { path: '/image-config', name: '图片配置', access: 'canImage', from: 'settings.image' },
      { path: '/shift-type', name: '班次类型', access: 'canShiftType' },
      { path: '/rule-group', name: '规则组管理', access: 'canRuleGroup' },
      { path: '/fee-type', name: '诊费类型', access: 'canFeeType' },
      { path: '/fee-template', name: '诊费模板', access: 'canFeeTemplate' },
      { path: '/booking-notice', name: '预约须知', access: 'canBookingNotice' },
    ]
  },
  content: {
    name: '内容运营',
    icon: 'NotificationOutlined',
    access: 'canContentOperations',
    routes: [
      { path: '/content', name: '内容管理', access: 'canContent' },
      { path: '/message', name: '消息管理', access: 'canMessage' },
      { path: '/feedback', name: '用户反馈', access: 'canFeedback' },
    ]
  },
  monitoring: {
    name: '系统监控',
    icon: 'MonitorOutlined',
    access: 'canSystemMonitoring',
    routes: [
      { path: '/system/logs', name: '操作日志', access: 'canSystemLogs' },
      { path: '/system/checkin-audit', name: '签到审计', access: 'canCheckinAuditLogs' },
      { path: '/system/online-users', name: '在线用户', access: 'canOnlineUsers' },
      { path: '/system/analytics', name: '行为分析', access: 'canAnalytics' },
    ]
  }
}
```

## Risks / Trade-offs

| 风险 | 缓解措施 |
|------|----------|
| 菜单拆分后短期会增加学习成本 | 保留原有高频快捷入口，并通过命名保持迁移连续性 |
| 角色权限与路由 `access` 调整容易引入误伤 | 先定义映射表，再按域逐步收口，避免一次性大改 |
| settings 全部拆分导致页面数量大幅增加 | 通过配置中心统一收纳，保留原 settings 页面作为兼容入口，提供过渡期 |
| 遗留菜单能力去留不明会拖慢实现 | 在 proposal 阶段先对每个遗留能力给出处置结论 |
| 系统监控独立可能导致权限分散 | 建立清晰的监控域权限分组，与组织管理域明确区分 |

## Migration Plan

1. 输出新的菜单树、角色可见性矩阵和遗留能力去向表
2. 重构 `routes.ts` 和 `access.ts`，先调整导航骨架
3. 将高频配置从 `system/settings` 抽为独立页面或显式子导航
4. 为病历管理、租户订阅/用量补充正式承接页或次级导航
5. 保留并校正头部快捷入口，确保与正式导航一致
6. 进行角色回归验证，覆盖平台管理员、租户管理员、多门店管理员、普通门店用户

## Open Questions

- ~~`建卡名称配置` 最终是否应归入"患者与就诊卡配置"，还是继续保留在低频基础设置中~~ **已解决**：settings 全部拆分，就诊卡配置独立为配置中心下的菜单项
- `新闻分类`、`弹框管理` 等旧菜单能力是要恢复实现，还是正式从产品范围中移除（待团队确认）
- 系统监控独立域的权限模型细节（需与安全团队对齐）
