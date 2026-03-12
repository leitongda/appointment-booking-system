# 注册层处理方案

## 背景

当前服务端的路由注册入口在：

- [/Users/leijiadashao/leitond/appointment-booking-system/apps/server/app/api/v1/__init__.py](/Users/leijiadashao/leitond/appointment-booking-system/apps/server/app/api/v1/__init__.py)

它目前采用声明式注册表：

```python
ROUTER_REGISTRATIONS = [
    RouterRegistration("app.api.v1.auth", "/auth", ["认证"]),
    ...
]
```

实际情况是：

- 大多数 `app/api/v1/*.py` 已经退化为薄 wrapper
- 真实实现主要在 `app/modules/*`
- `api/v1` 继续保留的价值，已经从“实现层”变成“兼容注册层”

因此，注册层的后续目标，不是继续留一个历史目录，而是把它明确收敛成稳定的“路由挂载层”。

## 目标

注册层后续应满足：

1. 对外 API 前缀和路径保持不变
2. 路由注册逻辑集中、可读、可维护
3. 不再要求 `api/v1/*.py` 作为每个模块的中间跳板
4. 支持逐步删除历史 wrapper，而不是一次性大迁移

## 现状问题

### 1. 注册路径仍然指向 `app.api.v1.*`

虽然实现已经迁到 `modules`，但注册表仍然写成：

```python
RouterRegistration("app.api.v1.appointments", "/appointments", ["预约"])
```

这意味着：

- import 链更长
- wrapper 删除前，注册表无法直接脱离旧目录
- 读代码时会误以为 `api/v1` 仍是主入口

### 2. `api/v1` 目录语义不清

现在它既不是实现层，也还没彻底退化成纯注册层。  
如果不进一步处理，后续开发很容易又把实现加回去。

### 3. 删除 wrapper 缺少统一步骤

如果直接逐个删文件，而不先收敛注册表，会造成：

- import 断裂
- 路由来源不一致
- 迁移状态难以判断

## 推荐方案

建议分 3 步做，而不是一次性删除全部 `api/v1` 文件。

### 阶段 1. 注册表改为直连 `modules`

把 `ROUTER_REGISTRATIONS` 里的 `module` 从：

```python
"app.api.v1.xxx"
```

改为：

```python
"app.modules.xxx.router"
```

或在多 router 模块中改为：

```python
"app.modules.patients.router_manage"
"app.modules.patients.router_users"
```

这一步完成后，`api/v1/*.py` 就不再承担“注册链路上的必经节点”。

这是最关键的一步。

### 阶段 2. 把 `api/v1` 收敛成最小兼容层

注册表脱离后，`api/v1/*.py` 只保留两类文件：

1. 还没迁完、不适合马上删除的兼容入口
2. 极少数仍有外部工具或文档直接引用的旧模块路径

对已经没有引用价值的文件，直接删除。

### 阶段 3. 删除剩余 wrapper 或把 `api/v1` 改成纯聚合层

最终形态二选一：

#### 方案 A. 极简保留

保留：

- `app/api/v1/__init__.py`

删除：

- 绝大多数 `app/api/v1/*.py`

这种方式最干净。

#### 方案 B. 纯聚合层保留

保留少量 `api/v1/*.py`，但明确规定：

- 只允许 `from app.modules... import router`
- 不允许任何业务实现
- 不参与内部调用

这种方式更保守，适合过渡期更长的仓库。

## 建议采用的最终形态

建议采用 **方案 A**：

- `app/api/v1/__init__.py` 保留为统一注册层
- `ROUTER_REGISTRATIONS` 直接挂 `app.modules.*`
- 删除大部分 `app/api/v1/*.py`

原因：

- 当前多数 wrapper 已经没有业务价值
- 真正的稳定边界已经在 `modules`
- 继续保留大批 wrapper，只会增加维护噪音

## 建议改造顺序

### 第 1 批

- 修改 `app/api/v1/__init__.py`
- 让注册表直接引用 `app.modules.*`
- 跑全量测试确认路由总数不变

### 第 2 批

删除最简单的 wrapper：

- `analytics.py`
- `audit_logs.py`
- `auth.py`
- `blacklists.py`
- `content.py`
- `feedbacks.py`
- `messages.py`
- `statistics.py`
- `stores.py`
- `upload.py`
- `users.py`

### 第 3 批

删除多入口/特殊模块 wrapper：

- `patients.py`
- `user_manage.py`
- `doctor_portal.py`
- `import_export.py`
- `schedule_templates.py`
- `schedules.py`
- `appointments.py`
- `rule_sets.py`
- `websocket.py`

## 删除前检查

每删一批，至少执行：

```bash
cd apps/server
pytest -q
```

并且检查：

```bash
rg "app\\.api\\.v1\\." app tests
```

如果仓库内部还存在旧路径依赖，就不应删对应 wrapper。

## 验收标准

注册层处理完成后，应满足：

1. `app/api/v1/__init__.py` 直接注册 `app.modules.*`
2. 已删除 wrapper 不再被代码或测试引用
3. 路由总数与对外路径不变
4. 全量 `pytest` 通过
5. 新增功能不再向 `app/api/v1/*.py` 追加实现

## 风险点

### 1. 多 router 模块

像 `patients` 这种一个领域多个 router 文件，注册表改造时要明确挂哪个模块。

### 2. 测试中旧 import

如果某些测试还直接 import `app.api.v1.xxx`，会导致删除 wrapper 后失败。

### 3. 文档链接

如果内部文档或静态导出文件仍写死 `app.api.v1.*`，删除前要同步修正。

## 结论

注册层的正确处理方式不是继续保留整层 `api/v1` wrapper，而是：

1. 先把注册表改成直连 `modules`
2. 再逐批删除 `api/v1` wrapper
3. 最终把 `api/v1` 收敛为一个真正的聚合注册层
