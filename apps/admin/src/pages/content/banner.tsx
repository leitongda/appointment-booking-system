import { PageContainer, ProTable } from '@ant-design/pro-components';
import type { ProColumns } from '@ant-design/pro-components';
import { Button, Tag, Space, Image } from 'antd';
import { PlusOutlined } from '@ant-design/icons';

interface BannerRecord {
  id: string;
  title: string;
  imageUrl: string;
  linkUrl: string;
  sortOrder: number;
  status: number;
}

const BannerPage: React.FC = () => {
  const columns: ProColumns<BannerRecord>[] = [
    { title: '图片', dataIndex: 'imageUrl', width: 150, search: false, render: (_, r) => <Image width={120} src={r.imageUrl} /> },
    { title: '标题', dataIndex: 'title', width: 200 },
    { title: '跳转链接', dataIndex: 'linkUrl', width: 200, ellipsis: true, search: false },
    { title: '排序', dataIndex: 'sortOrder', width: 80, search: false },
    { title: '状态', dataIndex: 'status', width: 80, valueEnum: { 0: { text: '禁用' }, 1: { text: '启用', status: 'Success' } } },
    { title: '操作', valueType: 'option', width: 150, render: () => <Space><a>编辑</a><a>删除</a></Space> },
  ];

  return (
    <PageContainer>
      <ProTable<BannerRecord>
        rowKey="id"
        columns={columns}
        search={false}
        toolBarRender={() => [<Button key="add" type="primary" icon={<PlusOutlined />}>新增轮播图</Button>]}
        request={async () => ({ data: [], success: true, total: 0 })}
      />
    </PageContainer>
  );
};

export default BannerPage;

