import { PageContainer } from '@ant-design/pro-components';
import { Card, Descriptions, Tag, Input, Button, App, Empty, Spin } from 'antd';
import { SearchOutlined } from '@ant-design/icons';
import { useState } from 'react';
import { paymentApi } from '@hospital/api';
import type { PaymentOrderStatus } from '@hospital/api';

const STATUS_MAP: Record<number, { text: string; color: string }> = {
  0: { text: '待支付', color: 'orange' },
  1: { text: '已预约', color: 'blue' },
  2: { text: '已签到', color: 'cyan' },
  3: { text: '历史候诊', color: 'default' },
  4: { text: '就诊中', color: 'processing' },
  5: { text: '已完成', color: 'green' },
  6: { text: '已取消', color: 'default' },
  7: { text: '已过期', color: 'default' },
  8: { text: '已爽约', color: 'red' },
};

const REFUND_STATUS_MAP: Record<string, { text: string; color: string }> = {
  none: { text: '无退款', color: 'default' },
  refunding: { text: '退款中', color: 'orange' },
  refunded: { text: '已退款', color: 'green' },
  refund_failed: { text: '退款失败', color: 'red' },
};

const PaymentPage: React.FC = () => {
  const { message } = App.useApp();
  const [loading, setLoading] = useState(false);
  const [appointmentId, setAppointmentId] = useState('');
  const [paymentInfo, setPaymentInfo] = useState<PaymentOrderStatus | null>(null);

  const handleSearch = async () => {
    const id = appointmentId.trim();
    if (!id) {
      message.warning('请输入预约ID');
      return;
    }
    setLoading(true);
    try {
      const data = await paymentApi.getOrderStatus(id);
      setPaymentInfo(data);
    } catch (error: any) {
      message.error(error.message || '查询失败');
      setPaymentInfo(null);
    } finally {
      setLoading(false);
    }
  };

  const statusInfo = paymentInfo ? STATUS_MAP[paymentInfo.status] : null;
  const refundInfo = paymentInfo?.refund_status ? REFUND_STATUS_MAP[paymentInfo.refund_status] : null;

  return (
    <PageContainer>
      <Card style={{ marginBottom: 16 }}>
        <Input.Search
          placeholder="请输入预约ID查询支付状态"
          value={appointmentId}
          onChange={(e) => setAppointmentId(e.target.value)}
          onSearch={handleSearch}
          enterButton={<Button type="primary" icon={<SearchOutlined />}>查询</Button>}
          style={{ maxWidth: 500 }}
        />
      </Card>

      <Spin spinning={loading}>
        {paymentInfo ? (
          <Card title="支付信息">
            <Descriptions column={2} bordered size="middle">
              <Descriptions.Item label="预约ID">
                {paymentInfo.appointment_id}
              </Descriptions.Item>
              <Descriptions.Item label="预约状态">
                {statusInfo ? <Tag color={statusInfo.color}>{statusInfo.text}</Tag> : '未知'}
              </Descriptions.Item>
              <Descriptions.Item label="支付金额">
                {paymentInfo.payment_amount > 0
                  ? `¥${paymentInfo.payment_amount.toFixed(2)}`
                  : '-'}
              </Descriptions.Item>
              <Descriptions.Item label="支付交易号">
                {paymentInfo.payment_transaction_id || '-'}
              </Descriptions.Item>
              <Descriptions.Item label="支付时间">
                {paymentInfo.paid_at || '-'}
              </Descriptions.Item>
              <Descriptions.Item label="退款状态">
                {refundInfo ? <Tag color={refundInfo.color}>{refundInfo.text}</Tag> : '-'}
              </Descriptions.Item>
              <Descriptions.Item label="退款金额">
                {paymentInfo.refund_amount > 0
                  ? `¥${paymentInfo.refund_amount.toFixed(2)}`
                  : '-'}
              </Descriptions.Item>
            </Descriptions>
          </Card>
        ) : (
          <Card>
            <Empty description="请输入预约ID查询支付状态" />
          </Card>
        )}
      </Spin>
    </PageContainer>
  );
};

export default PaymentPage;
