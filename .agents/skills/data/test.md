---
name: Run Tests
description: 运行测试套件
category: development
tags: [test, quality]
parameters:
  - name: type
    type: choice
    required: false
    default: all
    description: 测试类型
    choices: [all, unit, integration]
  - name: coverage
    type: boolean
    required: false
    default: false
    description: 生成覆盖率报告
---

**用途**
运行项目测试套件。

**前置条件**
- 测试依赖已安装
- 测试数据库可用

**参数说明**
| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| --type | choice | 否 | all | 测试类型 |
| --coverage | boolean | 否 | false | 生成覆盖率报告 |

**执行步骤**

1. 激活 Python 虚拟环境（后端测试）

2. 根据 type 执行：

   **all**: 运行所有测试
   ```bash
   pytest
   ```

   **unit**: 运行单元测试
   ```bash
   pytest tests/unit/
   ```

   **integration**: 运行集成测试
   ```bash
   pytest tests/integration/
   ```

3. 如果 coverage=true：
   ```bash
   pytest --cov=app --cov-report=html
   ```

4. 显示测试结果摘要

**注意事项**
- 测试耗时约 1-3 分钟
- 集成测试需要完整的环境

**示例**
```bash
# 运行所有测试
/test

# 运行单元测试
/test --type unit

# 生成覆盖率报告
/test --coverage true
```
