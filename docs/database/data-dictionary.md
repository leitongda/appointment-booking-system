# 数据字典

> 基于 SQLAlchemy ORM 模型实际代码生成，最后更新：2026-02-06

---

## 概述

| 项目 | 数量 |
|------|------|
| 活跃业务表 | 48 |
| 已废弃/遗留表 | 14 |
| 业务域分类 | 14 |
| 公共审计字段(AuditMixin) | 4 |

---

## 公共字段

### TimestampMixin（时间戳）

大多数表通过继承 `AuditMixin` 自动拥有以下字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| `created_at` | DateTime | 创建时间 |
| `updated_at` | DateTime | 更新时间（自动维护） |

### AuditMixin（审计 = 时间戳 + 操作人）

继承 TimestampMixin，额外增加：

| 字段 | 类型 | 说明 |
|------|------|------|
| `created_by` | String(36), nullable | 创建人ID |
| `updated_by` | String(36), nullable | 更新人ID |

> 下文各表字段列表中不再重复列出 AuditMixin 的 4 个字段，仅在"混入"列标注是否包含。

---

## 废表清单（14 张）

### schema.sql 设计阶段定义但从未在 ORM 中实现（13 张）

| 废表名 | 原用途 | 废弃原因 | 替代方案 |
|--------|--------|----------|----------|
| `hospitals` | 医院表 | 架构简化，医院与分院合并 | `stores` |
| `branches` | 门店/分院表 | 架构简化，医院与分院合并 | `stores` |
| `menus` | 菜单表 | 权限系统重新设计为扁平权限码 | `permissions` |
| `role_menus` | 角色菜单关联表 | 随 menus 一起废弃 | `role_permissions` |
| `admin_roles` | 管理员角色关联表(多对多) | Admin 改为直接 FK 关联 Role | `admins.role_id` |
| `holidays` | 休息日/节假日表 | 休息日模型重新设计，支持门店+医生维度 | `rest_days` |
| `suspension_records` | 停诊记录表 | 停诊模型重新设计，支持门店维度 | `schedule_suspensions` |
| `news_types` | 新闻分类表 | 未实现独立分类表 | `news.type` 整数字段 |
| `popups` | 弹窗表 | 功能从未实现 | 无 |
| `settings` | 系统设置表 | 重新设计为支持门店级别覆盖 | `system_settings` |
| `home_menus` | 首页菜单表 | 功能从未实现 | 无 |
| `tab_menus` | 底部Tab菜单表 | 功能从未实现 | 无 |
| `notifications` | 通知表 | 消息系统重新设计 | `messages` |

### ORM 中存在但已废弃/遗留（1 张）

| 废表名 | 原用途 | 废弃原因 | 当前状态 |
|--------|--------|----------|----------|
| `custom_schedules` | 自定义排班表 | 数据已通过迁移 021 合并到 `schedules` 表 | 模型文件和服务代码仍存在（待清理），`__init__.py` 已注释不导出 |

---

## 一、用户与认证（2 张表）

### 1.1 users — 用户表

| 混入 | AuditMixin |
|------|-----------|

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `id` | String(36) | PK | 用户ID (UUID) |
| `phone` | String(20) | UNIQUE, INDEX, nullable | 手机号，微信用户可无 |
| `password_hash` | String(255) | NOT NULL | 密码哈希 |
| `nickname` | String(50) | | 昵称 |
| `avatar` | String(255) | | 头像URL |
| `gender` | Integer | default=0 | 性别: 0未知 1男 2女 |
| `openid` | String(100) | UNIQUE, INDEX | 微信小程序OpenID |
| `status` | Integer | default=1 | 状态: 0禁用 1正常 |
| `points` | Integer | default=0 | 当前积分 |
| `unionid` | String(100) | UNIQUE, INDEX, nullable | 微信开放平台统一ID |
| `wechat_nickname` | String(50) | nullable | 微信原始昵称 |
| `wechat_avatar` | String(500) | nullable | 微信原始头像URL |
| `wechat_synced_at` | DateTime | nullable | 最后同步微信信息时间 |

关联关系：
- `patients` → Patient (一对多)
- `point_logs` → PointLog (一对多)

---

### 1.2 patients — 就诊人表

| 混入 | AuditMixin |
|------|-----------|

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `id` | String(36) | PK | 就诊人ID (UUID) |
| `user_id` | String(36) | FK→users.id, NOT NULL | 所属用户ID |
| `store_id` | String(36) | FK→stores.id, INDEX, nullable | 首次就诊门店ID |
| `name` | String(50) | NOT NULL | 姓名 |
| `phone` | String(20) | NOT NULL | 手机号 |
| `id_card` | String(18) | | 身份证号 |
| `gender` | Integer | | 性别 |
| `age` | Integer | | 年龄 |
| `birthday` | DateTime | | 出生日期 |
| `relationship` | String(20) | | 与账号用户关系: 本人/父母/子女/配偶/其他 |
| `is_default` | Boolean | default=False | 是否默认就诊人 |
| `card_no` | String(50) | UNIQUE, INDEX | 就诊卡编号 |
| `province` | String(50) | | 省 |
| `city` | String(50) | | 市 |
| `district` | String(50) | | 区 |
| `street` | String(100) | | 街道/社区 |
| `id_card_type` | Integer | default=1 | 证件类型: 1身份证 2户口簿 3护照 |
| `ethnicity` | String(20) | default="汉族" | 民族 |
| `address` | String(255) | | 详细地址 |
| `source` | Integer | default=1 | 来源: 1用户添加 2管理员添加 |
| `total_consumption` | Numeric(10,2) | default=0 | 累计消费金额 |

关联关系：
- `user` → User (多对一)
- `store` → Store (多对一)

---

## 二、权限与管理（6 张表）

### 2.1 admins — 管理员表

| 混入 | AuditMixin |
|------|-----------|

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `id` | String(36) | PK | 管理员ID (UUID) |
| `username` | String(50) | UNIQUE, NOT NULL | 登录用户名 |
| `password_hash` | String(255) | NOT NULL | 密码哈希 |
| `name` | String(50) | | 姓名 |
| `phone` | String(20) | | 手机号 |
| `email` | String(100) | | 邮箱 |
| `avatar` | String(255) | | 头像URL |
| `role_id` | String(36) | FK→roles.id | 角色ID |
| `current_store_id` | String(36) | FK→stores.id, nullable | 当前选中门店ID，超级管理员可为空 |
| `status` | Integer | default=1 | 状态: 0禁用 1启用 |
| `last_login_at` | DateTime | | 最后登录时间 |
| `last_login_ip` | String(50) | | 最后登录IP |

关联关系：
- `role` → Role (多对一)
- `current_store` → Store (多对一)
- `stores` → Store (多对多，通过 admin_stores)

---

### 2.2 roles — 角色表

| 混入 | AuditMixin |
|------|-----------|

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `id` | String(36) | PK | 角色ID (UUID) |
| `name` | String(50) | NOT NULL | 角色名称 |
| `code` | String(50) | UNIQUE, NOT NULL | 角色编码，如 SUPER_ADMIN |
| `description` | String(200) | | 描述 |
| `status` | Integer | default=1 | 状态: 0禁用 1启用 |
| `permissions` | Text | | 权限列表，JSON格式 |

关联关系：
- `admins` → Admin (一对多)

---

### 2.3 permissions — 权限表

| 混入 | AuditMixin |
|------|-----------|

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `id` | String(36) | PK | 权限ID (UUID) |
| `code` | String(100) | UNIQUE, NOT NULL | 权限码，如 doctor:create |
| `name` | String(100) | NOT NULL | 权限名称 |
| `type` | String(20) | NOT NULL | 类型: menu/button |
| `parent_code` | String(100) | | 父级权限码 |
| `icon` | String(50) | | 图标（菜单权限可用） |
| `sort` | Integer | default=0 | 排序号 |

---

### 2.4 role_permissions — 角色权限关联表

| 混入 | 无 |
|------|-----------|

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `role_id` | String(36) | PK, FK→roles.id | 角色ID |
| `permission` | String(100) | PK | 权限标识，如 doctor:create |

---

### 2.5 admin_stores — 管理员门店关联表

| 混入 | 无 |
|------|-----------|

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `admin_id` | String(36) | PK, FK→admins.id (CASCADE) | 管理员ID |
| `store_id` | String(36) | PK, FK→stores.id (CASCADE) | 门店ID |
| `is_manager` | Integer | default=0 | 是否为该门店管理员: 0否 1是 |
| `created_at` | DateTime | | 创建时间 |

---

### 2.6 admin_login_history — 管理员登录历史表

| 混入 | 无 |
|------|-----------|

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `id` | String(36) | PK | 记录ID (UUID) |
| `admin_id` | String(36) | FK→admins.id, NOT NULL | 管理员ID |
| `login_time` | DateTime | NOT NULL | 登录时间 |
| `logout_time` | DateTime | nullable | 退出时间 |
| `logout_type` | String(20) | nullable | 退出类型: manual/timeout/kicked |
| `login_ip` | String(50) | | 登录IP |
| `user_agent` | String(500) | | User-Agent字符串 |
| `browser` | String(50) | | 浏览器 |
| `os` | String(50) | | 操作系统 |
| `device_type` | String(20) | | 设备类型: desktop/mobile/tablet |
| `duration` | Integer | nullable | 在线时长（秒） |

---

## 三、机构管理（2 张表）

### 3.1 stores — 门店/分院表

| 混入 | AuditMixin |
|------|-----------|

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `id` | String(36) | PK | 门店ID (UUID) |
| `name` | String(100) | NOT NULL | 门店名称 |
| `code` | String(50) | UNIQUE | 门店编码 |
| `address` | String(255) | | 详细地址 |
| `province` | String(50) | | 省份 |
| `city` | String(50) | | 城市 |
| `district` | String(50) | | 区县 |
| `latitude` | String(20) | | 纬度 |
| `longitude` | String(20) | | 经度 |
| `phone` | String(50) | | 联系电话 |
| `contact_person` | String(50) | | 联系人 |
| `description` | Text | | 门店简介 |
| `opening_time` | Time | | 营业开始时间 |
| `closing_time` | Time | | 营业结束时间 |
| `working_days` | String(50) | default="1,2,3,4,5,6,7" | 工作日(1-7) |
| `business_hours` | String(100) | | 营业时间描述 |
| `image` | String(255) | | 门店图片URL |
| `logo` | String(255) | | 门店Logo URL |
| `password` | String(100) | | 门店密码 |
| `email` | String(100) | | 邮箱 |
| `theme_style` | String(50) | | 风格选择 |
| `sort_order` | Integer | default=0 | 排序 |
| `status` | Integer | default=1 | 状态: 0停业 1营业 2禁用 |
| `wechat_app_id` | String(100) | | 微信小程序AppID |
| `wechat_app_secret` | String(100) | | 微信小程序Secret |
| `wechat_mch_id` | String(100) | | 微信支付商户号 |
| `wechat_api_key` | String(100) | | 微信支付API密钥 |
| `wechat_notify_url` | String(255) | | 微信支付回调地址 |
| `max_cards_per_user` | Integer | default=5 | 每用户可建就诊卡数量上限 |

---

### 3.2 departments — 科室表

| 混入 | AuditMixin |
|------|-----------|

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `id` | String(36) | PK | 科室ID (UUID) |
| `name` | String(100) | NOT NULL | 科室名称 |
| `parent_id` | String(36) | FK→departments.id | 父级科室ID（自关联） |
| `store_id` | String(36) | FK→stores.id, nullable | 默认门店ID |
| `description` | Text | | 科室描述 |
| `sort_order` | Integer | default=0 | 排序 |
| `is_hot` | Integer | default=0 | 是否热门: 0否 1是 |
| `status` | Integer | default=1 | 状态: 0禁用 1正常 |
| `tag` | String(100) | nullable | 科室标签 |
| `enable_banner` | Integer | default=0 | 是否开放banner: 0禁用 1启用 |
| `enable_intro` | Integer | default=0 | 是否开放科室简介: 0禁用 1启用 |
| `is_final` | Integer | default=0 | 是否终极科室: 0否 1是 |
| `is_recommended` | Integer | default=0 | 是否推荐: 0否 1是 |
| `banner_image` | String(500) | nullable | banner图片URL |
| `icon` | String(500) | nullable | 科室图标URL |
| `intro_images` | Text | nullable | 简介图片集JSON |
| `intro_content` | Text | nullable | 富文本简介 |
| `features` | Text | nullable | 科室特色JSON数组 |
| `appointment_notice` | Text | nullable | 预约须知 |
| `phone` | String(20) | nullable | 科室电话 |
| `location` | String(100) | nullable | 位置/楼层 |
| `working_hours` | String(200) | nullable | 工作时间 |

关联关系：
- `children` → Department (一对多，自关联)
- `doctors` → Doctor (一对多)
- `store` → Store (多对一)

---

## 四、医生管理（2 张表）

### 4.1 doctors — 医生表

| 混入 | AuditMixin |
|------|-----------|

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `id` | String(36) | PK | 医生ID (UUID) |
| `user_id` | String(36) | FK→users.id | 关联用户ID |
| `store_id` | String(36) | FK→stores.id | 所属门店ID |
| `department_id` | String(36) | FK→departments.id, NOT NULL | 所属科室ID |
| `name` | String(50) | NOT NULL | 医生姓名 |
| `username` | String(50) | UNIQUE, INDEX | 医生登录账号 |
| `phone` | String(20) | UNIQUE, INDEX | 手机号 |
| `password_hash` | String(255) | | 登录密码哈希 |
| `gender` | Integer | default=1 | 性别: 0女 1男 |
| `avatar` | String(255) | | 头像URL |
| `banner` | String(255) | | 医生banner图URL |
| `title` | String(50) | | 职称 |
| `years_of_experience` | Integer | default=0 | 医龄(年) |
| `education` | String(50) | | 学历 |
| `graduate_school` | String(100) | | 毕业院校 |
| `license_number` | String(100) | | 执业证书编号 |
| `license_image` | String(255) | | 执业证书图片URL |
| `honors` | Text | | 所获荣誉 |
| `schedule_desc` | String(255) | | 坐诊时间说明 |
| `max_daily_appointments` | Integer | default=0 | 每日最大接诊量，0不限制 |
| `online_consult_enabled` | Integer | default=0 | 是否支持在线问诊: 0否 1是 |
| `online_consult_fee` | Numeric(10,2) | default=0 | 在线问诊费用 |
| `page_style` | Integer | default=1 | 页面风格: 1/2/3 |
| `promo_video` | String(255) | | 宣传视频URL |
| `tags` | String(255) | | 标签，逗号分隔 |
| `specialty` | Text | | 擅长 |
| `introduction` | Text | | 简介 |
| `is_recommended` | Integer | default=0 | 是否推荐: 0否 1是 |
| `sort_order` | Integer | default=0 | 排序 |
| `status` | Integer | default=1 | 状态: 0禁用 1正常 |
| `last_login_at` | DateTime | | 最后登录时间 |
| `last_login_ip` | String(50) | | 最后登录IP |
| `use_fee_template` | Integer | default=0 | 是否使用诊费模板: 0否 1是 |

关联关系：
- `store` → Store (多对一)
- `department` → Department (多对一)
- `schedules` → Schedule (一对多)
- `consultation_fees` → DoctorConsultationFee (一对多，cascade)

---

### 4.2 doctor_booking_settings — 医生预约设置表

| 混入 | AuditMixin |
|------|-----------|

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `id` | String(36) | PK | 设置ID (UUID) |
| `store_id` | String(36) | FK→stores.id, NOT NULL | 门店ID |
| `doctor_id` | String(36) | FK→doctors.id, NOT NULL | 医生ID |
| `booking_start_offset` | Integer | default=0 | 预约开始偏移天数，0表示当天 |
| `booking_range_days` | Integer | default=14 | 预约范围天数，1-90天 |
| `release_time` | String(5) | default="00:00" | 放号时间 HH:mm 格式 |
| `status` | Integer | default=1 | 状态: 0禁用 1启用 |

唯一约束：`(store_id, doctor_id)`

---

## 五、排班管理（6 张表）

### 5.1 schedule_templates — 排班模板表

| 混入 | AuditMixin |
|------|-----------|

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `id` | String(36) | PK | 模板ID (UUID) |
| `name` | String(100) | NOT NULL | 模板名称 |
| `store_id` | String(36) | FK→stores.id, NOT NULL | 门店ID |
| `doctor_id` | String(36) | FK→doctors.id, NOT NULL | 医生ID |
| `department_id` | String(36) | FK→departments.id, NOT NULL | 科室ID |
| `weekdays` | Text | NOT NULL | 星期数组，JSON格式 [1,2,3,4,5] |
| `appointment_type` | String(20) | default="normal" | 预约类型: urgent/normal/expert/medical_insurance/self_pay |
| `start_time` | Time | NOT NULL | 开始时间 |
| `end_time` | Time | NOT NULL | 结束时间 |
| `slot_count` | Integer | NOT NULL, default=1 | 班次数量 |
| `slot_capacity` | Integer | NOT NULL, default=10 | 每班次人数 |
| `schedule_mode` | String(50) | default="weekly" | 排班方式 |
| `break_times` | Text | nullable | 排除时间段 JSON [{startTime, endTime}] |
| `status` | Integer | default=1 | 状态: 0禁用 1启用 |
| `last_generated_at` | DateTime | nullable | 上一次生成排班时间 |

关联关系：
- `store` → Store
- `doctor` → Doctor
- `department` → Department
- `schedules` → Schedule (一对多)

---

### 5.2 schedules — 排班表

| 混入 | AuditMixin |
|------|-----------|

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `id` | String(36) | PK | 排班ID (UUID) |
| `doctor_id` | String(36) | FK→doctors.id, NOT NULL | 医生ID |
| `store_id` | String(36) | FK→stores.id, nullable | 门店ID |
| `template_id` | String(36) | FK→schedule_templates.id, nullable | 来源模板ID（NULL表示自定义排班） |
| `shift_type_id` | String(36) | FK→shift_types.id, nullable | 班次类型ID |
| `schedule_date` | Date | NOT NULL | 排班日期 |
| `time_slot` | String(10) | nullable | 时段: AM/PM/morning/afternoon/evening |
| `start_time` | Time | | 开始时间 |
| `end_time` | Time | | 结束时间 |
| `start_at` | DateTime(tz) | nullable | 开始时间(带时区) |
| `end_at` | DateTime(tz) | nullable | 结束时间(带时区) |
| `timezone` | String(50) | default="Asia/Shanghai" | 时区 |
| `total_slots` | Integer | default=10 | 总号源 |
| `booked_slots` | Integer | default=0 | 已预约数 |
| `appointment_type` | String(20) | default="normal" | 预约类型: urgent/normal/expert/medical_insurance/self_pay |
| `status` | Integer | default=1 | 状态: 0停诊 1正常 |

关联关系：
- `doctor` → Doctor
- `store` → Store
- `template` → ScheduleTemplate
- `appointments` → Appointment (一对多)

---

### 5.3 rest_days — 休息日表

| 混入 | AuditMixin |
|------|-----------|

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `id` | String(36) | PK | 记录ID (UUID) |
| `store_id` | String(36) | FK→stores.id, NOT NULL | 门店ID |
| `doctor_ids` | Text | nullable | 医生ID列表,JSON数组,NULL表示门店所有医生 |
| `reason` | String(255) | | 休息原因 |
| `start_date` | Date | NOT NULL | 开始日期 |
| `end_date` | Date | NOT NULL | 结束日期 |
| `status` | Integer | default=1 | 状态: 0已取消 1生效中 |

---

### 5.4 schedule_suspensions — 停诊记录表

| 混入 | AuditMixin |
|------|-----------|

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `id` | String(36) | PK | 记录ID (UUID) |
| `store_id` | String(36) | FK→stores.id, NOT NULL | 门店ID |
| `doctor_id` | String(36) | FK→doctors.id, NOT NULL | 医生ID |
| `title` | String(100) | NOT NULL | 停诊标题 |
| `suspension_date` | Date | NOT NULL | 停诊日期 |
| `schedule_ids` | Text | | 选中的排班ID,JSON数组 |
| `time_slots` | Text | | 选中的时段,JSON数组 |
| `status` | Integer | default=1 | 状态: 0已取消 1生效中 |

---

### 5.5 schedule_generation_logs — 排班生成日志表

| 混入 | 无（仅 created_at） |
|------|-----------|

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `id` | String(36) | PK | 日志ID (UUID) |
| `template_id` | String(36) | FK→schedule_templates.id (CASCADE) | 排班规则ID |
| `operator_id` | String(36) | FK→admins.id (SET NULL), nullable | 操作人ID |
| `operator_name` | String(100) | nullable | 操作人姓名 |
| `action_type` | String(20) | NOT NULL | 操作类型: generate/delete/suspend |
| `start_date` | Date | nullable | 开始日期 |
| `end_date` | Date | nullable | 结束日期 |
| `affected_count` | Integer | default=0 | 影响的记录数 |
| `remark` | Text | nullable | 备注 |
| `created_at` | DateTime | server_default=now() | 创建时间 |

---

### 5.6 leave_requests — 停诊/调班申请表

| 混入 | AuditMixin |
|------|-----------|

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `id` | String(36) | PK | 申请ID (UUID) |
| `doctor_id` | String(36) | NOT NULL, INDEX | 医生ID |
| `request_type` | String(20) | NOT NULL | 申请类型: stop_clinic/schedule_change |
| `schedule_id` | String(36) | | 排班ID（停诊时） |
| `stop_date` | Date | | 停诊日期 |
| `stop_period` | String(20) | | 停诊时段: morning/afternoon/evening/all |
| `original_date` | Date | | 原日期（调班时） |
| `original_period` | String(20) | | 原时段 |
| `target_date` | Date | | 目标日期 |
| `target_period` | String(20) | | 目标时段 |
| `reason` | Text | NOT NULL | 申请原因 |
| `status` | String(20) | default="pending" | 状态: pending/approved/rejected/cancelled |
| `reviewer_id` | String(36) | | 审核人ID |
| `review_comment` | Text | | 审核意见 |
| `reviewed_at` | DateTime | | 审核时间 |
| `affected_appointments` | Integer | default=0 | 受影响预约数 |

---

## 六、规则引擎（7 张表）

### 6.1 shift_types — 班次类型表

| 混入 | AuditMixin |
|------|-----------|

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `id` | String(36) | PK | 班次类型ID (UUID) |
| `code` | String(50) | UNIQUE, NOT NULL | 类型代码: OPD/CHECKUP/EXAM/NURSING/SPECIAL |
| `name` | String(100) | NOT NULL | 类型名称 |
| `description` | Text | | 描述 |
| `enabled` | Boolean | NOT NULL, default=True | 是否启用 |

---

### 6.2 rule_sets — 规则组表

| 混入 | AuditMixin |
|------|-----------|

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `id` | String(36) | PK | 规则组ID (UUID) |
| `name` | String(200) | NOT NULL | 规则组名称 |
| `enabled` | Boolean | NOT NULL, default=True | 是否启用 |
| `priority` | Integer | NOT NULL, default=100 | 优先级(越小越优先) |
| `time_source` | String(20) | NOT NULL, default='SERVER' | 时间来源: SERVER/CLIENT |
| `timezone_source` | String(20) | NOT NULL, default='HOSPITAL' | 时区来源: HOSPITAL/SHIFT/USER |
| `compare_precision` | String(20) | NOT NULL, default='SECOND' | 比较精度: SECOND/MILLISECOND/MINUTE |
| `default_open_inclusive` | Boolean | NOT NULL, default=True | 默认开放边界包含 |
| `default_close_inclusive` | Boolean | NOT NULL, default=False | 默认截止边界包含 |
| `rounding_mode` | String(30) | NOT NULL, default='NONE' | 取整模式 |
| `clock_skew_tolerance_sec` | Integer | NOT NULL, default=5 | 时钟偏差容忍度(秒) |
| `description` | Text | | 描述 |

索引：`(enabled, priority)`

---

### 6.3 rule_set_shift_types — 规则组班次关联表

| 混入 | 无 |
|------|-----------|

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `rule_set_id` | String(36) | PK, FK→rule_sets.id (CASCADE) | 规则组ID |
| `shift_type_id` | String(36) | PK, FK→shift_types.id (CASCADE) | 班次类型ID |

索引：`(shift_type_id)`

---

### 6.4 rule_windows — 时间窗配置表

| 混入 | AuditMixin |
|------|-----------|

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `id` | String(36) | PK | 时间窗ID (UUID) |
| `rule_set_id` | String(36) | FK→rule_sets.id (CASCADE), NOT NULL | 规则组ID |
| `action` | String(30) | NOT NULL | 动作类型: BOOK/CHECKIN/CANCEL/HOLD_RELEASE |
| `reference_point` | String(50) | NOT NULL | 参考点: SHIFT_START/SHIFT_END/BOOKING_CREATED_AT |
| `open_offset_sec` | Integer | nullable | 开放偏移(秒)，可负可正，NULL表示不限制 |
| `close_offset_sec` | Integer | nullable | 截止偏移(秒)，可负可正，NULL表示不限制 |
| `open_inclusive` | Boolean | | 开放边界包含，NULL用规则组默认 |
| `close_inclusive` | Boolean | | 截止边界包含，NULL用规则组默认 |
| `fail_policy` | String(30) | NOT NULL, default='REJECT' | 失败策略: REJECT/ALLOW_WITH_TAG/AUTO_TO_WAITLIST |
| `fail_tag` | String(100) | | 失败标签 |
| `enabled` | Boolean | NOT NULL, default=True | 是否启用 |
| `description` | Text | | 描述 |

索引：`(rule_set_id, enabled)`

---

### 6.5 rule_booking_policies — 预约策略表

| 混入 | AuditMixin |
|------|-----------|

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `rule_set_id` | String(36) | PK, FK→rule_sets.id (CASCADE) | 规则组ID |
| `require_auth` | Boolean | NOT NULL, default=True | 是否要求登录 |
| `require_patient_profile_complete` | Boolean | NOT NULL, default=False | 是否要求档案完整 |
| `per_user_per_shift` | Integer | NOT NULL, default=1 | 每用户每班次最大预约数 |
| `per_user_per_day` | Integer | | 每用户每天最大预约数 |
| `per_user_per_week` | Integer | | 每用户每周最大预约数 |
| `conflict_same_shift` | String(20) | NOT NULL, default='REJECT' | 同班次冲突策略: REJECT/REPLACE |
| `conflict_overlap_time` | String(20) | NOT NULL, default='REJECT' | 时间重叠冲突策略: REJECT/ALLOW |
| `conflict_same_type_same_day` | String(20) | NOT NULL, default='ALLOW' | 同类型同日冲突策略: REJECT/ALLOW |

---

### 6.6 rule_checkin_policies — 签到策略表

| 混入 | AuditMixin |
|------|-----------|

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `rule_set_id` | String(36) | PK, FK→rule_sets.id (CASCADE) | 规则组ID |
| `require_booking` | Boolean | NOT NULL, default=True | 是否必须预约 |
| `allow_onsite_booking` | Boolean | NOT NULL, default=False | 是否允许现场补约 |
| `max_times` | Integer | NOT NULL, default=1 | 允许签到次数 |
| `audit_log` | Boolean | NOT NULL, default=True | 是否记录审计日志 |
| `grace_period_sec` | Integer | NOT NULL, default=0 | 宽限期(秒) |
| `after_grace_status` | String(30) | | 宽限后状态: LATE/ON_TIME |
| `no_checkin_after_close` | String(30) | NOT NULL, default='KEEP_BOOKED' | 截止后未签到处理: KEEP_BOOKED/AUTO_CANCEL/ABSENT |

---

### 6.7 rule_capacity_policies — 容量策略表

| 混入 | AuditMixin |
|------|-----------|

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `rule_set_id` | String(36) | PK, FK→rule_sets.id (CASCADE) | 规则组ID |
| `total_capacity` | Integer | NOT NULL, default=0 | 总容量，0不限制 |
| `per_user_capacity` | Integer | NOT NULL, default=1 | 每用户容量 |
| `waitlist_enabled` | Boolean | NOT NULL, default=False | 是否启用候补 |
| `waitlist_max_size` | Integer | NOT NULL, default=0 | 候补队列最大长度 |
| `waitlist_promote_policy` | String(50) | NOT NULL, default='MANUAL' | 候补递补策略: MANUAL/AUTO |
| `overbooking_enabled` | Boolean | NOT NULL, default=False | 是否允许超额 |
| `overbooking_max` | Integer | NOT NULL, default=0 | 超额最大数量 |

---

## 七、预约管理（3 张表）

### 7.1 appointments — 预约表

| 混入 | AuditMixin |
|------|-----------|

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `id` | String(36) | PK | 预约ID (UUID) |
| `appointment_no` | String(50) | UNIQUE, NOT NULL | 预约单号 |
| `user_id` | String(36) | FK→users.id, NOT NULL | 用户ID |
| `patient_id` | String(36) | FK→patients.id, NOT NULL | 就诊人ID |
| `doctor_id` | String(36) | FK→doctors.id, NOT NULL | 医生ID |
| `schedule_id` | String(36) | FK→schedules.id, NOT NULL | 排班ID |
| `rule_set_id` | String(36) | FK→rule_sets.id, nullable | 应用的规则组ID |
| `queue_number` | Integer | | 队列号 |
| `status` | Integer | default=1 | 状态: 0待支付 1已预约 2已签到 3候诊中 4就诊中 5已完成 6已取消 7已过期 8已关闭 |
| `sign_in_time` | DateTime | | 签到时间 |
| `call_time` | DateTime | | 叫号时间 |
| `complete_time` | DateTime | | 完成时间 |
| `cancel_time` | DateTime | | 取消时间 |
| `cancel_reason` | Text | | 取消原因 |
| `remark` | Text | | 备注 |
| `symptom_description` | Text | nullable | 病情描述/预填信息 |
| `book_open_at` | DateTime(tz) | nullable | 预约开放时间(快照) |
| `book_close_at` | DateTime(tz) | nullable | 预约截止时间(快照) |
| `checkin_open_at` | DateTime(tz) | nullable | 签到开放时间(快照) |
| `checkin_close_at` | DateTime(tz) | nullable | 签到截止时间(快照) |
| `cancel_open_at` | DateTime(tz) | nullable | 取消开放时间(快照) |
| `cancel_close_at` | DateTime(tz) | nullable | 取消截止时间(快照) |
| `checkin_count` | Integer | default=0 | 签到次数 |
| `patient_name` | String(50) | nullable | 就诊人姓名(快照) |
| `patient_phone` | String(20) | nullable | 就诊人手机(快照) |
| `doctor_name` | String(50) | nullable | 医生姓名(快照) |
| `doctor_title` | String(50) | nullable | 医生职称(快照) |
| `department_name` | String(100) | nullable | 科室名称(快照) |
| `reminder_sent` | Integer | default=0 | 是否已发送提醒: 0否 1是 |
| `reminder_sent_at` | DateTime | | 提醒发送时间 |

关联关系：
- `schedule` → Schedule
- `patient` → Patient
- `doctor` → Doctor

---

### 7.2 appointment_checkins — 签到日志表

| 混入 | 无（仅 created_at） |
|------|-----------|

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `id` | String(36) | PK | 签到日志ID (UUID) |
| `appointment_id` | String(36) | FK→appointments.id (CASCADE), NOT NULL | 预约ID |
| `checkin_time` | DateTime(tz) | NOT NULL | 签到时间 |
| `checkin_method` | String(30) | NOT NULL | 签到方式: QR_CODE/MANUAL/PHONE |
| `device_info` | String(200) | | 设备信息 |
| `location_info` | String(200) | | 位置信息 |
| `operator_id` | String(36) | | 操作人ID |
| `operator_type` | String(20) | | 操作人类型: USER/ADMIN/DOCTOR |
| `status` | String(20) | NOT NULL, default='SUCCESS' | 状态: SUCCESS/FAILED/CANCELLED |
| `fail_reason` | String(200) | | 失败原因 |
| `created_at` | DateTime(tz) | NOT NULL | 创建时间 |

索引：`(appointment_id)`, `(checkin_time)`

---

### 7.3 waitlist_entries — 候补队列表

| 混入 | 无（仅 created_at） |
|------|-----------|

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `id` | String(36) | PK | 候补ID (UUID) |
| `user_id` | String(36) | NOT NULL, INDEX | 用户ID |
| `patient_id` | String(36) | NOT NULL | 就诊人ID |
| `schedule_id` | String(36) | FK→schedules.id, NOT NULL, INDEX | 排班ID |
| `shift_type_id` | String(36) | nullable | 班次类型ID |
| `status` | String(20) | NOT NULL, default='WAITING' | 状态: WAITING/PROMOTED/CANCELLED/EXPIRED |
| `position` | Integer | NOT NULL | 在队列中的位置 |
| `priority` | Integer | NOT NULL, default=100 | 优先级(越小越高) |
| `symptom_description` | String(500) | nullable | 症状描述 |
| `created_at` | DateTime | NOT NULL | 加入候补时间 |
| `promoted_at` | DateTime | nullable | 转预约时间 |
| `cancelled_at` | DateTime | nullable | 取消时间 |
| `operator_id` | String(36) | nullable | 操作人ID |
| `operator_type` | String(20) | nullable | 操作人类型: USER/ADMIN/SYSTEM |

索引：`(schedule_id, status)`, `(created_at)`, `(schedule_id, position)`

---

## 八、诊费管理（4 张表）

### 8.1 consultation_fee_types — 诊费类型表

| 混入 | AuditMixin |
|------|-----------|

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `id` | String(36) | PK | 类型ID (UUID) |
| `store_id` | String(36) | FK→stores.id (CASCADE), nullable | 门店ID，NULL表示全局类型 |
| `name` | String(50) | NOT NULL | 诊费类型名称 |
| `code` | String(50) | INDEX | 类型编码 |
| `description` | String(255) | | 描述 |
| `sort_order` | Integer | default=0 | 排序 |
| `status` | Integer | default=1 | 状态: 0禁用 1启用 |

唯一约束：`(store_id, code)`

---

### 8.2 consultation_fee_templates — 诊费模板表（全局默认）

| 混入 | AuditMixin |
|------|-----------|

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `id` | String(36) | PK | 模板ID (UUID) |
| `fee_type_id` | String(36) | FK→consultation_fee_types.id, UNIQUE, NOT NULL | 诊费类型ID |
| `initial_fee` | Numeric(10,2) | default=0 | 初诊金额 |
| `follow_up_fee` | Numeric(10,2) | default=0 | 复诊金额 |
| `status` | Integer | default=1 | 状态: 0禁用 1启用 |

---

### 8.3 store_fee_templates — 门店诊费模板表

| 混入 | AuditMixin |
|------|-----------|

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `id` | String(36) | PK | 模板ID (UUID) |
| `store_id` | String(36) | FK→stores.id (CASCADE), NOT NULL | 门店ID |
| `fee_type_id` | String(36) | FK→consultation_fee_types.id (CASCADE), NOT NULL | 诊费类型ID |
| `initial_fee` | Numeric(10,2) | default=0 | 初诊金额 |
| `follow_up_fee` | Numeric(10,2) | default=0 | 复诊金额 |
| `status` | Integer | default=1 | 状态: 0禁用 1启用 |

唯一约束：`(store_id, fee_type_id)`

---

### 8.4 doctor_consultation_fees — 医生诊费配置表

| 混入 | AuditMixin |
|------|-----------|

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `id` | String(36) | PK | 配置ID (UUID) |
| `doctor_id` | String(36) | FK→doctors.id, NOT NULL | 医生ID |
| `store_id` | String(36) | FK→stores.id, NOT NULL | 门店ID |
| `department_id` | String(36) | FK→departments.id, NOT NULL | 科室ID |
| `fee_type_id` | String(36) | FK→consultation_fee_types.id, NOT NULL | 诊费类型ID |
| `initial_fee` | Numeric(10,2) | default=0 | 初诊金额 |
| `follow_up_fee` | Numeric(10,2) | default=0 | 复诊金额 |
| `status` | Integer | default=1 | 状态: 0禁用 1启用 |

---

## 九、病历管理（1 张表）

### 9.1 medical_records — 病历表

| 混入 | AuditMixin |
|------|-----------|

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `id` | String(36) | PK | 病历ID (UUID) |
| `record_no` | String(50) | UNIQUE, NOT NULL | 病历号 |
| `appointment_id` | String(36) | FK→appointments.id, NOT NULL | 预约ID |
| `patient_id` | String(36) | FK→patients.id, NOT NULL | 患者ID |
| `doctor_id` | String(36) | FK→doctors.id, NOT NULL | 医生ID |
| `department_id` | String(36) | FK→departments.id, NOT NULL | 科室ID |
| `chief_complaint` | Text | | 主诉 |
| `present_illness` | Text | | 现病史 |
| `past_history` | Text | | 既往史 |
| `allergy_history` | Text | | 过敏史 |
| `physical_exam` | Text | | 体格检查 |
| `auxiliary_exam` | Text | | 辅助检查 |
| `diagnosis` | Text | NOT NULL | 诊断 |
| `treatment` | Text | | 治疗方案 |
| `prescription` | Text | | 处方 |
| `advice` | Text | | 医嘱 |
| `total_fee` | Numeric(10,2) | default=0 | 总费用 |
| `status` | Integer | default=2 | 状态: 1草稿 2已完成 |
| `visit_date` | DateTime | | 就诊日期 |

---

## 十、内容管理（4 张表）

### 10.1 news — 新闻资讯表

| 混入 | AuditMixin |
|------|-----------|

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `id` | String(36) | PK | 新闻ID (UUID) |
| `store_id` | String(36) | FK→stores.id, INDEX, nullable | 所属门店ID，NULL表示全局 |
| `title` | String(200) | NOT NULL | 标题 |
| `type` | Integer | default=1 | 类型: 1医院动态 2健康科普 3通知公告 4政策法规 |
| `cover_image` | String(500) | | 封面图URL |
| `summary` | String(500) | | 摘要 |
| `content` | Text | | 内容(富文本) |
| `view_count` | Integer | default=0 | 浏览次数 |
| `is_top` | Integer | default=0 | 是否置顶: 0否 1是 |
| `status` | Integer | default=0 | 状态: 0草稿 1已发布 |
| `publish_time` | DateTime | | 发布时间 |

---

### 10.2 notices — 公告通知表

| 混入 | AuditMixin |
|------|-----------|

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `id` | String(36) | PK | 公告ID (UUID) |
| `store_id` | String(36) | FK→stores.id, INDEX, nullable | 所属门店ID，NULL表示全局 |
| `title` | String(200) | NOT NULL | 标题 |
| `type` | Integer | default=1 | 类型: 1系统公告 2停诊通知 3活动通知 4重要提醒 |
| `content` | Text | | 内容 |
| `is_top` | Integer | default=0 | 是否置顶: 0否 1是 |
| `status` | Integer | default=0 | 状态: 0草稿 1已发布 |
| `publish_time` | DateTime | | 发布时间 |

---

### 10.3 banners — 轮播图表

| 混入 | AuditMixin |
|------|-----------|

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `id` | String(36) | PK | 轮播图ID (UUID) |
| `store_id` | String(36) | FK→stores.id, INDEX, nullable | 所属门店ID，NULL表示全局 |
| `title` | String(100) | | 标题 |
| `image_url` | String(500) | NOT NULL | 图片URL |
| `link_type` | Integer | default=0 | 链接类型: 0无跳转 1内部页面 2外部链接 3新闻详情 |
| `link_url` | String(500) | | 跳转链接 |
| `position` | String(50) | default='home' | 显示位置: home/department/profile |
| `sort_order` | Integer | default=0 | 排序 |
| `status` | Integer | default=1 | 状态: 0禁用 1启用 |

---

### 10.4 booking_notices — 预约须知表

| 混入 | AuditMixin |
|------|-----------|

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `id` | String(36) | PK | 须知ID (UUID) |
| `type` | String(50) | NOT NULL | 类型: BOOKING/VISIT/REFUND |
| `title` | String(100) | nullable | 标题 |
| `content` | Text | nullable | 内容 |
| `sort_order` | Integer | default=0 | 排序 |
| `status` | Integer | default=1 | 状态: 0禁用 1启用 |

---

## 十一、消息通知（3 张表）

### 11.1 messages — 消息表

| 混入 | AuditMixin |
|------|-----------|

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `id` | String(36) | PK | 消息ID (UUID) |
| `store_id` | String(36) | FK→stores.id, INDEX, nullable | 所属门店ID，NULL表示全局 |
| `user_id` | String(36) | NOT NULL, INDEX | 接收用户ID |
| `user_type` | String(20) | NOT NULL | 用户类型: patient/doctor |
| `title` | String(200) | NOT NULL | 消息标题 |
| `content` | Text | | 消息内容 |
| `message_type` | String(20) | default="system" | 消息类型: appointment/consultation/schedule/system/stop_clinic/feedback |
| `related_id` | String(36) | | 关联业务ID |
| `is_read` | Integer | default=0 | 是否已读: 0未读 1已读 |
| `read_at` | DateTime | | 阅读时间 |
| `extra_data` | Text | | 额外数据(JSON) |

---

### 11.2 message_templates — 消息模板表

| 混入 | AuditMixin |
|------|-----------|

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `id` | String(36) | PK | 模板ID (UUID) |
| `code` | String(50) | UNIQUE, NOT NULL | 模板编码 |
| `name` | String(100) | NOT NULL | 模板名称 |
| `message_type` | String(20) | NOT NULL | 消息类型 |
| `title_template` | String(200) | NOT NULL | 标题模板 |
| `content_template` | Text | NOT NULL | 内容模板 |
| `description` | String(255) | | 模板说明 |
| `status` | Integer | default=1 | 状态: 0禁用 1启用 |

---

### 11.3 email_templates — 邮件模板表

| 混入 | AuditMixin |
|------|-----------|

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `id` | String(36) | PK | 模板ID (UUID) |
| `code` | String(50) | UNIQUE, NOT NULL | 模板编码 |
| `name` | String(100) | NOT NULL | 模板名称 |
| `template_type` | String(30) | default="custom" | 模板类型: appointment_confirm/appointment_remind/appointment_cancel/stop_clinic/custom |
| `subject_template` | String(200) | NOT NULL | 邮件主题模板 |
| `content_template` | Text | NOT NULL | 邮件内容模板(HTML) |
| `description` | String(255) | | 模板说明 |
| `status` | Integer | default=1 | 状态: 0禁用 1启用 |

---

## 十二、系统配置（2 张表）

### 12.1 system_settings — 系统设置表

| 混入 | AuditMixin |
|------|-----------|

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `id` | String(36) | PK | 设置ID (UUID) |
| `store_id` | String(36) | FK→stores.id (CASCADE), nullable | 门店ID，为空表示全局配置 |
| `category` | String(50) | NOT NULL | 分类: booking/hospital/wechat/sms/time_periods/booking_fields/patient_card/image |
| `key` | String(100) | NOT NULL | 设置项键名 |
| `value` | Text | | 设置项值 |
| `description` | String(200) | | 描述 |

索引：`(store_id, category)`, `(store_id, category, key)`

---

### 12.2 store_visit_type_configs — 门店复诊规则配置表

| 混入 | AuditMixin |
|------|-----------|

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `id` | String(36) | PK | 配置ID (UUID) |
| `store_id` | String(36) | FK→stores.id (CASCADE), UNIQUE, NOT NULL | 门店ID |
| `time_limit` | Integer | NOT NULL, default=30 | 复诊时间限制值 |
| `time_unit` | String(10) | NOT NULL, default="days" | 时间单位: hours/days |
| `scope` | String(20) | NOT NULL, default="same_doctor" | 复诊范围: same_doctor/same_department/same_store |
| `status` | Integer | default=1 | 状态: 0禁用 1启用 |

---

## 十三、日志与审计（3 张表）

### 13.1 operation_logs — 操作日志表

| 混入 | 无（仅 created_at） |
|------|-----------|

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `id` | String(36) | PK | 日志ID (UUID) |
| `admin_id` | String(36) | FK→admins.id | 操作人ID |
| `admin_name` | String(50) | | 操作人姓名 |
| `module` | String(50) | | 模块 |
| `action` | String(100) | | 操作 |
| `method` | String(10) | | 请求方法 |
| `path` | String(255) | | 请求路径 |
| `params` | Text | | 请求参数 |
| `result` | String(20) | | 结果 |
| `ip` | String(50) | | IP地址 |
| `user_agent` | String(255) | | User-Agent |
| `duration` | Integer | | 耗时(毫秒) |
| `created_at` | DateTime | | 创建时间 |

---

### 13.2 user_behavior_logs — 用户行为日志表

| 混入 | 无（仅 created_at） |
|------|-----------|

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `id` | String(36) | PK | 日志ID (UUID) |
| `platform` | String(20) | NOT NULL | 平台: admin/h5/miniapp |
| `user_id` | String(36) | nullable | 用户ID |
| `session_id` | String(64) | nullable | 会话ID |
| `event_type` | String(30) | NOT NULL | 事件类型: page_view/page_leave/click/search/custom |
| `page_path` | String(255) | nullable | 页面路径 |
| `page_title` | String(100) | nullable | 页面标题 |
| `element_id` | String(100) | nullable | 元素ID |
| `element_text` | String(200) | nullable | 元素文本 |
| `search_keyword` | String(200) | nullable | 搜索关键词 |
| `event_name` | String(100) | nullable | 自定义事件名称 |
| `duration` | Integer | nullable | 停留时长(毫秒) |
| `referrer` | String(255) | nullable | 来源页面 |
| `extra_data` | Text | nullable | 额外数据(JSON) |
| `ip` | String(50) | nullable | IP地址 |
| `user_agent` | String(500) | nullable | User-Agent |
| `device_type` | String(20) | nullable | 设备类型: desktop/mobile/tablet |
| `browser` | String(50) | nullable | 浏览器 |
| `os` | String(50) | nullable | 操作系统 |
| `created_at` | DateTime | | 创建时间 |

---

### 13.3 point_logs — 积分流水表

| 混入 | AuditMixin |
|------|-----------|

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `id` | String(36) | PK | 流水ID (UUID) |
| `user_id` | String(36) | FK→users.id, NOT NULL, INDEX | 用户ID |
| `change_amount` | Integer | NOT NULL | 变更积分（正增负减） |
| `balance` | Integer | NOT NULL | 变更后余额 |
| `type` | Integer | default=4 | 类型: 1消费 2充值 3赠送 4手动调整 |
| `remark` | String(255) | | 备注 |
| `operator_id` | String(36) | | 操作人ID |

---

## 十四、用户服务（3 张表）

### 14.1 blacklists — 黑名单表

| 混入 | AuditMixin |
|------|-----------|

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `id` | String(36) | PK | 黑名单ID (UUID) |
| `user_id` | String(36) | FK→users.id, nullable | 用户ID |
| `store_id` | String(36) | FK→stores.id, nullable | 门店ID，不选则针对所有门店 |
| `keyword` | String(50) | | 手机号或身份证关键词 |
| `reason` | String(500) | | 黑名单原因/备注 |
| `no_show_count` | Integer | default=0 | 爽约次数（自动触发时记录） |
| `source` | Integer | default=1 | 来源: 1手动添加 2自动触发 |
| `expire_at` | DateTime | | 解禁时间 |
| `released_at` | DateTime | | 实际解禁时间 |
| `status` | Integer | default=1 | 状态: 1生效 0已解禁 |

---

### 14.2 feedbacks — 用户反馈表

| 混入 | AuditMixin |
|------|-----------|

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `id` | String(36) | PK | 反馈ID (UUID) |
| `user_id` | String(36) | NOT NULL, INDEX | 用户ID |
| `user_type` | String(20) | default="patient" | 用户类型: patient/doctor |
| `feedback_type` | String(20) | default="suggestion" | 反馈类型: suggestion/complaint/bug/other |
| `title` | String(200) | NOT NULL | 反馈标题 |
| `content` | Text | NOT NULL | 反馈内容 |
| `images` | Text | | 图片URL列表(JSON) |
| `contact` | String(50) | | 联系方式 |
| `status` | String(20) | default="pending" | 状态: pending/processing/resolved/closed |
| `handler_id` | String(36) | | 处理人ID |
| `reply` | Text | | 回复内容 |
| `handled_at` | DateTime | | 处理时间 |

---

### 14.3 user_favorites — 用户收藏表

| 混入 | AuditMixin |
|------|-----------|

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `id` | String(36) | PK | 收藏ID (UUID) |
| `user_id` | String(36) | FK→users.id, NOT NULL | 用户ID |
| `target_type` | String(20) | NOT NULL | 收藏类型: doctor/department |
| `target_id` | String(36) | NOT NULL | 收藏目标ID |

唯一约束：`(user_id, target_type, target_id)`
