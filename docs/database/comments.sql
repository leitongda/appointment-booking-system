-- ============================================
-- 预约挂号系统 - 全量表/字段中文注释脚本
-- 可直接在 PostgreSQL 中执行
-- 生成时间: 2026-02-06
-- ============================================

-- ============================================
-- 一、用户与认证
-- ============================================

COMMENT ON TABLE users IS '用户表 - C端用户（患者/微信用户）';
COMMENT ON COLUMN users.id IS '用户ID (UUID)';
COMMENT ON COLUMN users.phone IS '手机号，微信用户可为空';
COMMENT ON COLUMN users.password_hash IS '密码哈希';
COMMENT ON COLUMN users.nickname IS '昵称';
COMMENT ON COLUMN users.avatar IS '头像URL';
COMMENT ON COLUMN users.gender IS '性别: 0未知 1男 2女';
COMMENT ON COLUMN users.openid IS '微信小程序OpenID';
COMMENT ON COLUMN users.status IS '状态: 0禁用 1正常';
COMMENT ON COLUMN users.points IS '当前积分';
COMMENT ON COLUMN users.unionid IS '微信开放平台统一ID';
COMMENT ON COLUMN users.wechat_nickname IS '微信原始昵称';
COMMENT ON COLUMN users.wechat_avatar IS '微信原始头像URL';
COMMENT ON COLUMN users.wechat_synced_at IS '最后同步微信信息时间';
COMMENT ON COLUMN users.created_at IS '创建时间';
COMMENT ON COLUMN users.updated_at IS '更新时间';
COMMENT ON COLUMN users.created_by IS '创建人ID';
COMMENT ON COLUMN users.updated_by IS '更新人ID';

COMMENT ON TABLE patients IS '就诊人表 - 一个用户可绑定多个就诊人';
COMMENT ON COLUMN patients.id IS '就诊人ID (UUID)';
COMMENT ON COLUMN patients.user_id IS '所属用户ID';
COMMENT ON COLUMN patients.store_id IS '首次就诊门店ID';
COMMENT ON COLUMN patients.name IS '姓名';
COMMENT ON COLUMN patients.phone IS '手机号';
COMMENT ON COLUMN patients.id_card IS '身份证号';
COMMENT ON COLUMN patients.gender IS '性别';
COMMENT ON COLUMN patients.age IS '年龄';
COMMENT ON COLUMN patients.birthday IS '出生日期';
COMMENT ON COLUMN patients.relationship IS '与账号用户关系: 本人/父母/子女/配偶/其他';
COMMENT ON COLUMN patients.is_default IS '是否默认就诊人';
COMMENT ON COLUMN patients.card_no IS '就诊卡编号';
COMMENT ON COLUMN patients.province IS '省';
COMMENT ON COLUMN patients.city IS '市';
COMMENT ON COLUMN patients.district IS '区';
COMMENT ON COLUMN patients.street IS '街道/社区';
COMMENT ON COLUMN patients.id_card_type IS '证件类型: 1身份证 2户口簿 3护照';
COMMENT ON COLUMN patients.ethnicity IS '民族';
COMMENT ON COLUMN patients.address IS '详细地址';
COMMENT ON COLUMN patients.source IS '来源: 1用户添加 2管理员添加';
COMMENT ON COLUMN patients.total_consumption IS '累计消费金额';

-- ============================================
-- 二、权限与管理
-- ============================================

COMMENT ON TABLE admins IS '管理员表 - 后台管理人员';
COMMENT ON COLUMN admins.id IS '管理员ID (UUID)';
COMMENT ON COLUMN admins.username IS '登录用户名';
COMMENT ON COLUMN admins.password_hash IS '密码哈希';
COMMENT ON COLUMN admins.name IS '姓名';
COMMENT ON COLUMN admins.phone IS '手机号';
COMMENT ON COLUMN admins.email IS '邮箱';
COMMENT ON COLUMN admins.avatar IS '头像URL';
COMMENT ON COLUMN admins.role_id IS '角色ID';
COMMENT ON COLUMN admins.current_store_id IS '当前选中门店ID，超级管理员可为空';
COMMENT ON COLUMN admins.status IS '状态: 0禁用 1启用';
COMMENT ON COLUMN admins.last_login_at IS '最后登录时间';
COMMENT ON COLUMN admins.last_login_ip IS '最后登录IP';

COMMENT ON TABLE roles IS '角色表';
COMMENT ON COLUMN roles.id IS '角色ID (UUID)';
COMMENT ON COLUMN roles.name IS '角色名称';
COMMENT ON COLUMN roles.code IS '角色编码，如 SUPER_ADMIN';
COMMENT ON COLUMN roles.description IS '描述';
COMMENT ON COLUMN roles.status IS '状态: 0禁用 1启用';
COMMENT ON COLUMN roles.permissions IS '权限列表，JSON格式';

COMMENT ON TABLE permissions IS '权限表 - 扁平权限码模型';
COMMENT ON COLUMN permissions.id IS '权限ID (UUID)';
COMMENT ON COLUMN permissions.code IS '权限码，如 doctor:create';
COMMENT ON COLUMN permissions.name IS '权限名称';
COMMENT ON COLUMN permissions.type IS '类型: menu菜单 / button按钮';
COMMENT ON COLUMN permissions.parent_code IS '父级权限码';
COMMENT ON COLUMN permissions.icon IS '图标（菜单权限可用）';
COMMENT ON COLUMN permissions.sort IS '排序号';

COMMENT ON TABLE role_permissions IS '角色权限关联表';
COMMENT ON COLUMN role_permissions.role_id IS '角色ID';
COMMENT ON COLUMN role_permissions.permission IS '权限标识，如 doctor:create';

COMMENT ON TABLE rule_set_shift_types IS '规则组与班次类型关联表（多对多）';
COMMENT ON COLUMN rule_set_shift_types.rule_set_id IS '规则组ID';
COMMENT ON COLUMN rule_set_shift_types.shift_type_id IS '班次类型ID';

COMMENT ON TABLE admin_stores IS '管理员门店关联表（多对多）';
COMMENT ON COLUMN admin_stores.admin_id IS '管理员ID';
COMMENT ON COLUMN admin_stores.store_id IS '门店ID';
COMMENT ON COLUMN admin_stores.is_manager IS '是否为该门店管理员: 0否 1是';
COMMENT ON COLUMN admin_stores.created_at IS '创建时间';

COMMENT ON TABLE admin_login_history IS '管理员登录历史表';
COMMENT ON COLUMN admin_login_history.id IS '记录ID (UUID)';
COMMENT ON COLUMN admin_login_history.admin_id IS '管理员ID';
COMMENT ON COLUMN admin_login_history.login_time IS '登录时间';
COMMENT ON COLUMN admin_login_history.logout_time IS '退出时间';
COMMENT ON COLUMN admin_login_history.logout_type IS '退出类型: manual手动 / timeout超时 / kicked踢出';
COMMENT ON COLUMN admin_login_history.login_ip IS '登录IP';
COMMENT ON COLUMN admin_login_history.user_agent IS 'User-Agent字符串';
COMMENT ON COLUMN admin_login_history.browser IS '浏览器';
COMMENT ON COLUMN admin_login_history.os IS '操作系统';
COMMENT ON COLUMN admin_login_history.device_type IS '设备类型: desktop/mobile/tablet';
COMMENT ON COLUMN admin_login_history.duration IS '在线时长（秒）';

-- ============================================
-- 三、机构管理
-- ============================================

COMMENT ON TABLE stores IS '门店/分院表 - 系统多租户核心';
COMMENT ON COLUMN stores.id IS '门店ID (UUID)';
COMMENT ON COLUMN stores.name IS '门店名称';
COMMENT ON COLUMN stores.code IS '门店编码';
COMMENT ON COLUMN stores.address IS '详细地址';
COMMENT ON COLUMN stores.province IS '省份';
COMMENT ON COLUMN stores.city IS '城市';
COMMENT ON COLUMN stores.district IS '区县';
COMMENT ON COLUMN stores.latitude IS '纬度';
COMMENT ON COLUMN stores.longitude IS '经度';
COMMENT ON COLUMN stores.phone IS '联系电话';
COMMENT ON COLUMN stores.contact_person IS '联系人';
COMMENT ON COLUMN stores.description IS '门店简介';
COMMENT ON COLUMN stores.opening_time IS '营业开始时间';
COMMENT ON COLUMN stores.closing_time IS '营业结束时间';
COMMENT ON COLUMN stores.working_days IS '工作日(1-7)，逗号分隔';
COMMENT ON COLUMN stores.business_hours IS '营业时间描述';
COMMENT ON COLUMN stores.image IS '门店图片URL';
COMMENT ON COLUMN stores.logo IS '门店Logo URL';
COMMENT ON COLUMN stores.password IS '门店密码';
COMMENT ON COLUMN stores.email IS '邮箱';
COMMENT ON COLUMN stores.theme_style IS '风格选择';
COMMENT ON COLUMN stores.sort_order IS '排序';
COMMENT ON COLUMN stores.status IS '状态: 0停业 1营业 2禁用';
COMMENT ON COLUMN stores.wechat_app_id IS '微信小程序AppID';
COMMENT ON COLUMN stores.wechat_app_secret IS '微信小程序Secret';
COMMENT ON COLUMN stores.wechat_mch_id IS '微信支付商户号';
COMMENT ON COLUMN stores.wechat_api_key IS '微信支付API密钥';
COMMENT ON COLUMN stores.wechat_notify_url IS '微信支付回调地址';
COMMENT ON COLUMN stores.max_cards_per_user IS '每用户可建就诊卡数量上限';

COMMENT ON TABLE departments IS '科室表 - 支持树形结构';
COMMENT ON COLUMN departments.id IS '科室ID (UUID)';
COMMENT ON COLUMN departments.name IS '科室名称';
COMMENT ON COLUMN departments.parent_id IS '父级科室ID（自关联）';
COMMENT ON COLUMN departments.store_id IS '默认门店ID';
COMMENT ON COLUMN departments.description IS '科室描述';
COMMENT ON COLUMN departments.sort_order IS '排序';
COMMENT ON COLUMN departments.is_hot IS '是否热门: 0否 1是';
COMMENT ON COLUMN departments.status IS '状态: 0禁用 1正常';
COMMENT ON COLUMN departments.tag IS '科室标签';
COMMENT ON COLUMN departments.enable_banner IS '是否开放banner: 0禁用 1启用';
COMMENT ON COLUMN departments.enable_intro IS '是否开放科室简介: 0禁用 1启用';
COMMENT ON COLUMN departments.is_final IS '是否终极科室: 0否 1是';
COMMENT ON COLUMN departments.is_recommended IS '是否推荐: 0否 1是';
COMMENT ON COLUMN departments.banner_image IS 'banner图片URL';
COMMENT ON COLUMN departments.icon IS '科室图标URL';
COMMENT ON COLUMN departments.intro_images IS '简介图片集JSON';
COMMENT ON COLUMN departments.intro_content IS '富文本简介';
COMMENT ON COLUMN departments.features IS '科室特色JSON数组';
COMMENT ON COLUMN departments.appointment_notice IS '预约须知';
COMMENT ON COLUMN departments.phone IS '科室电话';
COMMENT ON COLUMN departments.location IS '位置/楼层';
COMMENT ON COLUMN departments.working_hours IS '工作时间';

-- ============================================
-- 四、医生管理
-- ============================================

COMMENT ON TABLE doctors IS '医生表';
COMMENT ON COLUMN doctors.id IS '医生ID (UUID)';
COMMENT ON COLUMN doctors.user_id IS '关联用户ID';
COMMENT ON COLUMN doctors.store_id IS '所属门店ID';
COMMENT ON COLUMN doctors.department_id IS '所属科室ID';
COMMENT ON COLUMN doctors.name IS '医生姓名';
COMMENT ON COLUMN doctors.username IS '医生登录账号';
COMMENT ON COLUMN doctors.phone IS '手机号';
COMMENT ON COLUMN doctors.password_hash IS '登录密码哈希';
COMMENT ON COLUMN doctors.gender IS '性别: 0女 1男';
COMMENT ON COLUMN doctors.avatar IS '头像URL';
COMMENT ON COLUMN doctors.banner IS '医生banner图URL';
COMMENT ON COLUMN doctors.title IS '职称';
COMMENT ON COLUMN doctors.years_of_experience IS '医龄(年)';
COMMENT ON COLUMN doctors.education IS '学历';
COMMENT ON COLUMN doctors.graduate_school IS '毕业院校';
COMMENT ON COLUMN doctors.license_number IS '执业证书编号';
COMMENT ON COLUMN doctors.license_image IS '执业证书图片URL';
COMMENT ON COLUMN doctors.honors IS '所获荣誉';
COMMENT ON COLUMN doctors.schedule_desc IS '坐诊时间说明';
COMMENT ON COLUMN doctors.max_daily_appointments IS '每日最大接诊量，0不限制';
COMMENT ON COLUMN doctors.online_consult_enabled IS '是否支持在线问诊: 0否 1是';
COMMENT ON COLUMN doctors.online_consult_fee IS '在线问诊费用';
COMMENT ON COLUMN doctors.page_style IS '页面风格: 1/2/3';
COMMENT ON COLUMN doctors.promo_video IS '宣传视频URL';
COMMENT ON COLUMN doctors.tags IS '标签，逗号分隔';
COMMENT ON COLUMN doctors.specialty IS '擅长';
COMMENT ON COLUMN doctors.introduction IS '简介';
COMMENT ON COLUMN doctors.is_recommended IS '是否推荐: 0否 1是';
COMMENT ON COLUMN doctors.sort_order IS '排序';
COMMENT ON COLUMN doctors.status IS '状态: 0禁用 1正常';
COMMENT ON COLUMN doctors.last_login_at IS '最后登录时间';
COMMENT ON COLUMN doctors.last_login_ip IS '最后登录IP';
COMMENT ON COLUMN doctors.use_fee_template IS '是否使用诊费模板: 0否 1是';

COMMENT ON TABLE doctor_booking_settings IS '医生预约设置表 - 按门店维度配置';
COMMENT ON COLUMN doctor_booking_settings.id IS '设置ID (UUID)';
COMMENT ON COLUMN doctor_booking_settings.store_id IS '门店ID';
COMMENT ON COLUMN doctor_booking_settings.doctor_id IS '医生ID';
COMMENT ON COLUMN doctor_booking_settings.booking_start_offset IS '预约开始偏移天数，0表示当天';
COMMENT ON COLUMN doctor_booking_settings.booking_range_days IS '预约范围天数，1-90天';
COMMENT ON COLUMN doctor_booking_settings.release_time IS '放号时间 HH:mm 格式';
COMMENT ON COLUMN doctor_booking_settings.status IS '状态: 0禁用 1启用';

-- ============================================
-- 五、排班管理
-- ============================================

COMMENT ON TABLE schedule_templates IS '排班模板表 - 周期性排班规则';
COMMENT ON COLUMN schedule_templates.id IS '模板ID (UUID)';
COMMENT ON COLUMN schedule_templates.name IS '模板名称';
COMMENT ON COLUMN schedule_templates.store_id IS '门店ID';
COMMENT ON COLUMN schedule_templates.doctor_id IS '医生ID';
COMMENT ON COLUMN schedule_templates.department_id IS '科室ID';
COMMENT ON COLUMN schedule_templates.weekdays IS '星期数组，JSON格式 [1,2,3,4,5]';
COMMENT ON COLUMN schedule_templates.appointment_type IS '预约类型: urgent/normal/expert/medical_insurance/self_pay';
COMMENT ON COLUMN schedule_templates.start_time IS '开始时间';
COMMENT ON COLUMN schedule_templates.end_time IS '结束时间';
COMMENT ON COLUMN schedule_templates.slot_count IS '班次数量';
COMMENT ON COLUMN schedule_templates.slot_capacity IS '每班次人数';
COMMENT ON COLUMN schedule_templates.schedule_mode IS '排班方式';
COMMENT ON COLUMN schedule_templates.break_times IS '排除时间段 JSON [{startTime, endTime}]';
COMMENT ON COLUMN schedule_templates.status IS '状态: 0禁用 1启用';
COMMENT ON COLUMN schedule_templates.last_generated_at IS '上一次生成排班时间';

COMMENT ON TABLE schedules IS '排班表 - 具体某天某时段的排班记录';
COMMENT ON COLUMN schedules.id IS '排班ID (UUID)';
COMMENT ON COLUMN schedules.doctor_id IS '医生ID';
COMMENT ON COLUMN schedules.store_id IS '门店ID';
COMMENT ON COLUMN schedules.template_id IS '来源模板ID（NULL表示自定义排班）';
COMMENT ON COLUMN schedules.shift_type_id IS '班次类型ID';
COMMENT ON COLUMN schedules.schedule_date IS '排班日期';
COMMENT ON COLUMN schedules.time_slot IS '时段: AM/PM/morning/afternoon/evening';
COMMENT ON COLUMN schedules.start_time IS '开始时间';
COMMENT ON COLUMN schedules.end_time IS '结束时间';
COMMENT ON COLUMN schedules.start_at IS '开始时间(带时区)';
COMMENT ON COLUMN schedules.end_at IS '结束时间(带时区)';
COMMENT ON COLUMN schedules.timezone IS '时区';
COMMENT ON COLUMN schedules.total_slots IS '总号源';
COMMENT ON COLUMN schedules.booked_slots IS '已预约数';
COMMENT ON COLUMN schedules.appointment_type IS '预约类型: urgent/normal/expert/medical_insurance/self_pay';
COMMENT ON COLUMN schedules.status IS '状态: 0停诊 1正常';

COMMENT ON TABLE rest_days IS '休息日表 - 门店/医生级别的休息日设置';
COMMENT ON COLUMN rest_days.id IS '记录ID (UUID)';
COMMENT ON COLUMN rest_days.store_id IS '门店ID';
COMMENT ON COLUMN rest_days.doctor_ids IS '医生ID列表,JSON数组,NULL表示门店所有医生';
COMMENT ON COLUMN rest_days.reason IS '休息原因';
COMMENT ON COLUMN rest_days.start_date IS '开始日期';
COMMENT ON COLUMN rest_days.end_date IS '结束日期';
COMMENT ON COLUMN rest_days.status IS '状态: 0已取消 1生效中';

COMMENT ON TABLE schedule_suspensions IS '停诊记录表';
COMMENT ON COLUMN schedule_suspensions.id IS '记录ID (UUID)';
COMMENT ON COLUMN schedule_suspensions.store_id IS '门店ID';
COMMENT ON COLUMN schedule_suspensions.doctor_id IS '医生ID';
COMMENT ON COLUMN schedule_suspensions.title IS '停诊标题';
COMMENT ON COLUMN schedule_suspensions.suspension_date IS '停诊日期';
COMMENT ON COLUMN schedule_suspensions.schedule_ids IS '选中的排班ID,JSON数组';
COMMENT ON COLUMN schedule_suspensions.time_slots IS '选中的时段,JSON数组';
COMMENT ON COLUMN schedule_suspensions.status IS '状态: 0已取消 1生效中';

COMMENT ON TABLE schedule_generation_logs IS '排班生成日志表';
COMMENT ON COLUMN schedule_generation_logs.id IS '日志ID (UUID)';
COMMENT ON COLUMN schedule_generation_logs.template_id IS '排班规则ID';
COMMENT ON COLUMN schedule_generation_logs.operator_id IS '操作人ID';
COMMENT ON COLUMN schedule_generation_logs.operator_name IS '操作人姓名';
COMMENT ON COLUMN schedule_generation_logs.action_type IS '操作类型: generate生成 / delete删除 / suspend停诊';
COMMENT ON COLUMN schedule_generation_logs.start_date IS '开始日期';
COMMENT ON COLUMN schedule_generation_logs.end_date IS '结束日期';
COMMENT ON COLUMN schedule_generation_logs.affected_count IS '影响的记录数';
COMMENT ON COLUMN schedule_generation_logs.remark IS '备注';
COMMENT ON COLUMN schedule_generation_logs.created_at IS '创建时间';

COMMENT ON TABLE leave_requests IS '停诊/调班申请表 - 医生发起的停诊或调班请求';
COMMENT ON COLUMN leave_requests.id IS '申请ID (UUID)';
COMMENT ON COLUMN leave_requests.doctor_id IS '医生ID';
COMMENT ON COLUMN leave_requests.request_type IS '申请类型: stop_clinic停诊 / schedule_change调班';
COMMENT ON COLUMN leave_requests.schedule_id IS '排班ID（停诊时）';
COMMENT ON COLUMN leave_requests.stop_date IS '停诊日期';
COMMENT ON COLUMN leave_requests.stop_period IS '停诊时段: morning/afternoon/evening/all';
COMMENT ON COLUMN leave_requests.original_date IS '原日期（调班时）';
COMMENT ON COLUMN leave_requests.original_period IS '原时段';
COMMENT ON COLUMN leave_requests.target_date IS '目标日期';
COMMENT ON COLUMN leave_requests.target_period IS '目标时段';
COMMENT ON COLUMN leave_requests.reason IS '申请原因';
COMMENT ON COLUMN leave_requests.status IS '状态: pending待审核 / approved已通过 / rejected已拒绝 / cancelled已取消';
COMMENT ON COLUMN leave_requests.reviewer_id IS '审核人ID';
COMMENT ON COLUMN leave_requests.review_comment IS '审核意见';
COMMENT ON COLUMN leave_requests.reviewed_at IS '审核时间';
COMMENT ON COLUMN leave_requests.affected_appointments IS '受影响预约数';

-- ============================================
-- 六、规则引擎
-- ============================================

COMMENT ON TABLE shift_types IS '班次类型表 - 定义不同类型的班次';
COMMENT ON COLUMN shift_types.id IS '班次类型ID (UUID)';
COMMENT ON COLUMN shift_types.code IS '类型代码: OPD门诊 / CHECKUP体检 / EXAM检查 / NURSING护理 / SPECIAL专科';
COMMENT ON COLUMN shift_types.name IS '类型名称';
COMMENT ON COLUMN shift_types.description IS '描述';
COMMENT ON COLUMN shift_types.enabled IS '是否启用';

COMMENT ON TABLE rule_sets IS '规则组表 - 预约/签到/容量规则的集合';
COMMENT ON COLUMN rule_sets.id IS '规则组ID (UUID)';
COMMENT ON COLUMN rule_sets.name IS '规则组名称';
COMMENT ON COLUMN rule_sets.enabled IS '是否启用';
COMMENT ON COLUMN rule_sets.priority IS '优先级(越小越优先)';
COMMENT ON COLUMN rule_sets.time_source IS '时间来源: SERVER/CLIENT';
COMMENT ON COLUMN rule_sets.timezone_source IS '时区来源: HOSPITAL/SHIFT/USER';
COMMENT ON COLUMN rule_sets.compare_precision IS '比较精度: SECOND/MILLISECOND/MINUTE';
COMMENT ON COLUMN rule_sets.default_open_inclusive IS '默认开放边界包含';
COMMENT ON COLUMN rule_sets.default_close_inclusive IS '默认截止边界包含';
COMMENT ON COLUMN rule_sets.rounding_mode IS '取整模式';
COMMENT ON COLUMN rule_sets.clock_skew_tolerance_sec IS '时钟偏差容忍度(秒)';
COMMENT ON COLUMN rule_sets.description IS '描述';

COMMENT ON TABLE rule_set_shift_types IS '规则组与班次类型关联表（多对多）';
COMMENT ON COLUMN rule_set_shift_types.rule_set_id IS '规则组ID';
COMMENT ON COLUMN rule_set_shift_types.shift_type_id IS '班次类型ID';

COMMENT ON TABLE rule_windows IS '时间窗配置表 - 定义预约/签到/取消的时间窗口';
COMMENT ON COLUMN rule_windows.id IS '时间窗ID (UUID)';
COMMENT ON COLUMN rule_windows.rule_set_id IS '规则组ID';
COMMENT ON COLUMN rule_windows.action IS '动作类型: BOOK预约 / CHECKIN签到 / CANCEL取消 / HOLD_RELEASE释放';
COMMENT ON COLUMN rule_windows.reference_point IS '参考点: SHIFT_START班次开始 / SHIFT_END班次结束 / BOOKING_CREATED_AT预约创建时';
COMMENT ON COLUMN rule_windows.open_offset_sec IS '开放偏移(秒)，可负可正，NULL不限制';
COMMENT ON COLUMN rule_windows.close_offset_sec IS '截止偏移(秒)，可负可正，NULL不限制';
COMMENT ON COLUMN rule_windows.open_inclusive IS '开放边界包含，NULL用规则组默认';
COMMENT ON COLUMN rule_windows.close_inclusive IS '截止边界包含，NULL用规则组默认';
COMMENT ON COLUMN rule_windows.fail_policy IS '失败策略: REJECT拒绝 / ALLOW_WITH_TAG带标签通过 / AUTO_TO_WAITLIST自动候补';
COMMENT ON COLUMN rule_windows.fail_tag IS '失败标签';
COMMENT ON COLUMN rule_windows.enabled IS '是否启用';
COMMENT ON COLUMN rule_windows.description IS '描述';

COMMENT ON TABLE rule_booking_policies IS '预约策略表 - 规则组的预约限制配置';
COMMENT ON COLUMN rule_booking_policies.rule_set_id IS '规则组ID';
COMMENT ON COLUMN rule_booking_policies.require_auth IS '是否要求登录';
COMMENT ON COLUMN rule_booking_policies.require_patient_profile_complete IS '是否要求档案完整';
COMMENT ON COLUMN rule_booking_policies.per_user_per_shift IS '每用户每班次最大预约数';
COMMENT ON COLUMN rule_booking_policies.per_user_per_day IS '每用户每天最大预约数';
COMMENT ON COLUMN rule_booking_policies.per_user_per_week IS '每用户每周最大预约数';
COMMENT ON COLUMN rule_booking_policies.conflict_same_shift IS '同班次冲突策略: REJECT/REPLACE';
COMMENT ON COLUMN rule_booking_policies.conflict_overlap_time IS '时间重叠冲突策略: REJECT/ALLOW';
COMMENT ON COLUMN rule_booking_policies.conflict_same_type_same_day IS '同类型同日冲突策略: REJECT/ALLOW';

COMMENT ON TABLE rule_checkin_policies IS '签到策略表 - 规则组的签到配置';
COMMENT ON COLUMN rule_checkin_policies.rule_set_id IS '规则组ID';
COMMENT ON COLUMN rule_checkin_policies.require_booking IS '是否必须预约';
COMMENT ON COLUMN rule_checkin_policies.allow_onsite_booking IS '是否允许现场补约';
COMMENT ON COLUMN rule_checkin_policies.max_times IS '允许签到次数';
COMMENT ON COLUMN rule_checkin_policies.audit_log IS '是否记录审计日志';
COMMENT ON COLUMN rule_checkin_policies.grace_period_sec IS '宽限期(秒)';
COMMENT ON COLUMN rule_checkin_policies.after_grace_status IS '宽限后状态: LATE/ON_TIME';
COMMENT ON COLUMN rule_checkin_policies.no_checkin_after_close IS '截止后未签到处理: KEEP_BOOKED保留 / AUTO_CANCEL自动取消 / ABSENT标记缺席';

COMMENT ON TABLE rule_capacity_policies IS '容量策略表 - 规则组的容量与候补配置';
COMMENT ON COLUMN rule_capacity_policies.rule_set_id IS '规则组ID';
COMMENT ON COLUMN rule_capacity_policies.total_capacity IS '总容量，0不限制';
COMMENT ON COLUMN rule_capacity_policies.per_user_capacity IS '每用户容量';
COMMENT ON COLUMN rule_capacity_policies.waitlist_enabled IS '是否启用候补';
COMMENT ON COLUMN rule_capacity_policies.waitlist_max_size IS '候补队列最大长度';
COMMENT ON COLUMN rule_capacity_policies.waitlist_promote_policy IS '候补递补策略: MANUAL手动 / AUTO自动';
COMMENT ON COLUMN rule_capacity_policies.overbooking_enabled IS '是否允许超额';
COMMENT ON COLUMN rule_capacity_policies.overbooking_max IS '超额最大数量';

-- ============================================
-- 七、预约管理
-- ============================================

COMMENT ON TABLE appointments IS '预约表 - 核心业务表';
COMMENT ON COLUMN appointments.id IS '预约ID (UUID)';
COMMENT ON COLUMN appointments.appointment_no IS '预约单号';
COMMENT ON COLUMN appointments.user_id IS '用户ID';
COMMENT ON COLUMN appointments.patient_id IS '就诊人ID';
COMMENT ON COLUMN appointments.doctor_id IS '医生ID';
COMMENT ON COLUMN appointments.schedule_id IS '排班ID';
COMMENT ON COLUMN appointments.rule_set_id IS '应用的规则组ID';
COMMENT ON COLUMN appointments.queue_number IS '队列号';
COMMENT ON COLUMN appointments.status IS '状态: 0待支付 1已预约 2已签到 3历史候诊(遗留) 4就诊中 5已完成 6已取消 7已过期 8已爽约';
COMMENT ON COLUMN appointments.sign_in_time IS '签到时间';
COMMENT ON COLUMN appointments.call_time IS '叫号时间';
COMMENT ON COLUMN appointments.complete_time IS '完成时间';
COMMENT ON COLUMN appointments.cancel_time IS '取消时间';
COMMENT ON COLUMN appointments.cancel_reason IS '取消原因';
COMMENT ON COLUMN appointments.remark IS '备注';
COMMENT ON COLUMN appointments.symptom_description IS '病情描述/预填信息';
COMMENT ON COLUMN appointments.book_open_at IS '预约开放时间(规则快照)';
COMMENT ON COLUMN appointments.book_close_at IS '预约截止时间(规则快照)';
COMMENT ON COLUMN appointments.checkin_open_at IS '签到开放时间(规则快照)';
COMMENT ON COLUMN appointments.checkin_close_at IS '签到截止时间(规则快照)';
COMMENT ON COLUMN appointments.cancel_open_at IS '取消开放时间(规则快照)';
COMMENT ON COLUMN appointments.cancel_close_at IS '取消截止时间(规则快照)';
COMMENT ON COLUMN appointments.checkin_count IS '签到次数';
COMMENT ON COLUMN appointments.patient_name IS '就诊人姓名(快照)';
COMMENT ON COLUMN appointments.patient_phone IS '就诊人手机(快照)';
COMMENT ON COLUMN appointments.doctor_name IS '医生姓名(快照)';
COMMENT ON COLUMN appointments.doctor_title IS '医生职称(快照)';
COMMENT ON COLUMN appointments.department_name IS '科室名称(快照)';
COMMENT ON COLUMN appointments.reminder_sent IS '是否已发送提醒: 0否 1是';
COMMENT ON COLUMN appointments.reminder_sent_at IS '提醒发送时间';

COMMENT ON TABLE appointment_checkins IS '签到日志表 - 记录每次签到操作';
COMMENT ON COLUMN appointment_checkins.id IS '签到日志ID (UUID)';
COMMENT ON COLUMN appointment_checkins.appointment_id IS '预约ID';
COMMENT ON COLUMN appointment_checkins.checkin_time IS '签到时间';
COMMENT ON COLUMN appointment_checkins.checkin_method IS '签到方式: QR_CODE扫码 / MANUAL手动 / PHONE手机';
COMMENT ON COLUMN appointment_checkins.device_info IS '设备信息';
COMMENT ON COLUMN appointment_checkins.location_info IS '位置信息';
COMMENT ON COLUMN appointment_checkins.operator_id IS '操作人ID';
COMMENT ON COLUMN appointment_checkins.operator_type IS '操作人类型: USER/ADMIN/DOCTOR';
COMMENT ON COLUMN appointment_checkins.status IS '状态: SUCCESS成功 / FAILED失败 / CANCELLED已取消';
COMMENT ON COLUMN appointment_checkins.fail_reason IS '失败原因';
COMMENT ON COLUMN appointment_checkins.created_at IS '创建时间';

COMMENT ON TABLE waitlist_entries IS '候补队列表 - 班次满员时的候补管理';
COMMENT ON COLUMN waitlist_entries.id IS '候补ID (UUID)';
COMMENT ON COLUMN waitlist_entries.user_id IS '用户ID';
COMMENT ON COLUMN waitlist_entries.patient_id IS '就诊人ID';
COMMENT ON COLUMN waitlist_entries.schedule_id IS '排班ID';
COMMENT ON COLUMN waitlist_entries.shift_type_id IS '班次类型ID';
COMMENT ON COLUMN waitlist_entries.status IS '状态: WAITING等待中 / PROMOTED已转预约 / CANCELLED已取消 / EXPIRED已过期';
COMMENT ON COLUMN waitlist_entries.position IS '在队列中的位置';
COMMENT ON COLUMN waitlist_entries.priority IS '优先级(越小越高)';
COMMENT ON COLUMN waitlist_entries.symptom_description IS '症状描述';
COMMENT ON COLUMN waitlist_entries.created_at IS '加入候补时间';
COMMENT ON COLUMN waitlist_entries.promoted_at IS '转预约时间';
COMMENT ON COLUMN waitlist_entries.cancelled_at IS '取消时间';
COMMENT ON COLUMN waitlist_entries.operator_id IS '操作人ID';
COMMENT ON COLUMN waitlist_entries.operator_type IS '操作人类型: USER/ADMIN/SYSTEM';

-- ============================================
-- 八、诊费管理
-- ============================================

COMMENT ON TABLE consultation_fee_types IS '诊费类型表';
COMMENT ON COLUMN consultation_fee_types.id IS '类型ID (UUID)';
COMMENT ON COLUMN consultation_fee_types.store_id IS '门店ID，NULL表示全局类型';
COMMENT ON COLUMN consultation_fee_types.name IS '诊费类型名称';
COMMENT ON COLUMN consultation_fee_types.code IS '类型编码';
COMMENT ON COLUMN consultation_fee_types.description IS '描述';
COMMENT ON COLUMN consultation_fee_types.sort_order IS '排序';
COMMENT ON COLUMN consultation_fee_types.status IS '状态: 0禁用 1启用';

COMMENT ON TABLE consultation_fee_templates IS '诊费模板表 - 全局默认诊费配置';
COMMENT ON COLUMN consultation_fee_templates.id IS '模板ID (UUID)';
COMMENT ON COLUMN consultation_fee_templates.fee_type_id IS '诊费类型ID';
COMMENT ON COLUMN consultation_fee_templates.initial_fee IS '初诊金额';
COMMENT ON COLUMN consultation_fee_templates.follow_up_fee IS '复诊金额';
COMMENT ON COLUMN consultation_fee_templates.status IS '状态: 0禁用 1启用';

COMMENT ON TABLE store_fee_templates IS '门店诊费模板表 - 可覆盖全局模板';
COMMENT ON COLUMN store_fee_templates.id IS '模板ID (UUID)';
COMMENT ON COLUMN store_fee_templates.store_id IS '门店ID';
COMMENT ON COLUMN store_fee_templates.fee_type_id IS '诊费类型ID';
COMMENT ON COLUMN store_fee_templates.initial_fee IS '初诊金额';
COMMENT ON COLUMN store_fee_templates.follow_up_fee IS '复诊金额';
COMMENT ON COLUMN store_fee_templates.status IS '状态: 0禁用 1启用';

COMMENT ON TABLE doctor_consultation_fees IS '医生诊费配置表 - 最高优先级的诊费配置';
COMMENT ON COLUMN doctor_consultation_fees.id IS '配置ID (UUID)';
COMMENT ON COLUMN doctor_consultation_fees.doctor_id IS '医生ID';
COMMENT ON COLUMN doctor_consultation_fees.store_id IS '门店ID';
COMMENT ON COLUMN doctor_consultation_fees.department_id IS '科室ID';
COMMENT ON COLUMN doctor_consultation_fees.fee_type_id IS '诊费类型ID';
COMMENT ON COLUMN doctor_consultation_fees.initial_fee IS '初诊金额';
COMMENT ON COLUMN doctor_consultation_fees.follow_up_fee IS '复诊金额';
COMMENT ON COLUMN doctor_consultation_fees.status IS '状态: 0禁用 1启用';

-- ============================================
-- 九、病历管理
-- ============================================

COMMENT ON TABLE medical_records IS '病历表';
COMMENT ON COLUMN medical_records.id IS '病历ID (UUID)';
COMMENT ON COLUMN medical_records.record_no IS '病历号';
COMMENT ON COLUMN medical_records.appointment_id IS '预约ID';
COMMENT ON COLUMN medical_records.patient_id IS '患者ID';
COMMENT ON COLUMN medical_records.doctor_id IS '医生ID';
COMMENT ON COLUMN medical_records.department_id IS '科室ID';
COMMENT ON COLUMN medical_records.chief_complaint IS '主诉';
COMMENT ON COLUMN medical_records.present_illness IS '现病史';
COMMENT ON COLUMN medical_records.past_history IS '既往史';
COMMENT ON COLUMN medical_records.allergy_history IS '过敏史';
COMMENT ON COLUMN medical_records.physical_exam IS '体格检查';
COMMENT ON COLUMN medical_records.auxiliary_exam IS '辅助检查';
COMMENT ON COLUMN medical_records.diagnosis IS '诊断';
COMMENT ON COLUMN medical_records.treatment IS '治疗方案';
COMMENT ON COLUMN medical_records.prescription IS '处方';
COMMENT ON COLUMN medical_records.advice IS '医嘱';
COMMENT ON COLUMN medical_records.total_fee IS '总费用';
COMMENT ON COLUMN medical_records.status IS '状态: 1草稿 2已完成';
COMMENT ON COLUMN medical_records.visit_date IS '就诊日期';

-- ============================================
-- 十、内容管理
-- ============================================

COMMENT ON TABLE news IS '新闻资讯表';
COMMENT ON COLUMN news.id IS '新闻ID (UUID)';
COMMENT ON COLUMN news.store_id IS '所属门店ID，NULL表示全局';
COMMENT ON COLUMN news.title IS '标题';
COMMENT ON COLUMN news.type IS '类型: 1医院动态 2健康科普 3通知公告 4政策法规';
COMMENT ON COLUMN news.cover_image IS '封面图URL';
COMMENT ON COLUMN news.summary IS '摘要';
COMMENT ON COLUMN news.content IS '内容(富文本)';
COMMENT ON COLUMN news.view_count IS '浏览次数';
COMMENT ON COLUMN news.is_top IS '是否置顶: 0否 1是';
COMMENT ON COLUMN news.status IS '状态: 0草稿 1已发布';
COMMENT ON COLUMN news.publish_time IS '发布时间';

COMMENT ON TABLE notices IS '公告通知表';
COMMENT ON COLUMN notices.id IS '公告ID (UUID)';
COMMENT ON COLUMN notices.store_id IS '所属门店ID，NULL表示全局';
COMMENT ON COLUMN notices.title IS '标题';
COMMENT ON COLUMN notices.type IS '类型: 1系统公告 2停诊通知 3活动通知 4重要提醒';
COMMENT ON COLUMN notices.content IS '内容';
COMMENT ON COLUMN notices.is_top IS '是否置顶: 0否 1是';
COMMENT ON COLUMN notices.status IS '状态: 0草稿 1已发布';
COMMENT ON COLUMN notices.publish_time IS '发布时间';

COMMENT ON TABLE banners IS '轮播图表';
COMMENT ON COLUMN banners.id IS '轮播图ID (UUID)';
COMMENT ON COLUMN banners.store_id IS '所属门店ID，NULL表示全局';
COMMENT ON COLUMN banners.title IS '标题';
COMMENT ON COLUMN banners.image_url IS '图片URL';
COMMENT ON COLUMN banners.link_type IS '链接类型: 0无跳转 1内部页面 2外部链接 3新闻详情';
COMMENT ON COLUMN banners.link_url IS '跳转链接';
COMMENT ON COLUMN banners.position IS '显示位置: home首页 / department科室 / profile个人中心';
COMMENT ON COLUMN banners.sort_order IS '排序';
COMMENT ON COLUMN banners.status IS '状态: 0禁用 1启用';

COMMENT ON TABLE booking_notices IS '预约须知表';
COMMENT ON COLUMN booking_notices.id IS '须知ID (UUID)';
COMMENT ON COLUMN booking_notices.type IS '类型: BOOKING预约须知 / VISIT就诊须知 / REFUND退费须知';
COMMENT ON COLUMN booking_notices.title IS '标题';
COMMENT ON COLUMN booking_notices.content IS '内容';
COMMENT ON COLUMN booking_notices.sort_order IS '排序';
COMMENT ON COLUMN booking_notices.status IS '状态: 0禁用 1启用';

-- ============================================
-- 十一、消息通知
-- ============================================

COMMENT ON TABLE messages IS '消息表 - 站内消息';
COMMENT ON COLUMN messages.id IS '消息ID (UUID)';
COMMENT ON COLUMN messages.store_id IS '所属门店ID，NULL表示全局';
COMMENT ON COLUMN messages.user_id IS '接收用户ID';
COMMENT ON COLUMN messages.user_type IS '用户类型: patient/doctor';
COMMENT ON COLUMN messages.title IS '消息标题';
COMMENT ON COLUMN messages.content IS '消息内容';
COMMENT ON COLUMN messages.message_type IS '消息类型: appointment/consultation/schedule/system/stop_clinic/feedback';
COMMENT ON COLUMN messages.related_id IS '关联业务ID';
COMMENT ON COLUMN messages.is_read IS '是否已读: 0未读 1已读';
COMMENT ON COLUMN messages.read_at IS '阅读时间';
COMMENT ON COLUMN messages.extra_data IS '额外数据(JSON)';

COMMENT ON TABLE message_templates IS '消息模板表';
COMMENT ON COLUMN message_templates.id IS '模板ID (UUID)';
COMMENT ON COLUMN message_templates.code IS '模板编码';
COMMENT ON COLUMN message_templates.name IS '模板名称';
COMMENT ON COLUMN message_templates.message_type IS '消息类型';
COMMENT ON COLUMN message_templates.title_template IS '标题模板';
COMMENT ON COLUMN message_templates.content_template IS '内容模板';
COMMENT ON COLUMN message_templates.description IS '模板说明';
COMMENT ON COLUMN message_templates.status IS '状态: 0禁用 1启用';

COMMENT ON TABLE email_templates IS '邮件模板表';
COMMENT ON COLUMN email_templates.id IS '模板ID (UUID)';
COMMENT ON COLUMN email_templates.code IS '模板编码';
COMMENT ON COLUMN email_templates.name IS '模板名称';
COMMENT ON COLUMN email_templates.template_type IS '模板类型: appointment_confirm/appointment_remind/appointment_cancel/stop_clinic/custom';
COMMENT ON COLUMN email_templates.subject_template IS '邮件主题模板';
COMMENT ON COLUMN email_templates.content_template IS '邮件内容模板(HTML)';
COMMENT ON COLUMN email_templates.description IS '模板说明';
COMMENT ON COLUMN email_templates.status IS '状态: 0禁用 1启用';

-- ============================================
-- 十二、系统配置
-- ============================================

COMMENT ON TABLE system_settings IS '系统设置表 - 键值对存储，支持门店级别覆盖';
COMMENT ON COLUMN system_settings.id IS '设置ID (UUID)';
COMMENT ON COLUMN system_settings.store_id IS '门店ID，为空表示全局配置';
COMMENT ON COLUMN system_settings.category IS '分类: booking/hospital/wechat/sms/time_periods/booking_fields/patient_card/image';
COMMENT ON COLUMN system_settings.key IS '设置项键名';
COMMENT ON COLUMN system_settings.value IS '设置项值';
COMMENT ON COLUMN system_settings.description IS '描述';

COMMENT ON TABLE store_visit_type_configs IS '门店复诊规则配置表';
COMMENT ON COLUMN store_visit_type_configs.id IS '配置ID (UUID)';
COMMENT ON COLUMN store_visit_type_configs.store_id IS '门店ID';
COMMENT ON COLUMN store_visit_type_configs.time_limit IS '复诊时间限制值';
COMMENT ON COLUMN store_visit_type_configs.time_unit IS '时间单位: hours/days';
COMMENT ON COLUMN store_visit_type_configs.scope IS '复诊范围: same_doctor同医生 / same_department同科室 / same_store同门店';
COMMENT ON COLUMN store_visit_type_configs.status IS '状态: 0禁用 1启用';

-- ============================================
-- 十三、日志与审计
-- ============================================

COMMENT ON TABLE operation_logs IS '操作日志表 - 管理后台操作审计';
COMMENT ON COLUMN operation_logs.id IS '日志ID (UUID)';
COMMENT ON COLUMN operation_logs.admin_id IS '操作人ID';
COMMENT ON COLUMN operation_logs.admin_name IS '操作人姓名';
COMMENT ON COLUMN operation_logs.module IS '模块';
COMMENT ON COLUMN operation_logs.action IS '操作';
COMMENT ON COLUMN operation_logs.method IS '请求方法';
COMMENT ON COLUMN operation_logs.path IS '请求路径';
COMMENT ON COLUMN operation_logs.params IS '请求参数';
COMMENT ON COLUMN operation_logs.result IS '结果';
COMMENT ON COLUMN operation_logs.ip IS 'IP地址';
COMMENT ON COLUMN operation_logs.user_agent IS 'User-Agent';
COMMENT ON COLUMN operation_logs.duration IS '耗时(毫秒)';
COMMENT ON COLUMN operation_logs.created_at IS '创建时间';

COMMENT ON TABLE user_behavior_logs IS '用户行为日志表 - 前端埋点数据';
COMMENT ON COLUMN user_behavior_logs.id IS '日志ID (UUID)';
COMMENT ON COLUMN user_behavior_logs.platform IS '平台: admin/h5/miniapp';
COMMENT ON COLUMN user_behavior_logs.user_id IS '用户ID';
COMMENT ON COLUMN user_behavior_logs.session_id IS '会话ID';
COMMENT ON COLUMN user_behavior_logs.event_type IS '事件类型: page_view/page_leave/click/search/custom';
COMMENT ON COLUMN user_behavior_logs.page_path IS '页面路径';
COMMENT ON COLUMN user_behavior_logs.page_title IS '页面标题';
COMMENT ON COLUMN user_behavior_logs.element_id IS '元素ID';
COMMENT ON COLUMN user_behavior_logs.element_text IS '元素文本';
COMMENT ON COLUMN user_behavior_logs.search_keyword IS '搜索关键词';
COMMENT ON COLUMN user_behavior_logs.event_name IS '自定义事件名称';
COMMENT ON COLUMN user_behavior_logs.duration IS '停留时长(毫秒)';
COMMENT ON COLUMN user_behavior_logs.referrer IS '来源页面';
COMMENT ON COLUMN user_behavior_logs.extra_data IS '额外数据(JSON)';
COMMENT ON COLUMN user_behavior_logs.ip IS 'IP地址';
COMMENT ON COLUMN user_behavior_logs.user_agent IS 'User-Agent';
COMMENT ON COLUMN user_behavior_logs.device_type IS '设备类型: desktop/mobile/tablet';
COMMENT ON COLUMN user_behavior_logs.browser IS '浏览器';
COMMENT ON COLUMN user_behavior_logs.os IS '操作系统';
COMMENT ON COLUMN user_behavior_logs.created_at IS '创建时间';

COMMENT ON TABLE point_logs IS '积分流水表';
COMMENT ON COLUMN point_logs.id IS '流水ID (UUID)';
COMMENT ON COLUMN point_logs.user_id IS '用户ID';
COMMENT ON COLUMN point_logs.change_amount IS '变更积分（正增负减）';
COMMENT ON COLUMN point_logs.balance IS '变更后余额';
COMMENT ON COLUMN point_logs.type IS '类型: 1消费 2充值 3赠送 4手动调整';
COMMENT ON COLUMN point_logs.remark IS '备注';
COMMENT ON COLUMN point_logs.operator_id IS '操作人ID';

-- ============================================
-- 十四、用户服务
-- ============================================

COMMENT ON TABLE blacklists IS '黑名单表';
COMMENT ON COLUMN blacklists.id IS '黑名单ID (UUID)';
COMMENT ON COLUMN blacklists.user_id IS '用户ID';
COMMENT ON COLUMN blacklists.store_id IS '门店ID，不选则针对所有门店';
COMMENT ON COLUMN blacklists.keyword IS '手机号或身份证关键词';
COMMENT ON COLUMN blacklists.reason IS '黑名单原因/备注';
COMMENT ON COLUMN blacklists.no_show_count IS '爽约次数（自动触发时记录）';
COMMENT ON COLUMN blacklists.source IS '来源: 1手动添加 2自动触发';
COMMENT ON COLUMN blacklists.expire_at IS '解禁时间';
COMMENT ON COLUMN blacklists.released_at IS '实际解禁时间';
COMMENT ON COLUMN blacklists.status IS '状态: 1生效 0已解禁';

COMMENT ON TABLE feedbacks IS '用户反馈表';
COMMENT ON COLUMN feedbacks.id IS '反馈ID (UUID)';
COMMENT ON COLUMN feedbacks.user_id IS '用户ID';
COMMENT ON COLUMN feedbacks.user_type IS '用户类型: patient/doctor';
COMMENT ON COLUMN feedbacks.feedback_type IS '反馈类型: suggestion建议 / complaint投诉 / bug问题反馈 / other其他';
COMMENT ON COLUMN feedbacks.title IS '反馈标题';
COMMENT ON COLUMN feedbacks.content IS '反馈内容';
COMMENT ON COLUMN feedbacks.images IS '图片URL列表(JSON)';
COMMENT ON COLUMN feedbacks.contact IS '联系方式';
COMMENT ON COLUMN feedbacks.status IS '状态: pending待处理 / processing处理中 / resolved已解决 / closed已关闭';
COMMENT ON COLUMN feedbacks.handler_id IS '处理人ID';
COMMENT ON COLUMN feedbacks.reply IS '回复内容';
COMMENT ON COLUMN feedbacks.handled_at IS '处理时间';

COMMENT ON TABLE user_favorites IS '用户收藏表';
COMMENT ON COLUMN user_favorites.id IS '收藏ID (UUID)';
COMMENT ON COLUMN user_favorites.user_id IS '用户ID';
COMMENT ON COLUMN user_favorites.target_type IS '收藏类型: doctor医生 / department科室';
COMMENT ON COLUMN user_favorites.target_id IS '收藏目标ID';

-- ============================================
-- 附录：AuditMixin 公共审计字段批量注释
-- 以下表均继承 AuditMixin，统一补充 created_at/updated_at/created_by/updated_by 注释
-- (users 表已在上方单独注释，此处跳过)
-- ============================================

DO $$
DECLARE
    t TEXT;
    audit_tables TEXT[] := ARRAY[
        'patients', 'admins', 'roles', 'permissions',
        'stores', 'departments',
        'doctors', 'doctor_booking_settings',
        'schedule_templates', 'schedules', 'rest_days', 'schedule_suspensions', 'leave_requests',
        'shift_types', 'rule_sets', 'rule_windows', 'rule_booking_policies', 'rule_checkin_policies', 'rule_capacity_policies',
        'appointments',
        'consultation_fee_types', 'consultation_fee_templates', 'store_fee_templates', 'doctor_consultation_fees',
        'medical_records',
        'news', 'notices', 'banners', 'booking_notices',
        'messages', 'message_templates', 'email_templates',
        'system_settings', 'store_visit_type_configs',
        'point_logs',
        'blacklists', 'feedbacks', 'user_favorites'
    ];
BEGIN
    FOREACH t IN ARRAY audit_tables
    LOOP
        -- 仅在列存在时添加注释（避免无 AuditMixin 的表报错）
        IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = t AND column_name = 'created_at') THEN
            EXECUTE format('COMMENT ON COLUMN %I.created_at IS %L', t, '创建时间');
        END IF;
        IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = t AND column_name = 'updated_at') THEN
            EXECUTE format('COMMENT ON COLUMN %I.updated_at IS %L', t, '更新时间');
        END IF;
        IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = t AND column_name = 'created_by') THEN
            EXECUTE format('COMMENT ON COLUMN %I.created_by IS %L', t, '创建人ID');
        END IF;
        IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = t AND column_name = 'updated_by') THEN
            EXECUTE format('COMMENT ON COLUMN %I.updated_by IS %L', t, '更新人ID');
        END IF;
    END LOOP;
END
$$;
