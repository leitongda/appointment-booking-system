-- ============================================
-- 预约挂号系统 - 业务视图
-- 可直接在 PostgreSQL 中执行
-- 生成时间: 2026-02-06
-- ============================================

-- ============================================
-- 1. 医生完整信息视图
-- 用途: 查询医生时一次性获取科室和门店信息
-- ============================================
CREATE OR REPLACE VIEW v_doctor_full AS
SELECT
    d.id                    AS doctor_id,
    d.name                  AS doctor_name,
    d.username              AS doctor_username,
    d.phone                 AS doctor_phone,
    d.gender                AS doctor_gender,
    d.avatar                AS doctor_avatar,
    d.title                 AS doctor_title,
    d.years_of_experience,
    d.education,
    d.graduate_school,
    d.specialty,
    d.introduction,
    d.tags,
    d.is_recommended,
    d.sort_order            AS doctor_sort,
    d.status                AS doctor_status,
    d.max_daily_appointments,
    d.use_fee_template,
    d.last_login_at         AS doctor_last_login,
    -- 科室信息
    dep.id                  AS department_id,
    dep.name                AS department_name,
    dep.icon                AS department_icon,
    dep.is_hot              AS department_is_hot,
    -- 门店信息
    s.id                    AS store_id,
    s.name                  AS store_name,
    s.code                  AS store_code,
    s.address               AS store_address,
    s.phone                 AS store_phone,
    -- 时间戳
    d.created_at,
    d.updated_at
FROM doctors d
LEFT JOIN departments dep ON d.department_id = dep.id
LEFT JOIN stores s ON d.store_id = s.id;

COMMENT ON VIEW v_doctor_full IS '医生完整信息视图 - 含科室和门店信息';

-- ============================================
-- 2. 排班详情视图
-- 用途: 查看排班时获取完整的医生、科室、门店、班次信息
-- ============================================
CREATE OR REPLACE VIEW v_schedule_detail AS
SELECT
    sch.id                  AS schedule_id,
    sch.schedule_date,
    sch.time_slot,
    sch.start_time,
    sch.end_time,
    sch.start_at,
    sch.end_at,
    sch.timezone,
    sch.total_slots,
    sch.booked_slots,
    sch.total_slots - sch.booked_slots AS available_slots,
    sch.appointment_type,
    sch.status              AS schedule_status,
    -- 医生信息
    d.id                    AS doctor_id,
    d.name                  AS doctor_name,
    d.title                 AS doctor_title,
    d.avatar                AS doctor_avatar,
    -- 科室信息
    dep.id                  AS department_id,
    dep.name                AS department_name,
    -- 门店信息
    s.id                    AS store_id,
    s.name                  AS store_name,
    -- 模板信息
    st.id                   AS template_id,
    st.name                 AS template_name,
    -- 班次类型
    sht.id                  AS shift_type_id,
    sht.code                AS shift_type_code,
    sht.name                AS shift_type_name,
    -- 时间戳
    sch.created_at
FROM schedules sch
LEFT JOIN doctors d ON sch.doctor_id = d.id
LEFT JOIN departments dep ON d.department_id = dep.id
LEFT JOIN stores s ON sch.store_id = s.id
LEFT JOIN schedule_templates st ON sch.template_id = st.id
LEFT JOIN shift_types sht ON sch.shift_type_id = sht.id;

COMMENT ON VIEW v_schedule_detail IS '排班详情视图 - 含医生、科室、门店、模板、班次类型';

-- ============================================
-- 3. 预约详情视图
-- 用途: 预约列表和详情页的一站式查询
-- ============================================
CREATE OR REPLACE VIEW v_appointment_detail AS
SELECT
    a.id                    AS appointment_id,
    a.appointment_no,
    a.status                AS appointment_status,
    a.queue_number,
    a.sign_in_time,
    a.call_time,
    a.complete_time,
    a.cancel_time,
    a.cancel_reason,
    a.remark,
    a.symptom_description,
    a.reminder_sent,
    a.checkin_count,
    -- 快照字段
    a.patient_name          AS snapshot_patient_name,
    a.patient_phone         AS snapshot_patient_phone,
    a.doctor_name           AS snapshot_doctor_name,
    a.doctor_title          AS snapshot_doctor_title,
    a.department_name       AS snapshot_department_name,
    -- 规则时间窗快照
    a.book_open_at,
    a.book_close_at,
    a.checkin_open_at,
    a.checkin_close_at,
    a.cancel_open_at,
    a.cancel_close_at,
    -- 排班信息
    sch.schedule_date,
    sch.time_slot,
    sch.start_time          AS schedule_start_time,
    sch.end_time            AS schedule_end_time,
    sch.appointment_type,
    -- 医生实时信息
    d.id                    AS doctor_id,
    d.name                  AS doctor_name,
    d.title                 AS doctor_title,
    d.avatar                AS doctor_avatar,
    d.phone                 AS doctor_phone,
    -- 科室信息
    dep.id                  AS department_id,
    dep.name                AS department_name,
    -- 门店信息
    s.id                    AS store_id,
    s.name                  AS store_name,
    s.address               AS store_address,
    -- 就诊人信息
    p.id                    AS patient_id,
    p.name                  AS patient_name,
    p.phone                 AS patient_phone,
    p.id_card               AS patient_id_card,
    p.gender                AS patient_gender,
    p.card_no               AS patient_card_no,
    -- 用户信息
    u.id                    AS user_id,
    u.phone                 AS user_phone,
    u.nickname              AS user_nickname,
    -- 时间戳
    a.created_at,
    a.updated_at
FROM appointments a
LEFT JOIN schedules sch ON a.schedule_id = sch.id
LEFT JOIN doctors d ON a.doctor_id = d.id
LEFT JOIN departments dep ON d.department_id = dep.id
LEFT JOIN stores s ON sch.store_id = s.id
LEFT JOIN patients p ON a.patient_id = p.id
LEFT JOIN users u ON a.user_id = u.id;

COMMENT ON VIEW v_appointment_detail IS '预约详情视图 - 含排班、医生、科室、门店、就诊人、用户信息';

-- ============================================
-- 4. 医生排班概览视图
-- 用途: 按医生+日期聚合排班情况
-- ============================================
CREATE OR REPLACE VIEW v_doctor_schedule_overview AS
SELECT
    d.id                    AS doctor_id,
    d.name                  AS doctor_name,
    d.title                 AS doctor_title,
    dep.name                AS department_name,
    s.id                    AS store_id,
    s.name                  AS store_name,
    sch.schedule_date,
    COUNT(sch.id)           AS shift_count,
    SUM(sch.total_slots)    AS total_slots,
    SUM(sch.booked_slots)   AS booked_slots,
    SUM(sch.total_slots) - SUM(sch.booked_slots) AS available_slots,
    MIN(sch.start_time)     AS earliest_start,
    MAX(sch.end_time)       AS latest_end,
    -- 是否有停诊排班
    SUM(CASE WHEN sch.status = 0 THEN 1 ELSE 0 END) AS suspended_count
FROM schedules sch
JOIN doctors d ON sch.doctor_id = d.id
LEFT JOIN departments dep ON d.department_id = dep.id
LEFT JOIN stores s ON sch.store_id = s.id
WHERE sch.status IN (0, 1)
GROUP BY d.id, d.name, d.title, dep.name, s.id, s.name, sch.schedule_date;

COMMENT ON VIEW v_doctor_schedule_overview IS '医生排班概览视图 - 按医生和日期聚合';

-- ============================================
-- 5. 门店统计视图
-- 用途: 门店运营数据概览
-- ============================================
CREATE OR REPLACE VIEW v_store_statistics AS
SELECT
    s.id                    AS store_id,
    s.name                  AS store_name,
    s.code                  AS store_code,
    s.status                AS store_status,
    -- 科室数
    (SELECT COUNT(*) FROM departments dep WHERE dep.store_id = s.id AND dep.status = 1) AS active_department_count,
    -- 医生数
    (SELECT COUNT(*) FROM doctors doc WHERE doc.store_id = s.id AND doc.status = 1) AS active_doctor_count,
    -- 管理员数
    (SELECT COUNT(*) FROM admin_stores ast WHERE ast.store_id = s.id) AS admin_count,
    -- 今日排班数
    (SELECT COUNT(*) FROM schedules sch WHERE sch.store_id = s.id AND sch.schedule_date = CURRENT_DATE AND sch.status = 1) AS today_schedule_count,
    -- 今日预约数
    (SELECT COUNT(*) FROM appointments a
     JOIN schedules sch2 ON a.schedule_id = sch2.id
     WHERE sch2.store_id = s.id AND sch2.schedule_date = CURRENT_DATE AND a.status IN (1, 2, 3, 4, 5)) AS today_appointment_count,
    -- 本月预约总数
    (SELECT COUNT(*) FROM appointments a2
     JOIN schedules sch3 ON a2.schedule_id = sch3.id
     WHERE sch3.store_id = s.id
       AND sch3.schedule_date >= DATE_TRUNC('month', CURRENT_DATE)
       AND sch3.schedule_date < DATE_TRUNC('month', CURRENT_DATE) + INTERVAL '1 month'
       AND a2.status IN (1, 2, 3, 4, 5)) AS month_appointment_count
FROM stores s;

COMMENT ON VIEW v_store_statistics IS '门店统计视图 - 含科室数、医生数、预约数等运营数据';

-- ============================================
-- 6. 就诊人完整信息视图
-- 用途: 就诊人列表和详情查询
-- ============================================
CREATE OR REPLACE VIEW v_patient_full AS
SELECT
    p.id                    AS patient_id,
    p.name                  AS patient_name,
    p.phone                 AS patient_phone,
    p.id_card,
    p.gender,
    p.age,
    p.birthday,
    p.relationship,
    p.is_default,
    p.card_no,
    p.province,
    p.city,
    p.district,
    p.street,
    p.address,
    p.id_card_type,
    p.ethnicity,
    p.source,
    p.total_consumption,
    -- 用户信息
    u.id                    AS user_id,
    u.phone                 AS user_phone,
    u.nickname              AS user_nickname,
    u.openid                AS user_openid,
    -- 首次就诊门店
    s.id                    AS first_store_id,
    s.name                  AS first_store_name,
    -- 预约统计
    (SELECT COUNT(*) FROM appointments a WHERE a.patient_id = p.id) AS total_appointments,
    (SELECT COUNT(*) FROM appointments a WHERE a.patient_id = p.id AND a.status = 5) AS completed_appointments,
    (SELECT COUNT(*) FROM appointments a WHERE a.patient_id = p.id AND a.status = 6) AS cancelled_appointments,
    -- 时间戳
    p.created_at,
    p.updated_at
FROM patients p
LEFT JOIN users u ON p.user_id = u.id
LEFT JOIN stores s ON p.store_id = s.id;

COMMENT ON VIEW v_patient_full IS '就诊人完整信息视图 - 含用户信息、门店、预约统计';

-- ============================================
-- 7. 病历详情视图
-- 用途: 病历查询和展示
-- ============================================
CREATE OR REPLACE VIEW v_medical_record_detail AS
SELECT
    mr.id                   AS record_id,
    mr.record_no,
    mr.chief_complaint,
    mr.present_illness,
    mr.past_history,
    mr.allergy_history,
    mr.physical_exam,
    mr.auxiliary_exam,
    mr.diagnosis,
    mr.treatment,
    mr.prescription,
    mr.advice,
    mr.total_fee,
    mr.status               AS record_status,
    mr.visit_date,
    -- 预约信息
    a.id                    AS appointment_id,
    a.appointment_no,
    a.status                AS appointment_status,
    -- 就诊人信息
    p.id                    AS patient_id,
    p.name                  AS patient_name,
    p.phone                 AS patient_phone,
    p.gender                AS patient_gender,
    p.age                   AS patient_age,
    p.id_card               AS patient_id_card,
    -- 医生信息
    d.id                    AS doctor_id,
    d.name                  AS doctor_name,
    d.title                 AS doctor_title,
    -- 科室信息
    dep.id                  AS department_id,
    dep.name                AS department_name,
    -- 时间戳
    mr.created_at,
    mr.updated_at
FROM medical_records mr
LEFT JOIN appointments a ON mr.appointment_id = a.id
LEFT JOIN patients p ON mr.patient_id = p.id
LEFT JOIN doctors d ON mr.doctor_id = d.id
LEFT JOIN departments dep ON mr.department_id = dep.id;

COMMENT ON VIEW v_medical_record_detail IS '病历详情视图 - 含预约、就诊人、医生、科室信息';

-- ============================================
-- 8. 医生诊费配置视图（含多级继承）
-- 用途: 查询医生实际生效的诊费（医生级 > 门店级 > 全局级）
-- ============================================
CREATE OR REPLACE VIEW v_doctor_fee_config AS
SELECT
    d.id                    AS doctor_id,
    d.name                  AS doctor_name,
    d.title                 AS doctor_title,
    s.id                    AS store_id,
    s.name                  AS store_name,
    dep.id                  AS department_id,
    dep.name                AS department_name,
    cft.id                  AS fee_type_id,
    cft.name                AS fee_type_name,
    cft.code                AS fee_type_code,
    -- 各级诊费
    gft.initial_fee         AS global_initial_fee,
    gft.follow_up_fee       AS global_follow_up_fee,
    sft.initial_fee         AS store_initial_fee,
    sft.follow_up_fee       AS store_follow_up_fee,
    dcf.initial_fee         AS doctor_initial_fee,
    dcf.follow_up_fee       AS doctor_follow_up_fee,
    -- 实际生效诊费（医生级 > 门店级 > 全局级）
    COALESCE(dcf.initial_fee, sft.initial_fee, gft.initial_fee, 0) AS effective_initial_fee,
    COALESCE(dcf.follow_up_fee, sft.follow_up_fee, gft.follow_up_fee, 0) AS effective_follow_up_fee,
    -- 生效来源
    CASE
        WHEN dcf.initial_fee IS NOT NULL THEN 'doctor'
        WHEN sft.initial_fee IS NOT NULL THEN 'store'
        WHEN gft.initial_fee IS NOT NULL THEN 'global'
        ELSE 'none'
    END AS fee_source
FROM doctors d
CROSS JOIN consultation_fee_types cft
LEFT JOIN stores s ON d.store_id = s.id
LEFT JOIN departments dep ON d.department_id = dep.id
LEFT JOIN consultation_fee_templates gft ON gft.fee_type_id = cft.id AND gft.status = 1
LEFT JOIN store_fee_templates sft ON sft.fee_type_id = cft.id AND sft.store_id = d.store_id AND sft.status = 1
LEFT JOIN doctor_consultation_fees dcf ON dcf.fee_type_id = cft.id AND dcf.doctor_id = d.id AND dcf.store_id = d.store_id AND dcf.status = 1
WHERE d.status = 1 AND cft.status = 1;

COMMENT ON VIEW v_doctor_fee_config IS '医生诊费配置视图 - 含多级继承（医生级>门店级>全局级）';

-- ============================================
-- 9. 管理员完整信息视图
-- 用途: 管理员列表和详情查询
-- ============================================
CREATE OR REPLACE VIEW v_admin_full AS
SELECT
    adm.id                  AS admin_id,
    adm.username,
    adm.name                AS admin_name,
    adm.phone               AS admin_phone,
    adm.email               AS admin_email,
    adm.avatar              AS admin_avatar,
    adm.status              AS admin_status,
    adm.last_login_at,
    adm.last_login_ip,
    -- 角色信息
    r.id                    AS role_id,
    r.name                  AS role_name,
    r.code                  AS role_code,
    -- 当前门店
    cs.id                   AS current_store_id,
    cs.name                 AS current_store_name,
    -- 绑定门店数
    (SELECT COUNT(*) FROM admin_stores ast WHERE ast.admin_id = adm.id) AS bound_store_count,
    -- 绑定门店列表（逗号分隔）
    (SELECT STRING_AGG(st.name, ', ' ORDER BY st.name)
     FROM admin_stores ast2
     JOIN stores st ON ast2.store_id = st.id
     WHERE ast2.admin_id = adm.id) AS bound_store_names,
    -- 时间戳
    adm.created_at,
    adm.updated_at
FROM admins adm
LEFT JOIN roles r ON adm.role_id = r.id
LEFT JOIN stores cs ON adm.current_store_id = cs.id;

COMMENT ON VIEW v_admin_full IS '管理员完整信息视图 - 含角色、当前门店、绑定门店列表';
