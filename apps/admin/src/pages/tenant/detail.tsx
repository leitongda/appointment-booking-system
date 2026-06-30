import { PageContainer, ProForm, ProFormDigit, ProFormSwitch } from '@ant-design/pro-components';
import { Card, Descriptions, Tag, Statistic, Row, Col, Button, Tabs, Table, Popconfirm, Select, App, Upload, Alert, List, Space, Typography } from 'antd';
import { history, useParams, useAccess } from '@umijs/max';
import { useEffect, useState, useCallback } from 'react';
import { tenantApi } from '@hospital/api';
import { downloadBlob } from '@/utils/download';
import type {
  Tenant,
  TenantUsageLog,
  TenantUsageSummary,
  TenantSubscription,
  PasswordPolicy,
  TenantUsageTrend,
} from '@hospital/api';

const { Text } = Typography;

/** 解析 JSON 字符串，失败返回默认值 */
function safeParseJson<T>(value: string | undefined | null, fallback: T): T {
  if (!value) return fallback;
  try {
    return JSON.parse(value) as T;
  } catch {
    return fallback;
  }
}

const TENANT_STATUS_MAP: Record<number, { text: string; color: string }> = {
  0: { text: '已禁用', color: 'default' },
  1: { text: '正常', color: 'success' },
  2: { text: '已欠费', color: 'error' },
  3: { text: '试用中', color: 'warning' },
};

const TenantDetailPage: React.FC = () => {
  const { id } = useParams();
  const access = useAccess();
  const { message } = App.useApp();
  const [tenant, setTenant] = useState<Tenant | null>(null);
  const [usage, setUsage] = useState<TenantUsageSummary | null>(null);
  const [subscriptions, setSubscriptions] = useState<TenantSubscription[]>([]);
  const [usageLogs, setUsageLogs] = useState<TenantUsageLog[]>([]);
  const [loading, setLoading] = useState(true);

  // 标签管理状态
  const [allTags, setAllTags] = useState<string[]>([]);
  const [tenantTags, setTenantTags] = useState<string[]>([]);
  const [tagLoading, setTagLoading] = useState(false);

  // 密码策略状态
  const [passwordPolicy, setPasswordPolicy] = useState<PasswordPolicy | null>(null);
  const [policyLoading, setPolicyLoading] = useState(false);

  // 用量趋势状态
  const [usageTrends, setUsageTrends] = useState<TenantUsageTrend[]>([]);
  const [trendsLoading, setTrendsLoading] = useState(false);

  // 备份/恢复状态
  const [backupLoading, setBackupLoading] = useState(false);
  const [importLoading, setImportLoading] = useState(false);
  const [precheckResult, setPrecheckResult] = useState<{
    compatible: boolean;
    warnings: string[];
    blockers: string[];
  } | null>(null);
  const [pendingFile, setPendingFile] = useState<File | null>(null);

  const loadData = async () => {
    setLoading(true);
    try {
      const [tenantRes, usageRes, subRes, usageLogRes] = await Promise.all([
        tenantApi.getTenant(id),
        tenantApi.getTenantUsage(id),
        tenantApi.getTenantSubscriptions(id, 10),
        tenantApi.getTenantUsageLogs(id, { limit: 30 }),
      ]);
      const t = (tenantRes as any)?.data ?? tenantRes;
      setTenant(t);
      setUsage((usageRes as any)?.data ?? usageRes);
      setSubscriptions((subRes as any)?.data ?? subRes ?? []);
      setUsageLogs((usageLogRes as any)?.data ?? usageLogRes ?? []);
      // 从租户数据中提取标签（tags 是 JSON 字符串）
      const parsedTags = safeParseJson<string[]>(t?.tags, []);
      setTenantTags(parsedTags);
    } catch (error) {
      message.error('加载租户信息失败');
      history.back();
    } finally {
      setLoading(false);
    }
  };

  const loadTags = useCallback(async () => {
    try {
      const tags = await tenantApi.getAllTags();
      setAllTags(tags || []);
    } catch {
      // ignore
    }
  }, []);

  const loadPasswordPolicy = useCallback(async () => {
    setPolicyLoading(true);
    try {
      const policy = await tenantApi.getPasswordPolicy(id);
      setPasswordPolicy(policy);
    } catch {
      // 使用默认值
      setPasswordPolicy({
        minLength: 8,
        maxLength: 128,
        requireUppercase: true,
        requireLowercase: true,
        requireDigit: true,
        requireSpecialChar: false,
      });
    } finally {
      setPolicyLoading(false);
    }
  }, [id]);

  const loadUsageTrends = useCallback(async () => {
    setTrendsLoading(true);
    try {
      const trends = await tenantApi.getTenantUsageTrends(id, { limit: 30 });
      setUsageTrends(trends || []);
    } catch {
      // ignore
    } finally {
      setTrendsLoading(false);
    }
  }, [id]);

  useEffect(() => {
    loadData();
    loadTags();
  }, [id]);

  const handleActivate = async () => {
    await tenantApi.activateTenant(id);
    message.success('租户已激活');
    loadData();
  };

  const handleSuspend = async () => {
    await tenantApi.suspendTenant(id);
    message.success('租户已暂停');
    loadData();
  };

  const handleTagsChange = async (tags: string[]) => {
    setTagLoading(true);
    try {
      await tenantApi.updateTenantTags(id, tags);
      setTenantTags(tags);
      message.success('标签已更新');
      loadTags();
    } catch (error: any) {
      message.error(error.message || '更新标签失败');
    } finally {
      setTagLoading(false);
    }
  };

  const handlePasswordPolicySubmit = async (values: any) => {
    try {
      const updated = await tenantApi.updatePasswordPolicy(id, values);
      setPasswordPolicy(updated);
      message.success('密码策略已更新');
    } catch (error: any) {
      message.error(error.message || '更新密码策略失败');
    }
  };

  const handleExportBackup = async () => {
    setBackupLoading(true);
    try {
      const blob = await tenantApi.exportTenantBackup(id);
      downloadBlob(blob as any, `tenant_${(tenant?.tenantCode || id).slice(0, 8)}_backup.json`);
      message.success('备份导出成功');
    } catch (error: any) {
      message.error(error.message || '备份导出失败');
    } finally {
      setBackupLoading(false);
    }
  };

  const handlePrecheckImport = async (file: File) => {
    setImportLoading(true);
    setPrecheckResult(null);
    setPendingFile(null);
    try {
      const result = await tenantApi.precheckTenantImport(id, file);
      setPrecheckResult(result);
      if (result.compatible && result.blockers.length === 0) {
        setPendingFile(file);
      }
    } catch (error: any) {
      message.error(error.message || '预检失败');
    } finally {
      setImportLoading(false);
    }
    return false; // prevent auto upload
  };

  const handleConfirmImport = async (overwrite: boolean) => {
    if (!pendingFile) return;
    setImportLoading(true);
    try {
      const result = await tenantApi.importTenantBackup(id, pendingFile, overwrite);
      message.success(result.message || '数据恢复成功');
      setPrecheckResult(null);
      setPendingFile(null);
      loadData();
    } catch (error: any) {
      message.error(error.message || '数据恢复失败');
    } finally {
      setImportLoading(false);
    }
  };

  if (!tenant) return null;

  // 用量趋势表格列
  const trendColumns = [
    { title: '日期', dataIndex: 'date', width: 100 },
    { title: '预约量', dataIndex: 'appointmentCount', width: 80 },
    { title: '完成量', dataIndex: 'completedCount', width: 80 },
    { title: '取消量', dataIndex: 'cancelledCount', width: 80 },
    { title: '新增用户', dataIndex: 'newUserCount', width: 80 },
    { title: '活跃用户', dataIndex: 'activeUserCount', width: 80 },
    { title: '存储(MB)', dataIndex: 'storageUsedMb', width: 100, render: (v: number) => Number(v || 0).toFixed(2) },
  ];

  return (
    <PageContainer
      title={tenant.name}
      extra={[
        access.hasPermission('tenant:update') && tenant.status === 0 && (
          <Button key="activate" type="primary" onClick={handleActivate}>
            激活租户
          </Button>
        ),
        access.hasPermission('tenant:update') && tenant.status === 1 && (
          <Popconfirm
            key="suspend"
            title="确定暂停该租户吗？"
            onConfirm={handleSuspend}
          >
            <Button danger>暂停租户</Button>
          </Popconfirm>
        ),
        access.hasPermission('tenant:update') && (
          <Button key="edit" onClick={() => history.push(`/platform/tenant/${id}/edit`)}>
            编辑
          </Button>
        ),
        <Button key="back" onClick={() => history.push('/platform/tenant')}>
          返回
        </Button>,
      ].filter(Boolean)}
    >
      <Row gutter={24}>
        <Col span={16}>
          <Card loading={loading}>
            <Tabs
              items={[
                {
                  key: 'overview',
                  label: '租户概览',
                  children: (
                    <Descriptions column={2} items={[
                      { key: '0', label: '租户标识', children: tenant.tenantCode },
                      { key: '1', label: '状态', children: (
                        <Tag color={TENANT_STATUS_MAP[tenant.status]?.color}>
                          {TENANT_STATUS_MAP[tenant.status]?.text}
                        </Tag>
                      ) },
                      { key: '2', label: '订阅计划', children: (
                        tenant.subscriptionPlanName ? (
                          <Tag color="blue">{tenant.subscriptionPlanName}</Tag>
                        ) : (
                          <Tag>未订阅</Tag>
                        )
                      ) },
                      { key: '3', label: '计费周期', children: tenant.billingCycle === 'yearly' ? '年付' : '月付' },
                      { key: '4', label: '订阅到期', children: tenant.subscriptionEndAt || '-' },
                      { key: '5', label: '创建时间', children: tenant.createdAt },
                      { key: '6', label: '联系人', children: tenant.contactName || '-' },
                      { key: '7', label: '联系电话', children: tenant.contactPhone || '-' },
                      { key: '8', label: '联系邮箱', children: tenant.contactEmail || '-' },
                      { key: '9', label: '详细地址', span: 2, children: tenant.address || '-' },
                      { key: '10', label: '子域名', children: tenant.subdomain || '-' },
                      { key: '11', label: '自定义域名', children: tenant.customDomain || '-' },
                      { key: '12', label: '标签', span: 2, children: (
                        <Select
                          mode="tags"
                          style={{ minWidth: 300 }}
                          placeholder="输入或选择标签"
                          value={tenantTags}
                          onChange={handleTagsChange}
                          loading={tagLoading}
                          options={allTags.map((t) => ({ label: t, value: t }))}
                          tokenSeparators={[',']}
                        />
                      ) },
                    ]} />
                  ),
                },
                {
                  key: 'config',
                  label: '租户配置',
                  children: (() => {
                    const features = safeParseJson<Record<string, boolean>>(tenant.features, {});
                    const branding = safeParseJson<{ logoUrl?: string; themeColor?: string }>(tenant.brandingConfig, {});
                    const tagsArr = safeParseJson<string[]>(tenant.tags, []);

                    const featureLabels: Record<string, string> = {
                      online_payment: '在线支付',
                      evaluation: '评价功能',
                      waiting_queue: '候诊排队',
                      online_service: '在线客服',
                      miniapp_live: '小程序直播',
                      wechat_integration: '微信集成',
                      sms_notification: '短信通知',
                      export_data: '数据导出',
                      api_access: 'API 开放接口',
                      custom_branding: '自定义品牌',
                      sso: '单点登录 (SSO)',
                      basic_appointment: '基础预约',
                      basic_schedule: '基础排班',
                      basic_statistics: '基础统计',
                      advanced_statistics: '高级数据分析',
                      priority_support: '优先技术支持',
                      beta_features: '灰度功能总开关',
                      beta_ai_assistant: 'AI 辅助',
                      beta_analytics_v2: '新版数据分析',
                    };

                    const enabledFeatures = Object.entries(features)
                      .filter(([_, v]) => v)
                      .map(([k]) => featureLabels[k] || k);
                    const disabledFeatures = Object.entries(features)
                      .filter(([_, v]) => !v)
                      .map(([k]) => featureLabels[k] || k);

                    return (
                      <>
                        <Card title="功能开关" size="small" style={{ marginBottom: 16 }}>
                          {Object.keys(features).length === 0 ? (
                            <Text type="secondary">未配置功能开关</Text>
                          ) : (
                            <>
                              <div style={{ marginBottom: 8 }}>
                                <Text strong>已启用: </Text>
                                {enabledFeatures.length > 0
                                  ? enabledFeatures.map((f) => <Tag color="success" key={f}>{f}</Tag>)
                                  : <Text type="secondary">无</Text>}
                              </div>
                              <div>
                                <Text strong>未启用: </Text>
                                {disabledFeatures.length > 0
                                  ? disabledFeatures.map((f) => <Tag key={f}>{f}</Tag>)
                                  : <Text type="secondary">无</Text>}
                              </div>
                            </>
                          )}
                        </Card>

                        <Card title="品牌配置" size="small" style={{ marginBottom: 16 }}>
                          {branding.logoUrl || branding.themeColor ? (
                            <Descriptions column={2} size="small">
                              {branding.logoUrl && (
                                <Descriptions.Item label="Logo">
                                  <a href={branding.logoUrl} target="_blank" rel="noreferrer">{branding.logoUrl}</a>
                                </Descriptions.Item>
                              )}
                              {branding.themeColor && (
                                <Descriptions.Item label="主题色">
                                  <Space>
                                    <span style={{
                                      display: 'inline-block',
                                      width: 20,
                                      height: 20,
                                      borderRadius: 4,
                                      backgroundColor: branding.themeColor,
                                      border: '1px solid var(--color-border)',
                                      verticalAlign: 'middle',
                                    }} />
                                    <Text>{branding.themeColor}</Text>
                                  </Space>
                                </Descriptions.Item>
                              )}
                            </Descriptions>
                          ) : (
                            <Text type="secondary">未配置品牌信息</Text>
                          )}
                        </Card>

                        <Card title="限流配置" size="small" style={{ marginBottom: 16 }}>
                          <Descriptions column={2} size="small">
                            <Descriptions.Item label="每分钟请求上限">
                              {tenant.rateLimitPerMinute ?? '使用全局默认值 (300)'}
                            </Descriptions.Item>
                            <Descriptions.Item label="每秒请求上限">
                              {tenant.rateLimitPerSecond ?? '使用全局默认值 (50)'}
                            </Descriptions.Item>
                          </Descriptions>
                        </Card>

                        <Card title="运维配置" size="small" style={{ marginBottom: 16 }}>
                          <Descriptions column={2} size="small">
                            <Descriptions.Item label="日志保留天数">
                              {tenant.logRetentionDays ?? 90} 天
                            </Descriptions.Item>
                            <Descriptions.Item label="自定义域名">
                              {tenant.customDomain || '-'}
                            </Descriptions.Item>
                            <Descriptions.Item label="子域名前缀">
                              {tenant.subdomain || '-'}
                            </Descriptions.Item>
                            <Descriptions.Item label="租户标签">
                              {tagsArr.length > 0
                                ? tagsArr.map((t) => <Tag color="blue" key={t}>{t}</Tag>)
                                : '-'}
                            </Descriptions.Item>
                          </Descriptions>
                        </Card>

                        <Card title="安全策略" size="small">
                          {(() => {
                            // 从 tenant.passwordPolicy 获取，或从 API 获取的 passwordPolicy
                            const rawPolicy = passwordPolicy || safeParseJson<Record<string, any>>(tenant.passwordPolicy, {} as Record<string, any>);
                            const hasPolicy = rawPolicy && Object.keys(rawPolicy).length > 0;
                            if (!hasPolicy) {
                              return <Text type="secondary">使用系统默认策略</Text>;
                            }
                            // 兼容两种格式：API 返回的 camelCase 和数据库存储的 snake_case
                            const minLength = (rawPolicy as any).minLength ?? (rawPolicy as any).min_length ?? '-';
                            const requireUppercase = ((rawPolicy as any).requireUppercase ?? (rawPolicy as any).require_uppercase) ? '是' : '否';
                            const requireDigit = ((rawPolicy as any).requireDigit ?? (rawPolicy as any).require_digit) ? '是' : '否';
                            const requireSpecial = ((rawPolicy as any).requireSpecialChar ?? (rawPolicy as any).require_special) ? '是' : '否';
                            return (
                              <Descriptions column={2} size="small">
                                <Descriptions.Item label="密码最小长度">{minLength}</Descriptions.Item>
                                <Descriptions.Item label="要求大写字母">{requireUppercase}</Descriptions.Item>
                                <Descriptions.Item label="要求数字">{requireDigit}</Descriptions.Item>
                                <Descriptions.Item label="要求特殊字符">{requireSpecial}</Descriptions.Item>
                              </Descriptions>
                            );
                          })()}
                        </Card>
                      </>
                    );
                  })(),
                },
                {
                  key: 'subscriptions',
                  label: '订阅记录',
                  children: (
                    <Table
                      dataSource={subscriptions}
                      rowKey="id"
                      size="small"
                      pagination={false}
                      columns={[
                        { title: '计划', dataIndex: 'planName', width: 120 },
                        { title: '周期', dataIndex: 'billingCycle', width: 80, render: (v) => v === 'yearly' ? '年付' : '月付' },
                        { title: '开始时间', dataIndex: 'startAt', width: 120 },
                        { title: '结束时间', dataIndex: 'endAt', width: 120 },
                        { title: '金额', dataIndex: 'finalAmount', width: 100, render: (v) => v ? `¥${v}` : '-' },
                        {
                          title: '支付状态',
                          dataIndex: 'paymentStatus',
                          width: 100,
                          render: (v) => {
                            const map: Record<string, { text: string; color: string }> = {
                              pending: { text: '待支付', color: 'warning' },
                              paid: { text: '已支付', color: 'success' },
                              failed: { text: '支付失败', color: 'error' },
                            };
                            const item = map[v] || { text: v, color: 'default' };
                            return <Tag color={item.color}>{item.text}</Tag>;
                          },
                        },
                        { title: '自动续费', dataIndex: 'autoRenew', width: 80, render: (v) => (v ? '是' : '否') },
                      ]}
                    />
                  ),
                },
                {
                  key: 'usage-logs',
                  label: '用量日志',
                  children: (
                    <Table
                      dataSource={usageLogs}
                      rowKey="id"
                      size="small"
                      pagination={false}
                      columns={[
                        { title: '日期', dataIndex: 'usageDate', width: 120 },
                        { title: '预约量', dataIndex: 'appointmentCount', width: 90 },
                        { title: '完成量', dataIndex: 'appointmentCompletedCount', width: 90 },
                        { title: '取消量', dataIndex: 'appointmentCancelledCount', width: 90 },
                        { title: '新增用户', dataIndex: 'newUserCount', width: 90 },
                        { title: '活跃用户', dataIndex: 'activeUserCount', width: 90 },
                        { title: '活跃医生', dataIndex: 'activeDoctorCount', width: 90 },
                        { title: '存储(MB)', dataIndex: 'storageUsedMb', width: 110, render: (v) => Number(v || 0).toFixed(2) },
                      ]}
                    />
                  ),
                },
                {
                  key: 'usage-trends',
                  label: '用量趋势',
                  children: (
                    <Table
                      dataSource={usageTrends}
                      rowKey="date"
                      size="small"
                      loading={trendsLoading}
                      pagination={false}
                      columns={trendColumns}
                    />
                  ),
                },
                {
                  key: 'password-policy',
                  label: '密码策略',
                  children: passwordPolicy ? (
                    <ProForm
                      key={policyLoading ? 'policy-loading' : 'policy-loaded'}
                      onFinish={handlePasswordPolicySubmit}
                      initialValues={passwordPolicy}
                      submitter={{ searchConfig: { submitText: '保存策略' }, resetButtonProps: { style: { display: 'none' } } }}
                    >
                      <ProFormDigit name="minLength" label="最小长度" min={1} max={128} rules={[{ required: true }]} />
                      <ProFormDigit name="maxLength" label="最大长度" min={1} max={256} rules={[{ required: true }]} />
                      <ProFormSwitch name="requireUppercase" label="要求大写字母" />
                      <ProFormSwitch name="requireLowercase" label="要求小写字母" />
                      <ProFormSwitch name="requireDigit" label="要求数字" />
                      <ProFormSwitch name="requireSpecialChar" label="要求特殊字符" />
                      <ProFormDigit name="maxAge" label="密码有效期（天）" min={0} extra="0 表示永不过期" />
                      <ProFormDigit name="preventReuse" label="禁止重复次数" min={0} extra="0 表示不限制" />
                      <ProFormDigit name="lockoutThreshold" label="锁定阈值（次）" min={0} extra="连续错误密码次数，0 表示不锁定" />
                      <ProFormDigit name="lockoutDuration" label="锁定时长（分钟）" min={0} extra="0 表示永久锁定" />
                    </ProForm>
                  ) : null,
                },
                {
                  key: 'backup',
                  label: '数据备份',
                  children: (
                    <div>
                      <Alert
                        type="info"
                        showIcon
                        message="数据备份与恢复"
                        description="导出租户全部数据（门店、科室、医生、管理员、排班、预约）为 JSON 文件。恢复时会将备份数据导入到当前租户。"
                        style={{ marginBottom: 16 }}
                      />
                      <Card title="导出备份" size="small" style={{ marginBottom: 16 }}>
                        <p>将当前租户的全部业务数据导出为 JSON 文件，可用于数据迁移或灾备。</p>
                        <Button
                          type="primary"
                          loading={backupLoading}
                          onClick={handleExportBackup}
                        >
                          导出备份文件
                        </Button>
                      </Card>
                      <Card title="导入恢复" size="small">
                        <p>上传之前导出的备份文件，预检后确认恢复。导入前会检查数据兼容性。</p>
                        <Upload
                          accept=".json"
                          showUploadList={false}
                          beforeUpload={handlePrecheckImport}
                          disabled={importLoading}
                        >
                          <Button loading={importLoading}>选择备份文件</Button>
                        </Upload>
                        {precheckResult && (
                          <div style={{ marginTop: 16 }}>
                            {precheckResult.blockers.length > 0 && (
                              <Alert
                                type="error"
                                showIcon
                                message="导入被阻止"
                                description={
                                  <List
                                    size="small"
                                    dataSource={precheckResult.blockers}
                                    renderItem={(item) => <List.Item>{item}</List.Item>}
                                  />
                                }
                                style={{ marginBottom: 16 }}
                              />
                            )}
                            {precheckResult.warnings.length > 0 && (
                              <Alert
                                type="warning"
                                showIcon
                                message="注意事项"
                                description={
                                  <List
                                    size="small"
                                    dataSource={precheckResult.warnings}
                                    renderItem={(item) => <List.Item>{item}</List.Item>}
                                  />
                                }
                                style={{ marginBottom: 16 }}
                              />
                            )}
                            {precheckResult.compatible && precheckResult.blockers.length === 0 && (
                              <Space>
                                <Popconfirm
                                  title="确定恢复数据？"
                                  description="此操作将向当前租户导入备份数据。"
                                  onConfirm={() => handleConfirmImport(false)}
                                >
                                  <Button type="primary" loading={importLoading}>
                                    确认恢复
                                  </Button>
                                </Popconfirm>
                                <Popconfirm
                                  title="确定覆盖恢复？"
                                  description="覆盖模式会替换已存在的数据，请谨慎操作。"
                                  onConfirm={() => handleConfirmImport(true)}
                                >
                                  <Button danger loading={importLoading}>
                                    覆盖恢复
                                  </Button>
                                </Popconfirm>
                              </Space>
                            )}
                          </div>
                        )}
                      </Card>
                    </div>
                  ),
                },
              ]}
              onChange={(key) => {
                if (key === 'usage-trends' && usageTrends.length === 0) loadUsageTrends();
                if (key === 'password-policy' && !passwordPolicy) loadPasswordPolicy();
              }}
            />
          </Card>
        </Col>

        <Col span={8}>
          <Card title="用量概览" loading={loading}>
            <Row gutter={[16, 16]}>
              <Col span={12}>
                <Statistic
                  title="门店数"
                  value={usage?.totalStores || 0}
                  suffix={`/ ${usage?.maxStores || '无限制'}`}
                />
              </Col>
              <Col span={12}>
                <Statistic
                  title="管理员数"
                  value={usage?.totalAdmins || 0}
                  suffix={`/ ${usage?.maxAdmins || '无限制'}`}
                />
              </Col>
              <Col span={12}>
                <Statistic
                  title="医生数"
                  value={usage?.totalDoctors || 0}
                  suffix={`/ ${usage?.maxDoctors || '无限制'}`}
                />
              </Col>
              <Col span={12}>
                <Statistic
                  title="本月预约"
                  value={usage?.monthAppointmentCount || 0}
                  suffix={`/ ${usage?.maxAppointmentsPerMonth || '无限制'}`}
                />
              </Col>
              <Col span={12}>
                <Statistic
                  title="本月完成"
                  value={usage?.monthCompletedCount || 0}
                  styles={{ content: { color: '#3f8600' } }}
                />
              </Col>
              <Col span={12}>
                <Statistic
                  title="本月取消"
                  value={usage?.monthCancelledCount || 0}
                  styles={{ content: { color: 'var(--color-error-active)' } }}
                />
              </Col>
              <Col span={24}>
                <Statistic
                  title="存储空间"
                  value={usage?.storageUsedMb || 0}
                  precision={2}
                  suffix={`MB / ${usage?.maxStorageMb || '无限制'} MB`}
                />
              </Col>
            </Row>
          </Card>

          <Card title="配额限制" style={{ marginTop: 24 }} loading={loading}>
            <Descriptions column={1} size="small" items={[
              { key: '0', label: '最大门店数', children: tenant.maxStores || '使用计划默认值' },
              { key: '1', label: '最大管理员数', children: tenant.maxAdmins || '使用计划默认值' },
              { key: '2', label: '最大医生数', children: tenant.maxDoctors || '使用计划默认值' },
              { key: '3', label: '月预约上限', children: tenant.maxAppointmentsPerMonth || '使用计划默认值' },
            ]} />
          </Card>
        </Col>
      </Row>
    </PageContainer>
  );
};

export default TenantDetailPage;
