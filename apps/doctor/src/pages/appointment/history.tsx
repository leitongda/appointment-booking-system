import { PageContainer, ProTable } from '@ant-design/pro-components';
import type { ProColumns } from '@ant-design/pro-components';
import { Tag } from 'antd';
import { APPOINTMENT_STATUS_MAP, APPOINTMENT_STATUS_COLOR, TIME_SLOT_MAP } from '@hospital/shared';

interface AppointmentRecord {
  id: string;
  appointmentNo: string;
  patientName: string;
  appointmentDate: string;
  timeSlot: string;
  status: number;
}

const HistoryAppointmentPage: React.FC = () => {
  const columns: ProColumns<AppointmentRecord>[] = [
    { title: '预约单号', dataIndex: 'appointmentNo', width: 150 },
    { title: '患者姓名', dataIndex: 'patientName', width: 100 },
    { title: '预约日期', dataIndex: 'appointmentDate', width: 120, valueType: 'date' },
    { title: '时段', dataIndex: 'timeSlot', width: 80, render: (_, r) => TIME_SLOT_MAP[r.timeSlot] },
    { title: '状态', dataIndex: 'status', width: 100, render: (_, r) => <Tag color={APPOINTMENT_STATUS_COLOR[r.status]}>{APPOINTMENT_STATUS_MAP[r.status]}</Tag> },
    { title: '操作', width: 100, render: () => <a>查看</a> },
  ];

  return (
    <PageContainer>
      <ProTable<AppointmentRecord>
        rowKey="id"
        columns={columns}
        search={{ labelWidth: 'auto' }}
        request={async () => ({ data: [], success: true, total: 0 })}
      />
    </PageContainer>
  );
};

export default HistoryAppointmentPage;

