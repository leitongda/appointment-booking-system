# 通用审批流引擎

## 架构概览

通用审批引擎提供可配置的审批流程，支持多种审批模式和业务类型。

### 核心组件

| 文件 | 职责 |
|------|------|
| `engine.py` | 引擎核心：发起、审批、拒绝、转交、撤回、节点推进 |
| `router.py` | 流程定义 CRUD API |
| `router_instances.py` | 审批实例 API（列表、详情、审批、拒绝、转交、撤回） |
| `service_definitions.py` | 流程定义服务层（版本管理、激活时快照） |
| `service_instances.py` | 审批实例服务层（委托给引擎） |
| `assignee_resolver.py` | 审批人解析（角色/用户/部门/动态字段） |
| `condition_evaluator.py` | 条件分支评估（eq/neq/gt/gte/lt/lte/in/not_in/contains/exists） |
| `callback_registry.py` | 业务模块回调注册表 |
| `business_callbacks.py` | 内置业务回调处理器 |

### 数据模型

| 表 | 用途 |
|---|------|
| `approval_flow_definitions` | 流程模板（名称、业务类型、版本、状态、表单模式） |
| `approval_flow_nodes` | 流程节点（类型、审批模式、审批人配置、超时设置） |
| `approval_flow_conditions` | 条件分支规则 |
| `approval_instances` | 审批实例（每次提交创建一条） |
| `approval_records` | 审计记录（每次操作记录一条） |
| `approval_tasks` | 审批任务（每个审批人一条） |

## 状态机

### 实例状态

```
pending -> approved
        -> rejected
        -> cancelled
        -> withdrawn
```

### 任务状态

```
pending -> completed
        -> cancelled
        -> transferred
        -> expired
```

## 支持的操作

- **发起** (`start_instance`): 创建实例，解析第一个审批节点，创建任务
- **审批** (`approve`): Redis 分布式锁，完成任务，检查节点完成条件，推进到下一节点
- **拒绝** (`reject`): 标记实例为拒绝，取消所有待处理任务
- **转交** (`delegate`): 将任务从一个审批人转交给另一个
- **撤回** (`withdraw`): 仅申请人可撤回，且仅在无审批记录时

## 审批模式

每个审批节点支持三种模式：

- `or` (或签): 一人通过即可
- `and` (会签): 所有人必须通过
- `sequential` (依次审批): 按顺序逐个审批

## 节点类型

- `start`: 起始节点
- `approval`: 审批节点
- `cc`: 抄送节点
- `condition`: 条件分支节点
- `end`: 结束节点

## 已接入的业务类型

| 业务类型 | 发起端 | 回调端 | 说明 |
|----------|--------|--------|------|
| `leave_request` | `_start_approval_if_configured()` | `handle_leave_request_approval()` | 停诊/调班审批 |
| `extra_quota` | `_start_approval_if_configured()` | `handle_extra_quota_approval()` | 加号审批 |

### 接入模式

1. **发起端**: 业务模块在创建申请时调用 `ApprovalEngine.start_instance()`，捕获 `FlowNotFoundError` 作为无流程定义时的 fallback
2. **回调端**: 在 `business_callbacks.py` 中定义处理器，在 `__init__.py` 中通过 `register_builtin_callbacks()` 注册
3. **Fallback**: 无流程定义时，业务模块使用各自的旧审核入口（`review()`/`approve()`/`reject()`）

## Celery 异步任务

- `send_approval_notification`: WebSocket 通知审批人/申请人
- `check_approval_timeouts`: 每 10 分钟检查超时任务，触发提醒/自动审批/自动拒绝

## 前端页面

- 审批中心: `/approval/instances` (待办/已办/我发起)
- 流程定义管理: `/approval/definitions` (CRUD、激活、归档、复制)
