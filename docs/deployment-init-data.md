# 系统上线数据初始化指南

本文档描述医院预约挂号系统发布到线上后需要初始化的基础数据。

---

## 一、必须初始化的核心数据

### 1. 权限数据（permissions）

**脚本位置**: `apps/server/scripts/init_permissions.py`

系统定义了完整的权限树，包含 13 个主菜单模块和对应的按钮权限：

| 模块 | 权限码 | 说明 |
|------|--------|------|
| 仪表盘 | dashboard | 首页数据展示 |
| 门店管理 | store | 门店增删改查 |
| 科室管理 | department | 科室增删改查 |
| 医生管理 | doctor | 医生增删改查、预约设置 |
| 排班管理 | schedule | 排班、模板、休息日、停诊管理 |
| 预约管理 | appointment | 预约列表、状态更新、取消、统计 |
| 患者管理 | patient | 患者信息管理 |
| 停诊审核 | leave-request | 停诊申请审批 |
| 用户反馈 | feedback | 用户反馈处理 |
| 消息管理 | message | 消息发送管理 |
| 内容管理 | content | 新闻、公告、轮播图管理 |
| 统计分析 | statistics | 数据统计报表 |
| 系统设置 | system | 角色、用户、配置、诊费、日志管理 |

**执行命令**:

```bash
cd apps/server && python scripts/init_permissions.py
```

---

### 2. 角色数据（roles）

**脚本位置**: `apps/server/scripts/init_roles.py`

系统采用三级角色体系：

| 角色编码 | 角色名称 | 权限说明 |
|---------|---------|----------|
| SUPER_ADMIN | 超级管理员 | 所有权限，无门店限制，可管理所有门店数据 |
| STORE_ADMIN | 门店管理员 | 可管理绑定门店的数据和用户，不能管理角色 |
| STORE_USER | 门店用户 | 基础查看权限，具体权限由管理员分配 |

**执行命令**:

```bash
cd apps/server && python scripts/init_roles.py
```

> **提示**: 使用 `--force` 参数可强制重置所有角色：`python scripts/init_roles.py --force`

---

### 3. 超级管理员账号（admins）

**脚本位置**: `apps/server/scripts/init_data.py`

默认管理员账号信息：

| 字段 | 默认值 | 说明 |
|------|-------|------|
| username | admin | 登录用户名 |
| password | admin123 | 登录密码 |
| name | 系统管理员 | 显示名称 |
| phone | 13800000000 | 联系电话 |
| email | admin@hospital.com | 邮箱 |

**执行命令**:

```bash
cd apps/server && python scripts/init_data.py
```

> ⚠️ **安全警告**: 上线后务必立即修改默认密码！

---

### 4. 消息模板（message_templates）

**脚本位置**: `apps/server/scripts/init_message_templates.py`

系统预置 10 个核心消息模板：

| 模板编码 | 模板名称 | 触发场景 |
|---------|---------|---------|
| appointment_success | 预约成功通知 | 患者预约成功后发送 |
| appointment_cancel | 预约取消通知 | 患者取消预约后发送 |
| appointment_reminder | 就诊提醒 | 就诊前一天发送 |
| sign_in_success | 签到成功通知 | 患者签到成功后发送 |
| call_patient | 叫号通知 | 叫号时发送 |
| stop_clinic_patient | 停诊通知-患者 | 医生停诊时通知患者 |
| stop_clinic_approved | 停诊申请通过 | 停诊申请通过时通知医生 |
| stop_clinic_rejected | 停诊申请拒绝 | 停诊申请拒绝时通知医生 |
| schedule_change_approved | 调班申请通过 | 调班申请通过时通知医生 |
| feedback_reply | 反馈回复通知 | 反馈回复时通知用户 |

**执行命令**:

```bash
cd apps/server && python scripts/init_message_templates.py
```

---

## 二、需要通过后台配置的业务数据

### 5. 门店数据（stores）

至少需要创建一个门店，必填信息包括：

- **门店名称**: 如「总院」「XX分院」
- **门店编码**: 唯一标识，如 `main`、`branch_east`
- **地址**: 详细地址
- **联系电话**: 门店电话
- **营业时间**: 如 `08:00-17:30`
- **门店描述**: 简要介绍

### 6. 科室数据（departments）

根据实际业务创建科室，常见科室参考：

- 内科、外科、儿科、妇产科
- 口腔科、眼科、耳鼻喉科
- 皮肤科、中医科、康复科
- 体检中心等

每个科室需要指定所属门店。

### 7. 医生数据（doctors）

创建医生账号，必填信息包括：

| 字段 | 说明 |
|------|------|
| 姓名 | 医生真实姓名 |
| 手机号 | 登录账号，需唯一 |
| 登录密码 | 医生端登录密码 |
| 所属门店 | 选择门店 |
| 所属科室 | 选择科室 |
| 职称 | 主任医师/副主任医师/主治医师/医师等 |
| 专长 | 擅长领域 |
| 简介 | 个人介绍 |

---

## 三、系统配置数据

### 8. 系统设置（system_settings）

系统设置分为多个分类，首次使用时会自动创建默认值：

#### 预约配置 (booking)

| 配置项 | 默认值 | 说明 |
|--------|-------|------|
| advance_days | 10 | 可提前预约天数 |
| same_day_booking | true | 是否允许当天预约 |
| cancel_hours | 2 | 就诊前 N 小时内不可取消 |
| per_day_limit | 3 | 每人每天预约限制数量 |
| per_doctor_limit | 1 | 每人对同一医生的预约限制 |
| no_show_limit | 3 | 爽约 N 次进入黑名单 |
| blacklist_days | 30 | 黑名单禁止预约天数 |

#### 医院信息 (hospital)

| 配置项 | 说明 |
|--------|------|
| name | 医院名称 |
| level | 医院等级（三甲/三乙/二甲等） |
| address | 医院地址 |
| phone | 联系电话 |
| work_time | 工作时间 |
| introduction | 医院简介 |
| logo | 医院 Logo 图片地址 |

#### 微信配置 (wechat)

| 配置项 | 说明 |
|--------|------|
| app_id | 小程序 AppID |
| app_secret | 小程序 Secret |
| mch_id | 微信支付商户号 |
| api_key | 微信支付 API 密钥 |
| notify_url | 支付回调地址 |

#### 短信配置 (sms)

| 配置项 | 说明 |
|--------|------|
| provider | 短信服务商（默认 aliyun） |
| access_key_id | AccessKey ID |
| access_key_secret | AccessKey Secret |
| sign_name | 短信签名 |
| template_code_booking | 预约成功模板编码 |
| template_code_remind | 就诊提醒模板编码 |
| template_code_cancel | 取消预约模板编码 |

#### 时段配置 (time_periods)

默认配置为两个时段：

```json
[
  {"key": "morning", "name": "上午", "startTime": "06:00", "endTime": "12:00"},
  {"key": "afternoon", "name": "下午", "startTime": "12:00", "endTime": "18:00"}
]
```

可根据实际情况调整或增加时段（如夜间门诊）。

#### 就诊卡配置 (patient_card)

| 配置项 | 默认值 | 说明 |
|--------|-------|------|
| card_name | 就诊卡 | 就诊卡名称 |
| card_description | - | 描述文字（限16字） |
| max_cards_per_user | 5 | 每用户可建卡数量 |
| show_on_homepage | false | 首页是否展示 |

---

## 四、可选数据（根据业务需要）

### 9. 诊费类型（consultation_fee_types）

如需使用诊费功能，需配置诊费类型：

| 类型示例 | 编码 | 说明 |
|---------|------|------|
| 普通门诊 | normal | 常规挂号诊费 |
| 专家门诊 | expert | 专家诊费 |
| 特需门诊 | special | 特需服务诊费 |

配置完诊费类型后，还需配置：
- **全局诊费模板**: 系统默认诊费标准
- **门店诊费模板**: 各门店的诊费标准（可覆盖全局）
- **医生诊费配置**: 各医生的具体诊费

### 10. 内容数据

| 内容类型 | 说明 |
|---------|------|
| 轮播图（banners） | 首页轮播广告图 |
| 公告（notices） | 系统公告、停诊通知、活动通知 |
| 新闻资讯（news） | 医院新闻、健康资讯 |
| 预约须知（booking_notices） | 预约、就诊、退款须知 |

---

## 五、初始化执行顺序

### 方式一：使用独立脚本（推荐生产环境）

```bash
cd apps/server

# 1. 确保数据库已创建并运行迁移
alembic upgrade head

# 2. 初始化权限（必须最先执行）
python scripts/init_permissions.py

# 3. 初始化角色（依赖权限数据）
python scripts/init_roles.py

# 4. 初始化基础数据（管理员账号）
python scripts/init_data.py

# 5. 初始化消息模板
python scripts/init_message_templates.py
```

### 方式二：使用演示数据脚本（仅用于测试环境）

```bash
cd apps/server

# 初始化完整演示数据（包含测试门店、科室、医生等）
python scripts/init_demo_data.py
```

演示数据包含：
- 2 个门店（总院 + 西城分院）
- 3 个管理员账号
- 10 个科室
- 17 个医生
- 3 个测试用户

---

## 六、上线安全检查清单

- [ ] **修改默认密码**: 超级管理员默认密码 `admin123` 必须立即修改
- [ ] **配置微信小程序**: 填入真实的 AppID 和 Secret
- [ ] **配置微信支付**: 填入商户号和 API 密钥（如需支付功能）
- [ ] **配置短信服务**: 填入阿里云短信的 AccessKey 和模板
- [ ] **配置医院信息**: 完善医院名称、地址、电话等基本信息
- [ ] **创建业务数据**: 添加真实的门店、科室、医生信息
- [ ] **配置排班**: 为医生设置排班模板或具体排班
- [ ] **测试预约流程**: 完整测试一次预约流程确保正常
- [ ] **备份数据**: 初始化完成后做一次数据库备份

---

## 七、相关脚本说明

| 脚本文件 | 功能说明 |
|---------|---------|
| `init_permissions.py` | 初始化系统权限数据 |
| `init_roles.py` | 初始化三级角色体系 |
| `init_data.py` | 初始化超级管理员和基础数据 |
| `init_message_templates.py` | 初始化消息模板 |
| `init_demo_data.py` | 初始化完整演示数据（测试用） |
| `init_doctors.py` | 单独初始化测试医生数据 |
| `init_db.py` | 初始化数据库表结构 |

