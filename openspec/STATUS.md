# OpenSpec 项目状态追踪

> 最后更新： 2026-04-23
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
| `refactor-admin-menu-information-architecture` | 待对齐 | P1 | 0% | Admin 菜单信息架构重构 - 依赖团队确认命名、拆分顺序和兼容策略 |
| `add-template-driven-miniapp-platform` | 待立项 | P2 | 0% | 模板驱动的小程序实例平台 - 需要单独的产品/发布/运维负责人 |

### 已归档的 Changes

| Change ID | 归档日期 | 优先级 | 说明 |
|-----------|---------|--------|------|
| `add-schedule-rule-enhancements` | 2026-03-27 | P1 | 排班规则功能增强 (批量删除/停诊、生成历史、前端交互) |
| `refactor-server-module-boundaries` | 2026-03-27 | P1 | 服务端模块边界重构 (services/ 迁移到 modules/ 结构，删除兼容层) |
| `fix-payment-closure-and-refund-flow` | 2026-04-23 | P0 | 支付创建、重试支付、退款闭环、回调幂等、超时竞态、legacy 兼容策略和联调文档均已完成 |
| `update-appointment-list-page-size` | 2026-04-23 | P1 | 预约列表分页上限、条件校验与测试已完成 |
| `enhance-schedule-rule-management` | 2026-04-23 | P1 | 与已归档的 add-schedule-rule-enhancements 功能重复，作为重复项归档 |

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

**当前执行建议:**
- 暂不进入实现阶段
- 先完成团队对齐会议并将结论写回 proposal/tasks
- 对齐完成后，再分为“路由/权限骨架”和“settings 内容拆分”两批推进

### 4. enhance-schedule-rule-management (已归档)

**归档位置:** `/openspec/changes/archive/2026-04-23-enhance-schedule-rule-management/`

**说明:** 与 `add-schedule-rule-enhancements` 功能重复，作为重复项归档。不再按此 change 开发，后续排班规则相关需求应基于已归档的 `add-schedule-rule-enhancements` 成果继续提出新 change。

### 5. update-appointment-list-page-size (已归档)

**归档位置:** `/openspec/changes/archive/2026-04-23-update-appointment-list-page-size/`

**任务清单状态:**
- [x] 1.1.1 在 `apps/server/app/core/config.py` 增加 `APPOINTMENTS_MAX_PAGE_SIZE`
- [x] 1.1.2 在 `apps/server/.env.example` 补充配置说明
- [x] 1.2.1 调整预约列表 `page_size` 上限至可配置值
- [x] 1.2.2 当 `page_size > 100` 时，仅允许管理员请求且必须提供 `start_date` 与 `end_date`
- [x] 1.2.3 返回明确的校验错误信息
- [x] 1.3.1 更新 `AppointmentListQuery.page_size` 的上限与描述
- [x] 2.1 更新 `docs/api/README.md` 分页说明
- [x] 2.2 补充 `packages/api/src/modules/appointment.ts` 注释说明
- [x] 3.1 补充后端集成测试，覆盖 4 个核心场景

### 6. fix-payment-closure-and-refund-flow (已归档)

**归档位置:** `/openspec/changes/archive/2026-04-23-fix-payment-closure-and-refund-flow/`

**说明:** 支付创建、重试支付、退款闭环、回调幂等、超时竞态、legacy 兼容策略和联调文档均已完成。

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
- [x] 多租户架构文档 (docs/architecture-multi-tenant.md)
- [x] 测试覆盖 (租户隔离、跨租户访问拒绝等)

**已于 2026-04-16 复核完成的改造:**
- [x] 配额实时检查集成到门店/管理员/医生/预约创建 API (`apps/server/tests/tenants/test_quota.py` 通过)
- [x] 导入服务租户隔离 (`apps/server/tests/tenants/test_import_tenant_isolation.py` 通过)
- [x] 缓存隔离测试补充 (`apps/server/tests/tenants/test_cache_isolation.py` 通过)
- [x] 分布式锁键添加租户维度 (`apps/server/tests/tenants/test_distributed_lock_isolation.py` 通过)
- [x] 存储配额统计实现（本地存储按 `tenants/<tenant_id>/` 前缀统计）

**待完成的改造:**
- 暂无明确的 P1/P2 遗留项；如需进一步精确统计非本地对象存储用量，建议单独创建 change 设计对象存储枚举/元数据方案

---

## 下一步行动建议

### 立即执行 (本周)

1. ~~**归档 add-schedule-rule-enhancements**~~ 已完成 (2026-03-27)
2. ~~**归档 refactor-server-module-boundaries**~~ 已完成 (2026-03-27)
3. ~~**归档 fix-payment-closure-and-refund-flow**~~ 已完成 (2026-04-23)
4. ~~**归档 update-appointment-list-page-size**~~ 已完成 (2026-04-23)
5. ~~**归档 enhance-schedule-rule-management**~~ 已完成 (2026-04-23)

### 需要团队决策 (本周)

6. **refactor-admin-menu-information-architecture 对齐会议**
   - 确认菜单命名方案
   - 确认 settings 拆分优先级
   - 确认兼容性处理策略

### 下一周期规划

7. **P1 多租户改造完善**
   - 已完成，当前转入维护期

8. **refactor-admin-menu-information-architecture**
   - 团队对齐完成后拆成两批推进

9. **add-template-driven-miniapp-platform**
   - 单独立项，避免与 backlog 清理工作并行耦合
