-- ============================================================================
-- M6 上线后：外键孤儿清洗 + 约束 VALIDATE（PostgreSQL / psql）
--
-- 适用：p3a1–p3a8 已 upgrade；p3a6 为 16 张表、p3a8 为 5 张诊费/邮件表
--       创建 NOT VALID 外键 fk_<table>_tenant；生产/预发已 pg_dump 备份。
--
-- 用法（默认 dry-run，只读统计与孤儿清单，不写数据）：
--   psql "$DATABASE_URL" -v ON_ERROR_STOP=1 \
--        -f apps/server/scripts/m6_post_deploy_cleanse_and_validate.sql
--
-- 实际清洗 + VALIDATE（确认备份与孤儿清单后）：
--   psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -v apply=1 \
--        -f apps/server/scripts/m6_post_deploy_cleanse_and_validate.sql
--
-- 清洗配方分两类（R4-6，与 migrations/versions/p3a6_tenant_fk.py 文档一致）：
--   A. 可空表（10 张）：tenant_id 为 NULL 合法，孤儿可直接 SET NULL；
--   B. NOT NULL 表（6 张）：禁止 SET NULL，必须先人工确认——
--      导出孤儿清单 → 按业务重映射到有效租户，或 DELETE 后重建 → 再 VALIDATE。
--      本脚本只输出孤儿清单与示例语句，不自动改动 B 类数据。
--
-- 执行顺序：前置检查 → （备份）→ 可空表清洗 → NOT NULL 表人工处置
--          → 全量 VALIDATE → 前后孤儿计数与 convalidated 汇总。
-- 任一步失败：停止；保留 NOT VALID 约束，回退该表改动后再查孤儿来源。
-- ============================================================================

\set ON_ERROR_STOP on
\pset pager off
SET lock_timeout = '5s';
SET statement_timeout = '0';

-- 默认 dry-run；用 -v apply=1 才执行清洗与 VALIDATE。
\if :{?apply}
\else
\set apply 0
\endif

\echo ''
\echo '############################################################################'
\echo '# M6 post-deploy: apply=' :apply ' (0=dry-run, 1=执行清洗与 VALIDATE)'
\echo '############################################################################'

-- ----------------------------------------------------------------------------
-- 0. 前置：16 张表 / 外键是否存在
-- ----------------------------------------------------------------------------
\echo ''
\echo '=== 0. 前置检查: 21 张表（p3a6 16 + p3a8 5）与 fk_<table>_tenant 约束是否存在 ==='
SELECT format(
         'SELECT %L AS table_name, %L AS tenant_id_column, %L AS fk_constraint',
         v.t, 'tenant_id', 'fk_' || v.t || '_tenant')
FROM (VALUES
      ('email_templates'), ('message_templates'), ('notification_logs'),
      ('notification_preferences'), ('rule_set_audit_logs'), ('schedule_audit_logs'),
      ('unified_templates'), ('notification_groups'), ('notification_recipients'),
      ('notification_deliveries'), ('channel_strategies'), ('recipient_rules'),
      ('news'), ('notices'), ('banners'), ('content_versions'),
      ('consultation_fee_types'), ('consultation_fee_templates'),
      ('store_fee_templates'), ('doctor_consultation_fees'),
      ('store_email_recipients')
) AS v(t)
WHERE to_regclass('public.' || v.t) IS NOT NULL
  AND EXISTS (
      SELECT 1 FROM pg_constraint c
      WHERE c.conname = 'fk_' || v.t || '_tenant'
        AND c.conrelid = to_regclass('public.' || v.t)
  )
ORDER BY v.t
\gexec

\echo '--- 0b. 缺失（表或外键不存在）的条目 ---'
SELECT format('SELECT %L AS skipped_item, %L AS status', v.t, 'SKIP(missing table or fk)')
FROM (VALUES
      ('email_templates'), ('message_templates'), ('notification_logs'),
      ('notification_preferences'), ('rule_set_audit_logs'), ('schedule_audit_logs'),
      ('unified_templates'), ('notification_groups'), ('notification_recipients'),
      ('notification_deliveries'), ('channel_strategies'), ('recipient_rules'),
      ('news'), ('notices'), ('banners'), ('content_versions'),
      ('consultation_fee_types'), ('consultation_fee_templates'),
      ('store_fee_templates'), ('doctor_consultation_fees'),
      ('store_email_recipients')
) AS v(t)
WHERE to_regclass('public.' || v.t) IS NULL
   OR NOT EXISTS (
      SELECT 1 FROM pg_constraint c
      WHERE c.conname = 'fk_' || v.t || '_tenant'
        AND c.conrelid = to_regclass('public.' || v.t)
   )
ORDER BY v.t
\gexec

-- ----------------------------------------------------------------------------
-- 1. 清洗前孤儿计数（全部 16 表）
-- ----------------------------------------------------------------------------
\echo ''
\echo '=== 1. 清洗前: 各表外键孤儿计数 ==='
WITH candidates(t) AS (
    VALUES
      ('email_templates'), ('message_templates'), ('notification_logs'),
      ('notification_preferences'), ('rule_set_audit_logs'), ('schedule_audit_logs'),
      ('unified_templates'), ('notification_groups'), ('notification_recipients'),
      ('notification_deliveries'), ('channel_strategies'), ('recipient_rules'),
      ('news'), ('notices'), ('banners'), ('content_versions'),
      ('consultation_fee_types'), ('consultation_fee_templates'),
      ('store_fee_templates'), ('doctor_consultation_fees'),
      ('store_email_recipients')
)
SELECT format(
         'SELECT %L AS table_name, count(*) AS orphans_before '
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

-- ----------------------------------------------------------------------------
-- 2. A 类：可空表孤儿置 NULL —— 仅 apply=1 执行（p3a8 的 5 张表列均可空，归入本类）
-- ----------------------------------------------------------------------------
\echo ''
\echo '=== 2. A 类（可空表，10+5 张）: SET tenant_id = NULL WHERE 孤儿（apply=1 才执行）==='
\if :apply
WITH nullable(t) AS (
    VALUES
      ('email_templates'), ('message_templates'), ('notification_logs'),
      ('notification_preferences'), ('rule_set_audit_logs'), ('schedule_audit_logs'),
      ('news'), ('notices'), ('banners'), ('content_versions'),
      ('consultation_fee_types'), ('consultation_fee_templates'),
      ('store_fee_templates'), ('doctor_consultation_fees'),
      ('store_email_recipients')
)
SELECT format(
         'UPDATE public.%I e SET tenant_id = NULL '
         'WHERE e.tenant_id IS NOT NULL '
         'AND NOT EXISTS (SELECT 1 FROM public.tenants t WHERE t.id = e.tenant_id)',
         v.t)
FROM nullable v
WHERE to_regclass('public.' || v.t) IS NOT NULL
  AND EXISTS (
      SELECT 1 FROM information_schema.columns c
      WHERE c.table_schema = 'public' AND c.table_name = v.t AND c.column_name = 'tenant_id'
  )
ORDER BY v.t
\gexec
\echo 'A 类清洗已提交（逐表 UPDATE 成功后自动提交）。'
\else
\echo 'A 类清洗已跳过（dry-run）。加 -v apply=1 执行。'
\endif

-- ----------------------------------------------------------------------------
-- 3. B 类：NOT NULL 表（6 张）——只输出孤儿清单，禁止自动 SET NULL
-- ----------------------------------------------------------------------------
\echo ''
\echo '=== 3. B 类（NOT NULL 表）: 孤儿清单（必须人工重映射或 DELETE，脚本不自动改）==='
WITH required(t) AS (
    VALUES
      ('unified_templates'), ('notification_groups'), ('notification_recipients'),
      ('notification_deliveries'), ('channel_strategies'), ('recipient_rules')
)
SELECT format(
         'SELECT %L AS table_name, count(*) AS orphans_manual '
         'FROM public.%I e '
         'WHERE e.tenant_id IS NOT NULL '
         'AND NOT EXISTS (SELECT 1 FROM public.tenants t WHERE t.id = e.tenant_id)',
         v.t, v.t)
FROM required v
WHERE to_regclass('public.' || v.t) IS NOT NULL
  AND EXISTS (
      SELECT 1 FROM information_schema.columns c
      WHERE c.table_schema = 'public' AND c.table_name = v.t AND c.column_name = 'tenant_id'
  )
ORDER BY v.t
\gexec

\echo '--- B 类人工处置示例（按业务确认后逐表执行，禁止批量 DELETE 生产数据）---'
\echo '-- 1) 导出孤儿：'
\echo '--    \copy (SELECT * FROM public.notification_groups g WHERE g.tenant_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM public.tenants t WHERE t.id=g.tenant_id)) TO ''notification_groups_orphans.csv'' CSV HEADER'
\echo '-- 2) 重映射到有效租户（需业务确认目标租户）：'
\echo '--    UPDATE public.notification_groups SET tenant_id = ''<target_tenant_id>'' WHERE id = ''<orphan_id>'';'
\echo '-- 3) 或删除后重建（仅在确认无保留价值时）：'
\echo '--    DELETE FROM public.notification_deliveries WHERE group_id = ''<orphan_group_id>'';'
\echo '--    DELETE FROM public.notification_groups WHERE id = ''<orphan_group_id>'';'

-- ----------------------------------------------------------------------------
-- 4. VALIDATE：16 表逐个校验 —— 仅 apply=1 执行
--    VALIDATE 只加 SHARE UPDATE EXCLUSIVE 锁，不阻塞读写；lock_timeout=5s。
-- ----------------------------------------------------------------------------
\echo ''
\echo '=== 4. VALIDATE CONSTRAINT（apply=1 才执行；逐表失败会立即中止）==='
\if :apply
WITH candidates(t) AS (
    VALUES
      ('email_templates'), ('message_templates'), ('notification_logs'),
      ('notification_preferences'), ('rule_set_audit_logs'), ('schedule_audit_logs'),
      ('unified_templates'), ('notification_groups'), ('notification_recipients'),
      ('notification_deliveries'), ('channel_strategies'), ('recipient_rules'),
      ('news'), ('notices'), ('banners'), ('content_versions'),
      ('consultation_fee_types'), ('consultation_fee_templates'),
      ('store_fee_templates'), ('doctor_consultation_fees'),
      ('store_email_recipients')
)
SELECT format('ALTER TABLE public.%I VALIDATE CONSTRAINT %I', v.t, 'fk_' || v.t || '_tenant')
FROM candidates v
WHERE to_regclass('public.' || v.t) IS NOT NULL
  AND EXISTS (
      SELECT 1 FROM pg_constraint c
      WHERE c.conname = 'fk_' || v.t || '_tenant'
        AND c.conrelid = to_regclass('public.' || v.t)
  )
ORDER BY v.t
\gexec
\echo 'VALIDATE 已执行。'
\else
\echo 'VALIDATE 已跳过（dry-run）。加 -v apply=1 执行。'
\endif

-- ----------------------------------------------------------------------------
-- 5. 清洗后复核：孤儿计数应全为 0
-- ----------------------------------------------------------------------------
\echo ''
\echo '=== 5. 清洗后: 各表外键孤儿计数（应为 0；B 类未人工处置时可能 >0）==='
WITH candidates(t) AS (
    VALUES
      ('email_templates'), ('message_templates'), ('notification_logs'),
      ('notification_preferences'), ('rule_set_audit_logs'), ('schedule_audit_logs'),
      ('unified_templates'), ('notification_groups'), ('notification_recipients'),
      ('notification_deliveries'), ('channel_strategies'), ('recipient_rules'),
      ('news'), ('notices'), ('banners'), ('content_versions'),
      ('consultation_fee_types'), ('consultation_fee_templates'),
      ('store_fee_templates'), ('doctor_consultation_fees'),
      ('store_email_recipients')
)
SELECT format(
         'SELECT %L AS table_name, count(*) AS orphans_after '
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

-- ----------------------------------------------------------------------------
-- 6. 汇总：16 个 fk_*_tenant 的 convalidated（期望全部 true）
-- ----------------------------------------------------------------------------
\echo ''
\echo '=== 6. 约束状态汇总: fk_*_tenant 的 convalidated（期望全 true）==='
SELECT conname AS constraint_name,
       conrelid::regclass AS table_name,
       convalidated,
       CASE WHEN convalidated THEN 'PASS' ELSE 'FAIL(NOT VALID)' END AS status
FROM pg_constraint
WHERE conname LIKE 'fk\_%\_tenant' ESCAPE '\'
ORDER BY conrelid::regclass::text;

\echo ''
\echo '### M6 复核完成：孤儿=0 且 convalidated 全 true 才视为通过 ###'
