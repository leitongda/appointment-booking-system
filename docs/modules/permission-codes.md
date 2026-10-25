# 权限码使用关系清单

> 由 `apps/server/scripts/gen_permission_matrix.py` 生成，请勿手改；
> 权限目录的 source of truth 是 `apps/server/scripts/init_permissions.py`。

- 目录权限码：130 个
- 后端守卫引用：148 个码
- 前端（admin）引用：114 个码
- 后端守卫使用但目录缺失（漂移，需修）：48 个
- 目录内但前后端零引用（展示型）：0 个

后端列格式为 `模块路径:行号`（`require_permission` 族调用处）；前端列为 admin 源码引用文件数。

## ⚠️ 目录外权限码（守卫在用、无法授权）

| 权限码 | 后端调用处 |
|---|---|
| `approval-flow:create` | app/modules/approval_flows/router.py:208; app/modules/approval_flows/router.py:242; app/modules/approval_flows/router.py:339; app/modules/approval_flows/router.py:427 |
| `approval-flow:delete` | app/modules/approval_flows/router.py:307; app/modules/approval_flows/router.py:408 |
| `approval-flow:list` | app/modules/approval_flows/router.py:158; app/modules/approval_flows/router.py:221; app/modules/approval_flows/router.py:325; app/modules/approval_flows/router.py:443; app/modules/approval_flows/router.py:56; app/modules/approval_flows/router.py:80; app/modules/approval_flows/router.py:93 |
| `approval-flow:manage` | app/modules/approval_flows/router.py:373; app/modules/approval_flows/router.py:392 |
| `approval-flow:update` | app/modules/approval_flows/router.py:354 |
| `approval-instance:manage` | app/modules/approval_flows/router_instances.py:236; app/modules/approval_flows/router_instances.py:257; app/modules/approval_flows/router_instances.py:278 |
| `approval:approve` | app/modules/approval_flows/router_instances.py:146; app/modules/approval_flows/router_instances.py:169; app/modules/approval_flows/router_instances.py:192 |
| `approval:read` | app/modules/approval_flows/router_instances.py:103; app/modules/approval_flows/router_instances.py:117; app/modules/approval_flows/router_instances.py:131; app/modules/approval_flows/router_instances.py:215; app/modules/approval_flows/router_instances.py:35; app/modules/approval_flows/router_instances.py:65; app/modules/approval_flows/router_instances.py:89 |
| `attendance:record` | app/modules/attendance_records/router.py:155; app/modules/attendance_records/router.py:176; app/modules/attendance_records/router.py:217 |
| `contact:create` | app/modules/contacts/router.py:211; app/modules/contacts/router.py:88; app/modules/contacts/router_channels.py:72; app/modules/contacts/router_groups.py:50; app/modules/contacts/router_tags.py:30 |
| `contact:delete` | app/modules/contacts/router.py:126; app/modules/contacts/router.py:319; app/modules/contacts/router_channels.py:110; app/modules/contacts/router_groups.py:88; app/modules/contacts/router_tags.py:68 |
| `contact:edit` | app/modules/contacts/router.py:106; app/modules/contacts/router.py:332; app/modules/contacts/router.py:345; app/modules/contacts/router.py:358; app/modules/contacts/router_channels.py:125; app/modules/contacts/router_channels.py:90; app/modules/contacts/router_groups.py:68; app/modules/contacts/router_tags.py:48 |
| `contact:export` | app/modules/contacts/router.py:146 |
| `contact:view` | app/modules/contacts/router.py:146; app/modules/contacts/router.py:47; app/modules/contacts/router.py:74; app/modules/contacts/router_channels.py:34; app/modules/contacts/router_channels.py:58; app/modules/contacts/router_groups.py:37; app/modules/contacts/router_tags.py:18 |
| `doctor:review` | app/modules/doctor_reviews/router.py:103 |
| `freelance:create` | app/modules/freelance_fees/router.py:108; app/modules/freelance_fees/router.py:208; app/modules/freelance_fees/router.py:251; app/modules/freelance_fees/router.py:618 |
| `freelance:delete` | app/modules/freelance_fees/router.py:136 |
| `freelance:list` | app/modules/freelance_fees/router.py:157; app/modules/freelance_fees/router.py:188; app/modules/freelance_fees/router.py:238; app/modules/freelance_fees/router.py:319; app/modules/freelance_fees/router.py:348; app/modules/freelance_fees/router.py:452; app/modules/freelance_fees/router.py:468; app/modules/freelance_fees/router.py:484; app/modules/freelance_fees/router.py:500; app/modules/freelance_fees/router.py:520; app/modules/freelance_fees/router.py:68; app/modules/freelance_fees/router.py:93 |
| `freelance:settle` | app/modules/freelance_fees/router.py:373; app/modules/freelance_fees/router.py:393; app/modules/freelance_fees/router.py:413; app/modules/freelance_fees/router.py:432 |
| `freelance:update` | app/modules/freelance_fees/router.py:122; app/modules/freelance_fees/router.py:222; app/modules/freelance_fees/router.py:268 |
| `lowcode:page:codegen` | app/modules/lowcode/router.py:575; app/modules/lowcode/router.py:624 |
| `lowcode:page:deploy` | app/modules/lowcode/router.py:855; app/modules/lowcode/router.py:932; app/modules/lowcode/router.py:972 |
| `lowcode:page:read` | app/modules/lowcode/router.py:175; app/modules/lowcode/router.py:293; app/modules/lowcode/router.py:465; app/modules/lowcode/router.py:488; app/modules/lowcode/router.py:525; app/modules/lowcode/router.py:691; app/modules/lowcode/router.py:767; app/modules/lowcode/router.py:894 |
| `lowcode:template` | app/modules/lowcode/router_template.py:257; app/modules/lowcode/router_template.py:327; app/modules/lowcode/router_template.py:387; app/modules/lowcode/router_template.py:416; app/modules/lowcode/router_template.py:459; app/modules/lowcode/router_template.py:505; app/modules/lowcode/router_template.py:560 |
| `lowcode:template:create` | app/modules/lowcode/router_template.py:257 |
| `lowcode:template:delete` | app/modules/lowcode/router_template.py:387 |
| `lowcode:template:fork` | app/modules/lowcode/router_template.py:416 |
| `lowcode:template:list` | app/modules/lowcode/router_template.py:560 |
| `lowcode:template:read` | app/modules/lowcode/router_template.py:459 |
| `lowcode:template:update` | app/modules/lowcode/router_template.py:327; app/modules/lowcode/router_template.py:505 |
| `points:list` | app/modules/points/router.py:40; app/modules/points/router.py:70 |
| `points:update` | app/modules/points/router.py:96 |
| `record:export` | app/modules/attendance_records/router.py:217 |
| `rule_set:create` | app/modules/import_export/router_import.py:290 |
| `schedule:extra-quota` | app/modules/schedules/router_extra_quota.py:201; app/modules/schedules/router_extra_quota.py:40 |
| `schedule:extra-quota:approve` | app/modules/schedules/router_extra_quota.py:112; app/modules/schedules/router_extra_quota.py:152 |
| `schedule:read` | app/modules/import_export/router_export.py:598; app/modules/schedule_suspensions/router.py:195; app/modules/schedule_suspensions/router.py:45; app/modules/schedules/router.py:128; app/modules/schedules/router.py:225; app/modules/schedules/router.py:477; app/modules/schedules/router_custom.py:92; app/modules/schedules/router_statistics.py:231; app/modules/schedules/router_statistics.py:320; app/modules/schedules/router_statistics.py:440; app/modules/schedules/router_statistics.py:70 |
| `schedule:room` | app/modules/schedule_rooms/router.py:150; app/modules/schedule_rooms/router.py:175; app/modules/schedule_rooms/router.py:203 |
| `schedule:suspend` | app/modules/schedule_suspensions/router.py:115; app/modules/schedule_suspensions/router.py:161; app/modules/schedule_suspensions/router.py:231; app/modules/schedules/router.py:687; app/modules/schedules/router.py:730 |
| `support_ticket:list` | app/modules/support_tickets/router.py:106; app/modules/support_tickets/router.py:48 |
| `support_ticket:manage` | app/modules/support_tickets/router.py:169; app/modules/support_tickets/router.py:192; app/modules/support_tickets/router.py:216; app/modules/support_tickets/router.py:239 |
| `support_ticket:update` | app/modules/support_tickets/router.py:146 |
| `support_ticket:view` | app/modules/support_tickets/router.py:123 |
| `system:config` | app/modules/notification_logs/router.py:139 |
| `system:monitoring` | app/modules/notification_logs/router.py:108; app/modules/notification_logs/router.py:122; app/modules/notification_logs/router.py:191; app/modules/notification_logs/router.py:211; app/modules/notification_logs/router.py:63; app/modules/notification_logs/router.py:95 |
| `waitlist:cancel` | app/modules/waitlist/router.py:426 |
| `waitlist:promote` | app/modules/waitlist/router.py:384 |
| `waitlist:read` | app/modules/waitlist/router.py:241; app/modules/waitlist/router.py:292 |

## 仪表盘（`dashboard`）

| 权限码 | 名称 | 类型 | 后端守卫 | 前端引用 |
|---|---|---|---|---|
| `dashboard` | 仪表盘 | menu | — | 4 |
| &nbsp;&nbsp;`dashboard:view` | 查看仪表盘 | button | — | 1 |

## 门店管理（`store`）

| 权限码 | 名称 | 类型 | 后端守卫 | 前端引用 |
|---|---|---|---|---|
| `store` | 门店管理 | menu | — | 3 |
| &nbsp;&nbsp;`store:list` | 查看门店列表 | button | app/modules/import_export/router_export.py:264 | 3 |
| &nbsp;&nbsp;`store:create` | 新增门店 | button | app/modules/import_export/router_import.py:250; app/modules/stores/router.py:318 | 2 |
| &nbsp;&nbsp;`store:export` | 导出门店 | button | app/modules/import_export/router_export.py:264 | — |
| &nbsp;&nbsp;`store:update` | 编辑门店 | button | app/modules/store_visit_type_configs/router.py:64; app/modules/store_visit_type_configs/router.py:82; app/modules/stores/router.py:359 | 3 |
| &nbsp;&nbsp;`store:delete` | 删除门店 | button | app/modules/stores/router.py:404 | 2 |

## 科室管理（`department`）

| 权限码 | 名称 | 类型 | 后端守卫 | 前端引用 |
|---|---|---|---|---|
| `department` | 科室管理 | menu | — | 5 |
| &nbsp;&nbsp;`department:list` | 查看科室列表 | button | app/modules/import_export/router_export.py:206 | 1 |
| &nbsp;&nbsp;`department:create` | 新增科室 | button | app/modules/departments/router.py:221; app/modules/import_export/router_import.py:193 | 2 |
| &nbsp;&nbsp;`department:export` | 导出科室 | button | app/modules/import_export/router_export.py:206 | — |
| &nbsp;&nbsp;`department:update` | 编辑科室 | button | app/modules/departments/router.py:189; app/modules/departments/router.py:245; app/modules/departments/router.py:389 | 2 |
| &nbsp;&nbsp;`department:delete` | 删除科室 | button | app/modules/departments/router.py:271 | 2 |

## 医生管理（`doctor`）

| 权限码 | 名称 | 类型 | 后端守卫 | 前端引用 |
|---|---|---|---|---|
| `doctor` | 医生管理 | menu | — | 14 |
| &nbsp;&nbsp;`doctor:list` | 查看医生列表 | button | app/modules/import_export/router_export.py:74 | 2 |
| &nbsp;&nbsp;`doctor:detail` | 查看医生详情 | button | — | 2 |
| &nbsp;&nbsp;`doctor:create` | 新增医生 | button | app/modules/doctors/router.py:738; app/modules/import_export/router_import.py:55 | 4 |
| &nbsp;&nbsp;`doctor:export` | 导出医生 | button | app/modules/import_export/router_export.py:74 | — |
| &nbsp;&nbsp;`doctor:update` | 编辑医生 | button | app/modules/consultation_fees/router.py:343; app/modules/consultation_fees/router.py:390; app/modules/consultation_fees/router.py:408; app/modules/consultation_fees/router.py:436; app/modules/doctor_booking_settings/router.py:114; app/modules/doctor_booking_settings/router.py:146; app/modules/doctor_booking_settings/router.py:200; app/modules/doctors/router.py:675; app/modules/doctors/router.py:780 | 4 |
| &nbsp;&nbsp;`doctor:delete` | 删除医生 | button | app/modules/doctor_booking_settings/router.py:175; app/modules/doctors/router.py:820 | 4 |
| &nbsp;&nbsp;`doctor:booking-setting` | 预约设置 | button | app/modules/doctor_booking_settings/router.py:46; app/modules/doctor_booking_settings/router.py:76; app/modules/doctor_booking_settings/router.py:91 | 1 |

## 排班管理（`schedule`）

| 权限码 | 名称 | 类型 | 后端守卫 | 前端引用 |
|---|---|---|---|---|
| `schedule` | 排班管理 | menu | — | 7 |
| &nbsp;&nbsp;`schedule:list` | 查看排班列表 | button | app/modules/export/router.py:102 | 1 |
| &nbsp;&nbsp;`schedule:create` | 新增排班 | button | app/modules/import_export/router_import.py:364; app/modules/rest_days/router.py:103; app/modules/schedule_templates/router.py:219; app/modules/schedule_templates/router.py:351; app/modules/schedule_templates/router.py:594; app/modules/schedule_templates/router.py:650; app/modules/schedule_templates/router.py:694; app/modules/schedule_templates/router.py:857; app/modules/schedule_templates/router.py:912; app/modules/schedules/router.py:530; app/modules/schedules/router.py:582; app/modules/schedules/router.py:940; app/modules/schedules/router_custom.py:287 | 2 |
| &nbsp;&nbsp;`schedule:export` | 导出排班 | button | app/modules/export/router.py:102 | — |
| &nbsp;&nbsp;`schedule:update` | 编辑排班 | button | app/modules/rest_days/router.py:164; app/modules/schedule_templates/router.py:277; app/modules/schedule_templates/router.py:776; app/modules/schedules/router.py:280; app/modules/schedules/router.py:618; app/modules/schedules/router.py:813; app/modules/schedules/router.py:859; app/modules/schedules/router.py:896 | 2 |
| &nbsp;&nbsp;`schedule:delete` | 删除排班 | button | app/modules/rest_days/router.py:146; app/modules/schedule_suspensions/router.py:213; app/modules/schedule_templates/router.py:323; app/modules/schedule_templates/router.py:732; app/modules/schedules/router.py:771; app/modules/schedules/router_custom.py:437 | 2 |
| &nbsp;&nbsp;`schedule:template` | 排班模板 | button | — | 3 |
| &nbsp;&nbsp;`schedule:custom` | 自定义排班 | button | — | 2 |
| &nbsp;&nbsp;`schedule:rest-day` | 休息日设置 | button | — | 1 |
| &nbsp;&nbsp;`schedule:suspension` | 停诊管理 | button | — | 1 |
| &nbsp;&nbsp;`schedule:statistics` | 排班统计 | button | — | 1 |
| &nbsp;&nbsp;`schedule_template:list` | 查看排班模板列表 | button | app/modules/import_export/router_export.py:318 | — |
| &nbsp;&nbsp;`schedule_template:export` | 导出排班模板 | button | app/modules/import_export/router_export.py:318 | — |

## 预约管理（`appointment`）

| 权限码 | 名称 | 类型 | 后端守卫 | 前端引用 |
|---|---|---|---|---|
| `appointment` | 预约管理 | menu | — | 7 |
| &nbsp;&nbsp;`appointment:list` | 查看预约列表 | button | app/modules/export/router.py:41 | 1 |
| &nbsp;&nbsp;`appointment:detail` | 查看预约详情 | button | — | 3 |
| &nbsp;&nbsp;`appointment:export` | 导出预约 | button | app/modules/export/router.py:41 | — |
| &nbsp;&nbsp;`appointment:update` | 更新预约状态 | button | — | 3 |
| &nbsp;&nbsp;`appointment:cancel` | 取消预约 | button | — | 3 |
| &nbsp;&nbsp;`appointment:refund` | 预约退款 | button | app/modules/refunds/router.py:166; app/modules/refunds/router.py:194; app/modules/refunds/router.py:81; app/modules/refunds/router.py:97 | 3 |
| &nbsp;&nbsp;`appointment:manage` | 预约流转操作 | button | app/modules/appointments/router_flow.py:152; app/modules/appointments/router_flow.py:208; app/modules/appointments/router_flow.py:261; app/modules/appointments/router_flow.py:316; app/modules/appointments/router_flow.py:372 | — |
| &nbsp;&nbsp;`appointment:statistics` | 预约统计 | button | — | 1 |

## 患者管理（`patient`）

| 权限码 | 名称 | 类型 | 后端守卫 | 前端引用 |
|---|---|---|---|---|
| `patient` | 患者管理 | menu | — | 8 |
| &nbsp;&nbsp;`patient:list` | 查看患者列表 | button | app/modules/export/router.py:75; app/modules/import_export/router_export.py:149; app/modules/patients/router_manage.py:64; app/modules/patients/router_manage.py:88; app/modules/patients/router_users.py:57 | 1 |
| &nbsp;&nbsp;`patient:detail` | 查看患者详情 | button | app/modules/patients/router_manage.py:104; app/modules/patients/router_manage.py:164; app/modules/patients/router_manage.py:190; app/modules/patients/router_manage.py:210; app/modules/patients/router_manage.py:256; app/modules/patients/router_users.py:79 | 3 |
| &nbsp;&nbsp;`patient:create` | 新增患者 | button | app/modules/import_export/router_import.py:121; app/modules/patients/router_manage.py:42 | 3 |
| &nbsp;&nbsp;`patient:export` | 导出患者 | button | app/modules/export/router.py:75; app/modules/import_export/router_export.py:149 | — |
| &nbsp;&nbsp;`patient:update` | 编辑患者 | button | app/modules/patients/router_manage.py:121; app/modules/patients/router_manage.py:231; app/modules/patients/router_manage.py:270; app/modules/patients/router_manage.py:285; app/modules/patients/router_manage.py:301; app/modules/patients/router_manage.py:321; app/modules/patients/router_manage.py:337; app/modules/patients/router_users.py:112; app/modules/patients/router_users.py:160; app/modules/patients/router_users.py:176; app/modules/patients/router_users.py:196; app/modules/patients/router_users.py:95 | 6 |
| &nbsp;&nbsp;`patient:delete` | 删除患者 | button | app/modules/patients/router_manage.py:137; app/modules/patients/router_users.py:141; app/modules/patients/router_users.py:217 | 6 |

## 停诊审核（`leave-request`）

| 权限码 | 名称 | 类型 | 后端守卫 | 前端引用 |
|---|---|---|---|---|
| `leave-request` | 停诊审核 | menu | — | 2 |
| &nbsp;&nbsp;`leave-request:list` | 查看停诊申请 | button | — | 2 |
| &nbsp;&nbsp;`leave-request:approve` | 审批停诊申请 | button | app/modules/leave_requests/router.py:152 | 2 |

## 用户反馈（`feedback`）

| 权限码 | 名称 | 类型 | 后端守卫 | 前端引用 |
|---|---|---|---|---|
| `feedback` | 用户反馈 | menu | — | 2 |
| &nbsp;&nbsp;`feedback:list` | 查看反馈列表 | button | app/modules/feedbacks/router.py:63; app/modules/feedbacks/router.py:88; app/modules/feedbacks/router.py:99; app/modules/import_export/router_export.py:540 | 2 |
| &nbsp;&nbsp;`feedback:export` | 导出反馈 | button | app/modules/import_export/router_export.py:540 | — |
| &nbsp;&nbsp;`feedback:reply` | 回复反馈 | button | app/modules/feedbacks/router.py:145; app/modules/feedbacks/router.py:162 | 2 |
| &nbsp;&nbsp;`feedback:delete` | 删除反馈 | button | app/modules/feedbacks/router.py:177 | 1 |

## 消息管理（`message`）

| 权限码 | 名称 | 类型 | 后端守卫 | 前端引用 |
|---|---|---|---|---|
| `message` | 消息管理 | menu | — | 7 |
| &nbsp;&nbsp;`message:list` | 查看消息列表 | button | app/modules/messages/router.py:121; app/modules/messages/router.py:283; app/modules/unified_message/router.py:218; app/modules/unified_message/router.py:306 | 1 |
| &nbsp;&nbsp;`message:send` | 发送消息 | button | app/modules/messages/router.py:134; app/modules/messages/router.py:154; app/modules/messages/router.py:319; app/modules/messages/router.py:336; app/modules/unified_message/router.py:239; app/modules/unified_message/router.py:264; app/modules/unified_message/router.py:326; app/modules/unified_message/router.py:348; app/modules/unified_message/router.py:61; app/modules/unified_message/router.py:75 | 4 |
| &nbsp;&nbsp;`message:delete` | 删除消息 | button | app/modules/messages/router.py:174; app/modules/unified_message/router.py:284; app/modules/unified_message/router.py:368 | 4 |

## 内容管理（`content`）

| 权限码 | 名称 | 类型 | 后端守卫 | 前端引用 |
|---|---|---|---|---|
| `content` | 内容管理 | menu | — | 11 |
| &nbsp;&nbsp;`content:news` | 新闻管理 | button | app/modules/content/router.py:43; app/modules/content/router.py:576 | 1 |
| &nbsp;&nbsp;`content:news:create` | 新增新闻 | button | app/modules/content/router.py:123; app/modules/content/router.py:43 | 2 |
| &nbsp;&nbsp;`content:news:update` | 编辑新闻 | button | app/modules/content/router.py:140; app/modules/content/router.py:43 | 1 |
| &nbsp;&nbsp;`content:news:delete` | 删除新闻 | button | app/modules/content/router.py:154; app/modules/content/router.py:168; app/modules/content/router.py:182; app/modules/content/router.py:196; app/modules/content/router.py:43; app/modules/content/router.py:86 | 1 |
| &nbsp;&nbsp;`content:notice` | 公告管理 | button | app/modules/content/router.py:216; app/modules/content/router.py:576 | 1 |
| &nbsp;&nbsp;`content:notice:create` | 新增公告 | button | app/modules/booking_notices/router.py:92; app/modules/content/router.py:216; app/modules/content/router.py:300 | 2 |
| &nbsp;&nbsp;`content:notice:update` | 编辑公告 | button | app/modules/booking_notices/router.py:105; app/modules/booking_notices/router.py:135; app/modules/content/router.py:216; app/modules/content/router.py:317 | 1 |
| &nbsp;&nbsp;`content:notice:delete` | 删除公告 | button | app/modules/booking_notices/router.py:120; app/modules/content/router.py:216; app/modules/content/router.py:263; app/modules/content/router.py:331; app/modules/content/router.py:345; app/modules/content/router.py:359; app/modules/content/router.py:373 | 1 |
| &nbsp;&nbsp;`content:banner` | 轮播图管理 | button | app/modules/content/router.py:392; app/modules/content/router.py:576 | 1 |
| &nbsp;&nbsp;`content:banner:create` | 新增轮播图 | button | app/modules/content/router.py:392; app/modules/content/router.py:473 | 2 |
| &nbsp;&nbsp;`content:banner:update` | 编辑轮播图 | button | app/modules/content/router.py:392; app/modules/content/router.py:490; app/modules/content/router.py:558 | 1 |
| &nbsp;&nbsp;`content:banner:delete` | 删除轮播图 | button | app/modules/content/router.py:392; app/modules/content/router.py:438; app/modules/content/router.py:504; app/modules/content/router.py:518; app/modules/content/router.py:532; app/modules/content/router.py:546 | 1 |

## 统计分析（`statistics`）

| 权限码 | 名称 | 类型 | 后端守卫 | 前端引用 |
|---|---|---|---|---|
| `statistics` | 统计分析 | menu | — | 2 |
| &nbsp;&nbsp;`statistics:view` | 查看统计分析 | button | — | 1 |

## 页面搭建（`lowcode`）

| 权限码 | 名称 | 类型 | 后端守卫 | 前端引用 |
|---|---|---|---|---|
| `lowcode` | 页面搭建 | menu | — | 2 |
| &nbsp;&nbsp;`lowcode:page` | 页面管理 | button | app/modules/lowcode/router.py:109; app/modules/lowcode/router.py:133; app/modules/lowcode/router.py:175; app/modules/lowcode/router.py:194; app/modules/lowcode/router.py:233; app/modules/lowcode/router.py:251; app/modules/lowcode/router.py:269; app/modules/lowcode/router.py:293; app/modules/lowcode/router.py:328; app/modules/lowcode/router.py:407; app/modules/lowcode/router.py:443; app/modules/lowcode/router.py:465; app/modules/lowcode/router.py:488; app/modules/lowcode/router.py:525; app/modules/lowcode/router.py:575; app/modules/lowcode/router.py:624; app/modules/lowcode/router.py:691; app/modules/lowcode/router.py:732; app/modules/lowcode/router.py:767; app/modules/lowcode/router.py:855; app/modules/lowcode/router.py:894; app/modules/lowcode/router.py:932; app/modules/lowcode/router.py:972 | 1 |
| &nbsp;&nbsp;`lowcode:page:list` | 查看页面列表 | button | app/modules/lowcode/router.py:109 | 1 |
| &nbsp;&nbsp;`lowcode:page:create` | 新增页面 | button | app/modules/lowcode/router.py:133; app/modules/lowcode/router.py:328 | 1 |
| &nbsp;&nbsp;`lowcode:page:update` | 编辑页面 | button | app/modules/lowcode/router.py:194; app/modules/lowcode/router.py:269; app/modules/lowcode/router.py:443; app/modules/lowcode/router.py:732 | 1 |
| &nbsp;&nbsp;`lowcode:page:delete` | 删除页面 | button | app/modules/lowcode/router.py:233; app/modules/lowcode/router.py:251 | 1 |
| &nbsp;&nbsp;`lowcode:page:publish` | 发布页面 | button | app/modules/lowcode/router.py:407; app/modules/lowcode/router.py:805 | 1 |
| &nbsp;&nbsp;`lowcode:marketplace` | 模板市场 | button | — | 1 |
| &nbsp;&nbsp;`lowcode:marketplace:view` | 查看模板市场 | button | — | 1 |
| &nbsp;&nbsp;`lowcode:marketplace:publish` | 发布模板 | button | app/modules/lowcode/router.py:805 | 1 |

## 系统设置（`system`）

| 权限码 | 名称 | 类型 | 后端守卫 | 前端引用 |
|---|---|---|---|---|
| `system` | 系统设置 | menu | — | 5 |
| &nbsp;&nbsp;`system:role` | 角色管理 | button | app/modules/admin/router_roles.py:28; app/modules/admin/router_roles.py:43; app/modules/admin/router_roles.py:57 | 2 |
| &nbsp;&nbsp;`system:role:list` | 查看角色列表 | button | app/modules/admin/router_roles.py:28; app/modules/admin/router_roles.py:43; app/modules/admin/router_roles.py:57 | 2 |
| &nbsp;&nbsp;`system:role:create` | 新增角色 | button | app/modules/admin/router_roles.py:72 | 2 |
| &nbsp;&nbsp;`system:role:update` | 编辑角色 | button | app/modules/admin/router_roles.py:90 | 2 |
| &nbsp;&nbsp;`system:role:delete` | 删除角色 | button | app/modules/admin/router_roles.py:126 | 3 |
| &nbsp;&nbsp;`system:role:permission` | 分配权限 | button | app/modules/admin/router_permissions.py:20; app/modules/admin/router_permissions.py:30; app/modules/admin/router_permissions.py:54; app/modules/admin/router_permissions.py:78; app/modules/admin/router_permissions.py:90; app/modules/admin/router_roles.py:110 | 3 |
| &nbsp;&nbsp;`system:user` | 用户管理 | button | app/modules/admin/router_admins.py:46; app/modules/admin/router_admins.py:71 | 1 |
| &nbsp;&nbsp;`system:user:list` | 查看用户列表 | button | app/modules/admin/router_admins.py:46; app/modules/admin/router_admins.py:71 | 1 |
| &nbsp;&nbsp;`system:user:create` | 新增用户 | button | app/modules/admin/router_admins.py:87 | 2 |
| &nbsp;&nbsp;`system:user:update` | 编辑用户 | button | app/modules/admin/router_admins.py:121 | 2 |
| &nbsp;&nbsp;`system:user:delete` | 删除用户 | button | app/modules/admin/router_admins.py:186 | 2 |
| &nbsp;&nbsp;`system:user:reset-password` | 重置密码 | button | app/modules/admin/router_admins.py:162 | 3 |
| &nbsp;&nbsp;`admin:list` | 查看系统用户列表 | button | app/modules/import_export/router_export.py:402 | — |
| &nbsp;&nbsp;`admin:export` | 导出系统用户 | button | app/modules/import_export/router_export.py:402 | — |
| &nbsp;&nbsp;`system:settings` | 系统配置 | button | app/modules/email_templates/router.py:104; app/modules/email_templates/router.py:119; app/modules/email_templates/router.py:87 | 2 |
| &nbsp;&nbsp;`settings:edit` | 编辑系统设置 | button | app/modules/settings/router.py:123; app/modules/settings/router.py:184; app/modules/settings/router.py:215; app/modules/settings/router.py:261; app/modules/settings/router.py:310; app/modules/settings/router.py:405; app/modules/settings/router.py:422; app/modules/settings/router.py:464; app/modules/settings/router.py:477; app/modules/settings/router.py:530; app/modules/settings/router.py:562; app/modules/settings/router.py:593; app/modules/settings/router.py:606; app/modules/settings/router.py:670; app/modules/settings/router.py:696 | 2 |
| &nbsp;&nbsp;`settings:wechat` | 编辑微信配置 | button | app/modules/settings/router.py:215; app/modules/settings/router.py:234 | 2 |
| &nbsp;&nbsp;`settings:sms` | 编辑短信配置 | button | app/modules/settings/router.py:261; app/modules/settings/router.py:278 | 2 |
| &nbsp;&nbsp;`settings:email` | 编辑邮件配置 | button | app/modules/settings/router.py:310; app/modules/settings/router.py:334 | 2 |
| &nbsp;&nbsp;`blacklist:list` | 查看黑名单列表 | button | app/modules/blacklists/router.py:39 | 2 |
| &nbsp;&nbsp;`blacklist:create` | 新增黑名单 | button | app/modules/blacklists/router.py:64 | 3 |
| &nbsp;&nbsp;`blacklist:delete` | 移除黑名单 | button | app/modules/blacklists/router.py:88 | 2 |
| &nbsp;&nbsp;`system:consultation-fee` | 诊费管理 | button | app/modules/consultation_fees/router.py:129; app/modules/consultation_fees/router.py:168; app/modules/consultation_fees/router.py:197; app/modules/consultation_fees/router.py:210; app/modules/consultation_fees/router.py:257; app/modules/consultation_fees/router.py:275; app/modules/consultation_fees/router.py:91 | 3 |
| &nbsp;&nbsp;`system:log` | 操作日志 | button | app/modules/admin/router_monitoring.py:105; app/modules/admin/router_monitoring.py:155; app/modules/admin/router_monitoring.py:217; app/modules/admin/router_monitoring.py:294; app/modules/admin/router_monitoring.py:424; app/modules/admin/router_monitoring.py:54; app/modules/admin/router_monitoring.py:79 | 1 |
| &nbsp;&nbsp;`log:list` | 查看操作日志明细 | button | app/modules/admin/router_monitoring.py:105; app/modules/admin/router_monitoring.py:155; app/modules/admin/router_monitoring.py:217; app/modules/admin/router_monitoring.py:294; app/modules/admin/router_monitoring.py:424; app/modules/admin/router_monitoring.py:54; app/modules/admin/router_monitoring.py:79; app/modules/import_export/router_export.py:479 | — |
| &nbsp;&nbsp;`log:export` | 导出操作日志 | button | app/modules/import_export/router_export.py:479 | — |
| &nbsp;&nbsp;`rule_set:list` | 查看规则组列表 | button | app/modules/import_export/router_export.py:738 | — |
| &nbsp;&nbsp;`rule_set:export` | 导出规则组 | button | app/modules/import_export/router_export.py:738 | — |

## 内容站点（`cms`）

| 权限码 | 名称 | 类型 | 后端守卫 | 前端引用 |
|---|---|---|---|---|
| `cms` | 内容站点 | menu | — | 1 |
| &nbsp;&nbsp;`cms:site` | 站点管理 | button | app/modules/cms/router_sites.py:45; app/modules/cms/router_sites.py:68 | 1 |
| &nbsp;&nbsp;`cms:site:create` | 新增站点 | button | app/modules/cms/router_sites.py:45; app/modules/cms/router_sites.py:82 | 2 |
| &nbsp;&nbsp;`cms:site:update` | 编辑站点 | button | app/modules/cms/router_sites.py:45; app/modules/cms/router_sites.py:99 | 2 |
| &nbsp;&nbsp;`cms:site:delete` | 删除站点 | button | app/modules/cms/router_sites.py:118; app/modules/cms/router_sites.py:132; app/modules/cms/router_sites.py:146; app/modules/cms/router_sites.py:160; app/modules/cms/router_sites.py:45 | 2 |
| &nbsp;&nbsp;`cms:category` | 栏目管理 | button | app/modules/cms/router_categories.py:44; app/modules/cms/router_categories.py:62; app/modules/cms/router_categories.py:74 | 1 |
| &nbsp;&nbsp;`cms:category:create` | 新增栏目 | button | app/modules/cms/router_categories.py:44; app/modules/cms/router_categories.py:88 | 2 |
| &nbsp;&nbsp;`cms:category:update` | 编辑栏目 | button | app/modules/cms/router_categories.py:105; app/modules/cms/router_categories.py:138; app/modules/cms/router_categories.py:44 | 2 |
| &nbsp;&nbsp;`cms:category:delete` | 删除栏目 | button | app/modules/cms/router_categories.py:124; app/modules/cms/router_categories.py:44 | 2 |
| &nbsp;&nbsp;`cms:article` | 文章管理 | button | app/modules/cms/router_articles.py:125; app/modules/cms/router_articles.py:139; app/modules/cms/router_articles.py:50 | 2 |
| &nbsp;&nbsp;`cms:article:create` | 新增文章 | button | app/modules/cms/router_articles.py:171; app/modules/cms/router_articles.py:50 | 2 |
| &nbsp;&nbsp;`cms:article:update` | 编辑文章 | button | app/modules/cms/router_articles.py:188; app/modules/cms/router_articles.py:50 | 2 |
| &nbsp;&nbsp;`cms:article:delete` | 删除文章 | button | app/modules/cms/router_articles.py:102; app/modules/cms/router_articles.py:207; app/modules/cms/router_articles.py:221; app/modules/cms/router_articles.py:235; app/modules/cms/router_articles.py:249; app/modules/cms/router_articles.py:50 | 2 |
