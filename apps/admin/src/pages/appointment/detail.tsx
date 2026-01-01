import { PageContainer, ProDescriptions } from '@ant-design/pro-components';
import { Card, Tag, Button, Space, Spin, Timeline, Divider } from 'antd';
import { useEffect, useState } from 'react';
import { history, useParams } from '@umijs/max';
import { appointmentApi } from '@hospital/api';
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
  8: { text: '已关闭', color: 'default' },
};

const TIME_SLOT_MAP: Record<string, string> = {
  morning: '上午',
  afternoon: '下午',
  evening: '晚上',
};

const AppointmentDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const [loading, setLoading] = useState(true);
  const [appointment, setAppointment] = useState<Appointment | null>(null);

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

  const status = STATUS_MAP[appointment?.status ?? -1] || { text: '未知', color: 'default' };

  return (
    <PageContainer
      title="预约详情"
      extra={<Button onClick={() => history.push('/appointment/list')}>返回列表</Button>}
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
          </ProDescriptions>
        </Card>

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
              ...(appointment?.completedAt ? [{
                color: 'green',
                children: (
                  <div>
                    <strong>完成就诊</strong>
                    <p style={{ color: '#666', margin: 0 }}>{appointment.completedAt}</p>
                  </div>
                ),
              }] : []),
              ...(appointment?.cancelledAt ? [{
                color: 'red',
                children: (
                  <div>
                    <strong>已取消</strong>
                    <p style={{ color: '#666', margin: 0 }}>{appointment.cancelledAt}</p>
                    {appointment.cancelReason && <p style={{ color: '#999', margin: 0 }}>原因：{appointment.cancelReason}</p>}
                  </div>
                ),
              }] : []),
            ]}
          />
        </Card>
      </Spin>
    </PageContainer>
  );
};

export default AppointmentDetailPage;
