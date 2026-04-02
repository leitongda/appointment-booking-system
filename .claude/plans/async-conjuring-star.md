# 规则组配置说明文档 - 实施计划

## Context

规则组（RuleSet）是预约挂号系统的核心配置机制，包含 5 张关联表、6 类配置项、多时间窗 AND 逻辑、优先级匹配等复杂概念。当前只有开发阶段的设计文档（`docs/ruleset/` 下），缺少面向管理员/运营人员的配置说明文档。用户需要一份带场景举例的实用配置指南。

## 实施方案

创建文件: `docs/ruleset/规则组配置说明文档.md`

### 文档结构

1. **概述** -- 规则组概念、组成结构、班次类型、生效规则
2. **配置项详细说明** (6 个子章节)
   - 规则组基础配置（名称、优先级、启用状态）
   - 时间口径默认值（时间来源、时区、精度、边界包含）
   - 时间窗配置（动作类型、参考点、偏移量、失败策略）
   - 预约策略（限次、冲突链）
   - 签到策略（宽限期、爽约处理）
   - 容量策略（候补、超额）
3. **时间窗工作机制** -- 偏移量计算公式、边界包含规则、多时间窗 AND 逻辑（含演算示例）
4. **优先级机制** -- FIRST_MATCH 规则说明
5. **系统预设模板详解**（4个，假设班次 09:00-12:00 演算）
   - 标准门诊、专家门诊、体检预约、急诊
6. **自定义场景配置示例**（3个）
   - 专科护理、VIP 特需门诊、检查检验
7. **常见配置错误与注意事项**（10个常见错误）
8. **附录：速查表**

### 关键源文件

- `apps/server/app/models/rule_set.py` -- 数据模型 + 系统预设种子数据
- `apps/server/app/modules/rule_engine/time_windows.py` -- 时间窗引擎逻辑
- `apps/server/app/modules/rule_engine/validation.py` -- 冲突检查链
- `apps/admin/src/constants/rule-set.ts` -- 前端预设模板 + UI 标签映射
- `docs/ruleset/readme.md` -- 原始设计理念

### 验证方式

- 文档中的偏移量计算、时间窗演算结果需与 `time_windows.py` 中的 `_get_reference_time` 和 `_is_in_window` 逻辑一致
- 预设模板配置需与 `rule_set.py` 第 217-427 行的 `get_system_presets()` 数据一致
- 冲突检查链顺序需与 `validation.py` 第 194-201 行的 `_BOOKING_CONFLICT_CHECKS` 一致
