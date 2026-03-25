## 阶段 0：团队对齐（新增前置条件）

- [ ] 0.1 与团队对齐菜单命名方案
  - [ ] 确认：组织与权限 → 组织管理
  - [ ] 确认：经营配置 → 配置中心
  - [ ] 确认：内容与触达 → 内容运营
  - [ ] 确认：新增"系统监控"独立一级菜单
- [ ] 0.2 确认 settings 拆分的优先级和顺序
- [ ] 0.3 确认兼容性处理策略（是否保留原 settings 页面作为过渡）

## 阶段 1：创建新页面组件

### 1.1 租户与平台管理
- [ ] `pages/tenant/usage.tsx` - 租户用量统计

### 1.2 病历管理
- [ ] `pages/medical-record/detail.tsx` - 病历详情
- [ ] `pages/medical-record/form.tsx` - 病历编辑

### 1.3 配置中心（从 settings 迁移）
- [ ] `pages/configuration/booking-rules.tsx` - 预约规则（从 settings.booking 迁移）
- [ ] `pages/configuration/blacklist.tsx` - 黑名单管理（从 settings.blacklist 迁移）
- [ ] `pages/configuration/wechat-config.tsx` - 微信配置（从 settings.wechat 迁移）
- [ ] `pages/configuration/booking-fields.tsx` - 预约选项（从 settings.bookingFields 迁移）
- [ ] `pages/configuration/patient-card-config.tsx` - 就诊卡配置（从 settings.patientCard 迁移）
- [ ] `pages/configuration/hospital-info.tsx` - 医院信息（从 settings.hospital 迁移）
- [ ] `pages/configuration/email-config.tsx` - 邮件配置（从 settings.email 迁移）
- [ ] `pages/configuration/image-config.tsx` - 图片配置（从 settings.image 迁移）

### 1.4 系统监控
- [ ] `pages/system/monitoring/index.tsx` - 系统监控聚合页（可选）
- [ ] `pages/system/analytics.tsx` - 行为分析（如需独立页面）

## 阶段 2：更新路由配置

- [ ] 2.1 重构 `config/routes.ts` 的一级菜单结构
  - [ ] 更新"平台管理"域（租户管理、订阅计划）
  - [ ] 更新"组织管理"域（门店、科室、角色、用户）
  - [ ] 更新"医疗业务"域（医生、排班、预约、患者、就诊卡、病历、停诊）
  - [ ] 新增"配置中心"域（包含所有从 settings 迁移的路由）
  - [ ] 更新"内容运营"域（内容、消息、反馈）
  - [ ] 新增"系统监控"域（日志、审计、在线用户、行为分析）
- [ ] 2.2 调整二级菜单层级
- [ ] 2.3 新增租户用量、配置中心、系统监控路由
- [ ] 2.4 配置旧 settings 路由到新路由的重定向规则

## 阶段 3：更新权限配置

- [ ] 3.1 更新 `src/access.ts` 权限检查函数
  - [ ] 新增租户用量权限：`canTenantUsage`
  - [ ] 新增病历管理细粒度权限：`canMedicalRecordDetail`, `canMedicalRecordCreate`, `canMedicalRecordUpdate`, `canMedicalRecordDelete`
  - [ ] 新增配置中心细分权限
  - [ ] 新增系统监控域权限
- [ ] 3.2 新增细分权限点（如上面 1.3 所列）
- [ ] 3.3 调整权限分组逻辑（如权限分组调整所示）
- [ ] 3.4 更新角色与权限的映射关系

## 阶段 4：迁移和兼容

- [ ] 4.1 从 `system/settings.tsx` 迁移各 tab 内容到新页面
  - [ ] 迁移 booking tab 内容到 booking-rules.tsx
  - [ ] 迁移 blacklist tab 内容到 blacklist.tsx
  - [ ] 迁移 wechat tab 内容到 wechat-config.tsx
  - [ ] 迁移 bookingFields tab 内容到 booking-fields.tsx
  - [ ] 迁移 patientCard tab 内容到 patient-card-config.tsx
  - [ ] 迁移 hospital tab 内容到 hospital-info.tsx
  - [ ] 迁移 email tab 内容到 email-config.tsx
  - [ ] 迁移 image tab 内容到 image-config.tsx
- [ ] 4.2 保留 `system/settings` 作为兼容入口
  - [ ] 添加 deprecation warning 横幅
  - [ ] 提供到新菜单的跳转链接
  - [ ] 配置自动重定向（可选）
- [ ] 4.3 更新头部快捷入口，确保指向新路由
- [ ] 4.4 更新所有引用旧 settings 路径的代码

## 阶段 5：验证

- [ ] 5.1 验证不同角色的菜单可见性
  - [ ] 超级管理员：所有菜单可见
  - [ ] 租户管理员：除平台管理外的所有菜单
  - [ ] 门店管理员：组织管理（部分）、医疗业务（部分）、配置中心（部分）
  - [ ] 医生：仅医疗业务相关菜单
  - [ ] 普通后台用户：根据权限配置验证
- [ ] 5.2 验证所有路由跳转正常
  - [ ] 旧 settings 路由正确重定向到新路由
  - [ ] 快捷入口跳转到正确的新路由
  - [ ] 面包屑导航正确显示
- [ ] 5.3 验证快捷入口与正式菜单的一致性
  - [ ] 签到二维码 → 系统监控/签到审计
  - [ ] 诊费设置 → 配置中心/诊费类型或诊费模板
  - [ ] 复诊规则 → 配置中心/规则组管理
- [ ] 5.4 验证权限控制
  - [ ] 无权限时正确隐藏菜单
  - [ ] 无权限时正确拦截访问
  - [ ] 细粒度权限正确生效
- [ ] 5.5 回归测试关键业务流程
  - [ ] 预约流程
  - [ ] 排班流程
  - [ ] 配置修改流程

## 阶段 6：文档更新

- [ ] 6.1 更新用户文档，反映新菜单结构
- [ ] 6.2 更新权限文档，说明新增权限点
- [ ] 6.3 提供 migration guide，帮助用户适应新结构
