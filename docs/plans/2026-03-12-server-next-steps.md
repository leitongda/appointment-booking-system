# Server Refactor Next Steps

## 当前状态

已完成的核心工作：

- `app/api/v1` 主要业务入口已迁到 `app/modules/*`
- `app/common`、`app/infrastructure` 骨架已建立
- 大部分高优先级和中优先级 `app/services/*` 已拆分为模块实现或基础设施适配
- `services/storage/*`、`services/appointment_service.py`、`services/patient_service.py` 兼容层已删除
- `content`、`booking_notices`、`store_email_recipients` 的兼容测试已补齐
- 运行期目录已统一到 `apps/server/var/server/*`
- 文档、OpenSpec、todo 已完成主干同步，后续仍需持续复核
- **注册层已收缩完成** (2026-03-12)
  - `ROUTER_REGISTRATIONS` 直连 `app.modules.*`
  - 删除全部 38 个 `api/v1/*.py` wrapper
  - 只保留 `api/v1/__init__.py` 作为路由注册层

## 下一步优先级

### 1. 模块内部继续拆细

可选优化（非阻塞）：

- `admin` 再拆细：`router_auth` / `router_admins` / `router_roles` / `router_monitoring` 内部继续减小文件
- `doctor_portal` 再拆细：分成 `profile`、`schedules`、`appointments`、`queue`、`history`、`follow_up`
- `import_export` 再拆细：分成 `export`、`template`、`import` 子 router

### 2. 补充行为测试

- `patients` 模块补 service 行为测试，覆盖黑名单、家庭成员、积分、删除约束
- `appointments` 模块补取消、过号、复诊、队列查询等更全的行为测试
- 补 `async_client` 级别的集成测试，覆盖登录、鉴权、分页、权限失败场景

### 3. 基础设施层补充

- 如有需要，补 `cache/redis` 适配层而不是直接在业务中使用 `RedisCache`

### 4. 最终验收

- [x] 全量单测通过 (186 passed)
- [x] 关键集成测试通过
- [x] `api/v1` 中已迁移文件全部保持薄包装 → 已删除全部 wrapper
- [ ] 新功能开发不再向旧大文件追加代码
- [ ] 文档、OpenSpec、代码结构三者一致

## 最关键的约束

- 不改变对外 API 路径
- 不改变现有请求/响应结构
- 每一批删除后都必须跑测试
- 没有内部引用清干净之前，不删除对应兼容层

---

## 任务分配计划 (2026-03-12)

### Team 1: 模块拆分组（并行执行）

| Task ID | 任务 | 目标文件 | 当前行数 | 拆分方案 |
|---------|------|----------|----------|----------|
| #1 | 拆分 import_export | `router.py` | 1071 | `router_export`, `router_import`, `router_template` |
| #2 | 拆分 appointments | `router.py` | 942 | `router_booking`, `router_flow`, `router_query` |
| #3 | 拆分 doctor_portal | `router.py` | 689 | `router_profile`, `router_schedules`, `router_appointments`, `router_queue`, `router_history`, `router_follow_up` |
| #4 | 拆分 admin/router_auth | `router_auth.py` | ~500 | `router_auth_login`, `router_auth_token`, `router_auth_password` |

### Team 2: 测试补充组（并行执行）

| Task ID | 任务 | 测试范围 | 依赖 |
|---------|------|----------|------|
| #5 | patients 模块测试 | 黑名单、家庭成员、积分、删除约束 | 无 |
| #6 | appointments 模块测试 | 取消、过号、复诊、队列查询 | Task #2 |
| #7 | async_client 集成测试 | 登录、鉴权、分页、权限边界 | 无 |

### Team 3: 基础设施组

| Task ID | 任务 | 输出 |
|---------|------|------|
| #8 | cache/redis 适配层 | `app/infrastructure/cache/` |

### Team 4: 最终验收组

| Task ID | 任务 | 依赖 |
|---------|------|------|
| #9 | 文档一致性验证 | #1, #2, #3, #4, #8 |

### 执行顺序

```
Phase 1 (并行):
  ├── Task #1: 拆分 import_export
  ├── Task #2: 拆分 appointments ─────────┐
  ├── Task #3: 拆分 doctor_portal          │
  ├── Task #4: 拆分 admin/router_auth      │
  ├── Task #5: patients 测试               │
  ├── Task #7: async_client 集成测试       │
  └── Task #8: cache/redis 适配层          │
                                           │
Phase 2 (等待 Phase 1 完成):               │
  └── Task #6: appointments 测试 ◄─────────┘

Phase 3 (等待全部完成):
  └── Task #9: 文档一致性验证
```

### 验收标准

每个拆分任务完成后需：
1. 运行相关单元测试确保通过
2. 运行相关集成测试确保通过
3. 确认 API 路径未改变
4. 更新模块 `__init__.py` 导出

---

## 执行日志

### 2026-03-12 15:41 - 第一批并行执行

**尝试并行启动 7 个 agents**，但因 API 速率限制 (429) 全部中断：

| Task ID | 任务 | 状态 | 备注 |
|---------|------|------|------|
| #1 | 拆分 import_export | 429 失败 | 已读取模块结构 |
| #2 | 拆分 appointments | 429 失败 | 已分析 service 层 |
| #3 | 拆分 doctor_portal | 429 失败 | 未开始 |
| #4 | 拆分 admin/router_auth | 429 失败 | 已读取文件 |
| #5 | 补充 patients 测试 | 进行中 | 正在分析模型 |
| #7 | async_client 集成测试 | 权限拒绝 | Write 被禁止 |
| #8 | cache/redis 适配层 | 429 失败 | 已分析 infrastructure |

**教训**：并行启动过多 agents 会触发速率限制，建议每次最多 1-2 个。

### 下一步

- 等待速率限制解除后逐个重试
- 或由主 agent 直接执行任务（不启动子 agent）
