import type { ProColumns } from '@ant-design/pro-components';
import { PageContainer, ProTable } from '@ant-design/pro-components';
import { Popconfirm } from 'antd';
import { CheckCircleOutlined, StopOutlined } from '@ant-design/icons';
import { platformAnnouncementApi } from '@hospital/api';
import type { PlatformAnnouncement } from '@hospital/api';
import { createListRequest } from '@/utils/proTable';
import { useListPage } from '@/hooks/useListPage';
import { CreateButton, createOperationColumn, OperationButton } from '@/components/ListOperations';

const PlatformAnnouncementPage: React.FC = () => {
  const { actionRef, handleDelete, handleAction } = useListPage({
    deleteFn: platformAnnouncementApi.delete,
  });

  const handlePublish = (id: string) => {
    handleAction(() => platformAnnouncementApi.publish(id), {
      successText: '发布成功',
      reloadOnSuccess: true,
    });
  };

  const handleRevoke = (id: string) => {
    handleAction(() => platformAnnouncementApi.revoke(id), {
      successText: '撤回成功',
      reloadOnSuccess: true,
    });
  };

  const columns: ProColumns<PlatformAnnouncement>[] = [
    { title: '标题', dataIndex: 'title', ellipsis: true },
    {
      title: '状态',
      dataIndex: 'status',
      width: 90,
      valueEnum: {
        draft: { text: '草稿', status: 'Default' },
        published: { text: '已发布', status: 'Success' },
        revoked: { text: '已撤回', status: 'Error' },
      },
    },
    {
      title: '优先级',
      dataIndex: 'priority',
      width: 80,
      valueEnum: {
        0: { text: '普通' },
        1: { text: '重要', status: 'Warning' },
        2: { text: '紧急', status: 'Error' },
      },
    },
    {
      title: '目标',
      dataIndex: 'targetType',
      width: 80,
      search: false,
      valueEnum: { all: '全部租户', specific: '指定租户' },
    },
    {
      title: '发布人',
      dataIndex: 'publisherName',
      width: 100,
      search: false,
      render: (_, r) => r.publisherName || '-',
    },
    {
      title: '阅读率',
      width: 90,
      search: false,
      render: (_, r) => (r.totalCount > 0 ? `${r.readCount}/${r.totalCount}` : '-'),
    },
    { title: '创建时间', dataIndex: 'createdAt', valueType: 'dateTime', width: 160, search: false },
    {
      title: '发布时间',
      dataIndex: 'publishAt',
      valueType: 'dateTime',
      width: 160,
      search: false,
      render: (_, r) => r.publishAt || '-',
    },
    createOperationColumn<PlatformAnnouncement>({
      width: 200,
      editUrl: (r) => `/platform/announcement/${r.id}/edit`,
      editPermission: 'platform-announcement:update',
      onDelete: handleDelete,
      deletePermission: 'platform-announcement:delete',
      canDelete: (r) => r.status !== 'published',
      extraButtons: (r) => (
        <>
          {r.status === 'draft' && (
            <Popconfirm title="确定发布该公告吗？" onConfirm={() => handlePublish(r.id)}>
              <OperationButton
                type="custom"
                permission="platform-announcement:publish"
                icon={<CheckCircleOutlined />}
                label="发布"
              />
            </Popconfirm>
          )}
          {r.status === 'published' && (
            <Popconfirm title="确定撤回该公告吗？" onConfirm={() => handleRevoke(r.id)}>
              <OperationButton
                type="custom"
                permission="platform-announcement:revoke"
                icon={<StopOutlined />}
                label="撤回"
              />
            </Popconfirm>
          )}
        </>
      ),
    }),
  ];

  return (
    <PageContainer>
      <ProTable<PlatformAnnouncement>
        headerTitle="平台公告列表"
        actionRef={actionRef}
        rowKey="id"
        columns={columns}
        request={createListRequest(platformAnnouncementApi.getList)}
        toolBarRender={() => [
          <CreateButton
            key="add"
            permission="platform-announcement:create"
            url="/platform/announcement/create"
            label="发布公告"
          />,
        ]}
        pagination={{ defaultPageSize: 10 }}
      />
    </PageContainer>
  );
};

export default PlatformAnnouncementPage;
