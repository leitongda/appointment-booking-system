import { PageContainer, ProTable } from '@ant-design/pro-components';
import type { ProColumns, ActionType } from '@ant-design/pro-components';
import { Space, Tag } from 'antd';
import { useRef } from 'react';
import { history } from 'umi';
import type { Appointment } from '@hospital/shared';
import { APPOINTMENT_STATUS_MAP, APPOINTMENT_STATUS_COLOR, TIME_SLOT_MAP } from '@hospital/shared';

const AppointmentListPage: React.FC = () => {
  const actionRef = useRef<ActionType>();

  const columns: ProColumns<Appointment>[] = [
    {
      title: '预约单号',
      dataIndex: 'appointmentNo',
      width: 150,
      copyable: true,
    },
    {
      title: '就诊人',
      dataIndex: ['patient', 'name'],
      width: 100,
    },
    {
      title: '医生',
      dataIndex: ['doctor', 'name'],
      width: 100,
    },
    {
      title: '预约日期',
      dataIndex: 'appointmentDate',
      width: 120,
      valueType: 'date',
    },
    {
      title: '时段',
      dataIndex: 'timeSlot',
      width: 80,
      render: (_, record) => TIME_SLOT_MAP[record.timeSlot] || record.timeSlot,
    },
    {
      title: '队列号',
      dataIndex: 'queueNumber',
      width: 80,
      search: false,
    },
    {
      title: '挂号费',
      dataIndex: 'fee',
      width: 100,
      search: false,
      render: (_, record) => record.fee ? `¥${record.fee}` : '-',
    },
    {
      title: '状态',
      dataIndex: 'status',
      width: 100,
      valueEnum: Object.entries(APPOINTMENT_STATUS_MAP).reduce(
        (acc, [key, value]) => ({
          ...acc,
          [key]: { text: value },
        }),
        {}
      ),
      render: (_, record) => (
        <Tag color={APPOINTMENT_STATUS_COLOR[record.status]}>
          {APPOINTMENT_STATUS_MAP[record.status]}
        </Tag>
      ),
    },
    {
      title: '预约时间',
      dataIndex: 'createdAt',
      width: 180,
      valueType: 'dateTime',
      search: false,
    },
    {
      title: '操作',
      valueType: 'option',
      width: 120,
      render: (_, record) => (
        <Space>
          <a onClick={() => history.push(`/appointment/${record.id}`)}>详情</a>
        </Space>
      ),
    },
  ];

  return (
    <PageContainer>
      <ProTable<Appointment>
        actionRef={actionRef}
        rowKey="id"
        columns={columns}
        search={{ labelWidth: 'auto' }}
        request={async (params) => {
          // TODO: 调用 API 获取数据
          return {
            data: [],
            success: true,
            total: 0,
          };
        }}
      />
    </PageContainer>
  );
};

export default AppointmentListPage;

