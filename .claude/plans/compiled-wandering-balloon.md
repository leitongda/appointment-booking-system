# P1 实施计划：7 项增强功能

## Context

P0 任务（统一消息迁移、WebSocket 患者端、检查报告、排队提醒）已全部完成。P1 阶段聚焦于：清理技术债（admin-v2 归档）、补齐业务功能（家庭成员、留存统计、智能导诊、消息推送）、强化质量保障（E2E 测试、多租户安全测试）。

## 依赖关系

```
P1-1 (admin-v2 归档)        ── 独立，无依赖
P1-2 (留存率/复诊率统计)      ── 独立
P1-3 (家庭成员角色分类)       ── 独立
P1-4 (H5 消息推送增强)       ── 依赖 P0-2 (WebSocket 患者端) ✓ 已完成
P1-5 (智能导诊)              ── 独立
P1-6 (E2E 用户旅程测试)      ── 依赖 P0-3/P0-4 完成 ✓
P1-7 (多租户隔离安全测试)     ── 独立
```

**执行顺序**：P1-1 → P1-3 → P1-2 → P1-4 → P1-5 → P1-6 → P1-7

---

## P1-1: admin-v2 归档（2h）

**目标**：移除实验性 admin-v2 应用，减少维护负担。

### 变更

| 操作 | 说明 |
|------|------|
| `git rm -r apps/admin-v2/` | 删除整个目录 |
| `pnpm-workspace.yaml` | 移除 `apps/admin-v2` 条目 |
| `package.json` (root) | 移除 `dev:admin-v2` / `build:admin-v2` scripts |
| `turbo.json` | 移除 admin-v2 相关 pipeline 配置 |

### 验证
- `pnpm install` 无报错
- `pnpm build` 全量构建成功
- `pnpm dev:admin` 正常启动

---

## P1-2: 用户留存率/复诊率统计（16-24h）

**目标**：数据大屏新增留存率和复诊率指标。

### 现有基础

- `apps/server/app/modules/statistics/router.py` — 已有 `/overview`, `/doctor-stats`, `/department-stats`, `/trend`
- `apps/server/app/models/appointment.py` — Appointment 模型含 `user_id`, `schedule_date`, `status`
- `VisitTypeService` (`modules/visit_type_configs/`) — 已有 `is_follow_up_visit()` 可复用

### 变更文件

| 文件 | 操作 | 说明 |
|------|------|------|
| `apps/server/app/modules/statistics/router.py` | 修改 | 新增 `/retention` 和 `/revisit-rate` 端点 |
| `apps/server/app/modules/statistics/service.py` | 修改 | 新增留存率/复诊率计算方法 |

### 关键实现

**留存率端点** `GET /statistics/retention`：
- 参数：`store_id`, `start_date`, `end_date`, `cohort` (day/week/month)
- 逻辑：按首次预约时间分组 cohort，统计后续 N 天/周/月内再次预约的用户比例
- SQL：自关联 Appointment 表，`user_id` 匹配 + 日期范围

**复诊率端点** `GET /statistics/revisit-rate`：
- 参数：`store_id`, `doctor_id?`, `department_id?`, `start_date`, `end_date`
- 逻辑：统计同一用户在同一医生/科室的重复就诊比例
- 复用：`VisitTypeService.is_follow_up_visit()` 判断是否复诊

### 验证
- 单元测试：留存率/复诊率计算逻辑
- API 测试：`GET /statistics/retention?store_id=xxx&start_date=2026-01-01&end_date=2026-05-01`

---

## P1-3: 家庭成员角色分类（16-24h）

**目标**：统一家庭成员关系类型，前端常量与后端校验一致。

### 现有基础

- `apps/server/app/models/family_member.py` — `relationship: String(20)`，无后端校验
- `apps/patient-h5/src/pages/family/add.tsx` — 前端常量 `SELF/CHILD/PARENT/SPOUSE/OTHER`
- `apps/patient-miniapp/src/packageProfile/pages/family/add.tsx` — 常量不一致

### 变更文件

| 文件 | 操作 | 说明 |
|------|------|------|
| `apps/server/app/models/family_member.py` | 修改 | 添加 `RELATIONSHIP_CHOICES` 常量 |
| `apps/server/app/schemas/family_member.py` | 修改 | 添加 `Literal` 类型校验 |
| `packages/shared/src/constants/family.ts` | 新建 | 共享关系类型常量 |
| `packages/shared/src/index.ts` | 修改 | 导出家庭成员常量 |
| `apps/patient-h5/src/pages/family/add.tsx` | 修改 | 引用共享常量 |
| `apps/patient-miniapp/src/packageProfile/pages/family/add.tsx` | 修改 | 引用共享常量 |

### 关键实现

**后端常量**：
```python
RELATIONSHIP_CHOICES = {
    "self": "本人",
    "spouse": "配偶",
    "child": "子女",
    "parent": "父母",
    "sibling": "兄弟姐妹",
    "other": "其他",
}
```

**共享前端常量** (`packages/shared/src/constants/family.ts`)：
```typescript
export const FAMILY_RELATIONSHIP_OPTIONS = [
  { value: 'self', label: '本人' },
  { value: 'spouse', label: '配偶' },
  { value: 'child', label: '子女' },
  { value: 'parent', label: '父母' },
  { value: 'sibling', label: '兄弟姐妹' },
  { value: 'other', label: '其他' },
] as const;
```

### 验证
- 后端：创建家庭成员时传入无效 relationship → 422 错误
- 前端：H5 和小程序显示一致的关系选项
- 回归：已有家庭成员数据不受影响

---

## P1-4: H5 消息推送增强（16-24h）

**目标**：利用已有的 WebSocket 患者端基础设施，增强 H5 消息中心的实时能力。

### 现有基础

- `apps/patient-h5/src/hooks/usePatientWebSocket.ts` — P0-2 已完成，支持 `onNewMessage` 回调
- `apps/patient-h5/src/pages/message/index.tsx` — 消息中心页面，当前轮询刷新
- `apps/server/app/modules/unified_message/service.py` — `_notify_new_message()` 已支持 WebSocket 推送

### 变更文件

| 文件 | 操作 | 说明 |
|------|------|------|
| `apps/patient-h5/src/pages/message/index.tsx` | 修改 | 集成 WebSocket，新消息实时插入列表 |
| `apps/patient-h5/src/hooks/usePatientWebSocket.ts` | 修改 | 增加 `onMessageRead` 回调支持 |
| `apps/patient-h5/src/components/MessageBadge/index.tsx` | 新建 | 未读消息角标组件（全局使用） |

### 关键实现

**消息中心实时更新**：
- 页面挂载时连接 WebSocket，监听 `onNewMessage`
- 收到新消息 → 插入列表顶部 + 未读计数 +1
- 页面卸载时断开连接

**未读角标组件**：
- 从 WebSocket 或 API 获取未读数
- 显示在 NavBar 右上角或 TabBar 图标上
- 支持 `max` 参数（显示 `99+`）

### 验证
- 发送站内信 → H5 消息中心实时显示新消息
- 角标组件：未读数 > 0 时显示，= 0 时隐藏

---

## P1-5: 智能导诊 - 关键词匹配版（24-32h）

**目标**：患者输入症状关键词，推荐匹配科室。

### 变更文件

| 文件 | 操作 | 说明 |
|------|------|------|
| `apps/server/app/models/department.py` | 修改 | 新增 `keywords` JSON 字段 |
| `apps/server/app/modules/departments/router.py` | 修改 | 新增 `/departments/symptom-match` 端点 |
| `apps/server/app/modules/departments/service.py` | 修改 | 新增关键词匹配逻辑 |
| `apps/server/migrations/versions/099_add_department_keywords.py` | 新建 | 迁移：添加 keywords 列 |
| `apps/patient-h5/src/pages/guide/index.tsx` | 新建 | 导诊页面（搜索框 + 结果列表） |
| `packages/api/src/modules/department.ts` | 修改 | 新增 `symptomMatch()` API |

### 关键实现

**Department 模型扩展**：
```python
keywords = Column(JSON, nullable=True)  # ["头痛", "偏头痛", "头晕", ...]
```

**匹配端点** `GET /departments/symptom-match?q=头痛`：
- 全文匹配：`keywords` JSON 数组包含查询词
- 结果排序：匹配关键词数量 > 科室名称匹配
- 返回：科室列表 + 匹配的关键词 + 推荐理由

**导诊页面**：
- 搜索框：输入症状描述（如"头疼"、"咳嗽"）
- 结果：推荐科室卡片（名称 + 匹配关键词 + 描述）
- 点击科室 → 跳转医生列表

### 验证
- `GET /departments/symptom-match?q=头痛` 返回神经内科
- `GET /departments/symptom-match?q=咳嗽` 返回呼吸内科
- 无匹配时返回空列表

---

## P1-6: 端到端用户旅程测试（16-24h）

**目标**：覆盖核心用户旅程的 E2E 测试。

### 变更文件

| 文件 | 操作 | 说明 |
|------|------|------|
| `apps/patient-h5/e2e/appointment.spec.ts` | 新建 | 预约全流程测试 |
| `apps/patient-h5/e2e/family.spec.ts` | 新建 | 家庭成员管理测试 |
| `apps/patient-h5/e2e/message.spec.ts` | 新建 | 消息中心测试 |
| `apps/admin/e2e/schedule.spec.ts` | 新建 | 排班管理测试 |
| `apps/server/tests/integration/test_queue_flow.py` | 新建 | 排队流程集成测试 |

### 测试场景

**预约全流程**（patient-h5）：
1. 浏览科室 → 选择医生 → 选择时段 → 确认预约 → 查看详情 → 取消预约

**排队流程**（integration）：
1. 创建预约 → 签到 → 医生叫号 → 患者收到通知 → 完成就诊

**家庭成员**（patient-h5）：
1. 添加家庭成员 → 编辑 → 删除 → 切换就诊人

### 验证
- `pnpm test:e2e` 全部通过
- 后端集成测试 `pytest tests/integration/test_queue_flow.py` 通过

---

## P1-7: 多租户隔离安全性测试（24-40h）

**目标**：验证租户数据隔离无漏洞。

### 变更文件

| 文件 | 操作 | 说明 |
|------|------|------|
| `apps/server/tests/security/test_tenant_isolation.py` | 新建 | 租户隔离安全测试套件 |
| `apps/server/tests/security/__init__.py` | 新建 | 包初始化 |

### 测试场景

**数据隔离**：
- 租户 A 不能查询租户 B 的预约/排班/医生/科室
- 租户 A 不能修改租户 B 的数据
- 无 tenant_id 的请求被拒绝

**存储隔离**：
- 租户 A 不能访问租户 B 的文件路径
- 文件上传路径包含 tenant_id

**缓存隔离**：
- Redis key 包含 tenant_id 前缀
- 租户 A 缓存不影响租户 B

**WebSocket 隔离**：
- 患者 WebSocket 只接收自己租户的消息
- 医生 WebSocket 同理

### 验证
- `pytest tests/security/test_tenant_isolation.py -v` 全部通过
- 覆盖率：核心 CRUD 接口 100% 租户过滤

---

## 全局验证

```bash
# 后端测试
cd apps/server
pytest tests/unit/ -v
pytest tests/integration/ -v
pytest tests/security/ -v

# 前端构建
pnpm build

# 前端 E2E
pnpm test:e2e
```
