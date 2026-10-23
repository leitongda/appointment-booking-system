-- 租户重构上线前只读核对（PostgreSQL）
-- 用途：为决策点 D1/D9/D13/D15/D20 与迁移 M6 的孤儿清洗提供依据
-- 用法：psql "$DATABASE_URL" -f tenant_null_tenant_id_audit.sql
-- 注意：全部为只读查询，不修改任何数据。

\echo '=== D20: 死代码表行数（必须为 0 才能 drop）==='
SELECT 'data_scopes' AS table_name, count(*) AS rows FROM data_scopes
UNION ALL
SELECT 'role_permissions', count(*) FROM role_permissions;

\echo '=== D13: 跨租户重复的管理员用户名 / 角色编码（>0 时 M2 迁移会中止）==='
SELECT 'admins.username' AS kind, username AS value, count(DISTINCT tenant_id) AS tenant_count
FROM admins
WHERE tenant_id IS NOT NULL
GROUP BY username
HAVING count(DISTINCT tenant_id) > 1
UNION ALL
SELECT 'roles.code', code, count(DISTINCT tenant_id)
FROM roles
WHERE tenant_id IS NOT NULL
GROUP BY code
HAVING count(DISTINCT tenant_id) > 1;

\echo '=== D9: 各表 tenant_id 为 NULL 的存量行占比（锚点过滤后不可见）==='
SELECT 'users' AS table_name, count(*) FILTER (WHERE tenant_id IS NULL) AS null_tenant, count(*) AS total FROM users
UNION ALL SELECT 'patients', count(*) FILTER (WHERE tenant_id IS NULL), count(*) FROM patients
UNION ALL SELECT 'doctors', count(*) FILTER (WHERE tenant_id IS NULL), count(*) FROM doctors
UNION ALL SELECT 'stores', count(*) FILTER (WHERE tenant_id IS NULL), count(*) FROM stores
UNION ALL SELECT 'schedules', count(*) FILTER (WHERE tenant_id IS NULL), count(*) FROM schedules
UNION ALL SELECT 'appointments', count(*) FILTER (WHERE tenant_id IS NULL), count(*) FROM appointments
UNION ALL SELECT 'medical_records', count(*) FILTER (WHERE tenant_id IS NULL), count(*) FROM medical_records
UNION ALL SELECT 'examination_reports', count(*) FILTER (WHERE tenant_id IS NULL), count(*) FROM examination_reports
UNION ALL SELECT 'follow_up_tasks', count(*) FILTER (WHERE tenant_id IS NULL), count(*) FROM follow_up_tasks
UNION ALL SELECT 'waitlist_entries', count(*) FILTER (WHERE tenant_id IS NULL), count(*) FROM waitlist_entries
UNION ALL SELECT 'messages', count(*) FILTER (WHERE tenant_id IS NULL), count(*) FROM messages
UNION ALL SELECT 'news', count(*) FILTER (WHERE tenant_id IS NULL), count(*) FROM news
UNION ALL SELECT 'notices', count(*) FILTER (WHERE tenant_id IS NULL), count(*) FROM notices
UNION ALL SELECT 'banners', count(*) FILTER (WHERE tenant_id IS NULL), count(*) FROM banners
UNION ALL SELECT 'system_settings', count(*) FILTER (WHERE tenant_id IS NULL), count(*) FROM system_settings;

\echo '=== D15: 预约与其支付配置的租户不一致（回调会拒收）==='
SELECT count(*) AS inconsistent_appointments
FROM appointments a
JOIN payment_profiles p ON p.id = a.payment_profile_id
WHERE a.tenant_id IS DISTINCT FROM p.tenant_id;

\echo '=== M6: 16 张表的外键孤儿（tenant_id 指向不存在的租户，>0 需先清洗）==='
SELECT 'email_templates' AS table_name, count(*) AS orphans FROM email_templates e WHERE e.tenant_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM tenants t WHERE t.id = e.tenant_id)
UNION ALL SELECT 'message_templates', count(*) FROM message_templates e WHERE e.tenant_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM tenants t WHERE t.id = e.tenant_id)
UNION ALL SELECT 'notification_logs', count(*) FROM notification_logs e WHERE e.tenant_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM tenants t WHERE t.id = e.tenant_id)
UNION ALL SELECT 'notification_preferences', count(*) FROM notification_preferences e WHERE e.tenant_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM tenants t WHERE t.id = e.tenant_id)
UNION ALL SELECT 'rule_set_audit_logs', count(*) FROM rule_set_audit_logs e WHERE e.tenant_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM tenants t WHERE t.id = e.tenant_id)
UNION ALL SELECT 'schedule_audit_logs', count(*) FROM schedule_audit_logs e WHERE e.tenant_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM tenants t WHERE t.id = e.tenant_id)
UNION ALL SELECT 'unified_templates', count(*) FROM unified_templates e WHERE e.tenant_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM tenants t WHERE t.id = e.tenant_id)
UNION ALL SELECT 'notification_groups', count(*) FROM notification_groups e WHERE e.tenant_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM tenants t WHERE t.id = e.tenant_id)
UNION ALL SELECT 'notification_recipients', count(*) FROM notification_recipients e WHERE e.tenant_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM tenants t WHERE t.id = e.tenant_id)
UNION ALL SELECT 'notification_deliveries', count(*) FROM notification_deliveries e WHERE e.tenant_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM tenants t WHERE t.id = e.tenant_id)
UNION ALL SELECT 'channel_strategies', count(*) FROM channel_strategies e WHERE e.tenant_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM tenants t WHERE t.id = e.tenant_id)
UNION ALL SELECT 'recipient_rules', count(*) FROM recipient_rules e WHERE e.tenant_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM tenants t WHERE t.id = e.tenant_id)
UNION ALL SELECT 'news', count(*) FROM news e WHERE e.tenant_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM tenants t WHERE t.id = e.tenant_id)
UNION ALL SELECT 'notices', count(*) FROM notices e WHERE e.tenant_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM tenants t WHERE t.id = e.tenant_id)
UNION ALL SELECT 'banners', count(*) FROM banners e WHERE e.tenant_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM tenants t WHERE t.id = e.tenant_id)
UNION ALL SELECT 'content_versions', count(*) FROM content_versions e WHERE e.tenant_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM tenants t WHERE t.id = e.tenant_id);

\echo '=== D1: 管理员账号分布（用于确认是否存在仅存于 users 表的旧管理员）==='
SELECT 'admins' AS source, count(*) AS rows FROM admins
UNION ALL
SELECT 'users', count(*) FROM users;

\echo '=== 软删除租户（purge 候选预览，90 天前）==='
SELECT tenant_code, name, deleted_at
FROM tenants
WHERE deleted_at IS NOT NULL
  AND deleted_at < (now() - interval '90 days')
ORDER BY deleted_at;
