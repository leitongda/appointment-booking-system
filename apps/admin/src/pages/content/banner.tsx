import { useMemo } from 'react';
import type { ProColumns } from '@ant-design/pro-components';
import { PageContainer, ProTable } from '@ant-design/pro-components';
import { Image } from 'antd';
import { contentApi } from '@hospital/api';
import { createListRequest } from '@/utils/proTable';
import { useListPage } from '@/hooks/useListPage';
import { useDict } from '@/hooks/useDict';
import { CreateButton, createOperationColumn } from '@/components/ListOperations';
import type { Banner } from '@hospital/api';

const BannerPage: React.FC = () => {
  const { actionRef, handleDelete } = useListPage({
    deleteFn: contentApi.deleteBanner,
  });
  const { options: positionOptions } = useDict('banner_position');
  const { options: linkTypeOptions } = useDict('banner_link_type');
  const positionEnum = useMemo(
    () => Object.fromEntries(positionOptions.map((o) => [o.value, o.label])),
    [positionOptions]
  );
  const linkTypeEnum = useMemo(
    () => Object.fromEntries(linkTypeOptions.map((o) => [Number(o.value), o.label])),
    [linkTypeOptions]
  );

  const columns: ProColumns<Banner>[] = [
    { title: '图片', dataIndex: 'imageUrl', width: 120, search: false, render: (_, r) => <Image src={r.imageUrl} width={100} /> },
    { title: '标题', dataIndex: 'title', ellipsis: true },
    { title: '位置', dataIndex: 'position', width: 100, valueEnum: positionEnum },
    { title: '链接类型', dataIndex: 'linkType', width: 100, search: false, valueEnum: linkTypeEnum },
    { title: '排序', dataIndex: 'sortOrder', width: 70, search: false },
    { title: '状态', dataIndex: 'status', width: 80, valueEnum: { 1: { text: '启用', status: 'Success' }, 0: { text: '禁用', status: 'Default' } } },
    createOperationColumn<Banner>({
      width: 120,
      editUrl: (r) => `/content-center/content/banner/${r.id}/edit`,
      editPermission: 'content:banner:update',
      onDelete: handleDelete,
      deletePermission: 'content:banner:delete',
      deleteConfirmText: '确定删除吗？',
    }),
  ];

  return (
    <PageContainer>
      <ProTable<Banner>
        headerTitle="轮播图列表"
        actionRef={actionRef}
        rowKey="id"
        columns={columns}
        request={createListRequest(contentApi.getBannerList)}
        toolBarRender={() => [
          <CreateButton
            key="add"
            permission="content:banner:create"
            url="/content-center/content/banner/create"
            label="新增轮播图"
          />,
        ]}
        pagination={{ defaultPageSize: 10 }}
      />
    </PageContainer>
  );
};

export default BannerPage;
