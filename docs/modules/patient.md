# 👥 患者管理模块需求文档

## 一、模块概述

患者管理模块负责患者档案、就诊人信息、黑名单等管理功能。

## 二、功能清单

### 2.1 患者档案
- 患者列表查询
- 患者详情
- 就诊历史记录
- 病历记录

### 2.2 就诊人管理
- 就诊人列表
- 添加/编辑就诊人
- 设置默认就诊人
- 删除就诊人

### 2.3 黑名单管理
- 黑名单列表
- 加入黑名单
- 移出黑名单
- 爽约规则配置

## 三、就诊人与用户关系

一个用户可以有多个就诊人：
- 本人
- 父母
- 子女
- 配偶
- 其他

## 四、黑名单规则

| 规则 | 默认值 | 说明 |
|------|--------|------|
| 爽约次数阈值 | 3次 | 累计爽约N次加入黑名单 |
| 黑名单时长 | 30天 | 黑名单有效期 |
| 限制内容 | 禁止预约 | 黑名单期间不可预约 |

## 五、数据模型

### patients 表
| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| user_id | UUID | 用户ID |
| name | VARCHAR | 姓名 |
| phone | VARCHAR | 手机号 |
| id_card | VARCHAR | 身份证号 |
| gender | SMALLINT | 性别 |
| birthday | DATE | 生日 |
| relationship | VARCHAR | 与用户关系 |
| is_default | BOOLEAN | 是否默认 |
| status | SMALLINT | 状态 |

### blacklists 表
| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| user_id | UUID | 用户ID |
| reason | VARCHAR | 原因 |
| no_show_count | INT | 爽约次数 |
| expire_at | TIMESTAMP | 过期时间 |
| status | SMALLINT | 状态 |

## 六、API接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /patients | 获取患者列表(管理员) |
| GET | /patients/:id | 获取患者详情 |
| GET | /users/patients | 获取我的就诊人 |
| POST | /users/patients | 添加就诊人 |
| PUT | /users/patients/:id | 更新就诊人 |
| DELETE | /users/patients/:id | 删除就诊人 |
| GET | /blacklists | 获取黑名单列表 |
| POST | /blacklists | 加入黑名单 |
| DELETE | /blacklists/:id | 移出黑名单 |

