# 业务域关系图

> 基于 SQLAlchemy ORM 实际模型生成，最后更新：2026-02-06

---

## 全局业务域总览

```mermaid
graph TB
    subgraph UserAuth["用户与认证 (2表)"]
        users["users<br/>用户表"]
        patients["patients<br/>就诊人表"]
    end

    subgraph AdminPerm["权限与管理 (6表)"]
        admins["admins<br/>管理员表"]
        roles["roles<br/>角色表"]
        permissions["permissions<br/>权限表"]
        role_permissions["role_permissions"]
        admin_stores["admin_stores"]
        admin_login_history["admin_login_history"]
    end

    subgraph Org["机构管理 (2表)"]
        stores["stores<br/>门店表"]
        departments["departments<br/>科室表"]
    end

    subgraph Doctor["医生管理 (2表)"]
        doctors["doctors<br/>医生表"]
        doctor_booking_settings["doctor_booking_settings"]
    end

    subgraph Schedule["排班管理 (6表)"]
        schedule_templates["schedule_templates"]
        schedules["schedules<br/>排班表"]
        rest_days["rest_days"]
        schedule_suspensions["schedule_suspensions"]
        schedule_generation_logs["schedule_generation_logs"]
        leave_requests["leave_requests"]
    end

    subgraph Rules["规则引擎 (7表)"]
        shift_types["shift_types"]
        rule_sets["rule_sets"]
        rule_set_shift_types["rule_set_shift_types"]
        rule_windows["rule_windows"]
        rule_booking_policies["rule_booking_policies"]
        rule_checkin_policies["rule_checkin_policies"]
        rule_capacity_policies["rule_capacity_policies"]
    end

    subgraph Appt["预约管理 (3表)"]
        appointments["appointments<br/>预约表"]
        appointment_checkins["appointment_checkins"]
        waitlist_entries["waitlist_entries"]
    end

    %% 核心数据流
    users -->|1:N| patients
    patients -->|N:1| appointments
    doctors -->|1:N| schedules
    schedules -->|1:N| appointments
    stores -->|1:N| doctors
    departments -->|1:N| doctors
    schedule_templates -->|1:N| schedules
    shift_types -->|M:N| rule_sets
    rule_sets -.->|匹配| appointments
    admins -->|M:N| stores
```

---

## 一、用户与认证

```mermaid
erDiagram
    users ||--o{ patients : "一个用户多个就诊人"
    users ||--o{ point_logs : "积分流水"
    users {
        string id PK "UUID"
        string phone UK "手机号"
        string password_hash "密码哈希"
        string nickname "昵称"
        string openid UK "微信OpenID"
        string unionid UK "微信UnionID"
        int gender "0未知 1男 2女"
        int status "0禁用 1正常"
        int points "当前积分"
    }
    patients {
        string id PK "UUID"
        string user_id FK "所属用户"
        string store_id FK "首次就诊门店"
        string name "姓名"
        string phone "手机号"
        string id_card "身份证号"
        string card_no UK "就诊卡编号"
        int source "1用户添加 2管理员添加"
    }
    point_logs {
        string id PK "UUID"
        string user_id FK "用户ID"
        int change_amount "变更积分"
        int balance "变更后余额"
        int type "1消费 2充值 3赠送 4调整"
    }
```

---

## 二、权限与管理

```mermaid
erDiagram
    admins }o--|| roles : "多对一"
    admins }o--o{ stores : "多对多(admin_stores)"
    roles ||--o{ role_permissions : "角色权限"
    admins ||--o{ admin_login_history : "登录历史"
    admins ||--o{ operation_logs : "操作日志"

    admins {
        string id PK "UUID"
        string username UK "用户名"
        string role_id FK "角色"
        string current_store_id FK "当前门店"
        int status "0禁用 1启用"
    }
    roles {
        string id PK "UUID"
        string name "角色名称"
        string code UK "角色编码"
        text permissions "权限JSON"
    }
    permissions {
        string id PK "UUID"
        string code UK "权限码"
        string name "权限名称"
        string type "menu/button"
        string parent_code "父级权限码"
    }
```

---

## 三、机构管理

```mermaid
erDiagram
    stores ||--o{ departments : "一个门店多个科室"
    departments ||--o{ departments : "自关联(父子科室)"
    stores ||--o{ doctors : "一个门店多个医生"
    departments ||--o{ doctors : "一个科室多个医生"

    stores {
        string id PK "UUID"
        string name "门店名称"
        string code UK "门店编码"
        string address "地址"
        time opening_time "开始营业"
        time closing_time "结束营业"
        int status "0停业 1营业 2禁用"
        string wechat_app_id "小程序AppID"
    }
    departments {
        string id PK "UUID"
        string name "科室名称"
        string parent_id FK "父科室"
        string store_id FK "门店"
        int is_hot "是否热门"
        int is_final "是否终极科室"
        int is_recommended "是否推荐"
    }
```

---

## 四、医生管理

```mermaid
erDiagram
    doctors }o--|| departments : "所属科室"
    doctors }o--|| stores : "所属门店"
    doctors ||--o{ doctor_booking_settings : "预约设置"
    doctors ||--o{ doctor_consultation_fees : "诊费配置"

    doctors {
        string id PK "UUID"
        string store_id FK "门店"
        string department_id FK "科室"
        string name "姓名"
        string title "职称"
        string specialty "擅长"
        int is_recommended "是否推荐"
        int status "0禁用 1正常"
    }
    doctor_booking_settings {
        string id PK "UUID"
        string store_id FK "门店"
        string doctor_id FK "医生"
        int booking_start_offset "开始偏移天数"
        int booking_range_days "预约范围天数"
        string release_time "放号时间HH:mm"
    }
```

---

## 五、排班管理

```mermaid
erDiagram
    schedule_templates ||--o{ schedules : "模板生成排班"
    doctors ||--o{ schedules : "医生排班"
    doctors ||--o{ schedule_suspensions : "停诊记录"
    doctors ||--o{ leave_requests : "停诊申请"
    stores ||--o{ rest_days : "休息日"
    schedule_templates ||--o{ schedule_generation_logs : "生成日志"

    schedule_templates {
        string id PK "UUID"
        string store_id FK "门店"
        string doctor_id FK "医生"
        string department_id FK "科室"
        text weekdays "星期JSON"
        time start_time "开始"
        time end_time "结束"
        int slot_count "班次数"
        int slot_capacity "每班人数"
    }
    schedules {
        string id PK "UUID"
        string doctor_id FK "医生"
        string store_id FK "门店"
        string template_id FK "来源模板"
        string shift_type_id FK "班次类型"
        date schedule_date "排班日期"
        int total_slots "总号源"
        int booked_slots "已预约数"
        int status "0停诊 1正常"
    }
    rest_days {
        string id PK "UUID"
        string store_id FK "门店"
        text doctor_ids "医生ID列表JSON"
        date start_date "开始"
        date end_date "结束"
    }
    schedule_suspensions {
        string id PK "UUID"
        string doctor_id FK "医生"
        date suspension_date "停诊日期"
        text schedule_ids "排班ID JSON"
    }
```

---

## 六、规则引擎

```mermaid
erDiagram
    rule_sets ||--o{ rule_windows : "时间窗"
    rule_sets ||--o| rule_booking_policies : "预约策略"
    rule_sets ||--o| rule_checkin_policies : "签到策略"
    rule_sets ||--o| rule_capacity_policies : "容量策略"
    rule_sets }o--o{ shift_types : "适用班次类型"

    rule_sets {
        string id PK "UUID"
        string name "规则组名称"
        bool enabled "是否启用"
        int priority "优先级"
        string time_source "SERVER/CLIENT"
        string timezone_source "HOSPITAL/SHIFT/USER"
    }
    shift_types {
        string id PK "UUID"
        string code UK "OPD/CHECKUP等"
        string name "类型名称"
        bool enabled "是否启用"
    }
    rule_windows {
        string id PK "UUID"
        string action "BOOK/CHECKIN/CANCEL"
        string reference_point "SHIFT_START等"
        int open_offset_sec "开放偏移秒"
        int close_offset_sec "截止偏移秒"
        string fail_policy "REJECT/ALLOW等"
    }
    rule_booking_policies {
        string rule_set_id PK "规则组ID"
        int per_user_per_shift "每用户每班次"
        int per_user_per_day "每用户每天"
        string conflict_same_shift "冲突策略"
    }
    rule_checkin_policies {
        string rule_set_id PK "规则组ID"
        bool require_booking "需要预约"
        int max_times "允许次数"
        int grace_period_sec "宽限期秒"
    }
    rule_capacity_policies {
        string rule_set_id PK "规则组ID"
        int total_capacity "总容量"
        bool waitlist_enabled "启用候补"
        bool overbooking_enabled "允许超额"
    }
```

---

## 七、预约管理（核心流程）

```mermaid
erDiagram
    users ||--o{ appointments : "用户预约"
    patients ||--o{ appointments : "就诊人预约"
    schedules ||--o{ appointments : "排班预约"
    doctors ||--o{ appointments : "医生预约"
    appointments ||--o{ appointment_checkins : "签到日志"
    schedules ||--o{ waitlist_entries : "候补队列"
    rule_sets ||--o{ appointments : "应用规则"

    appointments {
        string id PK "UUID"
        string appointment_no UK "预约单号"
        string user_id FK "用户"
        string patient_id FK "就诊人"
        string doctor_id FK "医生"
        string schedule_id FK "排班"
        string rule_set_id FK "规则组"
        int queue_number "队列号"
        int status "0-8 多状态"
        string patient_name "姓名快照"
        string doctor_name "医生快照"
    }
    appointment_checkins {
        string id PK "UUID"
        string appointment_id FK "预约"
        string checkin_method "QR_CODE/MANUAL/PHONE"
        string status "SUCCESS/FAILED"
    }
    waitlist_entries {
        string id PK "UUID"
        string schedule_id FK "排班"
        string user_id "用户"
        int position "队列位置"
        string status "WAITING/PROMOTED等"
    }
```

---

## 八、诊费管理（三级继承）

诊费配置遵循 **全局模板 < 门店模板 < 医生配置** 的优先级覆盖规则。

```mermaid
erDiagram
    consultation_fee_types ||--o{ consultation_fee_templates : "全局默认"
    consultation_fee_types ||--o{ store_fee_templates : "门店覆盖"
    consultation_fee_types ||--o{ doctor_consultation_fees : "医生覆盖"
    stores ||--o{ store_fee_templates : "门店诊费"
    doctors ||--o{ doctor_consultation_fees : "医生诊费"

    consultation_fee_types {
        string id PK "UUID"
        string store_id FK "门店(全局为NULL)"
        string name "类型名称"
        string code "编码"
    }
    consultation_fee_templates {
        string id PK "UUID"
        string fee_type_id FK "诊费类型"
        decimal initial_fee "初诊金额"
        decimal follow_up_fee "复诊金额"
    }
    store_fee_templates {
        string id PK "UUID"
        string store_id FK "门店"
        string fee_type_id FK "诊费类型"
        decimal initial_fee "初诊金额"
        decimal follow_up_fee "复诊金额"
    }
    doctor_consultation_fees {
        string id PK "UUID"
        string doctor_id FK "医生"
        string store_id FK "门店"
        string fee_type_id FK "诊费类型"
        decimal initial_fee "初诊金额"
        decimal follow_up_fee "复诊金额"
    }
```

```mermaid
graph LR
    A["consultation_fee_templates<br/>全局模板"] -->|"门店覆盖"| B["store_fee_templates<br/>门店模板"]
    B -->|"医生覆盖"| C["doctor_consultation_fees<br/>医生配置"]
    C -->|"最终生效"| D["实际诊费"]
```

---

## 九、预约核心数据流

```mermaid
sequenceDiagram
    participant U as 用户(users)
    participant P as 就诊人(patients)
    participant S as 排班(schedules)
    participant R as 规则引擎(rule_sets)
    participant A as 预约(appointments)
    participant W as 候补(waitlist_entries)
    participant C as 签到(appointment_checkins)
    participant M as 病历(medical_records)

    U->>P: 添加就诊人
    U->>S: 查看可预约排班
    S->>R: 匹配规则组(按shift_type)
    R-->>S: 返回时间窗+策略
    U->>A: 创建预约
    Note over A: 保存规则快照<br/>(book/checkin/cancel时间窗)
    alt 号源已满且开启候补
        A-->>W: 进入候补队列
        Note over W: position排序等待
        W-->>A: 有号源时递补为预约
    end
    U->>C: 到院签到
    Note over C: 校验签到时间窗<br/>记录签到日志
    A->>M: 就诊完成后创建病历
```

---

## 十、多租户(门店)数据隔离关系

以下表通过 `store_id` 实现门店级数据隔离：

```mermaid
graph TB
    Store["stores 门店表"]
    Store --- departments
    Store --- doctors
    Store --- schedules
    Store --- schedule_templates
    Store --- rest_days
    Store --- schedule_suspensions
    Store --- doctor_booking_settings
    Store --- system_settings
    Store --- store_visit_type_configs
    Store --- consultation_fee_types
    Store --- store_fee_templates
    Store --- doctor_consultation_fees
    Store --- news
    Store --- notices
    Store --- banners
    Store --- messages
    Store --- blacklists
    Store --- patients["patients(首次就诊门店)"]
    Store --- admin_stores["admin_stores(管理员绑定)"]
```
