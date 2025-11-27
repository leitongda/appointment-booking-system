import { PageContainer, ProTable } from '@ant-design/pro-components';
import type { ProColumns } from '@ant-design/pro-components';
import { Button, Tag, Space, Image } from 'antd';
import { PlusOutlined } from '@ant-design/icons';

interface NewsRecord {
  id: string;
  title: string;
  typeName: string;
  coverImage: string;
  viewCount: number;
  isTop: boolean;
  status: number;
  publishTime: string;
}

const NewsPage: React.FC = () => {
  const columns: ProColumns<NewsRecord>[] = [
    { title: '封面', dataIndex: 'coverImage', width: 100, search: false, render: (_, r) => r.coverImage ? <Image width={60} src={r.coverImage} /> : '-' },
    { title: '标题', dataIndex: 'title', width: 250, ellipsis: true },
    { title: '分类', dataIndex: 'typeName', width: 100 },
    { title: '浏览量', dataIndex: 'viewCount', width: 80, search: false },
    { title: '置顶', dataIndex: 'isTop', width: 80, render: (_, r) => r.isTop ? <Tag color="red">是</Tag> : <Tag>否</Tag> },
    { title: '状态', dataIndex: 'status', width: 80, valueEnum: { 0: { text: '草稿' }, 1: { text: '已发布', status: 'Success' } } },
    { title: '发布时间', dataIndex: 'publishTime', width: 180, valueType: 'dateTime', search: false },
    { title: '操作', valueType: 'option', width: 150, render: () => <Space><a>编辑</a><a>删除</a></Space> },
  ];

  return (
    <PageContainer>
      <ProTable<NewsRecord>
        rowKey="id"
        columns={columns}
        toolBarRender={() => [<Button key="add" type="primary" icon={<PlusOutlined />}>新增新闻</Button>]}
        request={async () => ({ data: [], success: true, total: 0 })}
      />
    </PageContainer>
  );
};

export default NewsPage;

