import { PageContainer, ProDescriptions } from '@ant-design/pro-components';
import { Card, Tag, Button, Space, Spin, Timeline, Divider, App, Popconfirm, Drawer, Form, InputNumber, Input, Table } from 'antd';
import { useEffect, useState } from 'react';
import { history, useParams, useAccess } from '@umijs/max';
import { appointmentApi } from '@hospital/api';
import { REFUND_STATUS_MAP, REFUND_STATUS_COLOR } from '@hospital/shared';
import type { Appointment } from '@hospital/shared';

const STATUS_MAP: Record<number, { text: string; color: string }> = {
  0: { text: '待支付', color: 'orange' },
  1: { text: '已预约', color: 'blue' },
  2: { text: '已签到', color: 'cyan' },
  3: { text: '候诊中', color: 'purple' },
  4: { text: '就诊中', color: 'processing' },
  5: { text: '已完成', color: 'green' },
  6: { text: '已取消', color: 'default' },
  7: { text: '已过期', color: 'default' },
  8: { text: '已爽约', color: 'red' },
};

const TIME_SLOT_MAP: Record<string, string> = {
  morning: '上午',
  afternoon: '下午',
  evening: '晚上',
};

interface RefundRecord {
  id: string;
  refundNo: string;
  refundAmount: number;
  status: string;
  refundReason: string;
  createdAt: string;
}

const AppointmentDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
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

  useEffect(() => {
    if (id) loadAppointment();
  }, [id]);

  const loadAppointment = async () => {
    if (!id) return;
    setLoading(true);
    try {
      const data = await appointmentApi.getDetail(id);
      setAppointment(data);
    } catch (error) {
      console.error('加载失败', error);
    } finally {
      setLoading(false);
    }
  };

  const loadRefundRecords = async () => {
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
  };

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

  const canRefund = appointment && appointment.paymentAmount && appointment.paymentAmount > 0 &&
    appointment.refundStatus !== 'refunded';

  const status = STATUS_MAP[appointment?.status ?? -1] || { text: '未知', color: 'default' };

  // 可退金额 = 原支付金额 - 已退款金额
  const maxRefundAmount = appointment?.paymentAmount && appointment?.refundedAmount
    ? appointment.paymentAmount - appointment.refundedAmount
    : (appointment?.paymentAmount ?? 0);

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
              发起退款
            </Button>
          )}
          <Button onClick={() => history.push('/medical-services/appointment/list')}>返回列表</Button>
        </Space>
      }
    >
      <Spin spinning={loading}>
        <Card title="基本信息">
          <ProDescriptions column={2}>
            <ProDescriptions.Item label="预约编号" copyable>{appointment?.appointmentNo}</ProDescriptions.Item>
            <ProDescriptions.Item label="当前状态">
              <Tag color={status.color}>{status.text}</Tag>
            </ProDescriptions.Item>
            <ProDescriptions.Item label="患者姓名">{appointment?.patientName}</ProDescriptions.Item>
            <ProDescriptions.Item label="患者手机">{appointment?.patientPhone || '-'}</ProDescriptions.Item>
            <ProDescriptions.Item label="预约医生">{appointment?.doctorName}</ProDescriptions.Item>
            <ProDescriptions.Item label="所属科室">{appointment?.departmentName}</ProDescriptions.Item>
            <ProDescriptions.Item label="预约日期">{appointment?.scheduleDate}</ProDescriptions.Item>
            <ProDescriptions.Item label="预约时段">{TIME_SLOT_MAP[appointment?.timeSlot || ''] || '-'}</ProDescriptions.Item>
            <ProDescriptions.Item label="排队号码">{appointment?.queueNumber || '-'}</ProDescriptions.Item>
            <ProDescriptions.Item label="门店名称">{appointment?.storeName || '-'}</ProDescriptions.Item>
          </ProDescriptions>
        </Card>

        {/* 支付信息 */}
        {appointment?.paymentAmount && appointment.paymentAmount > 0 && (
          <Card title="支付信息" style={{ marginTop: 16 }}>
            <ProDescriptions column={2}>
              <ProDescriptions.Item label="支付金额">
                ¥{appointment.paymentAmount.toFixed(2)}
              </ProDescriptions.Item>
              <ProDescriptions.Item label="支付时间">{appointment.paymentTime || '-'}</ProDescriptions.Item>
              <ProDescriptions.Item label="交易单号">
                <span style={{ fontFamily: 'monospace' }}>{appointment.paymentTransactionId || '-'}</span>
              </ProDescriptions.Item>
              <ProDescriptions.Item label="退款状态">
                {appointment.refundStatus && (
                  <Tag color={REFUND_STATUS_COLOR[appointment.refundStatus] || 'default'}>
                    {REFUND_STATUS_MAP[appointment.refundStatus] || appointment.refundStatus}
                  </Tag>
                )}
                {!appointment.refundStatus && '-'}
              </ProDescriptions.Item>
              <ProDescriptions.Item label="已退款金额">
                {appointment.refundedAmount ? `¥${appointment.refundedAmount.toFixed(2)}` : '-'}
              </ProDescriptions.Item>
            </ProDescriptions>
          </Card>
        )}

        {/* 病情描述 */}
        {appointment?.symptomDescription && (
          <Card title="病情描述" style={{ marginTop: 16 }}>
            <p style={{ margin: 0, whiteSpace: 'pre-wrap' }}>{appointment.symptomDescription}</p>
          </Card>
        )}

        {/* 签到方式 */}
        {appointment?.checkInMethod && (
          <Card title="签到信息" style={{ marginTop: 16 }}>
            <ProDescriptions column={2}>
              <ProDescriptions.Item label="签到方式">
                {appointment.checkInMethod === 'QR_CODE' && <Tag color="blue">扫码签到</Tag>}
                {appointment.checkInMethod === 'MANUAL' && <Tag color="green">手动签到</Tag>}
                {appointment.checkInMethod === 'PHONE' && <Tag color="orange">电话签到</Tag>}
                {!['QR_CODE', 'MANUAL', 'PHONE'].includes(appointment.checkInMethod) && appointment.checkInMethod}
              </ProDescriptions.Item>
              <ProDescriptions.Item label="签到时间">{appointment?.signInTime || '-'}</ProDescriptions.Item>
            </ProDescriptions>
          </Card>
        )}

        {/* 退款记录 */}
        {appointment?.paymentAmount && appointment.paymentAmount > 0 && (
          <Card title="退款记录" style={{ marginTop: 16 }}>
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
                    <p style={{ color: '#666', margin: 0 }}>{appointment?.createdAt}</p>
                  </div>
                ),
              },
              ...(appointment?.paymentTime ? [{
                color: 'orange',
                children: (
                  <div>
                    <strong>支付成功</strong>
                    <p style={{ color: '#666', margin: 0 }}>{appointment.paymentTime}</p>
                  </div>
                ),
              }] : []),
              ...(appointment?.signInTime ? [{
                color: 'blue',
                children: (
                  <div>
                    <strong>签到</strong>
                    <p style={{ color: '#666', margin: 0 }}>{appointment.signInTime}</p>
                  </div>
                ),
              }] : []),
              ...(appointment?.callTime ? [{
                color: 'cyan',
                children: (
                  <div>
                    <strong>叫号</strong>
                    <p style={{ color: '#666', margin: 0 }}>{appointment.callTime}</p>
                  </div>
                ),
              }] : []),
              ...(appointment?.completeTime ? [{
                color: 'green',
                children: (
                  <div>
                    <strong>完成就诊</strong>
                    <p style={{ color: '#666', margin: 0 }}>{appointment.completeTime}</p>
                  </div>
                ),
              }] : []),
              ...(appointment?.cancelTime ? [{
                color: 'red',
                children: (
                  <div>
                    <strong>已取消</strong>
                    <p style={{ color: '#666', margin: 0 }}>{appointment.cancelTime}</p>
                    {appointment.cancelReason && <p style={{ color: '#999', margin: 0 }}>原因：{appointment.cancelReason}</p>}
                  </div>
                ),
              }] : []),
            ]}
          />
        </Card>
      </Spin>

      {/* 退款抽屉 */}
      <Drawer
        title="发起退款"
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
          <ProDescriptions column={1} style={{ marginBottom: 16 }}>
            <ProDescriptions.Item label="预约编号">{appointment?.appointmentNo}</ProDescriptions.Item>
            <ProDescriptions.Item label="患者姓名">{appointment?.patientName}</ProDescriptions.Item>
            <ProDescriptions.Item label="原支付金额">
              ¥{(appointment?.paymentAmount ?? 0).toFixed(2)}
            </ProDescriptions.Item>
            <ProDescriptions.Item label="已退款金额">
              ¥{(appointment?.refundedAmount ?? 0).toFixed(2)}
            </ProDescriptions.Item>
            <ProDescriptions.Item label="可退金额">
              <span style={{ color: '#ff4d4f', fontWeight: 'bold' }}>
                ¥{maxRefundAmount.toFixed(2)}
              </span>
            </ProDescriptions.Item>
          </ProDescriptions>

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
