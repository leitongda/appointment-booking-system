import { PageContainer, ProTable } from '@ant-design/pro-components';
import type { ProColumns } from '@ant-design/pro-components';
import { Tag, Button, Space } from 'antd';
import { history } from 'umi';
import { APPOINTMENT_STATUS_MAP, APPOINTMENT_STATUS_COLOR, TIME_SLOT_MAP } from '@hospital/shared';

interface AppointmentRecord {
  id: string;
  appointmentNo: string;
  patientName: string;
  patientPhone: string;
  timeSlot: string;
  queueNumber: number;
  status: number;
  signInTime: string;
}

const TodayAppointmentPage: React.FC = () => {
  const columns: ProColumns<AppointmentRecord>[] = [
    { title: '队列号', dataIndex: 'queueNumber', width: 80, render: (_, r) => <Tag color="blue">第{r.queueNumber}号</Tag> },
    { title: '患者姓名', dataIndex: 'patientName', width: 100 },
    { title: '手机号', dataIndex: 'patientPhone', width: 130 },
    { title: '时段', dataIndex: 'timeSlot', width: 80, render: (_, r) => TIME_SLOT_MAP[r.timeSlot] },
    { title: '状态', dataIndex: 'status', width: 100, render: (_, r) => <Tag color={APPOINTMENT_STATUS_COLOR[r.status]}>{APPOINTMENT_STATUS_MAP[r.status]}</Tag> },
    { title: '签到时间', dataIndex: 'signInTime', width: 150 },
    { title: '操作', width: 180, render: (_, r) => (
      <Space>
        {r.status === 2 && <Button size="small" type="primary">呼叫</Button>}
        {r.status === 4 && <Button size="small" type="primary" onClick={() => history.push(`/medical-record/create?appointmentId=${r.id}`)}>填写病历</Button>}
      </Space>
    )},
  ];

  return (
    <PageContainer>
      <ProTable<AppointmentRecord>
        rowKey="id"
        columns={columns}
        search={false}
        request={async () => ({ data: [], success: true, total: 0 })}
      />
    </PageContainer>
  );
};

export default TodayAppointmentPage;

