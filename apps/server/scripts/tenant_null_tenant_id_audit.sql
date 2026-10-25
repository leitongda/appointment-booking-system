-- ============================================================================
-- 租户重构上线前只读核对（PostgreSQL / psql）
--
-- 用途：为决策点 D1/D9/D13/D15/D20 与迁移 M6 的孤儿清洗提供依据。
-- 用法：
--   psql "$DATABASE_URL" -v ON_ERROR_STOP=1 \
--        -f apps/server/scripts/tenant_null_tenant_id_audit.sql
--
-- 设计（R4-1）：
--   * 文件分两段：SECTION 1 = PRE-MIGRATION，SECTION 2 = POST-MIGRATION。
--   * SECTION 2 只补充 p3a1/p3a7 才新增的列（内容表、system_settings），
--     因此整文件在 pre 库与 post 库都能执行，且 post 库可得到全量结论：
--       pre  库：SECTION 1 正常输出，SECTION 2 自动 SKIP；
--       post 库：SECTION 1 + SECTION 2 = D9 全量表 / M6 全量 16 表。
--   * 所有表/列访问都先过 to_regclass() + information_schema.columns 守卫；
--     缺失的对象输出 `SKIP(missing)`，不会因一条 UNION 断掉整段。
--   * 全部为只读查询：不建表、不写入、不修改任何数据。
--   * `\set ON_ERROR_STOP on` 保证任一真实 ERROR 立即中止；
--     脚本能跑到最后即 ERROR 计数 = 0。
--
-- 判定：
--   D20 两表存在且行数=0 才允许 R3-3 的 drop 迁移；
--   D13 任一类重复 >0 都会让 p3a2 create_unique_constraint 失败；
--   D15 >0 表示支付回调会因租户不一致被拒收；
--   D9  内容表的 NULL 是平台级语义（D10），不参与业务回填；
--   M6  孤儿 >0 不得执行 VALIDATE，清洗配方见 scripts/m6_post_deploy_cleanse_and_validate.sql；
--   D1  改为日志观测门禁（R4-3），SQL 只提供样本规模，命中数以日志平台为准。
-- ============================================================================

\set ON_ERROR_STOP on
\pset pager off

\echo ''
\echo '############################################################################'
\echo '# SECTION 1/2: PRE-MIGRATION（alembic_version 在 p3a1 之前或之后均可执行）'
\echo '############################################################################'

-- ----------------------------------------------------------------------------
-- D20：死代码表行数 + 表存在性 + miniapp 归档实例口径（R4-5）
-- role_permissions 可能只由 scripts/init_db.py 的 create_all 建出，必须守卫。
-- ----------------------------------------------------------------------------
\echo ''
\echo '=== D20-1: data_scopes / role_permissions 行数（两表均存在且=0 才允许 drop）==='
SELECT CASE
         WHEN to_regclass('public.' || t) IS NULL
           THEN format('SELECT %L AS table_name, %L AS rows FROM (SELECT 1) AS x',
                       t, 'MISSING(表不存在，未执行 create_all)')
         ELSE format('SELECT %L AS table_name, count(*)::text AS rows FROM public.%I',
                     t, t)
       END
FROM (VALUES ('data_scopes'), ('role_permissions')) AS v(t)
ORDER BY t
\gexec

\echo ''
\echo '=== D20-2: miniapp_instances 按租户计数（status=2 为归档；产品需拍板配额是否计入）==='
SELECT format(
         'SELECT mi.tenant_id, tn.tenant_code, '
         'count(*) FILTER (WHERE mi.status = 2) AS archived_status2, '
         'count(*) AS total_instances '
         'FROM public.miniapp_instances mi '
         'LEFT JOIN public.tenants tn ON tn.id = mi.tenant_id '
         'GROUP BY mi.tenant_id, tn.tenant_code ORDER BY mi.tenant_id')
WHERE to_regclass('public.miniapp_instances') IS NOT NULL
\gexec
SELECT format('SELECT %L AS skipped_item, %L AS status', 'miniapp_instances', 'SKIP(missing)')
WHERE to_regclass('public.miniapp_instances') IS NULL
\gexec

-- ----------------------------------------------------------------------------
-- D13：跨租户 / 同租户 / 平台行 三类重复（R4-2）
-- 与 p3a2_admin_role_unique.py 的 (tenant_id, col) 唯一约束 +
-- tenant_id IS NULL 的 partial unique index 一一对应。
-- ----------------------------------------------------------------------------
\echo ''
\echo '=== D13: 管理员用户名 / 角色编码重复（scope=cross_tenant|same_tenant|platform，任一类>0 则 p3a2 会失败）==='
SELECT kind, scope, tenant_id, value, dup_count
FROM (
    -- 1) 跨租户重复：同一 username/code 出现在多个租户（p3a2 本身允许，但说明存在历史串号）
    SELECT 'admins.username'::text AS kind,
           'cross_tenant'::text   AS scope,
           NULL::varchar          AS tenant_id,
           username               AS value,
           count(DISTINCT tenant_id) AS dup_count
    FROM admins
    WHERE tenant_id IS NOT NULL
    GROUP BY username
    HAVING count(DISTINCT tenant_id) > 1

    UNION ALL
    SELECT 'roles.code'::text, 'cross_tenant'::text, NULL::varchar,
           code, count(DISTINCT tenant_id)
    FROM roles
    WHERE tenant_id IS NOT NULL
    GROUP BY code
    HAVING count(DISTINCT tenant_id) > 1

    -- 2) 同租户内重复：会直接让 uq_admins_tenant_username / uq_roles_tenant_code 创建失败
    UNION ALL
    SELECT 'admins.username'::text, 'same_tenant'::text, tenant_id,
           username, count(*)
    FROM admins
    WHERE tenant_id IS NOT NULL
    GROUP BY tenant_id, username
    HAVING count(*) > 1

    UNION ALL
    SELECT 'roles.code'::text, 'same_tenant'::text, tenant_id,
           code, count(*)
    FROM roles
    WHERE tenant_id IS NOT NULL
    GROUP BY tenant_id, code
    HAVING count(*) > 1

    -- 3) 平台行重复：tenant_id IS NULL 的 partial unique index 会失败
    UNION ALL
    SELECT 'admins.username'::text, 'platform'::text, NULL::varchar,
           username, count(*)
    FROM admins
    WHERE tenant_id IS NULL
    GROUP BY username
    HAVING count(*) > 1

    UNION ALL
    SELECT 'roles.code'::text, 'platform'::text, NULL::varchar,
           code, count(*)
    FROM roles
    WHERE tenant_id IS NULL
    GROUP BY code
    HAVING count(*) > 1
) d
ORDER BY scope, kind, value;

-- ----------------------------------------------------------------------------
-- D15：预约与其支付配置的租户不一致
-- ----------------------------------------------------------------------------
\echo ''
\echo '=== D15: 预约与支付配置租户不一致条数（>0 时回调会被拒收）==='
SELECT format(
         'SELECT count(*) AS inconsistent_appointments '
         'FROM public.appointments a '
         'JOIN public.payment_profiles p ON p.id = a.payment_profile_id '
         'WHERE a.tenant_id IS DISTINCT FROM p.tenant_id')
WHERE to_regclass('public.appointments') IS NOT NULL
  AND to_regclass('public.payment_profiles') IS NOT NULL
\gexec
SELECT format('SELECT %L AS skipped_item, %L AS status', 'appointments/payment_profiles', 'SKIP(missing)')
WHERE to_regclass('public.appointments') IS NULL
   OR to_regclass('public.payment_profiles') IS NULL
\gexec

-- ----------------------------------------------------------------------------
-- D9（业务表）：tenant_id 为 NULL 的存量行 + null_pct（R4-4）
-- 补 follow_up_plans / follow_up_records / follow_up_self_reports /
--    doctor_reviews / feedbacks 5 张表。
-- 每张表独立守卫：缺失输出 SKIP，不会拖垮整段。
-- ----------------------------------------------------------------------------
\echo ''
\echo '=== D9（业务表）: NULL tenant_id 行数 / total / null_pct（0 行表输出 0/0）==='
WITH candidates(t) AS (
    VALUES
      ('users'), ('patients'), ('doctors'), ('stores'), ('schedules'),
      ('appointments'), ('medical_records'), ('examination_reports'),
      ('follow_up_tasks'), ('follow_up_plans'), ('follow_up_records'),
      ('follow_up_self_reports'), ('doctor_reviews'), ('feedbacks'),
      ('waitlist_entries'), ('messages'),
      -- p3a8 新增（诊费/邮件接收人，2026-10-24；NULL=平台级语义，与内容表同口径看待）
      ('consultation_fee_types'), ('consultation_fee_templates'),
      ('store_fee_templates'), ('doctor_consultation_fees'),
      ('store_email_recipients')
)
SELECT format(
         'SELECT %L AS table_name, '
         'count(*) FILTER (WHERE tenant_id IS NULL) AS null_tenant, '
         'count(*) AS total, '
         'round(100.0 * count(*) FILTER (WHERE tenant_id IS NULL) / NULLIF(count(*), 0), 2) AS null_pct '
         'FROM public.%I',
         v.t, v.t)
FROM candidates v
WHERE to_regclass('public.' || v.t) IS NOT NULL
  AND EXISTS (
      SELECT 1 FROM information_schema.columns c
      WHERE c.table_schema = 'public' AND c.table_name = v.t AND c.column_name = 'tenant_id'
  )
ORDER BY v.t
\gexec

\echo '--- D9（业务表）: 以下表/列不存在，已跳过 ---'
SELECT format('SELECT %L AS skipped_item, %L AS status', v.t || '.tenant_id', 'SKIP(missing)')
FROM (VALUES
      ('users'), ('patients'), ('doctors'), ('stores'), ('schedules'),
      ('appointments'), ('medical_records'), ('examination_reports'),
      ('follow_up_tasks'), ('follow_up_plans'), ('follow_up_records'),
      ('follow_up_self_reports'), ('doctor_reviews'), ('feedbacks'),
      ('waitlist_entries'), ('messages')
) AS v(t)
WHERE NOT (
    to_regclass('public.' || v.t) IS NOT NULL
    AND EXISTS (
        SELECT 1 FROM information_schema.columns c
        WHERE c.table_schema = 'public' AND c.table_name = v.t AND c.column_name = 'tenant_id'
    )
)
ORDER BY v.t
\gexec

-- ----------------------------------------------------------------------------
-- D1：遗留管理员日志观测门禁（R4-3）
-- 只数行数无法识别“仅存 users 表的旧管理员”，改为以日志关键字为门禁。
-- ----------------------------------------------------------------------------
\echo ''
\echo '=== D1: 遗留 User 管理员 fallback 日志观测门禁（R4-3）==='
SELECT 'D1'::text AS gate,
       'legacy User admin fallback hit'::text AS log_keyword,
       'app/common/auth_unified.py:411'::text AS source,
       '连续 2 个发布周期命中=0 才允许 LEGACY_USER_ADMIN_FALLBACK=False'::text AS pass_condition,
       '按发布周期统计日志平台关键字命中数；任一周期>0 即不通过'::text AS how_to_check;

\echo '--- D1: 样本规模（仅用于判断观测面大小，不作为门禁依据）---'
SELECT format(
         'SELECT %L AS item, count(*)::text AS rows FROM public.%I', 'users', 'users')
WHERE to_regclass('public.users') IS NOT NULL
\gexec
SELECT format(
         'SELECT %L AS item, count(*)::text AS rows FROM public.%I', 'admins', 'admins')
WHERE to_regclass('public.admins') IS NOT NULL
\gexec
SELECT format('SELECT %L AS skipped_item, %L AS status', 'users/admins', 'SKIP(missing)')
WHERE to_regclass('public.users') IS NULL OR to_regclass('public.admins') IS NULL
\gexec

-- ----------------------------------------------------------------------------
-- M6（PRE 段）：tenant_id 在 p3a1 之前已存在的 12 张表
-- 4 张内容表（news/notices/banners/content_versions）的 tenant_id 由 p3a1 新增，
-- 其外键孤儿在 SECTION 2 复核。
-- ----------------------------------------------------------------------------
\echo ''
\echo '=== M6（PRE 段）: 12 张既有表的外键孤儿（>0 不得 VALIDATE）==='
WITH candidates(t) AS (
    VALUES
      ('email_templates'), ('message_templates'), ('notification_logs'),
      ('notification_preferences'), ('rule_set_audit_logs'), ('schedule_audit_logs'),
      ('unified_templates'), ('notification_groups'), ('notification_recipients'),
      ('notification_deliveries'), ('channel_strategies'), ('recipient_rules')
)
SELECT format(
         'SELECT %L AS table_name, count(*) AS orphans '
         'FROM public.%I e '
         'WHERE e.tenant_id IS NOT NULL '
         'AND NOT EXISTS (SELECT 1 FROM public.tenants t WHERE t.id = e.tenant_id)',
         v.t, v.t)
FROM candidates v
WHERE to_regclass('public.' || v.t) IS NOT NULL
  AND EXISTS (
      SELECT 1 FROM information_schema.columns c
      WHERE c.table_schema = 'public' AND c.table_name = v.t AND c.column_name = 'tenant_id'
  )
ORDER BY v.t
\gexec

\echo '--- M6（PRE 段）: 以下表/列不存在，已跳过 ---'
SELECT format('SELECT %L AS skipped_item, %L AS status', v.t || '.tenant_id', 'SKIP(missing)')
FROM (VALUES
      ('email_templates'), ('message_templates'), ('notification_logs'),
      ('notification_preferences'), ('rule_set_audit_logs'), ('schedule_audit_logs'),
      ('unified_templates'), ('notification_groups'), ('notification_recipients'),
      ('notification_deliveries'), ('channel_strategies'), ('recipient_rules')
) AS v(t)
WHERE NOT (
    to_regclass('public.' || v.t) IS NOT NULL
    AND EXISTS (
        SELECT 1 FROM information_schema.columns c
        WHERE c.table_schema = 'public' AND c.table_name = v.t AND c.column_name = 'tenant_id'
    )
)
ORDER BY v.t
\gexec


\echo ''
\echo '############################################################################'
\echo '# SECTION 2/2: POST-MIGRATION（补充 p3a1/p3a7 新增列的段落）'
\echo '#   在 pre 库执行时本段全部输出 SKIP(missing)，属预期。'
\echo '############################################################################'

-- ----------------------------------------------------------------------------
-- D9（内容表）：NULL 是平台级语义（D10），单列成段，不参与业务回填。
-- ----------------------------------------------------------------------------
\echo ''
\echo '=== D9（内容/平台配置表）: NULL tenant_id 行数 / total / null_pct（NULL=平台级，不参与业务回填）==='
WITH candidates(t) AS (
    VALUES ('news'), ('notices'), ('banners'), ('content_versions'), ('system_settings')
)
SELECT format(
         'SELECT %L AS table_name, '
         'count(*) FILTER (WHERE tenant_id IS NULL) AS null_tenant, '
         'count(*) AS total, '
         'round(100.0 * count(*) FILTER (WHERE tenant_id IS NULL) / NULLIF(count(*), 0), 2) AS null_pct '
         'FROM public.%I',
         v.t, v.t)
FROM candidates v
WHERE to_regclass('public.' || v.t) IS NOT NULL
  AND EXISTS (
      SELECT 1 FROM information_schema.columns c
      WHERE c.table_schema = 'public' AND c.table_name = v.t AND c.column_name = 'tenant_id'
  )
ORDER BY v.t
\gexec

\echo '--- D9（内容/平台配置表）: 以下表/列不存在，已跳过 ---'
SELECT format('SELECT %L AS skipped_item, %L AS status', v.t || '.tenant_id', 'SKIP(missing)')
FROM (VALUES ('news'), ('notices'), ('banners'), ('content_versions'), ('system_settings')) AS v(t)
WHERE NOT (
    to_regclass('public.' || v.t) IS NOT NULL
    AND EXISTS (
        SELECT 1 FROM information_schema.columns c
        WHERE c.table_schema = 'public' AND c.table_name = v.t AND c.column_name = 'tenant_id'
    )
)
ORDER BY v.t
\gexec

-- ----------------------------------------------------------------------------
-- M6（POST 段）：p3a1 新增 tenant_id 的 4 张内容表
-- 与 SECTION 1 的 12 张合起来即全量 16 张。
-- ----------------------------------------------------------------------------
\echo ''
\echo '=== M6（POST 段）: 4 张内容表的外键孤儿（与 PRE 段合计 16 表）==='
WITH candidates(t) AS (
    VALUES ('news'), ('notices'), ('banners'), ('content_versions')
)
SELECT format(
         'SELECT %L AS table_name, count(*) AS orphans '
         'FROM public.%I e '
         'WHERE e.tenant_id IS NOT NULL '
         'AND NOT EXISTS (SELECT 1 FROM public.tenants t WHERE t.id = e.tenant_id)',
         v.t, v.t)
FROM candidates v
WHERE to_regclass('public.' || v.t) IS NOT NULL
  AND EXISTS (
      SELECT 1 FROM information_schema.columns c
      WHERE c.table_schema = 'public' AND c.table_name = v.t AND c.column_name = 'tenant_id'
  )
ORDER BY v.t
\gexec

\echo '--- M6（POST 段）: 以下表/列不存在，已跳过 ---'
SELECT format('SELECT %L AS skipped_item, %L AS status', v.t || '.tenant_id', 'SKIP(missing)')
FROM (VALUES ('news'), ('notices'), ('banners'), ('content_versions')) AS v(t)
WHERE NOT (
    to_regclass('public.' || v.t) IS NOT NULL
    AND EXISTS (
        SELECT 1 FROM information_schema.columns c
        WHERE c.table_schema = 'public' AND c.table_name = v.t AND c.column_name = 'tenant_id'
    )
)
ORDER BY v.t
\gexec

-- ----------------------------------------------------------------------------
-- M6 约束状态：NOT VALID 属预期，VALIDATE 完成后应全为 true
-- ----------------------------------------------------------------------------
\echo ''
\echo '=== M6: fk_*_tenant 约束的 convalidated 状态（上线后应为 true）==='
SELECT conname AS constraint_name,
       conrelid::regclass AS table_name,
       convalidated
FROM pg_constraint
WHERE conname LIKE 'fk\_%\_tenant' ESCAPE '\'
ORDER BY conrelid::regclass::text;

-- ----------------------------------------------------------------------------
-- purge 候选预览（本期只出清单，不删除；TENANT_PURGE_* 无消费方）
-- ----------------------------------------------------------------------------
\echo ''
\echo '=== purge 候选预览: 软删除超过 90 天的租户（只读清单，不执行删除）==='
SELECT tenant_code, name, deleted_at
FROM tenants
WHERE deleted_at IS NOT NULL
  AND deleted_at < (now() - interval '90 days')
ORDER BY deleted_at;

\echo ''
\echo '### 审计完成：脚本正常结束 = ERROR 计数 0 ###'
