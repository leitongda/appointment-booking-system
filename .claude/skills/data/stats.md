---
name: Statistics
description: 显示数据统计信息
category: data
tags: [stats, data]
parameters:
  - name: type
    type: choice
    required: false
    default: all
    description: 统计类型
    choices: [all, appointment, patient, doctor, schedule]
---

**用途**
显示系统数据统计信息。

**前置条件**
- 数据库正在运行

**参数说明**
| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| --type | choice | 否 | all | 统计类型 |

**执行步骤**

根据 type 查询并显示：

1. **appointment**: 预约统计
   - 总预约数
   - 今日预约数
   - 待确认数
   - 已完成数
   - 已取消数

2. **patient**: 患者统计
   - 总患者数
   - 今日新增
   - 活跃患者（近 30 天有预约）

3. **doctor**: 医生统计
   - 总医生数
   - 在岗医生数
   - 各科室医生分布

4. **schedule**: 排班统计
   - 本周排班数
   - 今日排班数
   - 各科室排班分布

5. **all**: 显示所有统计

**注意事项**
- 数据实时从数据库查询
- 统计可能需要几秒钟

**示例**
```bash
# 显示所有统计
/stats

# 显示预约统计
/stats --type appointment

# 显示患者统计
/stats --type patient
```
