import { PageContainer, ProCard } from '@ant-design/pro-components';
import { Table, Button, Tag, Space, message } from 'antd';
import { PlusOutlined } from '@ant-design/icons';
import { TIME_SLOT_MAP, WEEKDAY_MAP } from '@hospital/shared';

const ScheduleTemplatePage: React.FC = () => {
  const columns = [
    { title: '医生', dataIndex: 'doctorName', width: 120 },
    { title: '星期', dataIndex: 'weekday', width: 80, render: (v: number) => WEEKDAY_MAP[v] },
    { title: '时段', dataIndex: 'timeSlot', width: 80, render: (v: string) => TIME_SLOT_MAP[v] },
    { title: '时间', width: 150, render: (_: any, r: any) => `${r.startTime} - ${r.endTime}` },
    { title: '号源数', dataIndex: 'totalSlots', width: 80 },
    { title: '状态', dataIndex: 'status', width: 80, render: (v: number) => v === 1 ? <Tag color="green">启用</Tag> : <Tag>禁用</Tag> },
    { title: '操作', width: 120, render: () => <Space><a>编辑</a><a>删除</a></Space> },
  ];

  return (
    <PageContainer>
      <ProCard
        title="排班模板"
        extra={<Button type="primary" icon={<PlusOutlined />}>新增模板</Button>}
      >
        <Table columns={columns} dataSource={[]} rowKey="id" />
      </ProCard>
    </PageContainer>
  );
};

export default ScheduleTemplatePage;

