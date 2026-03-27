# OpenSpec 项目状态追踪

> 最后更新： 2026-03-27
> 维护者: Team 6

---

## P0 任务完成记录

### 2026-03-26

| 任务 | 状态 | 提交 | 说明 |
|------|------|------|------|
| P0-1 管理员服务添加租户过滤 | **已完成** | `036c94f` | 在 `apps/server/app/modules/admin/service_admins.py` 中为 get_list、get_by_id、get_by_username、get_by_phone 等方法添加了 tenant_id 过滤 |
| P0-1 缓存键租户隔离 | **已完成** | `3444cd0` | 创建 `redis_admin_session_tenant.py`，管理员会话缓存键格式改为 `session:admin:{tenant_id}:{admin_id}` |
| P0 修复 - 管理员服务租户过滤和缓存键租户隔离 | **已完成** | `145090a` | 综合修复，完善测试覆盖 |

---

## P1 任务进展追踪

### 活跃的 OpenSpec Changes

| Change ID | 状态 | 优先级 | 完成度 | 说明 |
|-----------|------|--------|--------|------|
| `refactor-admin-menu-information-architecture` | 待对齐 | P1 | 0% | Admin 菜单信息架构重构 - 需要团队确认后才能开始 |
| `refactor-admin-menu-information-architecture` | 待对齐 | P1 | 0% | Admin 菜单信息架构重构 - 需要团队确认后才能开始 |
| `update-appointment-list-page-size` | 待开始 | P2 | 0% | 扩展预约列表分页上限 |
| `add-template-driven-miniapp-platform` | 待开始 | P2 | 0% | 模板驱动的小程序实例平台 |

### 已归档的 Changes

| Change ID | 归档日期 | 优先级 | 说明 |
|-----------|---------|--------|------|
| `add-schedule-rule-enhancements` | 2026-03-27 | P1 | 排班规则功能增强 (批量删除/停诊、生成历史、前端交互) |
| `refactor-server-module-boundaries` | 2026-03-27 | P1 | 服务端模块边界重构 (services/ 迁移到 modules/ 结构，删除兼容层) |

---

## 详细任务状态

### 1. add-schedule-rule-enhancements (已归档)

**归档位置:** `/openspec/changes/archive/2026-03-27-add-schedule-rule-enhancements/`

**任务清单状态:**
- [x] 1.1 创建 schedule_generation_logs 表的 migration 文件
- [x] 1.2 创建 ScheduleGenerationLog model
- [x] 2.1 创建 ScheduleGenerationLog schema
- [x] 2.2 实现生成历史记录服务
- [x] 2.3 新增批量删除排班 API
- [x] 2.4 新增批量停诊 API
- [x] 2.5 新增检查已生成排班 API
- [x] 2.6 新增获取生成历史 API
- [x] 2.7 修改生成排班 API，增加记录日志功能
- [x] 3.1 新增 scheduleTemplateApi 方法
- [x] 4.1 添加一键删除排班按钮和确认弹窗
- [x] 4.2 添加一键停诊按钮和确认弹窗
- [x] 4.3 生成排班时增加重复生成确认机制
- [x] 4.4 添加查看历史记录弹窗
- [x] 5.1 添加日期范围搜索组件

**待办事项:**
- ~~归档到 `openspec/changes/archive/`~~ 已完成 (2026-03-27)

### 2. refactor-server-module-boundaries (已归档)

**归档位置:** `/openspec/changes/archive/2026-03-27-refactor-server-module-boundaries/`

**已完成任务:**
- [x] 1.1 盘点现有 Server 端模块映射、超大文件和边界违规点
- [x] 1.2 为关键接口补充特征测试
- [x] 1.3 新增架构约束测试，禁止 Router 内定义业务 DTO
- [x] 1.4 新增架构约束测试，禁止 Router 直接执行 ORM 查询
- [x] 2.1 创建 `app/modules`、`app/common`、`app/infrastructure` 目录骨架
- [x] 2.2 抽离通用依赖到 `app/common/deps`
- [x] 2.3 抽离统一响应与错误处理辅助到 `app/common`
- [x] 2.4 调整 `main.py` 和 API 聚合方式以支持新模块注册
- [x] 3.1 迁移 `content` 模块到新结构
- [x] 3.2 迁移 `booking_notices` 模块到新结构
- [x] 3.3 迁移 `store_email_recipients` 模块到新结构
- [x] 3.4 保持旧 API 行为不变并补充回归测试
- [x] 4.1 拆分 `api/v1/admin.py` 为认证、管理员、角色权限、审计日志等子模块
- [x] 4.2 拆分 `api/v1/import_export.py` 为按领域组织的导入导出模块
- [x] 4.3 拆分 `api/v1/doctor_portal.py` 为日程、候诊、病历、随访子模块
- [x] 4.4 拆分 `services/appointment_service.py` 为预约创建、签到、叫号、状态流转子服务
- [x] 4.5 拆分 `services/patient_service.py` 为患者档案、家庭成员、后台患者管理子服务
- [x] 5.1 将存储、邮件、微信、Excel 等适配层整理到 `app/infrastructure`
- [x] 5.2 为日志与上传目录引入明确的运行期目录配置
- [x] 5.3 更新 `.gitignore`、部署文档和本地开发说明
- [x] 6.1 删除完成迁移模块的兼容导入
- [x] 6.2 更新 `docs/server` 架构文档
- [x] 6.3 运行测试并修复回归
- [x] 6.4 复核所有任务并更新状态

### 3. refactor-admin-menu-information-architecture (待对齐 - 0%)

**文件位置:** `/openspec/changes/refactor-admin-menu-information-architecture/`

**前置条件:**
- [ ] 与团队对齐菜单命名方案
- [ ] 确认 settings 拆分的优先级和顺序
- [ ] 确认兼容性处理策略

**任务清单状态:**
- 阶段 0-6 所有任务均未开始（共 106 个子任务）

### 4. enhance-schedule-rule-management (重复/待归档)

**文件位置:** `/openspec/changes/enhance-schedule-rule-management/`

**说明:** 与 `add-schedule-rule-enhancements` 功能重复，建议归档此 change 并保留 `add-schedule-rule-enhancements`。

---

## SaaS 多租户改造状态

### 完成度评估: ~85%

**已完成的改造:**
- [x] 租户模型设计 (Tenant, SubscriptionPlan, TenantNotification)
- [x] 租户上下文中间件 (Header/子域名/路径识别)
- [x] 数据层租户过滤 (add_tenant_filter, TenantFilteredQuery)
- [x] 认证层租户校验 (get_current_admin 强制校验)
- [x] 管理员服务租户过滤 (service_admins.py)
- [x] 管理员会话缓存租户隔离 (redis_admin_session_tenant.py)
- [x] 配额检查工具 (quota.py)
- [x] 通知服务 (notifications/service.py)
- [x] 定时任务 (用量统计、订阅到期、用量限制检查)
- [x] 多租户架构文档 (doc_v2/multi-tenant.md)
- [x] 测试覆盖 (租户隔离、跨租户访问拒绝等)

**待完成的改造 (P1):**
- [ ] 配额实时检查集成到各资源创建 API
- [ ] 导入服务租户隔离
- [ ] 缓存隔离测试补充
- [ ] 分布式锁键添加租户维度 (P2)

**待完成的改造 (P2):**
- [ ] 存储配额统计实现

---

## 下一步行动建议

### 立即执行 (本周)

1. ~~**归档 add-schedule-rule-enhancements**~~ 已完成 (2026-03-27)
2. ~~**归档 refactor-server-module-boundaries**~~ 已完成 (2026-03-27)

### 需要团队决策 (本周)

3. **refactor-admin-menu-information-architecture 对齐会议**
   - 确认菜单命名方案
   - 确认 settings 拆分优先级
   - 确认兼容性处理策略

### 下一周期规划

4. **P1 多租户改造完善**
   - 配额实时检查集成
   - 导入服务租户隔离
   - 缓存隔离测试

5. **update-appointment-list-page-size (P2)**
   - 等待 P1 任务完成后启动

6. **add-template-driven-miniapp-platform (P2)**
   - 等待 P1 任务完成后启动
