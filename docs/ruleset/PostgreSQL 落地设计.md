下面我基于你们现有 `appointments / schedules` 字段，给出一套 **PostgreSQL 落地设计（含类型映射、约束、索引、以及“规则绑定/审计/签到日志”扩展）**。重点是：让“预约/签到限制”规则可以随配置变化，但**历史预约仍可追溯当时用的规则**。

---

# 1）类型映射建议（从 String(36) → uuid）

你们现在主键/外键都是 `String(36)`（UUID 字符串）。在 PG 里强烈建议用 `uuid`：

* `id`, `user_id`, `patient_id`, `doctor_id`, `schedule_id`, `store_id`, `template_id` … → `uuid`
* `appointment_no` → `text` 或 `varchar(50)`（建议 `varchar(50)`，加 unique）
* `Text` → `text`
* `DateTime` → `timestamptz`（强烈建议带时区）
* `Date` → `date`
* `Time` → `time`（如果你们跨时区门店，建议把班次开始结束也存 `timestamptz`，见下文）

> 如果短期不改业务层 UUID 类型，也可以先用 `varchar(36)`，但会损失不少 PG 优势。

---

# 2）建议对 schedules 增加“绝对时间字段”（非常关键）

你们 schedules 目前是：`schedule_date + start_time + end_time`，规则计算时必须拼出“班次开始/结束时间”。
为了避免跨时区、夏令时、拼接错误，推荐在 schedules 增加：

* `start_at timestamptz`
* `end_at timestamptz`
* `timezone text`（如 `Asia/Shanghai`）

这样规则窗口计算直接基于 `start_at/end_at`，稳定很多。

---

# 3）DDL：schedules（含必要增强）

```sql
-- 如果要用 uuid：
create extension if not exists "pgcrypto";

create table schedules (
  id uuid primary key default gen_random_uuid(),

  doctor_id uuid not null,
  store_id uuid not null,
  template_id uuid null,

  schedule_date date not null,
  time_slot varchar(10) not null,
  start_time time not null,
  end_time time not null,

  -- 推荐新增：绝对时间 + 时区（用于规则计算、展示一致性）
  timezone text not null default 'Asia/Shanghai',
  start_at timestamptz generated always as
    (make_timestamptz(
        extract(year from schedule_date)::int,
        extract(month from schedule_date)::int,
        extract(day from schedule_date)::int,
        extract(hour from start_time)::int,
        extract(minute from start_time)::int,
        extract(second from start_time)::double precision,
        timezone
     )) stored,
  end_at timestamptz generated always as
    (make_timestamptz(
        extract(year from schedule_date)::int,
        extract(month from schedule_date)::int,
        extract(day from schedule_date)::int,
        extract(hour from end_time)::int,
        extract(minute from end_time)::int,
        extract(second from end_time)::double precision,
        timezone
     )) stored,

  total_slots int not null default 0 check (total_slots >= 0),
  booked_slots int not null default 0 check (booked_slots >= 0 and booked_slots <= total_slots),

  appointment_type varchar(20) not null,   -- 你们的“班次类型/预约类型”
  status int not null default 1 check (status in (0,1)), -- 0停诊 1正常

  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index idx_schedules_doctor_date on schedules (doctor_id, schedule_date);
create index idx_schedules_store_date on schedules (store_id, schedule_date);
create index idx_schedules_type_date on schedules (appointment_type, schedule_date);
create index idx_schedules_status_date on schedules (status, schedule_date);
```

> 注：`generated always as ... stored` 依赖 PG 12+，且 `make_timestamptz` 可用。
> 如果你们不想用 generated 字段，也可以在应用层写入 `start_at/end_at`。

---

# 4）DDL：appointments（增加“规则绑定/窗口快照/签到次数”）

你们 appointments 已经包含 sign_in_time 等字段，但为了“灵活规则”落地，建议加 3 类字段：

### A) 规则绑定（强烈建议）

让每条预约知道“当时用的是哪套规则”：

* `rule_set_id`
* `rule_set_version_id`（如果你们做版本发布；不做也可以先留空）

### B) 规则窗口快照（建议）

当预约创建时把“计算出来的窗口”落库，避免后续规则变更导致历史预约校验口径变了：

* `book_open_at`, `book_close_at`
* `checkin_open_at`, `checkin_close_at`
* （可选）`cancel_open_at`, `cancel_close_at`

### C) 签到统计（建议）

* `checkin_count`（快速判断超次）
* `last_checkin_at`（与 sign_in_time 可合并/保留兼容）

下面是完整 DDL（保持你们现有字段，并补充推荐字段）：

```sql
create table appointments (
  id uuid primary key default gen_random_uuid(),
  appointment_no varchar(50) not null unique,

  user_id uuid not null,
  patient_id uuid not null,
  doctor_id uuid not null,
  schedule_id uuid not null references schedules(id),

  -- 规则绑定（新增）
  rule_set_id bigint null,          -- references rule_set(id)
  rule_set_version_id bigint null,  -- references rule_set_version(id) 可选

  -- 状态：0待支付 1已预约 2已签到 3候诊中 4就诊中 5已完成 6已取消 7已过期 8已关闭
  status int not null check (status in (0,1,2,3,4,5,6,7,8)),

  queue_number int null,

  -- 时间记录（你们已有）
  sign_in_time timestamptz null,
  call_time timestamptz null,
  complete_time timestamptz null,
  cancel_time timestamptz null,

  cancel_reason text null,
  remark text null,
  symptom_description text null,

  patient_name varchar(50) null,
  patient_phone varchar(20) null,

  doctor_name varchar(50) null,
  doctor_title varchar(50) null,
  department_name varchar(100) null,

  reminder_sent int not null default 0 check (reminder_sent in (0,1)),
  reminder_sent_at timestamptz null,

  -- ===== 推荐新增：窗口快照（用于历史一致性）=====
  book_open_at timestamptz null,
  book_close_at timestamptz null,
  checkin_open_at timestamptz null,
  checkin_close_at timestamptz null,
  cancel_open_at timestamptz null,
  cancel_close_at timestamptz null,

  -- ===== 推荐新增：签到统计 =====
  checkin_count int not null default 0 check (checkin_count >= 0),
  last_checkin_at timestamptz null,

  -- 审计
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  created_by uuid null,
  updated_by uuid null
);

-- 高频查询索引：按用户/患者/医生/班次/状态/时间
create index idx_appointments_user_created on appointments (user_id, created_at desc);
create index idx_appointments_patient_created on appointments (patient_id, created_at desc);
create index idx_appointments_doctor_schedule on appointments (doctor_id, schedule_id);
create index idx_appointments_schedule_status on appointments (schedule_id, status);
create index idx_appointments_status_created on appointments (status, created_at desc);

-- “同一患者同一班次不能重复预约”（如果业务就是这样）
-- 若允许改约/多次，别加这个约束
create unique index uk_patient_schedule_active
  on appointments (patient_id, schedule_id)
  where status in (0,1,2,3,4);  -- 活跃态：待支付/已预约/已签到/候诊中/就诊中
```

> `uk_patient_schedule_active` 是医院常见强约束：同一患者同一班次不能同时存在多条“活跃预约”。
> 如果你们允许同班次重复支付/重复预约，就去掉或改成 `(user_id, schedule_id)`。

---

# 5）建议新增：签到日志表（避免只靠 sign_in_time）

你们现在 `appointments.sign_in_time` 只能记录一次签到时间，但规则里可能需要：

* 多次签到尝试（二维码扫了几次）
* 失败原因（不在窗口/未预约/超次数）
* 记录操作者/设备/渠道
* 后续对接风控、审计

建议新增 `appointment_checkins`：

```sql
create table appointment_checkins (
  id bigserial primary key,
  appointment_id uuid not null references appointments(id) on delete cascade,

  attempt_at timestamptz not null default now(),
  result text not null check (result in ('SUCCESS','REJECTED')),
  reject_reason text null, -- OUT_OF_WINDOW / NOT_BOOKED / EXCEED_MAX / SCHEDULE_CLOSED ...

  -- 可选：渠道/设备/操作者
  channel text null,       -- APP / H5 / KIOSK / ADMIN
  operator_id uuid null,
  device_id text null,
  extra jsonb null,

  created_at timestamptz not null default now()
);

create index idx_checkins_appointment_time on appointment_checkins (appointment_id, attempt_at desc);
```

配合 appointments 的 `checkin_count/last_checkin_at/sign_in_time`：

* 成功签到：写一条日志 + 更新 appointments 这三个冗余字段（加速查询、避免每次聚合）

---

# 6）把“规则配置表”与你们业务表关联起来

你前面要的 RuleSet/Window/Policy 表，我建议保留（就是我上一条给的 PG 版本）。现在把外键补上即可：

```sql
alter table appointments
  add constraint fk_appointments_rule_set
  foreign key (rule_set_id) references rule_set(id);

-- 如果你们做版本发布：
-- alter table appointments
--   add constraint fk_appointments_rule_set_version
--   foreign key (rule_set_version_id) references rule_set_version(id);
```

---

# 7）你们现有字段与“灵活规则”如何配合（落地流程）

## 预约创建时（BOOK）

1. 根据 `schedules.appointment_type` 匹配 `rule_set`
2. 读取 BOOK window + CHECKIN window（以及 CANCEL window 可选）
3. 基于 `schedules.start_at/end_at` 计算窗口，并写入：

   * `book_open_at/book_close_at`
   * `checkin_open_at/checkin_close_at`
4. 写入 `rule_set_id`（以及 `rule_set_version_id`）
5. 写入预约记录

## 签到时（CHECKIN）

1. 直接用 `appointments.checkin_open_at/checkin_close_at` 判断（历史一致）
2. 成功则：

   * `status = 2`
   * `sign_in_time = now()`（若你们只保留首次签到）
   * `checkin_count += 1`
   * `last_checkin_at = now()`
   * 插入 `appointment_checkins` 一条 SUCCESS
3. 失败则插入 `appointment_checkins` 一条 REJECTED（写 reject_reason）

---

# 8）你 schedules 的 booked_slots 并发更新（提醒）

`schedules.booked_slots` 在并发预约时非常容易超卖，PG 里建议：

* 预约成功时：`update schedules set booked_slots = booked_slots + 1 where id = ? and booked_slots < total_slots;`
* 用返回行数判断是否成功占位
* 或者把号源拆成独立号位表（更精确，但成本更高）

---



# 1）强制阻止：同一 patient 同一 schedule 不能重复“活跃预约”

做法：**部分唯一索引（partial unique index）**，只覆盖“活跃态”。

你们状态枚举里，符合“占用号源/仍有效”的一般是：

* 0 待支付
* 1 已预约
* 2 已签到
* 3 候诊中
* 4 就诊中
  （5 已完成、6 已取消、7 已过期、8 已关闭 不算活跃）

```sql
create unique index if not exists uk_appointments_patient_schedule_active
on appointments (patient_id, schedule_id)
where status in (0,1,2,3,4);
```

**效果：**

* 同一人预约同一班次：会被数据库强制拦截 ✅
* 已取消/过期/关闭后重新预约：不命中索引，允许 ✅

> 注意：如果“待支付(0)”你们不想占唯一（允许重复下单只保留最后一条），那就把 0 从 where 里移除。

---

# 2）允许但“提醒”：同一 patient 同日不同班次（上午/下午）仅提醒

数据库层无法“弹窗提醒”，但可以做到两种落地方式：

## 方案 A：写入提醒事件（推荐，最可控）

新增一张“规则提醒事件表”，当插入预约时如果检测到同日有其他 schedule 的活跃预约，就插入一条提醒事件，应用层拿到后提示用户（但不阻止）。

### 2.1 提醒事件表

```sql
create table if not exists appointment_warnings (
  id bigserial primary key,
  appointment_id uuid not null references appointments(id) on delete cascade,

  warning_type text not null
    check (warning_type in ('SAME_DAY_MULTIPLE')),

  message text not null,
  extra jsonb null,

  created_at timestamptz not null default now()
);

create index if not exists idx_warnings_appointment on appointment_warnings (appointment_id);
create index if not exists idx_warnings_created on appointment_warnings (created_at desc);
```

### 2.2 触发器函数：插入/更新为活跃态时检测

逻辑：当 `appointments` 新增，或状态变为活跃时，检查：

* 同 patient
* 同 schedule_date（通过 join schedules）
* 但 schedule_id 不同
* 且对方为活跃态

```sql
create or replace function fn_warn_same_day_multiple()
returns trigger language plpgsql as $$
declare
  v_date date;
  v_exists boolean;
begin
  -- 只对活跃态做提醒（避免取消/关闭等也产生提醒）
  if (new.status not in (0,1,2,3,4)) then
    return new;
  end if;

  select s.schedule_date into v_date
  from schedules s
  where s.id = new.schedule_id;

  if v_date is null then
    return new;
  end if;

  select exists (
    select 1
    from appointments a
    join schedules s2 on s2.id = a.schedule_id
    where a.patient_id = new.patient_id
      and a.id <> new.id
      and a.status in (0,1,2,3,4)
      and s2.schedule_date = v_date
  ) into v_exists;

  if v_exists then
    insert into appointment_warnings (appointment_id, warning_type, message, extra)
    values (
      new.id,
      'SAME_DAY_MULTIPLE',
      '该就诊人同日已存在其他班次预约，请确认是否重复预约。',
      jsonb_build_object('schedule_date', v_date)
    );
  end if;

  return new;
end $$;

drop trigger if exists trg_warn_same_day_multiple on appointments;

create trigger trg_warn_same_day_multiple
after insert on appointments
for each row
execute function fn_warn_same_day_multiple();
```

> 如果你们存在“先创建待支付(0)后支付成功变 1”的流程，并且想在支付成功时也提醒，可再加一个 `after update of status` 的触发器：当 `old.status not in 活跃 && new.status in 活跃` 时触发一次提醒。

并发与重复提醒：

* 你可以给 `appointment_warnings` 增加唯一去重（例如 `(appointment_id, warning_type)` unique），避免重复插入。

```sql
create unique index if not exists uk_warning_once
on appointment_warnings (appointment_id, warning_type);
```

---

# 3）取消后重新预约：数据库如何保证“允许”

只要你们取消时把 `status` 更新为 `6`（已取消），就自然不命中 partial unique index。

建议取消时也落 `cancel_time`：

```sql
update appointments
set status = 6,
    cancel_time = now(),
    cancel_reason = $1,
    updated_at = now()
where id = $2
  and status in (0,1,2);  -- 你们允许哪些状态可取消按业务定义
```

---

# 4）为了让这些规则跑得又快又稳：推荐索引

### 4.1 appointments 高性能查询索引

```sql
create index if not exists idx_appointments_patient_status
on appointments (patient_id, status);

create index if not exists idx_appointments_patient_created
on appointments (patient_id, created_at desc);

create index if not exists idx_appointments_schedule_status
on appointments (schedule_id, status);
```

### 4.2 schedules 用于提醒 join 的索引

```sql
create index if not exists idx_schedules_id_date
on schedules (id, schedule_date);
```

---

# 5）与你们“预约窗口/签到窗口规则”衔接（建议补一列）

为了后续灵活规则落地、历史一致性，我建议你们在 appointments 上保留我前面提到的窗口快照字段（至少 checkin 的）：

* `checkin_open_at`
* `checkin_close_at`

这样签到判断直接用预约创建时算好的窗口，不受后续规则变更影响。

---

如果你希望我把“支付成功后才占唯一”（即 `status=0` 不拦截）也支持，我可以给你两套索引/约束组合（并解释对重复下单、支付回调幂等等会有什么影响）。你们现在 `status=0 待支付` 是不是也要占用号源/占用唯一？
