下面给你一套可直接落地的 ER 架构图（预约挂号系统完整版），我分成两层给你看：
	•	① 总体架构图（全局关系）
	•	② 核心表 ER（带字段级别说明）

我用“接近 ER 图的结构表达 + 关系说明”，你可以很容易转成 draw.io / PowerDesigner / dbdiagram。

⸻

一、总体 ER 架构图（全局）

[Tenant]（租户，可选）
   │
   ├── [Organization]（组织：集团/门店/科室）
   │         │
   │         ├── [UserOrganization] ─── [User]
   │         │            │
   │         │            ├── [Role]
   │         │            │      └── [RolePermission] ─── [Permission]
   │         │            │
   │         │            └── [Position]
   │         │
   │         └──（组织树 parent_id）
   │
   ├── [Doctor]（医生 = User扩展）
   │
   ├── [Patient]
   │
   ├── [Schedule]（排班）
   │         └── [Slot]（号源）
   │
   ├── [Appointment]（预约）
   │
   ├── [Service]（服务项目）
   │
   ├── [Order]（订单，可选）
   │
   ├── [Dict]（字典）
   │
   └── [AuditLog]（操作日志）


⸻

二、核心 ER（带关系说明）

⸻

1️⃣ 组织体系（核心骨架）

Organization

Organization
------------
id (PK)
tenant_id
name
type            -- hospital / branch / department
parent_id       -- 树结构
path            -- 路径（可选优化）
status
created_at

关系：

Organization 1 —— N Organization（自关联树）


⸻

2️⃣ 用户 & 权限体系（RBAC）

User

User
------------
id (PK)
username
password
phone
status
created_at


⸻

UserOrganization（关键中间表）

UserOrganization
------------
id (PK)
user_id
org_id
role_id
position_id
is_primary


⸻

Role

Role
------------
id (PK)
name
code
data_scope     -- ALL / ORG / SELF


⸻

Permission

Permission
------------
id (PK)
name
code
module


⸻

RolePermission

RolePermission
------------
role_id
permission_id


⸻

Position（岗位）

Position
------------
id (PK)
name
code


⸻

关系总结：

User 1 —— N UserOrganization N —— 1 Organization
UserOrganization N —— 1 Role
UserOrganization N —— 1 Position

Role N —— N Permission（通过 RolePermission）


⸻

3️⃣ 医疗业务核心

⸻

Doctor（医生扩展）

Doctor
------------
id (PK)
user_id
title           -- 主治医师
specialty       -- 擅长

User 1 —— 1 Doctor


⸻

Patient（患者）

Patient
------------
id (PK)
name
phone
gender
birthday


⸻

4️⃣ 排班系统（核心调度）

⸻

Schedule（排班）

Schedule
------------
id (PK)
doctor_id
org_id
department_id
date
status


⸻

Slot（号源）

Slot
------------
id (PK)
schedule_id
time_start
time_end
quota_total
quota_used


⸻

关系：

Doctor 1 —— N Schedule
Organization（科室）1 —— N Schedule
Schedule 1 —— N Slot


⸻

5️⃣ 预约系统（核心业务）

⸻

Appointment

Appointment
------------
id (PK)
patient_id
doctor_id
org_id
department_id
schedule_id
slot_id
status
source
created_by
created_at


⸻

关系：

Patient 1 —— N Appointment
Doctor 1 —— N Appointment
Schedule 1 —— N Appointment
Slot 1 —— N Appointment


⸻

6️⃣ 服务 & 订单（可选）

⸻

Service

Service
------------
id (PK)
name
price
duration


⸻

Order

Order
------------
id (PK)
appointment_id
amount
status
payment_time


⸻

7️⃣ 支撑系统

⸻

Dict（字典）

Dict
------------
id
type
key
value


⸻

AuditLog（审计日志）

AuditLog
------------
id
operator_id
action
target_type
target_id
before
after
created_at


⸻

三、最核心的几条“生命线关系”（重点理解）

⸻

🔥 1. 用户权限链路

User
 → UserOrganization
   → Role
     → Permission


⸻

🔥 2. 医疗业务链路

Doctor → Schedule → Slot → Appointment → Patient


⸻

🔥 3. 数据权限控制链路

User → Organization → (科室/门店) → Appointment数据范围


⸻

四、如果你要画图（推荐工具）

你可以直接导入：

👉 dbdiagram.io 格式（我可以帮你生成）
👉 draw.io（我也可以给你 XML）
👉 或 Mermaid ER 图

⸻

五、给你一个 Mermaid ER 图版本（可直接渲染）

erDiagram

User ||--o{ UserOrganization : belongs
Organization ||--o{ UserOrganization : contains
Role ||--o{ UserOrganization : assigned
Role ||--o{ RolePermission : has
Permission ||--o{ RolePermission : mapped

User ||--|| Doctor : extends

Doctor ||--o{ Schedule : has
Organization ||--o{ Schedule : owns
Schedule ||--o{ Slot : contains

Patient ||--o{ Appointment : books
Doctor ||--o{ Appointment : serves
Schedule ||--o{ Appointment : linked
Slot ||--o{ Appointment : allocates


⸻

六、一句话总结你的系统架构

多组织 + RBAC权限 + 医疗调度（排班/号源） + 预约业务


⸻

七、如果你下一步要继续（我建议）

可以继续做：

👉 ✅ 完整建表 SQL（MySQL/PostgreSQL）
👉 ✅ 索引设计（高并发预约）
👉 ✅ 防超卖（号源并发控制）
👉 ✅ 接口设计（RESTful / GraphQL）

⸻

如果你想，我可以直接帮你再升级一版：

👉 “生产级架构图（含缓存 / MQ / 微服务拆分）”
👉 或 “高并发预约系统设计（防抢号崩溃）”

你现在这个设计，已经是中大型系统级别了 👍