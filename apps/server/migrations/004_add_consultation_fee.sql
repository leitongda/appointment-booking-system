-- 诊费类型表
CREATE TABLE consultation_fee_types (
    id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(50) NOT NULL COMMENT '诊费类型名称',
    code VARCHAR(50) UNIQUE COMMENT '类型编码',
    description VARCHAR(255) COMMENT '描述',
    sort_order INT DEFAULT 0 COMMENT '排序',
    status INT DEFAULT 1 COMMENT '状态: 0禁用 1启用',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- 诊费模板表（全局默认诊费配置）
CREATE TABLE consultation_fee_templates (
    id VARCHAR(36) PRIMARY KEY,
    fee_type_id VARCHAR(36) NOT NULL COMMENT '诊费类型ID',
    initial_fee DECIMAL(10, 2) DEFAULT 0 COMMENT '初诊金额',
    follow_up_fee DECIMAL(10, 2) DEFAULT 0 COMMENT '复诊金额',
    status INT DEFAULT 1 COMMENT '状态: 0禁用 1启用',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (fee_type_id) REFERENCES consultation_fee_types(id),
    UNIQUE KEY (fee_type_id)
);

-- 医生诊费配置表
CREATE TABLE doctor_consultation_fees (
    id VARCHAR(36) PRIMARY KEY,
    doctor_id VARCHAR(36) NOT NULL COMMENT '医生ID',
    store_id VARCHAR(36) NOT NULL COMMENT '门店ID',
    department_id VARCHAR(36) NOT NULL COMMENT '科室ID',
    fee_type_id VARCHAR(36) NOT NULL COMMENT '诊费类型ID',
    initial_fee DECIMAL(10, 2) DEFAULT 0 COMMENT '初诊金额',
    follow_up_fee DECIMAL(10, 2) DEFAULT 0 COMMENT '复诊金额',
    status INT DEFAULT 1 COMMENT '状态: 0禁用 1启用',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (doctor_id) REFERENCES doctors(id),
    FOREIGN KEY (store_id) REFERENCES stores(id),
    FOREIGN KEY (department_id) REFERENCES departments(id),
    FOREIGN KEY (fee_type_id) REFERENCES consultation_fee_types(id),
    UNIQUE KEY (doctor_id, store_id, department_id, fee_type_id)
);

CREATE INDEX ix_doctor_consultation_fees_doctor ON doctor_consultation_fees(doctor_id);
CREATE INDEX ix_doctor_consultation_fees_store ON doctor_consultation_fees(store_id);
CREATE INDEX ix_doctor_consultation_fees_department ON doctor_consultation_fees(department_id);

-- 医生表添加是否使用诊费模板字段
ALTER TABLE doctors ADD COLUMN use_fee_template INT DEFAULT 0 COMMENT '是否使用诊费模板 0否 1是';

-- 插入默认诊费类型
INSERT INTO consultation_fee_types (id, name, code, description, sort_order, status) VALUES
(UUID(), '专家', 'expert', '专家诊费', 1, 1),
(UUID(), '普通', 'normal', '普通诊费', 2, 1),
(UUID(), '加急', 'urgent', '加急诊费', 3, 1),
(UUID(), '医保', 'medical_insurance', '医保诊费', 4, 1),
(UUID(), '自费', 'self_pay', '自费诊费', 5, 1);
