## Context

排班规则管理是医院排班系统的核心功能。当前系统支持创建规则并生成排班，但缺少对已生成排班的批量管理能力和操作追溯能力。本次变更旨在增强规则管理的完整性。

## Goals / Non-Goals

**Goals:**
- 提供规则生成排班的批量删除和停诊能力
- 防止重复生成导致的数据混乱
- 提供操作历史追溯能力
- 增强排班列表的搜索能力

**Non-Goals:**
- 不改变现有的排班生成逻辑
- 不涉及预约流程的变更
- 不涉及权限模型的变更

## Decisions

### 1. 生成历史记录表设计

```sql
CREATE TABLE schedule_generation_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    template_ids UUID[] NOT NULL,           -- 使用的规则ID列表
    template_names TEXT[],                  -- 规则名称（冗余存储，便于查询）
    start_date DATE NOT NULL,               -- 生成的开始日期
    end_date DATE NOT NULL,                 -- 生成的结束日期
    generated_count INTEGER NOT NULL,       -- 生成的排班数量
    operation_type VARCHAR(20) NOT NULL,    -- 操作类型: 'create' | 'override'
    operator_id UUID NOT NULL,              -- 操作人ID
    operator_name VARCHAR(100),             -- 操作人姓名（冗余存储）
    store_id UUID,                          -- 门店ID（可选，用于多门店筛选）
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_generation_history_created_at ON schedule_generation_history(created_at DESC);
CREATE INDEX idx_generation_history_store_id ON schedule_generation_history(store_id);
```

**决策理由：**
- 使用数组存储 template_ids，支持多规则同时生成的场景
- 冗余存储 template_names 和 operator_name，避免关联查询，提升查询性能
- 添加 store_id 支持多门店场景下的数据隔离

### 2. 批量删除策略

- 通过 `template_id` 字段关联排班记录（Schedule 表已有此字段）
- 删除前检查是否有已预约的排班，如有则提示用户
- 支持选择是否同时取消预约

### 3. 冲突检测逻辑

```
检测条件：
- 相同的 template_id
- 日期范围有重叠
- 排班状态为正常（status = 1）

返回信息：
- 冲突的排班数量
- 冲突的日期范围
- 是否有已预约的排班
```

### 4. 前端交互设计

**一键删除/停诊流程：**
1. 选择规则（支持多选）
2. 点击操作按钮，弹出日期范围选择弹窗
3. 选择日期范围后，显示影响预览（将删除/停诊 X 条排班）
4. 确认执行

**生成排班冲突处理：**
1. 用户点击生成排班
2. 后端检测冲突，返回冲突信息
3. 前端显示冲突提示弹窗
4. 用户选择"覆盖生成"或"取消"

## Risks / Trade-offs

| 风险 | 缓解措施 |
|------|----------|
| 批量删除可能误删重要数据 | 删除前显示影响预览，二次确认 |
| 覆盖生成可能影响已预约的排班 | 检测已预约排班，提示用户 |
| 历史记录表数据量增长 | 定期归档历史数据（可后续实现） |

## Migration Plan

1. 创建数据库迁移脚本，添加 schedule_generation_history 表
2. 部署后端 API 变更
3. 部署前端页面变更
4. 无需数据迁移，新功能为增量添加

## Open Questions

- 是否需要支持历史记录的导出功能？（建议后续迭代）
- 批量停诊是否需要支持设置停诊结束时间？（当前设计为永久停诊，需手动恢复）
