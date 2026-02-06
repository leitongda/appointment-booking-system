-- ============================================
-- 医院挂号系统 - 数据库表结构 (实际 ORM 对齐版)
-- Database: PostgreSQL 16+
-- 同步自: apps/server/app/models/
-- 最后更新: 2026-02-06
--
-- 注意: 此文件为文档用途，实际表结构由 Alembic 迁移管理。
-- 已废弃的表见 data-dictionary.md 废表清单。
-- ============================================

-- 启用UUID扩展
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================
-- 一、用户与认证
-- ============================================

-- 用户表
CREATE TABLE users (
    id VARCHAR(36) PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    phone VARCHAR(20) UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    nickname VARCHAR(50),
    avatar VARCHAR(255),
    gender INTEGER DEFAULT 0,
    openid VARCHAR(100) UNIQUE,
    status INTEGER DEFAULT 1,
    points INTEGER DEFAULT 0,
    unionid VARCHAR(100) UNIQUE,
    wechat_nickname VARCHAR(50),
    wechat_avatar VARCHAR(500),
    wechat_synced_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(36),
    updated_by VARCHAR(36)
);

COMMENT ON TABLE users IS '用户表 - C端用户';
CREATE INDEX idx_users_phone ON users(phone);
CREATE INDEX idx_users_openid ON users(openid);

-- 就诊人表
CREATE TABLE patients (
    id VARCHAR(36) PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    user_id VARCHAR(36) NOT NULL REFERENCES users(id),
    store_id VARCHAR(36),
    name VARCHAR(50) NOT NULL,
    phone VARCHAR(20) NOT NULL,
    id_card VARCHAR(18),
    gender INTEGER,
    age INTEGER,
    birthday TIMESTAMP,
    relationship VARCHAR(20),
    is_default BOOLEAN DEFAULT FALSE,
    card_no VARCHAR(50) UNIQUE,
    province VARCHAR(50),
    city VARCHAR(50),
    district VARCHAR(50),
    street VARCHAR(100),
    id_card_type INTEGER DEFAULT 1,
    ethnicity VARCHAR(20) DEFAULT '汉族',
    address VARCHAR(255),
    source INTEGER DEFAULT 1,
    total_consumption NUMERIC(10,2) DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(36),
    updated_by VARCHAR(36)
);

COMMENT ON TABLE patients IS '就诊人表';
CREATE INDEX idx_patients_user ON patients(user_id);
CREATE INDEX idx_patients_card_no ON patients(card_no);
CREATE INDEX idx_patients_store ON patients(store_id);

-- ============================================
-- 二、权限与管理
-- ============================================

-- 角色表
CREATE TABLE roles (
    id VARCHAR(36) PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    name VARCHAR(50) NOT NULL,
    code VARCHAR(50) UNIQUE NOT NULL,
    description VARCHAR(200),
    status INTEGER DEFAULT 1,
    permissions TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(36),
    updated_by VARCHAR(36)
);

COMMENT ON TABLE roles IS '角色表';

-- 权限表
CREATE TABLE permissions (
    id VARCHAR(36) PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    code VARCHAR(100) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    type VARCHAR(20) NOT NULL,
    parent_code VARCHAR(100),
    icon VARCHAR(50),
    sort INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(36),
    updated_by VARCHAR(36)
);

COMMENT ON TABLE permissions IS '权限表';

-- 角色权限关联表
CREATE TABLE role_permissions (
    role_id VARCHAR(36) REFERENCES roles(id),
    permission VARCHAR(100),
    PRIMARY KEY (role_id, permission)
);

COMMENT ON TABLE role_permissions IS '角色权限关联表';

-- 管理员表
CREATE TABLE admins (
    id VARCHAR(36) PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    name VARCHAR(50),
    phone VARCHAR(20),
    email VARCHAR(100),
    avatar VARCHAR(255),
    role_id VARCHAR(36) REFERENCES roles(id),
    current_store_id VARCHAR(36),
    status INTEGER DEFAULT 1,
    last_login_at TIMESTAMP,
    last_login_ip VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(36),
    updated_by VARCHAR(36)
);

COMMENT ON TABLE admins IS '管理员表';

-- 管理员门店关联表
CREATE TABLE admin_stores (
    admin_id VARCHAR(36) REFERENCES admins(id) ON DELETE CASCADE,
    store_id VARCHAR(36) NOT NULL,
    is_manager INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (admin_id, store_id)
);

COMMENT ON TABLE admin_stores IS '管理员门店关联表（多对多）';

-- 管理员登录历史表
CREATE TABLE admin_login_history (
    id VARCHAR(36) PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    admin_id VARCHAR(36) NOT NULL REFERENCES admins(id),
    login_time TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    logout_time TIMESTAMP,
    logout_type VARCHAR(20),
    login_ip VARCHAR(50),
    user_agent VARCHAR(500),
    browser VARCHAR(50),
    os VARCHAR(50),
    device_type VARCHAR(20),
    duration INTEGER
);

COMMENT ON TABLE admin_login_history IS '管理员登录历史表';

-- 操作日志表
CREATE TABLE operation_logs (
    id VARCHAR(36) PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    admin_id VARCHAR(36) REFERENCES admins(id),
    admin_name VARCHAR(50),
    module VARCHAR(50),
    action VARCHAR(100),
    method VARCHAR(10),
    path VARCHAR(255),
    params TEXT,
    result VARCHAR(20),
    ip VARCHAR(50),
    user_agent VARCHAR(255),
    duration INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE operation_logs IS '操作日志表';
CREATE INDEX idx_operation_logs_admin ON operation_logs(admin_id);
CREATE INDEX idx_operation_logs_created ON operation_logs(created_at);

-- ============================================
-- 三、机构管理
-- ============================================

-- 门店/分院表
CREATE TABLE stores (
    id VARCHAR(36) PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    name VARCHAR(100) NOT NULL,
    code VARCHAR(50) UNIQUE,
    address VARCHAR(255),
    province VARCHAR(50),
    city VARCHAR(50),
    district VARCHAR(50),
    latitude VARCHAR(20),
    longitude VARCHAR(20),
    phone VARCHAR(50),
    contact_person VARCHAR(50),
    description TEXT,
    opening_time TIME,
    closing_time TIME,
    working_days VARCHAR(50) DEFAULT '1,2,3,4,5,6,7',
    business_hours VARCHAR(100),
    image VARCHAR(255),
    logo VARCHAR(255),
    password VARCHAR(100),
    email VARCHAR(100),
    theme_style VARCHAR(50),
    sort_order INTEGER DEFAULT 0,
    status INTEGER DEFAULT 1,
    wechat_app_id VARCHAR(100),
    wechat_app_secret VARCHAR(100),
    wechat_mch_id VARCHAR(100),
    wechat_api_key VARCHAR(100),
    wechat_notify_url VARCHAR(255),
    max_cards_per_user INTEGER DEFAULT 5,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(36),
    updated_by VARCHAR(36)
);

COMMENT ON TABLE stores IS '门店/分院表';

-- 科室表
CREATE TABLE departments (
    id VARCHAR(36) PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    name VARCHAR(100) NOT NULL,
    parent_id VARCHAR(36) REFERENCES departments(id),
    store_id VARCHAR(36) REFERENCES stores(id),
    description TEXT,
    sort_order INTEGER DEFAULT 0,
    is_hot INTEGER DEFAULT 0,
    status INTEGER DEFAULT 1,
    tag VARCHAR(100),
    enable_banner INTEGER DEFAULT 0,
    enable_intro INTEGER DEFAULT 0,
    is_final INTEGER DEFAULT 0,
    is_recommended INTEGER DEFAULT 0,
    banner_image VARCHAR(500),
    icon VARCHAR(500),
    intro_images TEXT,
    intro_content TEXT,
    features TEXT,
    appointment_notice TEXT,
    phone VARCHAR(20),
    location VARCHAR(100),
    working_hours VARCHAR(200),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(36),
    updated_by VARCHAR(36)
);

COMMENT ON TABLE departments IS '科室表';
CREATE INDEX idx_departments_parent ON departments(parent_id);
CREATE INDEX idx_departments_store ON departments(store_id);

-- ============================================
-- 四、医生管理
-- ============================================

-- 医生表
CREATE TABLE doctors (
    id VARCHAR(36) PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    user_id VARCHAR(36) REFERENCES users(id),
    store_id VARCHAR(36) REFERENCES stores(id),
    department_id VARCHAR(36) NOT NULL REFERENCES departments(id),
    name VARCHAR(50) NOT NULL,
    username VARCHAR(50) UNIQUE,
    phone VARCHAR(20) UNIQUE,
    password_hash VARCHAR(255),
    gender INTEGER DEFAULT 1,
    avatar VARCHAR(255),
    banner VARCHAR(255),
    title VARCHAR(50),
    years_of_experience INTEGER DEFAULT 0,
    education VARCHAR(50),
    graduate_school VARCHAR(100),
    license_number VARCHAR(100),
    license_image VARCHAR(255),
    honors TEXT,
    schedule_desc VARCHAR(255),
    max_daily_appointments INTEGER DEFAULT 0,
    online_consult_enabled INTEGER DEFAULT 0,
    online_consult_fee NUMERIC(10,2) DEFAULT 0,
    page_style INTEGER DEFAULT 1,
    promo_video VARCHAR(255),
    tags VARCHAR(255),
    specialty TEXT,
    introduction TEXT,
    is_recommended INTEGER DEFAULT 0,
    sort_order INTEGER DEFAULT 0,
    status INTEGER DEFAULT 1,
    last_login_at TIMESTAMP,
    last_login_ip VARCHAR(50),
    use_fee_template INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(36),
    updated_by VARCHAR(36)
);

COMMENT ON TABLE doctors IS '医生表';
CREATE INDEX idx_doctors_store ON doctors(store_id);
CREATE INDEX idx_doctors_department ON doctors(department_id);
CREATE INDEX idx_doctors_username ON doctors(username);

-- 医生预约设置表
CREATE TABLE doctor_booking_settings (
    id VARCHAR(36) PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    store_id VARCHAR(36) NOT NULL REFERENCES stores(id),
    doctor_id VARCHAR(36) NOT NULL REFERENCES doctors(id),
    booking_start_offset INTEGER DEFAULT 0,
    booking_range_days INTEGER DEFAULT 14,
    release_time VARCHAR(5) DEFAULT '00:00',
    status INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(36),
    updated_by VARCHAR(36),
    UNIQUE(store_id, doctor_id)
);

COMMENT ON TABLE doctor_booking_settings IS '医生预约设置表';

-- ============================================
-- 五、排班管理
-- ============================================

-- 排班模板表
CREATE TABLE schedule_templates (
    id VARCHAR(36) PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    name VARCHAR(100) NOT NULL,
    store_id VARCHAR(36) NOT NULL REFERENCES stores(id),
    doctor_id VARCHAR(36) NOT NULL REFERENCES doctors(id),
    department_id VARCHAR(36) NOT NULL REFERENCES departments(id),
    weekdays TEXT NOT NULL,
    appointment_type VARCHAR(20) DEFAULT 'normal',
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,
    slot_count INTEGER NOT NULL DEFAULT 1,
    slot_capacity INTEGER NOT NULL DEFAULT 10,
    schedule_mode VARCHAR(50) DEFAULT 'weekly',
    break_times TEXT,
    status INTEGER DEFAULT 1,
    last_generated_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(36),
    updated_by VARCHAR(36)
);

COMMENT ON TABLE schedule_templates IS '排班模板表';

-- 班次类型表
CREATE TABLE shift_types (
    id VARCHAR(36) PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    code VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(36),
    updated_by VARCHAR(36)
);

COMMENT ON TABLE shift_types IS '班次类型表';

-- 排班表
CREATE TABLE schedules (
    id VARCHAR(36) PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    doctor_id VARCHAR(36) NOT NULL REFERENCES doctors(id),
    store_id VARCHAR(36) REFERENCES stores(id),
    template_id VARCHAR(36) REFERENCES schedule_templates(id),
    shift_type_id VARCHAR(36) REFERENCES shift_types(id),
    schedule_date DATE NOT NULL,
    time_slot VARCHAR(10),
    start_time TIME,
    end_time TIME,
    start_at TIMESTAMP WITH TIME ZONE,
    end_at TIMESTAMP WITH TIME ZONE,
    timezone VARCHAR(50) DEFAULT 'Asia/Shanghai',
    total_slots INTEGER DEFAULT 10,
    booked_slots INTEGER DEFAULT 0,
    appointment_type VARCHAR(20) DEFAULT 'normal',
    status INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(36),
    updated_by VARCHAR(36)
);

COMMENT ON TABLE schedules IS '排班表';
CREATE INDEX idx_schedules_doctor ON schedules(doctor_id);
CREATE INDEX idx_schedules_date ON schedules(schedule_date);
CREATE INDEX idx_schedules_store ON schedules(store_id);

-- 休息日表
CREATE TABLE rest_days (
    id VARCHAR(36) PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    store_id VARCHAR(36) NOT NULL REFERENCES stores(id),
    doctor_ids TEXT,
    reason VARCHAR(255),
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    status INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(36),
    updated_by VARCHAR(36)
);

COMMENT ON TABLE rest_days IS '休息日表';

-- 停诊记录表
CREATE TABLE schedule_suspensions (
    id VARCHAR(36) PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    store_id VARCHAR(36) NOT NULL REFERENCES stores(id),
    doctor_id VARCHAR(36) NOT NULL REFERENCES doctors(id),
    title VARCHAR(100) NOT NULL,
    suspension_date DATE NOT NULL,
    schedule_ids TEXT,
    time_slots TEXT,
    status INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(36),
    updated_by VARCHAR(36)
);

COMMENT ON TABLE schedule_suspensions IS '停诊记录表';

-- 排班生成日志表
CREATE TABLE schedule_generation_logs (
    id VARCHAR(36) PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    template_id VARCHAR(36) NOT NULL REFERENCES schedule_templates(id) ON DELETE CASCADE,
    operator_id VARCHAR(36) REFERENCES admins(id) ON DELETE SET NULL,
    operator_name VARCHAR(100),
    action_type VARCHAR(20) NOT NULL,
    start_date DATE,
    end_date DATE,
    affected_count INTEGER DEFAULT 0,
    remark TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE schedule_generation_logs IS '排班生成日志表';

-- 停诊/调班申请表
CREATE TABLE leave_requests (
    id VARCHAR(36) PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    doctor_id VARCHAR(36) NOT NULL,
    request_type VARCHAR(20) NOT NULL,
    schedule_id VARCHAR(36),
    stop_date DATE,
    stop_period VARCHAR(20),
    original_date DATE,
    original_period VARCHAR(20),
    target_date DATE,
    target_period VARCHAR(20),
    reason TEXT NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',
    reviewer_id VARCHAR(36),
    review_comment TEXT,
    reviewed_at TIMESTAMP,
    affected_appointments INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(36),
    updated_by VARCHAR(36)
);

COMMENT ON TABLE leave_requests IS '停诊/调班申请表';
CREATE INDEX idx_leave_requests_doctor ON leave_requests(doctor_id);

-- ============================================
-- 六、规则引擎
-- ============================================

-- 规则组表
CREATE TABLE rule_sets (
    id VARCHAR(36) PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    name VARCHAR(200) NOT NULL,
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    priority INTEGER NOT NULL DEFAULT 100,
    time_source VARCHAR(20) NOT NULL DEFAULT 'SERVER',
    timezone_source VARCHAR(20) NOT NULL DEFAULT 'HOSPITAL',
    compare_precision VARCHAR(20) NOT NULL DEFAULT 'SECOND',
    default_open_inclusive BOOLEAN NOT NULL DEFAULT TRUE,
    default_close_inclusive BOOLEAN NOT NULL DEFAULT FALSE,
    rounding_mode VARCHAR(30) NOT NULL DEFAULT 'NONE',
    clock_skew_tolerance_sec INTEGER NOT NULL DEFAULT 5,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(36),
    updated_by VARCHAR(36)
);

COMMENT ON TABLE rule_sets IS '规则组表';
CREATE INDEX idx_rule_sets_enabled_priority ON rule_sets(enabled, priority);

-- 规则组班次关联表
CREATE TABLE rule_set_shift_types (
    rule_set_id VARCHAR(36) REFERENCES rule_sets(id) ON DELETE CASCADE,
    shift_type_id VARCHAR(36) REFERENCES shift_types(id) ON DELETE CASCADE,
    PRIMARY KEY (rule_set_id, shift_type_id)
);

CREATE INDEX idx_rsst_shift_type ON rule_set_shift_types(shift_type_id);

-- 时间窗配置表
CREATE TABLE rule_windows (
    id VARCHAR(36) PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    rule_set_id VARCHAR(36) NOT NULL REFERENCES rule_sets(id) ON DELETE CASCADE,
    action VARCHAR(30) NOT NULL,
    reference_point VARCHAR(50) NOT NULL,
    open_offset_sec INTEGER,
    close_offset_sec INTEGER,
    open_inclusive BOOLEAN,
    close_inclusive BOOLEAN,
    fail_policy VARCHAR(30) NOT NULL DEFAULT 'REJECT',
    fail_tag VARCHAR(100),
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(36),
    updated_by VARCHAR(36)
);

CREATE INDEX idx_rule_windows_rs ON rule_windows(rule_set_id, enabled);

-- 预约策略表
CREATE TABLE rule_booking_policies (
    rule_set_id VARCHAR(36) PRIMARY KEY REFERENCES rule_sets(id) ON DELETE CASCADE,
    require_auth BOOLEAN NOT NULL DEFAULT TRUE,
    require_patient_profile_complete BOOLEAN NOT NULL DEFAULT FALSE,
    per_user_per_shift INTEGER NOT NULL DEFAULT 1,
    per_user_per_day INTEGER,
    per_user_per_week INTEGER,
    conflict_same_shift VARCHAR(20) NOT NULL DEFAULT 'REJECT',
    conflict_overlap_time VARCHAR(20) NOT NULL DEFAULT 'REJECT',
    conflict_same_type_same_day VARCHAR(20) NOT NULL DEFAULT 'ALLOW',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(36),
    updated_by VARCHAR(36)
);

-- 签到策略表
CREATE TABLE rule_checkin_policies (
    rule_set_id VARCHAR(36) PRIMARY KEY REFERENCES rule_sets(id) ON DELETE CASCADE,
    require_booking BOOLEAN NOT NULL DEFAULT TRUE,
    allow_onsite_booking BOOLEAN NOT NULL DEFAULT FALSE,
    max_times INTEGER NOT NULL DEFAULT 1,
    audit_log BOOLEAN NOT NULL DEFAULT TRUE,
    grace_period_sec INTEGER NOT NULL DEFAULT 0,
    after_grace_status VARCHAR(30),
    no_checkin_after_close VARCHAR(30) NOT NULL DEFAULT 'KEEP_BOOKED',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(36),
    updated_by VARCHAR(36)
);

-- 容量策略表
CREATE TABLE rule_capacity_policies (
    rule_set_id VARCHAR(36) PRIMARY KEY REFERENCES rule_sets(id) ON DELETE CASCADE,
    total_capacity INTEGER NOT NULL DEFAULT 0,
    per_user_capacity INTEGER NOT NULL DEFAULT 1,
    waitlist_enabled BOOLEAN NOT NULL DEFAULT FALSE,
    waitlist_max_size INTEGER NOT NULL DEFAULT 0,
    waitlist_promote_policy VARCHAR(50) NOT NULL DEFAULT 'MANUAL',
    overbooking_enabled BOOLEAN NOT NULL DEFAULT FALSE,
    overbooking_max INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(36),
    updated_by VARCHAR(36)
);

-- ============================================
-- 七、预约管理
-- ============================================

-- 预约表
CREATE TABLE appointments (
    id VARCHAR(36) PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    appointment_no VARCHAR(50) UNIQUE NOT NULL,
    user_id VARCHAR(36) NOT NULL REFERENCES users(id),
    patient_id VARCHAR(36) NOT NULL REFERENCES patients(id),
    doctor_id VARCHAR(36) NOT NULL REFERENCES doctors(id),
    schedule_id VARCHAR(36) NOT NULL REFERENCES schedules(id),
    rule_set_id VARCHAR(36) REFERENCES rule_sets(id),
    queue_number INTEGER,
    status INTEGER DEFAULT 1,
    sign_in_time TIMESTAMP,
    call_time TIMESTAMP,
    complete_time TIMESTAMP,
    cancel_time TIMESTAMP,
    cancel_reason TEXT,
    remark TEXT,
    symptom_description TEXT,
    book_open_at TIMESTAMP WITH TIME ZONE,
    book_close_at TIMESTAMP WITH TIME ZONE,
    checkin_open_at TIMESTAMP WITH TIME ZONE,
    checkin_close_at TIMESTAMP WITH TIME ZONE,
    cancel_open_at TIMESTAMP WITH TIME ZONE,
    cancel_close_at TIMESTAMP WITH TIME ZONE,
    checkin_count INTEGER DEFAULT 0,
    patient_name VARCHAR(50),
    patient_phone VARCHAR(20),
    doctor_name VARCHAR(50),
    doctor_title VARCHAR(50),
    department_name VARCHAR(100),
    reminder_sent INTEGER DEFAULT 0,
    reminder_sent_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(36),
    updated_by VARCHAR(36)
);

COMMENT ON TABLE appointments IS '预约表';
CREATE INDEX idx_appointments_user ON appointments(user_id);
CREATE INDEX idx_appointments_patient ON appointments(patient_id);
CREATE INDEX idx_appointments_doctor ON appointments(doctor_id);
CREATE INDEX idx_appointments_schedule ON appointments(schedule_id);
CREATE INDEX idx_appointments_status ON appointments(status);

-- 签到日志表
CREATE TABLE appointment_checkins (
    id VARCHAR(36) PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    appointment_id VARCHAR(36) NOT NULL REFERENCES appointments(id) ON DELETE CASCADE,
    checkin_time TIMESTAMP WITH TIME ZONE NOT NULL,
    checkin_method VARCHAR(30) NOT NULL,
    device_info VARCHAR(200),
    location_info VARCHAR(200),
    operator_id VARCHAR(36),
    operator_type VARCHAR(20),
    status VARCHAR(20) NOT NULL DEFAULT 'SUCCESS',
    fail_reason VARCHAR(200),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_app_checkins_appointment ON appointment_checkins(appointment_id);
CREATE INDEX idx_app_checkins_time ON appointment_checkins(checkin_time);

-- 候补队列表
CREATE TABLE waitlist_entries (
    id VARCHAR(36) PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    user_id VARCHAR(36) NOT NULL,
    patient_id VARCHAR(36) NOT NULL,
    schedule_id VARCHAR(36) NOT NULL REFERENCES schedules(id),
    shift_type_id VARCHAR(36),
    status VARCHAR(20) NOT NULL DEFAULT 'WAITING',
    position INTEGER NOT NULL,
    priority INTEGER NOT NULL DEFAULT 100,
    symptom_description VARCHAR(500),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    promoted_at TIMESTAMP,
    cancelled_at TIMESTAMP,
    operator_id VARCHAR(36),
    operator_type VARCHAR(20)
);

CREATE INDEX ix_waitlist_schedule_status ON waitlist_entries(schedule_id, status);
CREATE INDEX ix_waitlist_created_at ON waitlist_entries(created_at);
CREATE INDEX ix_waitlist_position ON waitlist_entries(schedule_id, position);

-- ============================================
-- 八、诊费管理
-- ============================================

-- 诊费类型表
CREATE TABLE consultation_fee_types (
    id VARCHAR(36) PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    store_id VARCHAR(36) REFERENCES stores(id) ON DELETE CASCADE,
    name VARCHAR(50) NOT NULL,
    code VARCHAR(50),
    description VARCHAR(255),
    sort_order INTEGER DEFAULT 0,
    status INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(36),
    updated_by VARCHAR(36),
    UNIQUE(store_id, code)
);

-- 诊费模板表（全局）
CREATE TABLE consultation_fee_templates (
    id VARCHAR(36) PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    fee_type_id VARCHAR(36) NOT NULL UNIQUE REFERENCES consultation_fee_types(id),
    initial_fee NUMERIC(10,2) DEFAULT 0,
    follow_up_fee NUMERIC(10,2) DEFAULT 0,
    status INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(36),
    updated_by VARCHAR(36)
);

-- 门店诊费模板表
CREATE TABLE store_fee_templates (
    id VARCHAR(36) PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    store_id VARCHAR(36) NOT NULL REFERENCES stores(id) ON DELETE CASCADE,
    fee_type_id VARCHAR(36) NOT NULL REFERENCES consultation_fee_types(id) ON DELETE CASCADE,
    initial_fee NUMERIC(10,2) DEFAULT 0,
    follow_up_fee NUMERIC(10,2) DEFAULT 0,
    status INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(36),
    updated_by VARCHAR(36),
    UNIQUE(store_id, fee_type_id)
);

-- 医生诊费配置表
CREATE TABLE doctor_consultation_fees (
    id VARCHAR(36) PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    doctor_id VARCHAR(36) NOT NULL REFERENCES doctors(id),
    store_id VARCHAR(36) NOT NULL REFERENCES stores(id),
    department_id VARCHAR(36) NOT NULL REFERENCES departments(id),
    fee_type_id VARCHAR(36) NOT NULL REFERENCES consultation_fee_types(id),
    initial_fee NUMERIC(10,2) DEFAULT 0,
    follow_up_fee NUMERIC(10,2) DEFAULT 0,
    status INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(36),
    updated_by VARCHAR(36)
);

-- ============================================
-- 九、病历管理
-- ============================================

CREATE TABLE medical_records (
    id VARCHAR(36) PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    record_no VARCHAR(50) UNIQUE NOT NULL,
    appointment_id VARCHAR(36) NOT NULL REFERENCES appointments(id),
    patient_id VARCHAR(36) NOT NULL REFERENCES patients(id),
    doctor_id VARCHAR(36) NOT NULL REFERENCES doctors(id),
    department_id VARCHAR(36) NOT NULL REFERENCES departments(id),
    chief_complaint TEXT,
    present_illness TEXT,
    past_history TEXT,
    allergy_history TEXT,
    physical_exam TEXT,
    auxiliary_exam TEXT,
    diagnosis TEXT NOT NULL,
    treatment TEXT,
    prescription TEXT,
    advice TEXT,
    total_fee NUMERIC(10,2) DEFAULT 0,
    status INTEGER DEFAULT 2,
    visit_date TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(36),
    updated_by VARCHAR(36)
);

COMMENT ON TABLE medical_records IS '病历表';
CREATE INDEX idx_medical_records_appointment ON medical_records(appointment_id);
CREATE INDEX idx_medical_records_patient ON medical_records(patient_id);

-- ============================================
-- 十、内容管理
-- ============================================

CREATE TABLE news (
    id VARCHAR(36) PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    store_id VARCHAR(36) REFERENCES stores(id),
    title VARCHAR(200) NOT NULL,
    type INTEGER DEFAULT 1,
    cover_image VARCHAR(500),
    summary VARCHAR(500),
    content TEXT,
    view_count INTEGER DEFAULT 0,
    is_top INTEGER DEFAULT 0,
    status INTEGER DEFAULT 0,
    publish_time TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(36),
    updated_by VARCHAR(36)
);

CREATE TABLE notices (
    id VARCHAR(36) PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    store_id VARCHAR(36) REFERENCES stores(id),
    title VARCHAR(200) NOT NULL,
    type INTEGER DEFAULT 1,
    content TEXT,
    is_top INTEGER DEFAULT 0,
    status INTEGER DEFAULT 0,
    publish_time TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(36),
    updated_by VARCHAR(36)
);

CREATE TABLE banners (
    id VARCHAR(36) PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    store_id VARCHAR(36) REFERENCES stores(id),
    title VARCHAR(100),
    image_url VARCHAR(500) NOT NULL,
    link_type INTEGER DEFAULT 0,
    link_url VARCHAR(500),
    position VARCHAR(50) DEFAULT 'home',
    sort_order INTEGER DEFAULT 0,
    status INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(36),
    updated_by VARCHAR(36)
);

CREATE TABLE booking_notices (
    id VARCHAR(36) PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    type VARCHAR(50) NOT NULL,
    title VARCHAR(100),
    content TEXT,
    sort_order INTEGER DEFAULT 0,
    status INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(36),
    updated_by VARCHAR(36)
);

-- ============================================
-- 十一、消息通知
-- ============================================

CREATE TABLE messages (
    id VARCHAR(36) PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    store_id VARCHAR(36) REFERENCES stores(id),
    user_id VARCHAR(36) NOT NULL,
    user_type VARCHAR(20) NOT NULL,
    title VARCHAR(200) NOT NULL,
    content TEXT,
    message_type VARCHAR(20) DEFAULT 'system',
    related_id VARCHAR(36),
    is_read INTEGER DEFAULT 0,
    read_at TIMESTAMP,
    extra_data TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(36),
    updated_by VARCHAR(36)
);

CREATE INDEX idx_messages_user ON messages(user_id);
CREATE INDEX idx_messages_store ON messages(store_id);

CREATE TABLE message_templates (
    id VARCHAR(36) PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    code VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    message_type VARCHAR(20) NOT NULL,
    title_template VARCHAR(200) NOT NULL,
    content_template TEXT NOT NULL,
    description VARCHAR(255),
    status INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(36),
    updated_by VARCHAR(36)
);

CREATE TABLE email_templates (
    id VARCHAR(36) PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    code VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    template_type VARCHAR(30) DEFAULT 'custom',
    subject_template VARCHAR(200) NOT NULL,
    content_template TEXT NOT NULL,
    description VARCHAR(255),
    status INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(36),
    updated_by VARCHAR(36)
);

-- ============================================
-- 十二、系统配置
-- ============================================

CREATE TABLE system_settings (
    id VARCHAR(36) PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    store_id VARCHAR(36) REFERENCES stores(id) ON DELETE CASCADE,
    category VARCHAR(50) NOT NULL,
    key VARCHAR(100) NOT NULL,
    value TEXT,
    description VARCHAR(200),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(36),
    updated_by VARCHAR(36)
);

CREATE INDEX ix_system_settings_store_category ON system_settings(store_id, category);
CREATE INDEX ix_system_settings_store_category_key ON system_settings(store_id, category, key);

CREATE TABLE store_visit_type_configs (
    id VARCHAR(36) PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    store_id VARCHAR(36) NOT NULL UNIQUE REFERENCES stores(id) ON DELETE CASCADE,
    time_limit INTEGER NOT NULL DEFAULT 30,
    time_unit VARCHAR(10) NOT NULL DEFAULT 'days',
    scope VARCHAR(20) NOT NULL DEFAULT 'same_doctor',
    status INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(36),
    updated_by VARCHAR(36)
);

-- ============================================
-- 十三、日志与审计
-- ============================================

CREATE TABLE user_behavior_logs (
    id VARCHAR(36) PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    platform VARCHAR(20) NOT NULL,
    user_id VARCHAR(36),
    session_id VARCHAR(64),
    event_type VARCHAR(30) NOT NULL,
    page_path VARCHAR(255),
    page_title VARCHAR(100),
    element_id VARCHAR(100),
    element_text VARCHAR(200),
    search_keyword VARCHAR(200),
    event_name VARCHAR(100),
    duration INTEGER,
    referrer VARCHAR(255),
    extra_data TEXT,
    ip VARCHAR(50),
    user_agent VARCHAR(500),
    device_type VARCHAR(20),
    browser VARCHAR(50),
    os VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE point_logs (
    id VARCHAR(36) PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    user_id VARCHAR(36) NOT NULL REFERENCES users(id),
    change_amount INTEGER NOT NULL,
    balance INTEGER NOT NULL,
    type INTEGER DEFAULT 4,
    remark VARCHAR(255),
    operator_id VARCHAR(36),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(36),
    updated_by VARCHAR(36)
);

CREATE INDEX idx_point_logs_user ON point_logs(user_id);

-- ============================================
-- 十四、用户服务
-- ============================================

CREATE TABLE blacklists (
    id VARCHAR(36) PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    user_id VARCHAR(36) REFERENCES users(id),
    store_id VARCHAR(36) REFERENCES stores(id),
    keyword VARCHAR(50),
    reason VARCHAR(500),
    no_show_count INTEGER DEFAULT 0,
    source INTEGER DEFAULT 1,
    expire_at TIMESTAMP,
    released_at TIMESTAMP,
    status INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(36),
    updated_by VARCHAR(36)
);

CREATE TABLE feedbacks (
    id VARCHAR(36) PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    user_id VARCHAR(36) NOT NULL,
    user_type VARCHAR(20) DEFAULT 'patient',
    feedback_type VARCHAR(20) DEFAULT 'suggestion',
    title VARCHAR(200) NOT NULL,
    content TEXT NOT NULL,
    images TEXT,
    contact VARCHAR(50),
    status VARCHAR(20) DEFAULT 'pending',
    handler_id VARCHAR(36),
    reply TEXT,
    handled_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(36),
    updated_by VARCHAR(36)
);

CREATE INDEX idx_feedbacks_user ON feedbacks(user_id);

CREATE TABLE user_favorites (
    id VARCHAR(36) PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    user_id VARCHAR(36) NOT NULL REFERENCES users(id),
    target_type VARCHAR(20) NOT NULL,
    target_id VARCHAR(36) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(36),
    updated_by VARCHAR(36),
    UNIQUE(user_id, target_type, target_id)
);
