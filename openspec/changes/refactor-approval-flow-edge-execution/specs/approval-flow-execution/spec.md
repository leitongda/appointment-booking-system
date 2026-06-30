## ADDED Requirements

### Requirement: 审批流运行时必须优先按快照连线推进

系统 SHALL 在审批实例推进时优先使用实例流程定义快照中的 `edges` 选择下一节点，而不是根据 `sort_order` 推断下一节点。

#### Scenario: 线性审批按连线推进

- **GIVEN** 一个已激活流程的快照包含 `approval_a -> approval_b` 的连线
- **WHEN** `approval_a` 审批完成
- **THEN** 系统进入 `approval_b`
- **AND** 不依赖 `approval_b.sort_order` 是否刚好排在 `approval_a` 后面

#### Scenario: 历史快照没有连线

- **GIVEN** 一个运行中实例的快照没有 `edges`
- **WHEN** 当前节点审批完成
- **THEN** 系统 SHALL 使用旧的 `sort_order` 逻辑兼容推进
- **AND** 记录兼容回退日志

### Requirement: 条件节点必须按条件边选择路径

系统 SHALL 在条件节点上先评估条件组，匹配到目标节点后必须通过该目标对应的出边进入下一节点。

#### Scenario: 条件命中指定分支

- **GIVEN** 条件节点有一条指向 `manager_approval` 的条件规则
- **AND** 条件节点存在指向 `manager_approval` 的出边
- **WHEN** 表单数据满足该条件
- **THEN** 系统进入 `manager_approval`

#### Scenario: 条件命中但缺少对应边

- **GIVEN** 条件节点规则命中 `manager_approval`
- **AND** 条件节点不存在指向 `manager_approval` 的出边
- **WHEN** 系统推进该条件节点
- **THEN** 系统 SHALL 阻止推进并返回流程定义错误

#### Scenario: 条件不命中时走默认分支

- **GIVEN** 条件节点没有任何条件规则命中
- **AND** 条件节点存在 `sourceHandle=default` 的默认边
- **WHEN** 系统推进该条件节点
- **THEN** 系统进入默认边目标节点

### Requirement: 激活流程前必须通过图结构校验

系统 SHALL 在激活流程定义前校验节点和边构成的图结构，阻止运行时不可确定的流程进入 active 状态。

#### Scenario: 边引用不存在的节点

- **GIVEN** 流程定义包含一条指向不存在节点的边
- **WHEN** 管理员激活流程
- **THEN** 系统拒绝激活
- **AND** 返回可读的校验错误

#### Scenario: 普通审批节点存在多条无条件出边

- **GIVEN** 一个普通审批节点存在两条无条件出边
- **WHEN** 管理员激活流程
- **THEN** 系统拒绝激活
- **AND** 提示该节点存在歧义分支

#### Scenario: 条件节点有多个默认边

- **GIVEN** 一个条件节点存在两条 `sourceHandle=default` 出边
- **WHEN** 管理员激活流程
- **THEN** 系统拒绝激活
- **AND** 提示默认分支只能有一条

### Requirement: 抄送节点必须按连线继续推进

系统 SHALL 在处理抄送节点通知后继续使用该抄送节点的出边推进流程。

#### Scenario: 抄送节点连接到审批节点

- **GIVEN** 抄送节点有一条出边连接到 `approval_next`
- **WHEN** 流程推进到该抄送节点
- **THEN** 系统发送抄送通知
- **AND** 继续进入 `approval_next`
