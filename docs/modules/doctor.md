# 👨‍⚕️ 医生管理模块需求文档

## 一、模块概述

医生管理模块负责医生信息维护、预约设置、关联科室/门店等功能。

## 二、功能清单

### 2.1 医生列表
- 医生列表查询
- 按科室/门店/职称筛选
- 医生搜索

### 2.2 医生信息
- 基本信息：姓名、头像、职称
- 专业信息：擅长领域、简介
- 关联信息：所属科室、门店
- 预约设置：号源数、挂号费

### 2.3 医生状态
- 在职/离职
- 是否支持预约
- 是否推荐医生

## 三、职称定义

| 职称 | 说明 |
|------|------|
| 主任医师 | 正高级 |
| 副主任医师 | 副高级 |
| 主治医师 | 中级 |
| 住院医师 | 初级 |

## 四、数据模型

### doctors 表
| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| user_id | UUID | 用户ID |
| hospital_id | UUID | 医院ID |
| branch_id | UUID | 门店ID |
| department_id | UUID | 科室ID |
| employee_no | VARCHAR | 工号 |
| title | VARCHAR | 职称 |
| specialty | VARCHAR | 擅长领域 |
| introduction | TEXT | 简介 |
| consultation_fee | DECIMAL | 挂号费 |
| is_expert | BOOLEAN | 是否专家 |
| is_recommended | BOOLEAN | 是否推荐 |
| status | SMALLINT | 状态 |

## 五、API接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /doctors | 获取医生列表 |
| GET | /doctors/:id | 获取医生详情 |
| GET | /doctors/:id/schedules | 获取医生排班 |
| GET | /doctors/recommended | 获取推荐医生 |
| POST | /doctors | 创建医生 |
| PUT | /doctors/:id | 更新医生 |
| DELETE | /doctors/:id | 删除医生 |

