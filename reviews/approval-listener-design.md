# 审批流监听器设计方案

> 日期：2026-06-25
> 模式：集中调度
> 目标：为审批流设计器添加全局监听和执行监听能力

---

## 一、现状分析

### 已有能力

| 能力 | 状态 | 位置 |
|------|------|------|
| 节点级配置 | 有（审批模式、负责人、超时） | PropertyPanel |
| 流程级回调 | 有（硬编码） | `callback_registry.py` |
| 通知推送 | 有（WebSocket + Celery） | `approval_task.py` |
| Webhook | 无 | — |
| 节点生命周期事件 | 无 | — |
| 全局流程事件 | 无 | — |

### 缺口

1. **执行监听**：无法在节点进入/完成/离开时触发自定义动作
2. **全局监听**：无法在流程启动/结束/取消时触发跨节点动作
3. **Webhook**：无法向外部系统发送 HTTP 回调
4. **UI 配置**：所有回调逻辑硬编码，无法通过设计器配置

---

## 二、设计目标

参照 Camunda/Flowable 的 BPMN 监听器模型，结合本项目轻量化特点：

- **执行监听（Execution Listener）**：绑定到单个节点，监听节点生命周期事件
- **全局监听（Global Listener）**：绑定到流程定义，监听流程级事件
- **配置方式**：通过设计器 UI 配置，存储在节点/流程 JSON 数据中
- **执行方式**：后端引擎在对应事件点触发，支持多种动作类型

---

## 三、事件类型定义

### 3.1 执行监听事件（节点级）

| 事件 | 触发时机 | 适用节点类型 |
|------|---------|-------------|
| `start` | 节点开始执行前 | approval, cc, condition |
| `end` | 节点执行完成后 | approval, cc, condition |
| `take` | 边被遍历时 | edge（连接线） |

### 3.2 任务监听事件（审批节点专用）

| 事件 | 触发时机 | 适用节点类型 |
|------|---------|-------------|
| `create` | 审批任务创建时 | approval |
| `assignment` | 审批任务分配时 | approval |
| `complete` | 审批任务完成时 | approval |
| `timeout` | 审批超时时 | approval（已有超时机制，需对接） |

### 3.3 全局监听事件（流程级）

| 事件 | 触发时机 |
|------|---------|
| `process.start` | 流程实例启动时 |
| `process.end` | 流程实例正常结束时 |
| `process.cancel` | 流程实例被取消时 |
| `process.reject` | 流程实例被驳回时 |

---

## 四、动作类型定义

| 动作类型 | 说明 | 配置字段 |
|---------|------|---------|
| `webhook` | 向指定 URL 发送 HTTP POST 请求 | `url`, `headers`, `bodyTemplate` |
| `notification` | 发送站内通知 | `targetType` (role/user), `targetIds`, `template` |
| `sms` | 发送短信通知 | `phoneField`, `template` |
| `callback` | 调用已注册的 Python 回调函数 | `callbackName` |

> 注：不支持 `class` 和 `script` 类型（本项目非 Java 引擎，且脚本执行有安全风险）

---

## 五、数据模型

### 5.1 Listener 接口定义

```typescript
// packages/shared/src/types/approval.ts

/** 监听器动作类型 */
export type ListenerActionType = 'webhook' | 'notification' | 'sms' | 'callback';

/** 执行监听事件类型 */
export type ExecutionEvent = 'start' | 'end' | 'take';

/** 任务监听事件类型 */
export type TaskEvent = 'create' | 'assignment' | 'complete' | 'timeout';

/** 全局监听事件类型 */
export type GlobalEvent = 'process.start' | 'process.end' | 'process.cancel' | 'process.reject';

/** 监听器事件类型 = 执行事件 + 任务事件 + 全局事件 */
export type ListenerEvent = ExecutionEvent | TaskEvent | GlobalEvent;

/** 单个监听器配置 */
export interface ListenerConfig {
  id: string;
  event: ListenerEvent;
  actionType: ListenerActionType;
  /** 动作参数，结构取决于 actionType */
  actionConfig: WebhookConfig | NotificationConfig | SmsConfig | CallbackConfig;
  /** 监听器名称（可选，便于识别） */
  label?: string;
}

export interface WebhookConfig {
  url: string;
  headers?: Record<string, string>;
  bodyTemplate?: string;  // 支持 {{instanceId}}, {{nodeKey}} 等变量
  timeout?: number;       // 超时秒数，默认 10
  retryCount?: number;    // 重试次数，默认 3
}

export interface NotificationConfig {
  targetType: 'role' | 'user';
  targetIds: string[];
  titleTemplate?: string;
  contentTemplate?: string;
}

export interface SmsConfig {
  phoneField: string;     // 表单数据中的手机号字段名
  templateCode?: string;  // 短信模板编码
  templateParams?: Record<string, string>;
}

export interface CallbackConfig {
  callbackName: string;   // 对应 callback_registry 中注册的名称
}
```

### 5.2 存储结构

**节点级执行监听** — 存储在 `ApprovalFlowNode` 表的 JSON 字段中：

```json
// ApprovalFlowNode.listeners (新增 JSON 字段)
[
  {
    "id": "listener_1",
    "event": "start",
    "actionType": "webhook",
    "actionConfig": {
      "url": "https://api.example.com/hooks/approval-start",
      "bodyTemplate": "{\"node\": \"{{nodeKey}}\", \"instance\": \"{{instanceId}}\"}"
    },
    "label": "通知外部系统"
  }
]
```

**全局监听** — 存储在 `ApprovalFlowDefinition` 表的 JSON 字段中：

```json
// ApprovalFlowDefinition.global_listeners (新增 JSON 字段)
[
  {
    "id": "gl_1",
    "event": "process.start",
    "actionType": "notification",
    "actionConfig": {
      "targetType": "role",
      "targetIds": ["admin"],
      "titleTemplate": "新审批流程启动",
      "contentTemplate": "{{applicantName}} 发起了 {{flowName}}"
    },
    "label": "通知管理员"
  }
]
```

### 5.3 数据库变更

```python
# apps/server/app/models/approval_flow.py

class ApprovalFlowNode:
    # 新增字段
    listeners = Column(JSON, nullable=True, comment="执行监听器列表")

class ApprovalFlowDefinition:
    # 新增字段
    global_listeners = Column(JSON, nullable=True, comment="全局监听器列表")
```

---

## 六、后端引擎改造

### 6.1 监听器触发服务

新增文件：`apps/server/app/modules/approval_flows/listener_service.py`

```python
class ListenerService:
    """监听器触发服务 — 在引擎事件点调用"""

    async def fire_node_listeners(
        self,
        event: str,          # 'start' | 'end' | 'take'
        node: dict,          # 节点快照数据
        instance: ApprovalInstance,
        db: AsyncSession,
    ):
        """触发节点级执行监听器"""
        listeners = node.get("listeners") or []
        matching = [l for l in listeners if l["event"] == event]
        for listener in matching:
            await self._execute_action(listener, instance, node, db)

    async def fire_global_listeners(
        self,
        event: str,          # 'process.start' | 'process.end' | ...
        flow_def: dict,      # 流程定义数据
        instance: ApprovalInstance,
        db: AsyncSession,
    ):
        """触发全局监听器"""
        listeners = flow_def.get("global_listeners") or []
        matching = [l for l in listeners if l["event"] == event]
        for listener in matching:
            await self._execute_action(listener, instance, None, db)

    async def _execute_action(self, listener, instance, node, db):
        """根据 actionType 分发执行"""
        action_type = listener["actionType"]
        config = listener["actionConfig"]

        if action_type == "webhook":
            await self._fire_webhook(config, instance, node)
        elif action_type == "notification":
            await self._fire_notification(config, instance, node)
        elif action_type == "sms":
            await self._fire_sms(config, instance, node)
        elif action_type == "callback":
            await self._fire_callback(config, instance, db)
```

### 6.2 Webhook 执行

```python
async def _fire_webhook(self, config, instance, node):
    """发送 HTTP POST webhook，带重试"""
    url = self._render_template(config["url"], instance, node)
    body = self._render_template(config.get("bodyTemplate", "{}"), instance, node)
    headers = config.get("headers", {})
    timeout = config.get("timeout", 10)
    retry_count = config.get("retryCount", 3)

    for attempt in range(retry_count):
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    url, content=body, headers=headers, timeout=timeout
                )
                if resp.status_code < 400:
                    return
        except Exception:
            if attempt == retry_count - 1:
                # 记录失败日志，不阻塞主流程
                logger.error(f"Webhook failed after {retry_count} retries: {url}")
```

### 6.3 引擎事件注入点

在 `engine.py` 的关键位置注入监听器调用：

| 引擎方法 | 注入事件 | 监听器类型 |
|---------|---------|-----------|
| `start_instance()` | 流程启动后 | `process.start` (全局) |
| `_advance_to_node()` | 进入节点前 | `start` (执行) |
| `_complete_node()` | 节点完成后 | `end` (执行) |
| `approve()` / `reject()` | 审批任务完成 | `complete` (任务) |
| `_cancel_instance()` | 流程取消 | `process.cancel` (全局) |
| `_reject_instance()` | 流程驳回 | `process.reject` (全局) |

---

## 七、前端 UI 设计

### 7.1 执行监听 — PropertyPanel 扩展

在 PropertyPanel 中为 `approval`、`cc`、`condition` 节点添加"监听器"折叠面板：

```
┌─────────────────────────────┐
│ 节点属性                      │
│─────────────────────────────│
│ 名称: [审批节点          ]    │
│ 审批模式: [会签 ▾]           │
│ ...                          │
│─────────────────────────────│
│ ▶ 监听器 (2)                 │  ← 新增折叠面板
│─────────────────────────────│
│ 删除节点                      │
└─────────────────────────────┘

展开后：
┌─────────────────────────────┐
│ ▼ 监听器 (2)                 │
│─────────────────────────────│
│ ┌─────────────────────────┐ │
│ │ start → Webhook         │ │
│ │ https://api.example.com │ │
│ │              [编辑] [删] │ │
│ └─────────────────────────┘ │
│ ┌─────────────────────────┐ │
│ │ end → 站内通知           │ │
│ │ 通知角色: admin          │ │
│ │              [编辑] [删] │ │
│ └─────────────────────────┘ │
│ [+ 添加监听器]               │
└─────────────────────────────┘
```

### 7.2 全局监听 — 流程设置入口

在设计器工具栏添加"流程设置"按钮，打开 Drawer：

```
┌──────────────────────────────────────────┐
│ 流程设置                                   │
│──────────────────────────────────────────│
│                                          │
│ 全局监听                                   │
│ ┌──────────────────────────────────────┐ │
│ │ process.start → 通知管理员            │ │
│ │ 通知角色: admin, 发起人上级           │ │
│ │                        [编辑] [删除]  │ │
│ └──────────────────────────────────────┘ │
│ ┌──────────────────────────────────────┐ │
│ │ process.end → Webhook                │ │
│ │ https://api.example.com/hooks/end    │ │
│ │                        [编辑] [删除]  │ │
│ └──────────────────────────────────────┘ │
│                                          │
│ [+ 添加全局监听器]                         │
│                                          │
└──────────────────────────────────────────┘
```

### 7.3 监听器编辑弹窗

统一的监听器编辑 Modal：

```
┌─────────────────────────────────────┐
│ 编辑监听器                            │
│─────────────────────────────────────│
│                                     │
│ 名称 (可选): [通知外部系统       ]    │
│                                     │
│ 触发事件: [start ▾]                  │
│   可选: start / end / take           │
│   (全局监听时: process.start / ...)   │
│                                     │
│ 动作类型: [Webhook ▾]                │
│   可选: Webhook / 站内通知 / 短信 /  │
│         回调函数                     │
│                                     │
│ ── Webhook 配置 ──                   │
│ URL: [https://api.example.com  ]    │
│ 请求头:                              │
│   Key: [Authorization     ]         │
│   Value: [Bearer xxx       ]        │
│ 请求体模板:                           │
│ ┌───────────────────────────────┐   │
│ │ {                             │   │
│ │   "node": "{{nodeKey}}",      │   │
│ │   "instance": "{{instanceId}}"│   │
│ │ }                             │   │
│ └───────────────────────────────┘   │
│ 超时(秒): [10]  重试次数: [3]        │
│                                     │
│        [取消]  [确定]                │
└─────────────────────────────────────┘
```

### 7.4 节点视觉标识

在有监听器的节点上显示小圆点标识（与现有 CSS 节点样式兼容）：

```css
/* nodes.css 新增 */
.rf-node__listener-dot {
  position: absolute;
  top: -4px;
  right: -4px;
  width: 8px;
  height: 8px;
  background: #722ed1;
  border-radius: 50%;
  border: 1.5px solid #fff;
}
```

在 `ApprovalNode` 等组件中条件渲染：
```tsx
{d.listeners?.length > 0 && <div className="rf-node__listener-dot" />}
```

---

## 八、transform.ts 适配

### 8.1 fromFlowSchema（后端 → 前端）

```typescript
// 在 fromFlowSchema 中新增
node.data.listeners = apiNode.listeners || [];
flowData.globalListeners = apiData.global_listeners || [];
```

### 8.2 toFlowSchema（前端 → 后端）

```typescript
// 在 toFlowSchema 中新增
apiNode.listeners = node.data.listeners || [];
apiData.global_listeners = flowData.globalListeners || [];
```

---

## 九、模板变量

Webhook 和通知模板支持以下变量：

| 变量 | 说明 | 示例 |
|------|------|------|
| `{{instanceId}}` | 流程实例 ID | `inst_abc123` |
| `{{flowName}}` | 流程名称 | `请假审批` |
| `{{nodeKey}}` | 当前节点标识 | `approval_1` |
| `{{nodeName}}` | 当前节点名称 | `部门经理审批` |
| `{{applicantId}}` | 发起人 ID | `user_001` |
| `{{applicantName}}` | 发起人姓名 | `张三` |
| `{{action}}` | 触发动作 | `approve` / `reject` |
| `{{timestamp}}` | 触发时间戳 | `2026-06-25T10:30:00Z` |

---

## 十、实现优先级

| 阶段 | 内容 | 工作量 |
|------|------|--------|
| P0 | 数据模型 + 存储（DB 字段 + Schema） | 2h |
| P0 | PropertyPanel 监听器配置 UI | 6h |
| P0 | 全局监听 Drawer UI | 4h |
| P1 | 后端 ListenerService 核心 | 4h |
| P1 | Webhook 执行 + 重试 | 3h |
| P1 | 引擎事件注入 | 3h |
| P2 | 监听器编辑 Modal（完整表单） | 4h |
| P2 | 通知/短信动作实现 | 3h |
| P2 | 节点监听器标识（小圆点） | 1h |
| P3 | 监听器执行日志查看 | 4h |
| P3 | 模板变量预览 | 2h |

**总计：约 36h（P0+P1 = 22h 核心功能）**

---

## 十一、与现有 callback_registry 的关系

现有 `callback_registry` 是硬编码的进程内回调，用于 `leave_request`、`extra_quota` 两种业务类型。

**迁移策略：**
1. 新增 `callback` 动作类型，通过监听器配置调用已注册的 callback
2. `callback_registry` 保留作为底层执行器
3. 监听器的 `callbackName` 对应 `callback_registry.register()` 注册的名称
4. 长期目标：逐步将硬编码回调迁移到 UI 可配置的监听器

---

## 十二、风险与约束

| 风险 | 缓解措施 |
|------|---------|
| Webhook 超时阻塞引擎 | 异步执行（Celery task），不阻塞主流程 |
| 监听器配置错误导致流程异常 | 监听器失败不阻塞流程推进，仅记录日志 |
| 模板变量注入攻击 | 使用 Jinja2 沙箱渲染，限制可用变量 |
| 监听器数量过多影响性能 | 限制每个节点最多 10 个监听器 |
| 外部系统不可达 | Webhook 重试机制 + 失败告警 |
