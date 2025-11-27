import { PageContainer, ProCard } from '@ant-design/pro-components';
import { Calendar, Badge, Tag, Button, Modal, message } from 'antd';
import type { Dayjs } from 'dayjs';
import { TIME_SLOT_MAP } from '@hospital/shared';

const mockSchedules: Record<string, { timeSlot: string; total: number; booked: number }[]> = {
  '2024-11-28': [{ timeSlot: 'AM', total: 20, booked: 5 }],
  '2024-11-29': [{ timeSlot: 'AM', total: 20, booked: 10 }, { timeSlot: 'PM', total: 15, booked: 8 }],
};

const SchedulePage: React.FC = () => {
  const dateCellRender = (date: Dayjs) => {
    const dateStr = date.format('YYYY-MM-DD');
    const schedules = mockSchedules[dateStr];
    if (!schedules) return null;
    return (
      <ul style={{ listStyle: 'none', padding: 0, margin: 0 }}>
        {schedules.map((s) => (
          <li key={s.timeSlot}>
            <Badge status={s.booked < s.total ? 'success' : 'default'} text={`${TIME_SLOT_MAP[s.timeSlot]} ${s.booked}/${s.total}`} />
          </li>
        ))}
      </ul>
    );
  };

  const handleSuspend = () => {
    Modal.confirm({
      title: '申请停诊',
      content: '确定要申请停诊吗？已预约的患者将收到通知。',
      onOk: () => message.success('停诊申请已提交'),
    });
  };

  return (
    <PageContainer extra={<Button danger onClick={handleSuspend}>申请停诊</Button>}>
      <ProCard>
        <Calendar cellRender={(date) => dateCellRender(date)} />
      </ProCard>
    </PageContainer>
  );
};

export default SchedulePage;

