# 统一消息中心迁移 — 自适应多智能体研究画布

> 协作模式：集中调度
> 日期：2026-05-15
> 审查目标：统一消息中心迁移下一步行动计划

---

## 模式选择

**选定模式：** 集中调度

**选择理由：** "下一步"是规划问题，需要快速收敛到可执行的行动计划。无明确主导领域，已有清晰待办清单，主要价值在优先级排序和成本估算。

---

## Round 1：事实层（只写事实，不评价）

### PM — 产品视角

**产品定位：**
- 全栈医院预约挂号系统，SaaS 多租户架构
- 支持多门店/分院、多科室、多医生排班预约
- 消息中心是子系统之一，负责预约/就诊/排班/停诊/系统/反馈 6 种通知

**功能完成度：**
- 消息类型定义：6 种类型已定义（appointment, consultation, schedule, system, stop_clinic, feedback）
- 患者端 Tab：4 个（全部/预约/就诊/系统），缺 stop_clinic/feedback/schedule 独立 Tab
- 医生端 Tab：4 个（全部/排班/预约/系统），缺 consultation/stop_clinic/feedback 独立 Tab
- 管理端：展示全部 6 种类型，支持发送消息
- 小程序端：无独立消息中心页面
- 模板管理：后端 API 存在（CRUD），前端无管理页面
- 批量发送：后端 API 存在，前端无入口
- 通知设置：患者端和医生端有通知偏好设置页，管理端无

**目标用户线索：**
- 三类用户：患者（patient-h5/miniapp）、医生（doctor）、管理员（admin）
- API 层面统一，三端共用同一套 `/messages` 接口
- 当前所有 API 均调用旧 `MessageService`，未切换到 `UnifiedMessageService`

---

### Designer — 用户视角

**页面清单与结构：**
- admin：消息列表页（ProTable）、发送消息页（ProForm）、通知按钮（Popover）、通知日志页
- patient-h5：消息中心页（全屏 + PullToRefresh + InfiniteScroll + SwipeAction）、通知设置页
- doctor：消息中心页（PageContainer + List + WebSocket）、通知设置页
- 无跨端共享消息 UI 组件

**交互模式统计：**
- 通知面板：admin 用 Popover，其他端为全屏页面
- 未读数更新：admin 60 秒轮询，doctor WebSocket 实时，patient-h5 页面刷新时更新
- 标记全部已读：patient-h5/doctor/miniapp 有二次确认，admin 无确认
- 删除消息：patient-h5 左滑删除，admin Dropdown 菜单，doctor 直接删除链接，小程序无删除
- 时间格式化：5 种不同实现（dayjs fromNow、自定义函数、shared formatRelativeTime）

**组件一致性事实：**
- 类型定义通过 `@hospital/shared` 共享（Message, UnreadCount, MessageType）
- Tab 常量通过 `packages/shared/src/constants/message.ts` 共享
- admin 端 NotificationButton 有独立的 Message 接口（types.ts），未使用共享类型
- 各端时间格式化、未读标记视觉、操作交互均独立实现

---

### Engineer — 技术视角

**存储层事实：**
- 旧表：messages, message_templates, notification_logs, notification_preferences, email_templates
- 新表：notification_groups, notification_recipients, notification_deliveries, unified_templates, channel_strategies, recipient_rules
- Alembic migration 084 已创建，未执行
- 数据迁移脚本已创建，未执行（支持 --dry-run/--execute/--verify）
- notification_preferences 表缺少 consultation_enabled 和 feedback_enabled 列

**核心引擎事实：**
- UnifiedMessageService.send() 8 步流程：去重 -> 创建组 -> 创建接收人 -> 获取渠道 -> 偏好过滤 -> 渲染 -> 发送 -> 记录
- 双层去重：Redis SET NX EX（24h TTL）+ DB dedup_key unique
- 5 个渠道：in_app, wechat, sms, email, websocket
- 渠道策略：event.channels > channel_strategies 表 > _DEFAULT_CHANNEL_STRATEGY 字典

**依赖和模块耦合事实：**
- MessageServiceCompat 已创建但未被任何模块导入/实例化
- 规则引擎（RecipientRule）模型已定义但未接入发送流程
- Celery 任务中已集成统一消息分支（_should_use_unified + _send_via_unified）
- 业务模块通过 `self._compat("MessageService", MessageService)` 获取服务实例（DI 机制）

---

## Round 2：辩论层

### 简化投票矩阵（集中调度模式）

| 议题 | 裁决者立场 | Critic 质询 | 最终裁决 |
|------|-----------|------------|---------|
| notification_preferences 缺列优先级 | P0 | 实际是 fail-open，非数据丢失 | 降级为 P1 |
| compat.py 接入方案 | 替换导入 | 需理解 _compat() DI 机制 | 修正方案 |
| 规则引擎优先级 | Phase 2 | 半成品代码认知负担 | 保持 Phase 2，加 TODO 注释 |
| 执行顺序 | 补列 -> migration -> 接入 | migration 084 应先执行 | 修正顺序 |
| 灰度策略 | 全局 migration + 按租户 feature flag | 全局 vs 灰度矛盾 | 确认为"全局基础设施 + 按租户路由" |

### Critic 质询（9 个普通 + 3 个关键）

**普通质询：**

1. **[Critic -> 全体] notification_preferences 缺列的实际严重性被高估**
   - 论据：`notification_preference.py:73-75` 异常处理返回 `True`（fail-open），consultation/feedback 类型通知实际不会被过滤，而是无法被用户关闭
   - 要求回应：PM 确认触发频率，Engineer 确认 fail-open 是否有意设计
   - 级别：普通

2. **[Critic -> 全体] compat.py 接入方案与 DI 机制不匹配**
   - 论据：`service_booking.py:281` 使用 `self._compat("MessageService", MessageService)`，非直接导入
   - 要求回应：Engineer 确认 `_compat()` 机制
   - 级别：普通

3. **[Critic -> 全体] RecipientRule 半成品代码认知负担**
   - 论据：模型已定义、表已创建，但 service.py 完全不引用，非 YAGNI 而是"建了没用"
   - 要求回应：确认是否在 Phase 1 migration 中一并创建
   - 级别：普通

4. **[Critic -> 全体] 5 渠道注册 vs 可用**
   - 论据：wechat/sms/email 依赖外部配置，画布未验证是否已配置
   - 要求回应：Engineer 确认渠道可用性
   - 级别：普通

5. **[Critic -> 全体] admin 端类型不一致的运行时风险**
   - 论据：form.tsx 使用 reminder/notice，后端 MessageType 是严格枚举，Pydantic 会拒绝非法值
   - 要求回应：确认后端验证行为
   - 级别：普通

6. **[Critic -> 全体] 数据迁移回滚方案缺失**
   - 论据：migration 084 downgrade 可行性、数据迁移中断恢复、compat 回退路径均未讨论
   - 要求回应：补充完整回滚方案
   - 级别：普通

7. **[Critic -> 全体] Celery 分支测试覆盖未验证**
   - 论据：_send_via_unified 分支是否被测试覆盖，feature flag 意外启用的防御机制
   - 要求回应：确认测试状态
   - 级别：普通

8. **[Critic -> 全体] 小程序端优先级缺少用户数据**
   - 论据：小程序是否上线、用户量多少均未知
   - 要求回应：PM 确认上线状态
   - 级别：普通

9. **[Critic -> 全体] 竞品对比标准缺失**
   - 论据：无外部参照物评估迁移完成质量
   - 要求回应：明确评估标准是内部需求还是行业对标
   - 级别：普通

**关键质询：**

**🚨 A. [Critic -> 全体] 执行顺序隐含依赖未识别**
   - 论据：migration 084 创建新表是所有后续操作的基础，应先于补列执行
   - 要求回应：确认 migration 084 和 085 的依赖关系
   - 级别：🚨 关键

**🚨 B. [Critic -> 全体] 灰度发布策略与全局迁移的矛盾**
   - 议据：migration 和数据迁移是全局操作，feature flag 是按租户的，两者逻辑矛盾
   - 要求回应：明确迁移策略
   - 级别：🚨 关键

**🚨 C. [Critic -> 全体] 双写期间数据一致性未讨论**
   - 论据：compat.py 接入后新旧服务并行写入，新服务失败时返回 None，查询仍指向旧服务
   - 要求回应：设计数据一致性保障方案
   - 级别：🚨 关键

### 🚨 Critic 关键质询追踪

| # | 关键质询内容 | 裁决回应 | 处置 |
|---|------------|---------|------|
| A | 执行顺序隐含依赖 | 确认：migration 084 先于补列。两者技术独立（不同表），但 084 是基础 | 修正执行顺序 |
| B | 灰度策略矛盾 | 确认为"全局基础设施 + 按租户路由"模式：表结构全局创建，流量按租户 feature flag 路由。这是 SaaS 灰度发布的标准模式 | 记录策略 |
| C | 双写期间数据一致性 | 确认：compat.py 应实现"新服务失败时降级到旧服务"，查询接口在数据验证完成后统一切换（Phase 2） | 修改 compat.py |

---

## Round 3：共识层

### ✅ 共识项

1. **Alembic migration 084 执行（最高优先级）**
   **结论：** 6 张新表是所有后续操作的基础，必须先执行
   **建议行动：** 启动 Docker，执行 `alembic upgrade head`
   **成本估算：** 0.5h
   **优先级：** P0

2. **notification_preferences 补列**
   **结论：** consultation_enabled 和 feedback_enabled 列缺失，实际效果是"这两种类型通知无法被用户禁用"（fail-open），非数据丢失
   **建议行动：** 创建 migration 085 补充两列（默认 True），确保用户可以关闭这两种通知
   **成本估算：** 1h
   **优先级：** P1（Critic 质询后从 P0 降级）

3. **compat.py 接入业务层（修正方案）**
   **结论：** 业务模块使用 `self._compat("MessageService", MessageService)` DI 机制，非直接导入。需修改 `_compat()` 注册逻辑或在 DI 容器中注册 MessageServiceCompat
   **建议行动：**
   - 方案 A：修改 `_compat()` 方法，当 feature flag 启用时返回 MessageServiceCompat
   - 方案 B：在 DI 容器中注册 MessageServiceCompat 为 MessageService 的替代
   - 兼容层应实现"新服务失败时降级到旧服务"逻辑
   **成本估算：** 3h（含降级逻辑实现）
   **优先级：** P0

4. **admin form.tsx 类型对齐**
   **结论：** form.tsx 使用 reminder/notice 而非后端定义的 6 种类型。后端 Pydantic 使用严格枚举验证，会拒绝非法值返回 400 错误
   **建议行动：** 修改 TYPE_OPTIONS 为：system, appointment, consultation, schedule, stop_clinic, feedback
   **成本估算：** 0.5h
   **优先级：** P1

5. **数据迁移脚本执行**
   **结论：** 脚本已就绪，支持断点续传。需在 migration 084 之后执行
   **建议行动：** dry-run -> execute -> verify 三步走
   **成本估算：** 1h
   **优先级：** P1

6. **RecipientRule 模型保留但标记为 Phase 2**
   **结论：** 模型已定义、表已创建，但服务层未接入。保留模型（避免 migration 回滚），在 service.py 中添加 TODO 注释说明 Phase 2 接入计划
   **建议行动：** 在 service.py 的 send() 方法中添加 TODO 注释
   **成本估算：** 0.1h
   **优先级：** P2

### ⚡ 分歧项

1. **三端 UI 统一范围**
   **各方立场：**
   - PM：类型定义必须统一，交互可保留差异
   - Designer：交互差异合理（移动端 vs 桌面端），但类型 Tag 颜色应统一
   - Engineer：共享类型已统一，admin 端 types.ts 需改为使用共享类型
   **裁决/建议：** 仅对齐类型定义和 Tag 颜色映射，不统一交互模式
   **决策依据：** 各端交互差异符合平台特性（移动端滑动 vs 桌面端菜单）

---

## 被低估的优势

1. **双层去重机制已就绪**：Redis + DB dedup_key 双保险，迁移后可立即生效
2. **Celery 任务已集成**：_should_use_unified + _send_via_unified 分支已写好，feature flag 开启即可切换
3. **DI 机制支持平滑切换**：`_compat()` 工厂方法允许在不修改业务代码的情况下切换服务实现

---

## 行动计划（按执行顺序排序）

| 顺序 | 优先级 | 行动 | 成本 | 价值 | 负责 | 状态 |
|------|--------|------|------|------|------|------|
| 1 | P0 | Alembic migration 084 执行 | 0.5h | 高 | Engineer | 待执行 |
| 2 | P0 | compat.py 接入业务层 + 降级逻辑 | 3h | 高 | Engineer | 待执行 |
| 3 | P1 | notification_preferences 补列 | 1h | 中 | Engineer | 待执行 |
| 4 | P1 | admin form.tsx 类型对齐 | 0.5h | 中 | Engineer | 待执行 |
| 5 | P1 | 三端 Tab 配置统一（6 种类型） | 2h | 中 | Engineer | 待执行 |
| 6 | P1 | 数据迁移脚本 dry-run + execute | 1h | 中 | Engineer | 待执行 |
| 7 | P1 | 单元测试验证 | 0.5h | 中 | Engineer | 待执行 |
| 8 | P2 | RecipientRule TODO 注释 | 0.1h | 低 | Engineer | 待执行 |
| 9 | P2 | 小程序端消息中心页面 | 8h | 中 | Designer + Engineer | 待执行 |
| 10 | P2 | 规则引擎实现 | 4h | 中 | Engineer | Phase 2 |
| 11 | P2 | 模板管理 UI | 8h | 中 | Designer + Engineer | Phase 2 |

### P0：立即执行（高价值、低成本）

1. **Alembic migration 084 执行**
   - 启动 Docker：`docker-compose up -d postgres redis`
   - 执行：`cd apps/server && alembic upgrade head`
   - 验证：确认 6 张新表已创建
   - 回滚：`alembic downgrade 083`（新表为空时可安全回滚）

2. **compat.py 接入业务层 + 降级逻辑**
   - 研究 `_compat()` DI 机制的定义位置和注册逻辑
   - 修改 DI 配置，使 MessageServiceCompat 成为 MessageService 的替代
   - 在 compat.py 中实现降级逻辑：新服务失败时 fallback 到旧服务
   - 测试验证：feature flag=False 走旧服务，True 走新服务，新服务失败时降级

### P1：本轮迭代

1. **notification_preferences 补列**
   - 创建 migration 085：ALTER TABLE notification_preferences ADD COLUMN consultation_enabled BOOLEAN DEFAULT TRUE, ADD COLUMN feedback_enabled BOOLEAN DEFAULT TRUE
   - 测试验证：确认 consultation/feedback 类型偏好查询正常

2. **admin form.tsx 类型对齐**
   - 修改 TYPE_OPTIONS 为后端 MessageType 枚举值
   - 测试验证：确认发送消息功能正常

3. **数据迁移脚本执行**
   - dry-run：`python scripts/migrate_unified_message.py --dry-run`
   - execute：`python scripts/migrate_unified_message.py --execute`
   - verify：`python scripts/migrate_unified_message.py --verify`

4. **单元测试验证**
   - 运行：`pytest tests/unit/test_unified_message.py tests/unit/test_api_contract.py -v`
   - 运行：`pytest tests/unit/test_notification_dispatcher.py -v`
   - 运行：`pytest tests/unit/test_message_service.py -v`

### P2：下个周期规划

1. **RecipientRule TODO 注释**
   - 在 service.py send() 方法中添加 TODO，说明 Phase 2 将接入规则引擎

2. **规则引擎实现**
   - 在 UnifiedMessageService.send() 中接入 RecipientRule 解析
   - 成本：4h

3. **模板管理 UI**
   - admin 端新增模板列表页、创建/编辑表单
   - 成本：8h

### 用户已确认

1. **三端 Tab 配置统一** — 用户确认：统一为全部 6 种类型
   - 修改 `packages/shared/src/constants/message.ts`：PATIENT_MESSAGE_TABS 和 DOCTOR_MESSAGE_TABS 统一为 6 种类型
   - 成本：2h
   - 优先级：P1

2. **小程序端消息中心页面** — 用户确认：需要
   - 新建 Taro 页面，复用 patient-h5 交互模式
   - 成本：8h
   - 优先级：P2

---

## 迁移策略说明

**"全局基础设施 + 按租户路由"模式：**

1. **全局操作**（影响所有租户）：
   - Alembic migration 创建新表（表结构对所有租户可见）
   - 数据迁移脚本复制旧数据到新表

2. **按租户操作**（feature flag 控制）：
   - `beta_unified_message` 特性标志决定每个租户使用新服务还是旧服务
   - 兼容层 `MessageServiceCompat` 在运行时检查 feature flag，路由到对应服务

3. **回滚路径**：
   - 关闭 feature flag -> 所有租户回退到旧服务
   - 新表数据保留（不影响旧服务运行）
   - 如需完全回滚：`alembic downgrade 083` 删除新表

---

## 摘要

**使用模式：** 集中调度

**关键共识：**
- 6 项达成共识（migration 084、补列、compat 接入、类型对齐、数据迁移、RecipientRule 标记）

**关键分歧：**
- 1 项需要决策者介入（三端 Tab 统一）

**Top 3 P0 行动：**
1. Alembic migration 084 执行（0.5h）— 创建 6 张新表，所有后续操作的基础
2. compat.py 接入业务层 + 降级逻辑（3h）— 让兼容层真正生效，实现灰度切换
3. notification_preferences 补列（1h）— 确保用户可以关闭 consultation/feedback 通知

**Critic 关键洞察：**
- notification_preferences 缺列是 fail-open（无法禁用），非数据丢失，优先级从 P0 降为 P1
- compat.py 接入需理解 _compat() DI 机制，非简单替换导入
- 灰度策略是"全局基础设施 + 按租户路由"，非纯粹的按租户灰度

---

## 附录：模式切换日志

| 时间 | 从 | 到 | 原因 |
|------|-----|-----|------|
| - | - | - | 未发生模式切换 |
