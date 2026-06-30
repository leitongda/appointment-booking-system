import { PageContainer, ProDescriptions } from '@ant-design/pro-components';
import { Card, Tag, Button, Space, Spin, Timeline, Divider, App, Popconfirm, Drawer, Form, InputNumber, Input, Table } from 'antd';
import { useEffect, useState } from 'react';
import type { ReactNode } from 'react';
import { history, useParams, useAccess } from '@umijs/max';
import { appointmentApi } from '@hospital/api';
import type { RefundRecord } from '@hospital/api';
import { REFUND_STATUS_MAP, REFUND_STATUS_COLOR, APPOINTMENT_STATUS_TAG, REFUNDABLE_APPOINTMENT_STATUSES, TIME_SLOT_MAP } from '@hospital/shared';
import type { Appointment } from '@hospital/shared';

const STATUS_MAP = APPOINTMENT_STATUS_TAG;

const AppointmentDetailPage: React.FC = () => {
  const { id } = useParams();
  const { message: antMessage } = App.useApp();
  const access = useAccess();
  const isSuperAdmin = access.canSuperAdmin;
  const [loading, setLoading] = useState(true);
  const [appointment, setAppointment] = useState<Appointment | null>(null);
  const [refundDrawerOpen, setRefundDrawerOpen] = useState(false);
  const [refundLoading, setRefundLoading] = useState(false);
  const [refundRecords, setRefundRecords] = useState<RefundRecord[]>([]);
  const [refundRecordsLoading, setRefundRecordsLoading] = useState(false);
  const [form] = Form.useForm();

  async function loadRefundRecords() {
    if (!id) return;
    setRefundRecordsLoading(true);
    try {
      const data = await appointmentApi.getRefundRecords(id);
      setRefundRecords(data);
    } catch (error) {
      console.error('加载退款记录失败', error);
    } finally {
      setRefundRecordsLoading(false);
    }
  }

  async function loadAppointment() {
    if (!id) return;
    setLoading(true);
    try {
      const data = await appointmentApi.getDetail(id);
      setAppointment(data);
      if (data.paymentAmount && data.paymentAmount > 0) {
        await loadRefundRecords();
      } else {
        setRefundRecords([]);
      }
    } catch (error) {
      console.error('加载失败', error);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (id) loadAppointment();
  }, [id]);

  const handleCancelSignIn = async () => {
    if (!id) return;
    try {
      await appointmentApi.cancelSignIn(id);
      antMessage.success('取消签到成功');
      loadAppointment();
    } catch (error: any) {
      antMessage.error(error.message || '操作失败');
    }
  };

  const handleOpenRefundDrawer = async () => {
    setRefundDrawerOpen(true);
    await loadRefundRecords();
  };

  const handleRefundSubmit = async () => {
    if (!id || !appointment) return;

    try {
      const values = await form.validateFields();
      setRefundLoading(true);

      await appointmentApi.createRefund({
        appointmentId: id,
        refundAmount: values.refundAmount,
        refundReason: values.refundReason,
      });

      antMessage.success('退款申请已提交');
      setRefundDrawerOpen(false);
      form.resetFields();
      loadAppointment();
    } catch (error: any) {
      if (error.errorFields) {
        // 表单验证错误
        return;
      }
      antMessage.error(error.message || '退款失败');
    } finally {
      setRefundLoading(false);
    }
  };

  const canRefund = Boolean(
    appointment &&
      appointment.paymentAmount &&
      appointment.paymentAmount > 0 &&
      REFUNDABLE_APPOINTMENT_STATUSES.has(appointment.status) &&
      appointment.refundStatus !== 'refunded'
  );

  const status = STATUS_MAP[appointment?.status ?? -1] || { text: '未知', color: 'default' };
  const isCompletedRefundException = appointment?.status === 5;
  const isPaymentTimeoutExpired =
    appointment?.status === 7 && appointment?.cancelReason === '支付超时自动取消';

  // 可退金额 = 原支付金额 - 已退款金额
  const maxRefundAmount = appointment?.paymentAmount && appointment?.refundedAmount
    ? appointment.paymentAmount - appointment.refundedAmount
    : (appointment?.paymentAmount ?? 0);
  const refundButtonLabel = isCompletedRefundException ? '例外完成退款' : '发起退款';

  const refundTimelineItems = [...refundRecords]
    .sort((left, right) => (left.createdAt || '').localeCompare(right.createdAt || ''))
    .flatMap((record) => {
      const isAutoRefund = (record.refundReason || '').includes('支付回调晚到');
      const amountText = `¥${Number(record.refundAmount || 0).toFixed(2)}`;
      const items: { color: string; children: ReactNode }[] = [
        {
          color: isAutoRefund ? 'gold' : 'orange',
          children: (
            <div>
              <strong>{isAutoRefund ? '自动退款触发' : '退款发起'}</strong>
              <p style={{ color: 'var(--color-text-secondary)', margin: 0 }}>{record.createdAt || '-'}</p>
              <p style={{ color: 'var(--color-text-tertiary)', margin: 0 }}>
                {isAutoRefund ? record.refundReason : `${amountText} / ${record.refundReason || '未填写原因'}`}
              </p>
            </div>
          ),
        },
      ];

      if (record.status === 'processing') {
        items.push({
          color: 'processing',
          children: (
            <div>
              <strong>退款处理中</strong>
              <p style={{ color: 'var(--color-text-secondary)', margin: 0 }}>{record.updatedAt || record.createdAt || '-'}</p>
              <p style={{ color: 'var(--color-text-tertiary)', margin: 0 }}>{record.refundNo}</p>
            </div>
          ),
        });
      }

      if (record.status === 'success') {
        items.push({
          color: 'green',
          children: (
            <div>
              <strong>退款成功</strong>
              <p style={{ color: 'var(--color-text-secondary)', margin: 0 }}>{record.updatedAt || record.createdAt || '-'}</p>
              <p style={{ color: 'var(--color-text-tertiary)', margin: 0 }}>{amountText}</p>
            </div>
          ),
        });
      }

      if (record.status === 'failed') {
        items.push({
          color: 'red',
          children: (
            <div>
              <strong>退款失败</strong>
              <p style={{ color: 'var(--color-text-secondary)', margin: 0 }}>{record.updatedAt || record.createdAt || '-'}</p>
              <p style={{ color: 'var(--color-text-tertiary)', margin: 0 }}>{record.failedReason || '请检查退款回调或微信返回信息'}</p>
            </div>
          ),
        });
      }

      return items;
    });

  const refundColumns = [
    {
      title: '退款单号',
      dataIndex: 'refundNo',
      key: 'refundNo',
      width: 180,
      render: (text: string) => <span style={{ fontFamily: 'monospace' }}>{text}</span>,
    },
    {
      title: '退款金额',
      dataIndex: 'refundAmount',
      key: 'refundAmount',
      width: 100,
      render: (amount: number) => `¥${Number(amount).toFixed(2)}`,
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status: string) => (
        <Tag color={REFUND_STATUS_COLOR[status] || 'default'}>
          {REFUND_STATUS_MAP[status] || status}
        </Tag>
      ),
    },
    {
      title: '原因',
      dataIndex: 'refundReason',
      key: 'refundReason',
      ellipsis: true,
    },
    {
      title: '创建时间',
      dataIndex: 'createdAt',
      key: 'createdAt',
      width: 180,
    },
  ];

  return (
    <PageContainer
      title="预约详情"
      extra={
        <Space>
          {appointment?.status === 2 && isSuperAdmin && (
            <Popconfirm
              title="确定取消签到吗？"
              description="状态将恢复为已预约"
              onConfirm={handleCancelSignIn}
            >
              <Button danger>取消签到</Button>
            </Popconfirm>
          )}
          {canRefund && access.hasPermission('appointment:refund') && (
            <Button type="primary" onClick={handleOpenRefundDrawer}>
              {refundButtonLabel}
            </Button>
          )}
          <Button onClick={() => history.push('/medical-services/appointment/list')}>返回列表</Button>
        </Space>
      }
    >
      <Spin spinning={loading}>
        <Card title="基本信息">
          <ProDescriptions column={2} columns={[
            { key: '0', title: '预约编号', dataIndex: 'appointmentNo', copyable: true },
            { key: '1', title: '当前状态', render: () => <Tag color={status.color}>{status.text}</Tag> },
            { key: '2', title: '患者姓名', render: () => <span data-rrweb-mask-text>{appointment?.patientName || '-'}</span> },
            { key: '3', title: '患者手机', render: () => <span data-rrweb-mask-text>{appointment?.patientPhone || '-'}</span> },
            { key: '4', title: '预约医生', dataIndex: 'doctorName' },
            { key: '5', title: '所属科室', dataIndex: 'departmentName' },
            { key: '6', title: '预约日期', dataIndex: 'scheduleDate' },
            { key: '7', title: '预约时段', render: () => TIME_SLOT_MAP[appointment?.timeSlot || ''] || '-' },
            { key: '8', title: '排队号码', render: () => appointment?.queueNumber || '-' },
            { key: '9', title: '门店名称', render: () => appointment?.storeName || '-' },
          ]} />
        </Card>

        {/* 支付信息 */}
        {appointment?.paymentAmount && appointment.paymentAmount > 0 && (
          <Card title="支付信息" style={{ marginTop: 16 }}>
            <ProDescriptions column={2} columns={[
              { key: '0', title: '支付金额', render: () => `¥${appointment.paymentAmount!.toFixed(2)}` },
              { key: '1', title: '支付时间', render: () => appointment.paymentTime || '-' },
              { key: '2', title: '交易单号', render: () => <span style={{ fontFamily: 'monospace' }}>{appointment.paymentTransactionId || '-'}</span> },
              { key: '3', title: '退款状态', render: () => (
                <>
                  {appointment.refundStatus && (
                    <Tag color={REFUND_STATUS_COLOR[appointment.refundStatus] || 'default'}>
                      {REFUND_STATUS_MAP[appointment.refundStatus] || appointment.refundStatus}
                    </Tag>
                  )}
                  {!appointment.refundStatus && '-'}
                </>
              ) },
              { key: '4', title: '已退款金额', render: () => appointment.refundedAmount ? `¥${appointment.refundedAmount.toFixed(2)}` : '-' },
            ]} />
          </Card>
        )}

        {/* 病情描述 */}
        {appointment?.symptomDescription && (
          <Card title="病情描述" style={{ marginTop: 16 }}>
            <div className="rrweb-block" style={{ margin: 0, whiteSpace: 'pre-wrap' }}>{appointment.symptomDescription}</div>
          </Card>
        )}

        {/* 签到方式 */}
        {appointment?.checkInMethod && (
          <Card title="签到信息" style={{ marginTop: 16 }}>
            <ProDescriptions column={2} columns={[
              { key: '0', title: '签到方式', render: () => (
                <>
                  {appointment.checkInMethod === 'QR_CODE' && <Tag color="blue">扫码签到</Tag>}
                  {appointment.checkInMethod === 'MANUAL' && <Tag color="green">手动签到</Tag>}
                  {appointment.checkInMethod === 'PHONE' && <Tag color="orange">电话签到</Tag>}
                  {!['QR_CODE', 'MANUAL', 'PHONE'].includes(appointment.checkInMethod || '') && appointment.checkInMethod}
                </>
              ) },
              { key: '1', title: '签到时间', render: () => appointment?.signInTime || '-' },
            ]} />
          </Card>
        )}

        {/* 退款记录 */}
        {appointment?.paymentAmount && appointment.paymentAmount > 0 && (
          <Card
            title="退款记录"
            extra={isCompletedRefundException ? <Tag color="warning">已完成例外退款</Tag> : undefined}
            style={{ marginTop: 16 }}
          >
            <Table
              columns={refundColumns}
              dataSource={refundRecords}
              rowKey="id"
              loading={refundRecordsLoading}
              pagination={false}
              size="small"
            />
          </Card>
        )}

        <Card title="时间线" style={{ marginTop: 16 }}>
          <Timeline
            items={[
              {
                color: 'green',
                children: (
                  <div>
                    <strong>创建预约</strong>
                    <p style={{ color: 'var(--color-text-secondary)', margin: 0 }}>{appointment?.createdAt}</p>
                  </div>
                ),
              },
              ...(appointment?.paymentTime ? [{
                color: 'orange',
                children: (
                  <div>
                    <strong>支付成功</strong>
                    <p style={{ color: 'var(--color-text-secondary)', margin: 0 }}>{appointment.paymentTime}</p>
                  </div>
                ),
              }] : []),
              ...(isPaymentTimeoutExpired ? [{
                color: 'red',
                children: (
                  <div>
                    <strong>支付超时</strong>
                    <p style={{ color: 'var(--color-text-secondary)', margin: 0 }}>{appointment?.cancelTime || '-'}</p>
                    <p style={{ color: 'var(--color-text-tertiary)', margin: 0 }}>系统自动过期并释放号源</p>
                  </div>
                ),
              }] : []),
              ...(appointment?.signInTime ? [{
                color: 'blue',
                children: (
                  <div>
                    <strong>签到</strong>
                    <p style={{ color: 'var(--color-text-secondary)', margin: 0 }}>{appointment.signInTime}</p>
                  </div>
                ),
              }] : []),
              ...(appointment?.callTime ? [{
                color: 'cyan',
                children: (
                  <div>
                    <strong>叫号</strong>
                    <p style={{ color: 'var(--color-text-secondary)', margin: 0 }}>{appointment.callTime}</p>
                  </div>
                ),
              }] : []),
              ...(appointment?.completeTime ? [{
                color: 'green',
                children: (
                  <div>
                    <strong>完成就诊</strong>
                    <p style={{ color: 'var(--color-text-secondary)', margin: 0 }}>{appointment.completeTime}</p>
                  </div>
                ),
              }] : []),
              ...refundTimelineItems,
              ...(appointment?.cancelTime && !isPaymentTimeoutExpired ? [{
                color: 'red',
                children: (
                  <div>
                    <strong>{appointment?.status === 7 ? '已过期' : '已取消'}</strong>
                    <p style={{ color: 'var(--color-text-secondary)', margin: 0 }}>{appointment.cancelTime}</p>
                    {appointment.cancelReason && <p style={{ color: 'var(--color-text-tertiary)', margin: 0 }}>原因：{appointment.cancelReason}</p>}
                  </div>
                ),
              }] : []),
            ]}
          />
        </Card>
      </Spin>

      {/* 退款抽屉 */}
      <Drawer
        title={refundButtonLabel}
        open={refundDrawerOpen}
        onClose={() => setRefundDrawerOpen(false)}
        width={480}
        footer={
          <Space style={{ textAlign: 'right', width: '100%' }}>
            <Button onClick={() => setRefundDrawerOpen(false)}>取消</Button>
            <Popconfirm
              title="确认退款"
              description={`确认退回 ¥${form.getFieldValue('refundAmount') || maxRefundAmount.toFixed(2)}？`}
              onConfirm={handleRefundSubmit}
              okText="确认退款"
              cancelText="取消"
            >
              <Button type="primary" loading={refundLoading}>
                确认退款
              </Button>
            </Popconfirm>
          </Space>
        }
      >
        <Form form={form} layout="vertical">
          <ProDescriptions column={1} style={{ marginBottom: 16 }} columns={[
            { key: '0', title: '预约编号', render: () => appointment?.appointmentNo },
            { key: '1', title: '患者姓名', render: () => <span data-rrweb-mask-text>{appointment?.patientName || '-'}</span> },
            { key: '2', title: '退款模式', render: () => (
              isCompletedRefundException ? (
                <Tag color="warning">已完成例外退款</Tag>
              ) : (
                <Tag color="blue">常规退款</Tag>
              )
            ) },
            { key: '3', title: '原支付金额', render: () => `¥${(appointment?.paymentAmount ?? 0).toFixed(2)}` },
            { key: '4', title: '已退款金额', render: () => `¥${(appointment?.refundedAmount ?? 0).toFixed(2)}` },
            { key: '5', title: '可退金额', render: () => (
              <span style={{ color: 'var(--color-error)', fontWeight: 'bold' }}>
                ¥{maxRefundAmount.toFixed(2)}
              </span>
            ) },
          ]} />

          <Divider />

          <Form.Item
            label="退款金额（元）"
            name="refundAmount"
            initialValue={maxRefundAmount}
            rules={[
              { required: true, message: '请输入退款金额' },
              {
                type: 'number',
                min: 0.01,
                max: maxRefundAmount,
                message: `退款金额必须在 0.01 ~ ${maxRefundAmount.toFixed(2)} 之间`,
              },
            ]}
          >
            <InputNumber
              style={{ width: '100%' }}
              precision={2}
              min={0.01}
              max={maxRefundAmount}
              placeholder="请输入退款金额"
            />
          </Form.Item>

          <Form.Item
            label="退款原因"
            name="refundReason"
            rules={[{ required: true, message: '请输入退款原因' }]}
            extra={isCompletedRefundException ? '已完成就诊退款属于例外操作，必须保留明确原因。' : undefined}
          >
            <Input.TextArea
              rows={4}
              maxLength={200}
              showCount
              placeholder="请输入退款原因"
            />
          </Form.Item>
        </Form>
      </Drawer>
    </PageContainer>
  );
};

export default AppointmentDetailPage;
