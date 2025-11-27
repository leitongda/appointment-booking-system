import { PageContainer, ProTable } from '@ant-design/pro-components';
import type { ProColumns, ActionType } from '@ant-design/pro-components';
import { Button, Space, Tag, Progress } from 'antd';
import { PlusOutlined } from '@ant-design/icons';
import { useRef } from 'react';
import type { Schedule } from '@hospital/shared';
import { TIME_SLOT_MAP, SCHEDULE_STATUS_MAP } from '@hospital/shared';

const ScheduleListPage: React.FC = () => {
  const actionRef = useRef<ActionType>();

  const columns: ProColumns<Schedule>[] = [
    {
      title: '医生',
      dataIndex: ['doctor', 'name'],
      width: 120,
    },
    {
      title: '排班日期',
      dataIndex: 'scheduleDate',
      width: 120,
      valueType: 'date',
    },
    {
      title: '时段',
      dataIndex: 'timeSlot',
      width: 80,
      valueEnum: TIME_SLOT_MAP,
    },
    {
      title: '时间',
      width: 150,
      search: false,
      render: (_, record) => `${record.startTime} - ${record.endTime}`,
    },
    {
      title: '号源',
      width: 200,
      search: false,
      render: (_, record) => (
        <Space>
          <Progress
            percent={Math.round((record.bookedSlots / record.totalSlots) * 100)}
            size="small"
            style={{ width: 100 }}
          />
          <span>{record.bookedSlots}/{record.totalSlots}</span>
        </Space>
      ),
    },
    {
      title: '状态',
      dataIndex: 'status',
      width: 100,
      valueEnum: {
        0: { text: '停诊', status: 'Default' },
        1: { text: '正常', status: 'Success' },
        2: { text: '已满', status: 'Warning' },
      },
    },
    {
      title: '操作',
      valueType: 'option',
      width: 150,
      render: (_, record) => (
        <Space>
          <a>编辑</a>
          {record.status === 1 && <a style={{ color: 'red' }}>停诊</a>}
        </Space>
      ),
    },
  ];

  return (
    <PageContainer>
      <ProTable<Schedule>
        actionRef={actionRef}
        rowKey="id"
        columns={columns}
        search={{ labelWidth: 'auto' }}
        toolBarRender={() => [
          <Button key="add" type="primary" icon={<PlusOutlined />}>
            新增排班
          </Button>,
          <Button key="batch">批量排班</Button>,
        ]}
        request={async (params) => {
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

export default ScheduleListPage;

