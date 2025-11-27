import { PageContainer, ProTable } from '@ant-design/pro-components';
import type { ProColumns } from '@ant-design/pro-components';
import { Button, Tag, Space } from 'antd';
import { PlusOutlined } from '@ant-design/icons';

interface NoticeRecord {
  id: string;
  title: string;
  type: number;
  isTop: boolean;
  status: number;
  publishTime: string;
}

const NoticePage: React.FC = () => {
  const columns: ProColumns<NoticeRecord>[] = [
    { title: '标题', dataIndex: 'title', width: 300, ellipsis: true },
    { title: '类型', dataIndex: 'type', width: 100, valueEnum: { 1: '系统公告', 2: '停诊通知', 3: '活动通知' } },
    { title: '置顶', dataIndex: 'isTop', width: 80, render: (_, r) => r.isTop ? <Tag color="red">是</Tag> : <Tag>否</Tag> },
    { title: '状态', dataIndex: 'status', width: 80, valueEnum: { 0: { text: '草稿' }, 1: { text: '已发布', status: 'Success' } } },
    { title: '发布时间', dataIndex: 'publishTime', width: 180, valueType: 'dateTime', search: false },
    { title: '操作', valueType: 'option', width: 150, render: () => <Space><a>编辑</a><a>删除</a></Space> },
  ];

  return (
    <PageContainer>
      <ProTable<NoticeRecord>
        rowKey="id"
        columns={columns}
        toolBarRender={() => [<Button key="add" type="primary" icon={<PlusOutlined />}>新增公告</Button>]}
        request={async () => ({ data: [], success: true, total: 0 })}
      />
    </PageContainer>
  );
};

export default NoticePage;

