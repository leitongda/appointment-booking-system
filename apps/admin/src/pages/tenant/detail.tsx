import { PageContainer } from '@ant-design/pro-components';
import { Card, Descriptions, Tag, Statistic, Row, Col, Button, Space, Tabs, Table, message, Popconfirm } from 'antd';
import { history, useParams, useAccess } from '@umijs/max';
import { useEffect, useState } from 'react';
import { tenantApi } from '@hospital/api';
import type { Tenant, TenantUsageLog, TenantUsageSummary, TenantSubscription } from '@hospital/api';

const TENANT_STATUS_MAP: Record<number, { text: string; color: string }> = {
  0: { text: '已禁用', color: 'default' },
  1: { text: '正常', color: 'success' },
  2: { text: '已欠费', color: 'error' },
  3: { text: '试用中', color: 'warning' },
};

const TenantDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const access = useAccess();
  const [tenant, setTenant] = useState<Tenant | null>(null);
  const [usage, setUsage] = useState<TenantUsageSummary | null>(null);
  const [subscriptions, setSubscriptions] = useState<TenantSubscription[]>([]);
  const [usageLogs, setUsageLogs] = useState<TenantUsageLog[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadData();
  }, [id]);

  const loadData = async () => {
    setLoading(true);
    try {
      const [tenantRes, usageRes, subRes, usageLogRes] = await Promise.all([
        tenantApi.getTenant(id),
        tenantApi.getTenantUsage(id),
        tenantApi.getTenantSubscriptions(id, 10),
        tenantApi.getTenantUsageLogs(id, { limit: 30 }),
      ]);
      setTenant((tenantRes as any)?.data ?? tenantRes);
      setUsage((usageRes as any)?.data ?? usageRes);
      setSubscriptions((subRes as any)?.data ?? subRes ?? []);
      setUsageLogs((usageLogRes as any)?.data ?? usageLogRes ?? []);
    } catch (error) {
      message.error('加载租户信息失败');
      history.back();
    } finally {
      setLoading(false);
    }
  };

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

  if (!tenant) return null;

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
                    ]} />
                  ),
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
              ]}
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
                  styles={{ content: { color: '#cf1322' } }}
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
