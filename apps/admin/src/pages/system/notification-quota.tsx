import { PageContainer } from '@ant-design/pro-components';
import { Card, Row, Col, Statistic, Progress, Button, App, InputNumber, Space, Divider, Typography, Tag } from 'antd';
import { useRequest } from '@umijs/max';
import { notificationLogApi } from '@hospital/api';
import { useState, useCallback } from 'react';
import type { NotificationQuota, NotificationQuotaUpdate, UsageStats } from '@hospital/shared';

const CHANNEL_CONFIG: Record<string, { text: string; color: string; quotaKey: keyof NotificationQuotaUpdate }> = {
  sms: { text: '短信', color: 'blue', quotaKey: 'smsMonthlyLimit' },
  email: { text: '邮件', color: 'cyan', quotaKey: 'emailMonthlyLimit' },
  wechat: { text: '微信', color: 'purple', quotaKey: 'wechatMonthlyLimit' },
  in_app: { text: '站内信', color: 'green', quotaKey: 'inAppMonthlyLimit' },
};

const CHANNEL_COLORS: Record<string, string> = {
  blue: '#1677ff',
  cyan: '#13c2c2',
  green: '#52c41a',
  purple: '#722ed1',
};

const NotificationQuotaPage: React.FC = () => {
  const { message } = App.useApp();
  const [editing, setEditing] = useState(false);
  const [editValues, setEditValues] = useState<NotificationQuotaUpdate>({});
  const [saving, setSaving] = useState(false);

  const { data: quota, loading: quotaLoading, refresh: refreshQuota } = useRequest(
    () => notificationLogApi.getQuota(),
    {
      refreshDeps: [],
      onSuccess: (data: any) => {
        if (data?.quotas) {
          setEditValues({
            smsMonthlyLimit: data.quotas.smsMonthlyLimit,
            emailMonthlyLimit: data.quotas.emailMonthlyLimit,
            wechatMonthlyLimit: data.quotas.wechatMonthlyLimit,
            inAppMonthlyLimit: data.quotas.inAppMonthlyLimit,
          });
        }
      },
    },
  );

  const { data: usageData, loading: usageLoading } = useRequest(
    () => notificationLogApi.getUsageStats({ period: 'month' }),
    { refreshDeps: [] },
  );

  const quotaData = quota as NotificationQuota | undefined;
  const usage = usageData as UsageStats | undefined;

  const handleSave = useCallback(async () => {
    setSaving(true);
    try {
      await notificationLogApi.updateQuota(editValues);
      message.success('配额设置已更新');
      setEditing(false);
      refreshQuota();
    } catch (error: any) {
      message.error(error.message || '更新失败');
    } finally {
      setSaving(false);
    }
  }, [editValues, message, refreshQuota]);

  const handleCancel = useCallback(() => {
    setEditing(false);
    if (quotaData?.quotas) {
      setEditValues({
        smsMonthlyLimit: quotaData.quotas.smsMonthlyLimit,
        emailMonthlyLimit: quotaData.quotas.emailMonthlyLimit,
        wechatMonthlyLimit: quotaData.quotas.wechatMonthlyLimit,
        inAppMonthlyLimit: quotaData.quotas.inAppMonthlyLimit,
      });
    }
  }, [quotaData]);

  const channelEntries = usage?.byChannel ? Object.entries(usage.byChannel) : [];

  return (
    <PageContainer>
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={6}>
          <Card loading={quotaLoading}>
            <Statistic title="本期总发送" value={usage?.total || 0} />
          </Card>
        </Col>
        <Col span={6}>
          <Card loading={quotaLoading}>
            <Statistic title="统计周期" value={quotaData?.periodStart && quotaData?.periodEnd ? `${quotaData.periodStart} ~ ${quotaData.periodEnd}` : '-'} />
          </Card>
        </Col>
        <Col span={12}>
          <Card loading={usageLoading}>
            <Statistic title="按通道分布" value={channelEntries.length} suffix="种" />
            <Space style={{ marginTop: 8 }} wrap>
              {channelEntries.map(([ch, count]) => {
                const cfg = CHANNEL_CONFIG[ch];
                return cfg ? <Tag key={ch} color={cfg.color}>{cfg.text}: {count}</Tag> : null;
              })}
            </Space>
          </Card>
        </Col>
      </Row>

      <Row gutter={16}>
        <Col span={12}>
          <Card title="通道配额设置" extra={
            !editing ? (
              <Button type="link" onClick={() => setEditing(true)}>编辑</Button>
            ) : (
              <Space>
                <Button onClick={handleCancel}>取消</Button>
                <Button type="primary" loading={saving} onClick={handleSave}>保存</Button>
              </Space>
            )
          }>
            {Object.entries(CHANNEL_CONFIG).map(([key, cfg], index) => {
              const limit = quotaData?.quotas?.[cfg.quotaKey] as number | undefined;
              const used = quotaData?.usage?.[cfg.quotaKey] as number | undefined;
              const remaining = quotaData?.remaining?.[cfg.quotaKey] as number | undefined;
              const percent = (quotaData?.usagePercent?.[cfg.quotaKey] as number) || 0;

              return (
                <div key={key}>
                  {index > 0 && <Divider style={{ margin: '12px 0' }} />}
                  <div style={{ marginBottom: 8 }}>
                    <Space>
                      <Tag color={cfg.color}>{cfg.text}</Tag>
                      <Typography.Text strong>{cfg.text}月度配额</Typography.Text>
                    </Space>
                  </div>
                  {editing ? (
                    <InputNumber
                      min={0}
                      placeholder="留空表示不限制"
                      value={editValues[cfg.quotaKey]}
                      onChange={(v) => setEditValues(prev => ({ ...prev, [cfg.quotaKey]: v ?? undefined }))}
                      style={{ width: '100%' }}
                    />
                  ) : (
                    <>
                      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                        <Typography.Text type="secondary">
                          {limit ? `限额: ${limit}` : '未设置（不限制）'}
                        </Typography.Text>
                        {limit && (
                          <Typography.Text type="secondary">
                            已用: {used || 0} / 剩余: {remaining ?? limit}
                          </Typography.Text>
                        )}
                      </div>
                      {limit && (
                        <Progress
                          percent={Math.min(100, percent)}
                          size="small"
                          strokeColor={CHANNEL_COLORS[cfg.color]}
                          status={percent >= 90 ? 'exception' : 'active'}
                        />
                      )}
                    </>
                  )}
                </div>
              );
            })}
          </Card>
        </Col>
        <Col span={12}>
          <Card title="本月按通道分布" loading={usageLoading}>
            {channelEntries.length > 0 ? (
              <div>
                {channelEntries.map(([channel, count]) => {
                  const config = CHANNEL_CONFIG[channel] || { text: channel, color: 'default' };
                  const total = usage?.total || 1;
                  const percent = Math.round((count / total) * 100);
                  return (
                    <div key={channel} style={{ marginBottom: 12 }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                        <Space>
                          <Tag color={config.color}>{config.text}</Tag>
                          <Typography.Text>{count} 条</Typography.Text>
                        </Space>
                        <Typography.Text type="secondary">{percent}%</Typography.Text>
                      </div>
                      <Progress percent={percent} showInfo={false} strokeColor={CHANNEL_COLORS[config.color] || '#1677ff'} />
                    </div>
                  );
                })}
                <Divider />
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <Typography.Text strong>总计</Typography.Text>
                  <Typography.Text strong>{usage?.total || 0} 条</Typography.Text>
                </div>
              </div>
            ) : (
              <Typography.Text type="secondary">暂无数据</Typography.Text>
            )}
          </Card>
        </Col>
      </Row>

      {usage?.dailyTrend && usage.dailyTrend.length > 0 && (
        <Card title="本月每日发送趋势" style={{ marginTop: 16 }} loading={usageLoading}>
          <div style={{ display: 'flex', alignItems: 'flex-end', height: 120, gap: 2, overflow: 'auto' }}>
            {usage.dailyTrend.map((item) => {
              const maxCount = Math.max(...usage.dailyTrend.map(d => d.count), 1);
              const height = Math.max(4, (item.count / maxCount) * 100);
              return (
                <div
                  key={item.date}
                  style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', minWidth: 24 }}
                >
                  <Typography.Text style={{ fontSize: 10, marginBottom: 2 }}>{item.count}</Typography.Text>
                  <div
                    style={{
                      width: 16,
                      height,
                      background: '#1677ff',
                      borderRadius: '2px 2px 0 0',
                    }}
                  />
                  <Typography.Text style={{ fontSize: 9, marginTop: 2 }} type="secondary">
                    {item.date.slice(5)}
                  </Typography.Text>
                </div>
              );
            })}
          </div>
        </Card>
      )}
    </PageContainer>
  );
};

export default NotificationQuotaPage;
