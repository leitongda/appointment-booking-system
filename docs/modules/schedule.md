# 📅 排班管理模块需求文档

## 一、模块概述

排班管理模块负责医生出诊时间安排，包括排班模板、自定义排班、号源管理、停诊处理等功能。

## 二、功能清单

### 2.1 排班模板
- 创建周期排班模板（周一至周日）
- 设置每个时段的号源数量
- 模板启用/禁用

### 2.2 自定义排班
- 特殊日期排班
- 临时加班/调班
- 批量生成排班

### 2.3 号源管理
- 查看号源使用情况
- 号源数量调整
- 号源锁定/释放

### 2.4 休息日设置
- 节假日配置
- 医院统一休息日
- 调休日设置

### 2.5 停诊管理
- 医生申请停诊
- 管理员审核
- 通知已预约患者
- 处理退款/改约

### 2.6 排班统计
- 按医生统计
- 按科室统计
- 按门店统计

## 三、业务规则

### 3.1 排班生成规则
1. 根据排班模板自动生成排班
2. 排除休息日和节假日
3. 特殊日期排班覆盖模板排班

### 3.2 号源规则
- 号源数量不可超过模板上限
- 已预约号源不可减少
- 号源为0时自动标记为已满

### 3.3 停诊规则
- 停诊需提前申请审核
- 已有预约需通知患者
- 支持自动退款或改约

## 四、时段定义

| 时段 | 代码 | 默认时间 |
|------|------|---------|
| 上午 | AM | 08:00-12:00 |
| 下午 | PM | 14:00-17:30 |
| 夜间 | NIGHT | 18:00-21:00 |

## 五、数据模型

### schedule_templates 表
| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| doctor_id | UUID | 医生ID |
| weekday | SMALLINT | 星期(1-7) |
| time_slot | VARCHAR | 时段 |
| start_time | TIME | 开始时间 |
| end_time | TIME | 结束时间 |
| total_slots | INT | 号源数量 |
| status | SMALLINT | 状态 |

### schedules 表
| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| doctor_id | UUID | 医生ID |
| schedule_date | DATE | 排班日期 |
| time_slot | VARCHAR | 时段 |
| total_slots | INT | 总号源 |
| booked_slots | INT | 已预约数 |
| status | SMALLINT | 状态 |

## 六、API接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /schedules | 获取排班列表 |
| GET | /schedules/available | 获取可预约排班 |
| POST | /schedules | 创建排班 |
| POST | /schedules/batch | 批量创建 |
| POST | /schedules/generate | 根据模板生成 |
| PUT | /schedules/:id | 更新排班 |
| PUT | /schedules/:id/suspend | 停诊 |
| DELETE | /schedules/:id | 删除排班 |

