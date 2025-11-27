-- ============================================
-- 医院挂号系统 - 数据库表结构
-- Database: PostgreSQL 16+
-- ============================================

-- 启用UUID扩展
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================
-- 一、用户与权限相关表
-- ============================================

-- 用户表
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    phone VARCHAR(20) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    name VARCHAR(50) NOT NULL,
    id_card VARCHAR(18),
    gender SMALLINT DEFAULT 0,
    birthday DATE,
    avatar VARCHAR(500),
    role VARCHAR(20) NOT NULL,
    status SMALLINT DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE users IS '用户表';
COMMENT ON COLUMN users.gender IS '性别: 0未知 1男 2女';
COMMENT ON COLUMN users.role IS '角色: ADMIN/DOCTOR/PATIENT';
COMMENT ON COLUMN users.status IS '状态: 0禁用 1正常';

CREATE INDEX idx_users_role ON users(role);
CREATE INDEX idx_users_status ON users(status);

-- 角色表
CREATE TABLE roles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(50) NOT NULL,
    code VARCHAR(50) UNIQUE NOT NULL,
    description VARCHAR(200),
    status SMALLINT DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE roles IS '角色表';

-- 菜单表
CREATE TABLE menus (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    parent_id UUID REFERENCES menus(id),
    name VARCHAR(50) NOT NULL,
    path VARCHAR(200),
    component VARCHAR(200),
    icon VARCHAR(50),
    permission VARCHAR(100),
    type SMALLINT DEFAULT 1,
    sort_order INT DEFAULT 0,
    status SMALLINT DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE menus IS '菜单表';
COMMENT ON COLUMN menus.type IS '类型: 1目录 2菜单 3按钮';

-- 角色菜单关联表
CREATE TABLE role_menus (
    role_id UUID REFERENCES roles(id) ON DELETE CASCADE,
    menu_id UUID REFERENCES menus(id) ON DELETE CASCADE,
    PRIMARY KEY (role_id, menu_id)
);

-- 管理员表
CREATE TABLE admins (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id),
    department_id UUID,
    status SMALLINT DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 管理员角色关联表
CREATE TABLE admin_roles (
    admin_id UUID REFERENCES admins(id) ON DELETE CASCADE,
    role_id UUID REFERENCES roles(id) ON DELETE CASCADE,
    PRIMARY KEY (admin_id, role_id)
);

-- 操作日志表
CREATE TABLE operation_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    admin_id UUID REFERENCES admins(id),
    module VARCHAR(50),
    action VARCHAR(50),
    content TEXT,
    ip VARCHAR(50),
    user_agent VARCHAR(500),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE operation_logs IS '操作日志表';
CREATE INDEX idx_operation_logs_admin ON operation_logs(admin_id);
CREATE INDEX idx_operation_logs_created ON operation_logs(created_at);

-- ============================================
-- 二、机构相关表
-- ============================================

-- 医院表
CREATE TABLE hospitals (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) NOT NULL,
    code VARCHAR(50) UNIQUE NOT NULL,
    level VARCHAR(20),
    address VARCHAR(500),
    phone VARCHAR(20),
    logo VARCHAR(500),
    description TEXT,
    status SMALLINT DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE hospitals IS '医院表';
COMMENT ON COLUMN hospitals.level IS '医院等级: 三甲/三乙/二甲等';

-- 门店/分院表
CREATE TABLE branches (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    hospital_id UUID REFERENCES hospitals(id),
    name VARCHAR(100) NOT NULL,
    code VARCHAR(50),
    address VARCHAR(500),
    phone VARCHAR(20),
    latitude DECIMAL(10, 7),
    longitude DECIMAL(10, 7),
    open_time TIME,
    close_time TIME,
    status SMALLINT DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE branches IS '门店/分院表';
CREATE INDEX idx_branches_hospital ON branches(hospital_id);

-- 科室表
CREATE TABLE departments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    hospital_id UUID REFERENCES hospitals(id),
    branch_id UUID REFERENCES branches(id),
    parent_id UUID REFERENCES departments(id),
    name VARCHAR(100) NOT NULL,
    code VARCHAR(50),
    icon VARCHAR(500),
    description TEXT,
    sort_order INT DEFAULT 0,
    is_hot BOOLEAN DEFAULT FALSE,
    status SMALLINT DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE departments IS '科室表';
CREATE INDEX idx_departments_hospital ON departments(hospital_id);
CREATE INDEX idx_departments_branch ON departments(branch_id);
CREATE INDEX idx_departments_parent ON departments(parent_id);

-- ============================================
-- 三、医生相关表
-- ============================================

-- 医生表
CREATE TABLE doctors (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id),
    hospital_id UUID REFERENCES hospitals(id),
    branch_id UUID REFERENCES branches(id),
    department_id UUID REFERENCES departments(id),
    employee_no VARCHAR(50),
    title VARCHAR(50),
    specialty VARCHAR(500),
    introduction TEXT,
    avatar VARCHAR(500),
    consultation_fee DECIMAL(10, 2) DEFAULT 0,
    is_expert BOOLEAN DEFAULT FALSE,
    is_recommended BOOLEAN DEFAULT FALSE,
    sort_order INT DEFAULT 0,
    status SMALLINT DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE doctors IS '医生表';
COMMENT ON COLUMN doctors.title IS '职称: 主任医师/副主任医师/主治医师等';

CREATE INDEX idx_doctors_user ON doctors(user_id);
CREATE INDEX idx_doctors_hospital ON doctors(hospital_id);
CREATE INDEX idx_doctors_branch ON doctors(branch_id);
CREATE INDEX idx_doctors_department ON doctors(department_id);

-- ============================================
-- 四、患者相关表
-- ============================================

-- 就诊人表
CREATE TABLE patients (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id),
    name VARCHAR(50) NOT NULL,
    phone VARCHAR(20) NOT NULL,
    id_card VARCHAR(18),
    gender SMALLINT DEFAULT 0,
    birthday DATE,
    relationship VARCHAR(20),
    is_default BOOLEAN DEFAULT FALSE,
    status SMALLINT DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE patients IS '就诊人表';
COMMENT ON COLUMN patients.relationship IS '与用户关系: 本人/父母/子女/配偶/其他';

CREATE INDEX idx_patients_user ON patients(user_id);

-- 黑名单表
CREATE TABLE blacklists (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id),
    reason VARCHAR(500),
    no_show_count INT DEFAULT 0,
    expire_at TIMESTAMP,
    status SMALLINT DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE blacklists IS '黑名单表';
CREATE INDEX idx_blacklists_user ON blacklists(user_id);

-- ============================================
-- 五、排班相关表
-- ============================================

-- 排班模板表
CREATE TABLE schedule_templates (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    doctor_id UUID REFERENCES doctors(id),
    weekday SMALLINT NOT NULL,
    time_slot VARCHAR(20) NOT NULL,
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,
    total_slots INT NOT NULL,
    status SMALLINT DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(doctor_id, weekday, time_slot)
);

COMMENT ON TABLE schedule_templates IS '排班模板表';
COMMENT ON COLUMN schedule_templates.weekday IS '星期: 1-7';
COMMENT ON COLUMN schedule_templates.time_slot IS '时段: AM/PM/NIGHT';

-- 排班表
CREATE TABLE schedules (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    doctor_id UUID REFERENCES doctors(id),
    schedule_date DATE NOT NULL,
    time_slot VARCHAR(20) NOT NULL,
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,
    total_slots INT NOT NULL,
    booked_slots INT DEFAULT 0,
    status SMALLINT DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(doctor_id, schedule_date, time_slot)
);

COMMENT ON TABLE schedules IS '排班表';
COMMENT ON COLUMN schedules.status IS '状态: 0停诊 1正常 2已满';

CREATE INDEX idx_schedules_doctor ON schedules(doctor_id);
CREATE INDEX idx_schedules_date ON schedules(schedule_date);

-- 休息日表
CREATE TABLE holidays (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    hospital_id UUID REFERENCES hospitals(id),
    name VARCHAR(50) NOT NULL,
    holiday_date DATE NOT NULL,
    type SMALLINT DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE holidays IS '休息日/节假日表';
COMMENT ON COLUMN holidays.type IS '类型: 1节假日 2调休';

-- 停诊记录表
CREATE TABLE suspension_records (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    doctor_id UUID REFERENCES doctors(id),
    schedule_id UUID REFERENCES schedules(id),
    reason VARCHAR(500),
    status SMALLINT DEFAULT 0,
    approved_by UUID REFERENCES admins(id),
    approved_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE suspension_records IS '停诊记录表';
COMMENT ON COLUMN suspension_records.status IS '状态: 0待审核 1已通过 2已拒绝';

-- ============================================
-- 六、预约相关表
-- ============================================

-- 预约表
CREATE TABLE appointments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    appointment_no VARCHAR(50) UNIQUE NOT NULL,
    user_id UUID REFERENCES users(id),
    patient_id UUID REFERENCES patients(id),
    doctor_id UUID REFERENCES doctors(id),
    schedule_id UUID REFERENCES schedules(id),
    appointment_date DATE NOT NULL,
    time_slot VARCHAR(20) NOT NULL,
    queue_number INT,
    fee DECIMAL(10, 2),
    payment_status SMALLINT DEFAULT 0,
    payment_time TIMESTAMP,
    status SMALLINT DEFAULT 0,
    sign_in_time TIMESTAMP,
    call_time TIMESTAMP,
    complete_time TIMESTAMP,
    cancel_reason VARCHAR(500),
    source VARCHAR(20) DEFAULT 'MINI_PROGRAM',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE appointments IS '预约表';
COMMENT ON COLUMN appointments.status IS '状态: 0待支付 1已预约 2已签到 3候诊中 4就诊中 5已完成 6已取消 7已过期';
COMMENT ON COLUMN appointments.source IS '来源: MINI_PROGRAM/APP/WEB/SELF_SERVICE';

CREATE INDEX idx_appointments_user ON appointments(user_id);
CREATE INDEX idx_appointments_patient ON appointments(patient_id);
CREATE INDEX idx_appointments_doctor ON appointments(doctor_id);
CREATE INDEX idx_appointments_schedule ON appointments(schedule_id);
CREATE INDEX idx_appointments_date ON appointments(appointment_date);
CREATE INDEX idx_appointments_status ON appointments(status);

-- 病历表
CREATE TABLE medical_records (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    appointment_id UUID REFERENCES appointments(id),
    patient_id UUID REFERENCES patients(id),
    doctor_id UUID REFERENCES doctors(id),
    chief_complaint TEXT,
    present_illness TEXT,
    past_history TEXT,
    physical_exam TEXT,
    diagnosis TEXT,
    treatment TEXT,
    prescription JSONB,
    advice TEXT,
    visit_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE medical_records IS '病历表';
CREATE INDEX idx_medical_records_appointment ON medical_records(appointment_id);
CREATE INDEX idx_medical_records_patient ON medical_records(patient_id);
CREATE INDEX idx_medical_records_doctor ON medical_records(doctor_id);

-- ============================================
-- 七、内容管理相关表
-- ============================================

-- 新闻分类表
CREATE TABLE news_types (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(50) NOT NULL,
    sort_order INT DEFAULT 0,
    status SMALLINT DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 新闻表
CREATE TABLE news (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    type_id UUID REFERENCES news_types(id),
    title VARCHAR(200) NOT NULL,
    summary VARCHAR(500),
    content TEXT,
    cover_image VARCHAR(500),
    author VARCHAR(50),
    view_count INT DEFAULT 0,
    is_top BOOLEAN DEFAULT FALSE,
    status SMALLINT DEFAULT 1,
    publish_time TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE news IS '新闻资讯表';
CREATE INDEX idx_news_type ON news(type_id);

-- 轮播图表
CREATE TABLE banners (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title VARCHAR(100),
    image_url VARCHAR(500) NOT NULL,
    link_url VARCHAR(500),
    link_type SMALLINT DEFAULT 1,
    sort_order INT DEFAULT 0,
    status SMALLINT DEFAULT 1,
    start_time TIMESTAMP,
    end_time TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE banners IS '轮播图表';
COMMENT ON COLUMN banners.link_type IS '链接类型: 1内部页面 2外部链接 3无跳转';

-- 公告表
CREATE TABLE notices (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title VARCHAR(200) NOT NULL,
    content TEXT,
    type SMALLINT DEFAULT 1,
    is_top BOOLEAN DEFAULT FALSE,
    status SMALLINT DEFAULT 1,
    publish_time TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE notices IS '公告表';
COMMENT ON COLUMN notices.type IS '类型: 1系统公告 2停诊通知 3活动通知';

-- 弹框表
CREATE TABLE popups (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title VARCHAR(100),
    image_url VARCHAR(500) NOT NULL,
    link_url VARCHAR(500),
    position VARCHAR(20) DEFAULT 'HOME',
    frequency VARCHAR(20) DEFAULT 'ONCE',
    sort_order INT DEFAULT 0,
    status SMALLINT DEFAULT 1,
    start_time TIMESTAMP,
    end_time TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE popups IS '弹框表';
COMMENT ON COLUMN popups.position IS '显示位置: HOME/BOOKING/ALL';
COMMENT ON COLUMN popups.frequency IS '显示频率: ONCE/DAILY/ALWAYS';

-- ============================================
-- 八、系统设置相关表
-- ============================================

-- 系统设置表
CREATE TABLE settings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    key VARCHAR(100) UNIQUE NOT NULL,
    value TEXT,
    group_name VARCHAR(50),
    description VARCHAR(200),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE settings IS '系统设置表';

-- 首页菜单表
CREATE TABLE home_menus (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(50) NOT NULL,
    icon VARCHAR(500),
    link_url VARCHAR(500),
    link_type SMALLINT DEFAULT 1,
    sort_order INT DEFAULT 0,
    status SMALLINT DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE home_menus IS '首页菜单表';

-- 底部菜单表
CREATE TABLE tab_menus (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(50) NOT NULL,
    icon VARCHAR(500),
    active_icon VARCHAR(500),
    path VARCHAR(200),
    sort_order INT DEFAULT 0,
    status SMALLINT DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE tab_menus IS '底部Tab菜单表';

-- 预约须知表
CREATE TABLE booking_notices (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    type VARCHAR(50) NOT NULL,
    title VARCHAR(100),
    content TEXT,
    sort_order INT DEFAULT 0,
    status SMALLINT DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE booking_notices IS '预约须知表';
COMMENT ON COLUMN booking_notices.type IS '类型: BOOKING/VISIT/REFUND';

-- ============================================
-- 九、通知与反馈相关表
-- ============================================

-- 通知表
CREATE TABLE notifications (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id),
    title VARCHAR(200) NOT NULL,
    content TEXT,
    type VARCHAR(50),
    biz_id UUID,
    is_read BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE notifications IS '通知表';
COMMENT ON COLUMN notifications.type IS '类型: APPOINTMENT/SYSTEM/REMIND';

CREATE INDEX idx_notifications_user ON notifications(user_id);
CREATE INDEX idx_notifications_read ON notifications(is_read);

-- 用户反馈表
CREATE TABLE feedbacks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id),
    type VARCHAR(50),
    content TEXT NOT NULL,
    images VARCHAR(2000),
    contact VARCHAR(50),
    status SMALLINT DEFAULT 0,
    reply TEXT,
    reply_time TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE feedbacks IS '用户反馈表';
COMMENT ON COLUMN feedbacks.status IS '状态: 0待处理 1已处理 2已关闭';

CREATE INDEX idx_feedbacks_user ON feedbacks(user_id);
CREATE INDEX idx_feedbacks_status ON feedbacks(status);

-- ============================================
-- 十、初始化数据
-- ============================================

-- 初始化角色
INSERT INTO roles (id, name, code, description) VALUES
(uuid_generate_v4(), '超级管理员', 'SUPER_ADMIN', '系统最高权限'),
(uuid_generate_v4(), '运营管理员', 'OPERATOR', '日常运营管理'),
(uuid_generate_v4(), '排班管理员', 'SCHEDULER', '排班管理'),
(uuid_generate_v4(), '前台客服', 'RECEPTIONIST', '前台服务');

-- 初始化系统设置
INSERT INTO settings (key, value, group_name, description) VALUES
('booking_advance_days', '14', 'booking', '可提前预约天数'),
('booking_same_day', 'true', 'booking', '是否允许当天预约'),
('booking_cancel_hours', '2', 'booking', '就诊前N小时内不可取消'),
('booking_per_day_limit', '3', 'booking', '每人每天预约限制'),
('no_show_blacklist_count', '3', 'booking', '爽约N次进入黑名单'),
('wechat_app_id', '', 'wechat', '微信小程序AppID'),
('wechat_app_secret', '', 'wechat', '微信小程序Secret'),
('sms_sign_name', '医院名称', 'sms', '短信签名');

