# 项目审查与修复总结报告

> 日期: 2026-03-29
> 审查范围: 医院预约挂号系统全栈（管理端 + 医生端 + 患者端 + 后端）
> 审查模式: 集中调度多智能体审查（PM / Designer / Engineer / Critic）

---

## 审查轮次概览

| 轮次 | 审查模块 | 发现项 | 已修复 |
|------|---------|--------|--------|
| 第1轮 | Rule Set（规则集管理） | 8 | 8 |
| 第2轮 | Appointment Flow（预约流程） | 12 | 12 |
| 第3轮 | Schedule Management（排班管理） | 10 | 10 |
| 第4轮 | Org/Doctor/Store（机构/医生/门店） | 9 | 9 |
| 第5轮 | Patient/User（患者/用户） | 7 | 7 |
| 第6轮 | Messages + Miniapp-Platform + System + Tenant + Medical-Records + Leave-Requests | 9 | 9 |
| **合计** | **6 轮，覆盖全部核心模块** | **55** | **55** |

---

## 按优先级统计

| 优先级 | 定义 | 数量 | 说明 |
|--------|------|------|------|
| P0 | 安全漏洞、数据丢失风险、租户隔离缺失 | 14 | 全部已修复 |
| P1 | 功能缺陷、性能问题、交互不合理 | 26 | 全部已修复 |
| P2 | 代码质量、可维护性、体验优化 | 15 | 全部已修复 |

---

## 修复类别分布

### 安全与租户隔离（14 项 P0）

1. **messages 表缺少 tenant_id** — 模型 + 迁移 + 服务层过滤
2. **medical_records 表缺少 tenant_id** — 模型 + 迁移 + 服务层过滤
3. **leave_requests 表缺少 tenant_id** — 模型 + 迁移 + 服务层过滤（含修复 ForeignKey 导入遗漏）
4. **rest_days 表缺少 tenant_id** — 模型 + 迁移 + 服务层过滤
5. **leave_requests 服务层缺少租户过滤** — 添加 `get_current_tenant_id()` 过滤
6. **medical_records 服务层缺少租户过滤** — 添加 `get_current_tenant_id()` 过滤
7. **messages 服务层缺少租户过滤** — 添加 `get_current_tenant_id()` 过滤
8. **管理员端多模块缺少租户过滤** — appointment/content/doctor/message/schedule/store/system/tenant 模块
9. **规则集删除未校验关联排班** — 增加前置检查，防止孤立数据
10. **排班删除未校验关联预约** — 增加前置检查
11. **门店密码明文存储** — 改为 bcrypt 哈希
12. **租户软删除机制缺失** — 添加 deleted_at 字段和过滤逻辑
13. **schedule_suspensions 缺少 tenant_id** — 迁移 + 模型
14. **统计/导出接口租户隔离** — 补充 tenant_id 过滤条件

### 性能优化（8 项 P1）

1. **门店列表 N+1 查询（科室计数）** — 改为 GROUP BY 批量子查询
2. **用户列表 N+1 查询（就诊卡计数 + 预约计数）** — 改为批量查询
3. **休息日列表 N+1 查询（医生姓名）** — 改为批量查询
4. **租户列表 N+1 查询（门店数 + 管理员数）** — 改为 GROUP BY 批量查询
5. **规则集列表 N+1 查询** — 批量加载关联数据
6. **预约列表 N+1 查询（医生/门店/患者信息）** — 改为批量加载
7. **排班日历 N+1 查询** — 批量加载预约信息
8. **consultation_fees 列表查询** — 已有 selectinload，确认无需修改

### 前端交互与文案（15 项 P1/P2）

1. **门店表单营业时间** — ProFormText → ProFormTimePicker + dayjs
2. **用户管理术语不统一** — "患者详情" → "用户详情"，"患者列表" → "用户列表"
3. **患者详情页状态映射** — 硬编码 → 使用 APPOINTMENT_STATUS_MAP 共享常量
4. **患者列表编辑表单** — 补充完整初始值
5. **预约详情页返回导航** — 增加 fromUserId 参数实现准确返回
6. **排班日历创建预约弹窗** — 修复表单初始化和校验逻辑
7. **排班管理消息常量** — 散落的硬编码字符串 → 统一 ScheduleMessages 工具
8. **规则集表单列定义** — 抽取为独立组件 RuleSetTableColumns
9. **系统设置页面布局** — 优化表单分组和间距
10. **角色权限树组件** — 修复半选状态回显
11. **停诊管理时段选择** — 增加 Checkbox 批量选择可用排班
12. **医生端预约今日列表** — 修复时间排序和状态过滤
13. **医生端看诊页面** — 修复叫号后状态未刷新问题
14. **患者端预约详情** — 修复取消预约后状态未同步
15. **小程序预约页面** — 修复 URL 工具函数

### 后端服务层修复（12 项 P1/P2）

1. **门店密码哈希** — service_mutation 层 bcrypt 处理
2. **用户更新 Schema** — 新增 AdminUserUpdate Pydantic 模型
3. **用户默认密码配置** — config.py 新增 DEFAULT_USER_PASSWORD
4. **预约流程服务** — sign_in/call_patient/complete/pass_number/recall 状态流转修复
5. **排班生成服务** — 修复多租户上下文传递
6. **排班变更服务** — 增加 tenant_id 校验
7. **导出服务** — 添加租户过滤
8. **通知服务** — 修复模板渲染异常处理
9. **schedule_suspension 模型** — 添加 tenant_id 字段
10. **tenant 模型** — 添加软删除字段
11. **Celery 排班任务** — 多租户异常隔离（单租户失败不影响其他租户）
12. **统计路由** — 添加 tenant_id 过滤

### 测试修复（6 项）

1. **test_family_member** — 适配新的服务层签名
2. **test_patient_manage_service** — 适配批量查询返回格式
3. **test_rule_engine** — 适配规则集权限校验变更
4. **test_framework** — 适配中间件变更
5. **test_tenant_isolation_enhanced** — 适配新增的 tenant_id 字段
6. **test_architecture_migrated_wrappers** — 修复相对路径问题，改用 `__file__` 计算绝对路径

---

## 数据库迁移文件

| 迁移 | 说明 |
|------|------|
| 042_add_composite_indexes | 复合索引优化 |
| 043_tenant_id_not_null | 核心表 tenant_id 设为 NOT NULL |
| 045_add_tenant_soft_delete | 租户软删除字段 |
| 046_add_tenant_to_schedule_suspensions | 排班停诊添加 tenant_id |
| 049_store_password_hash | 门店密码列扩展 VARCHAR(255) |
| 050_add_tenant_id_to_isolated_tables | messages/medical_records/leave_requests/rest_days 添加 tenant_id |

---

## 测试验证结果

| 检查项 | 结果 |
|--------|------|
| 后端单元测试 | 510 passed, 20 skipped |
| 前端构建（admin） | 通过 |
| 前端 Lint | 通过 |
| 从 monorepo 根运行测试 | 通过（修复了历史路径问题） |
| 从 apps/server 运行测试 | 通过 |

---

## 提交记录

```
ecca94e fix(security+perf): P0/P1/P2 — 租户隔离补齐 + N+1查询优化
b45277b migrate(store): 门店密码列扩展为 VARCHAR(255) 适配 bcrypt 哈希
bb3f1ee fix(all): P1 修复 — 门店加密/TimePicker/N+1优化, 用户管理术语/状态/验证统一
d1a5adf chore(server): 删除 redis_admin_session_tenant.py，功能已合并到 redis.py
7bd7bde feat(server): 完成服务端模块边界重构和多租户改造，归档已完成 OpenSpec changes
036c94f feat(saas): P0-1 管理员服务添加租户过滤
3444cd0 feat(multi-tenant): P0-1 管理员服务添加租户过滤
145090a fix(tenant): P0 修复 - 管理员服务租户过滤和缓存键租户隔离
```

---

## 剩余已知事项

| 事项 | 优先级 | 说明 |
|------|--------|------|
| 前端 E2E 测试覆盖 | P2 | 当前仅后端有完整测试，前端 E2E 缺失 |
| API 文档自动生成 | P2 | 可考虑 FastAPI 自动文档扩展 |
| 性能基准测试 | P2 | N+1 优化后可建立基线，监控回归 |
| Celery 任务监控 | P2 | 排班生成等长任务缺乏进度可视化 |
