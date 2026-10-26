/**
 * 知识库列表：全部可见 / 我的 / 共享给我 / 租户公共
 */
import type { ProColumns } from '@ant-design/pro-components';
import { ModalForm, PageContainer, ProFormRadio, ProFormText, ProFormTextArea, ProTable } from '@ant-design/pro-components';
import { Button, Result, Segmented, Space, Tag, Typography } from 'antd';
import { PlusOutlined, SearchOutlined, ShareAltOutlined } from '@ant-design/icons';
import { useState } from 'react';
import { history } from '@umijs/max';
import { knowledgeApi } from '@hospital/api';
import type { KnowledgeBase, KnowledgeBaseCreateData, KnowledgeBaseScope } from '@hospital/api';
import { createListRequest } from '@/utils/proTable';
import { useListPage } from '@/hooks/useListPage';
import { OperationButton, OperationGroup } from '@/components/ListOperations';
import { PAGINATION_CONFIG } from '@/constants/pagination';
import ShareModal from './components/ShareModal';
import { PERMISSION_MAP, VISIBILITY_MAP, isFeatureDisabled, isOwner } from './shared';

const SCOPE_OPTIONS: { label: string; value: KnowledgeBaseScope }[] = [
  { label: '全部可见', value: 'all' },
  { label: '我的', value: 'mine' },
  { label: '共享给我', value: 'shared' },
  { label: '租户公共', value: 'tenant' },
];

const KnowledgeBasesPage: React.FC = () => {
  const { actionRef, message, access, handleDelete, reload } = useListPage({
    deleteFn: knowledgeApi.deleteBase,
    deleteSuccessText: '知识库已删除',
  });
  const [scope, setScope] = useState<KnowledgeBaseScope>('all');
  const [createOpen, setCreateOpen] = useState(false);
  const [shareTarget, setShareTarget] = useState<KnowledgeBase | null>(null);
  const [featureDisabled, setFeatureDisabled] = useState(false);

  const request = createListRequest<KnowledgeBase>(
    async (params: { scope?: KnowledgeBaseScope; keyword?: string; page?: number; pageSize?: number }) => {
      try {
        return await knowledgeApi.listBases(params);
      } catch (error) {
        if (isFeatureDisabled(error)) {
          setFeatureDisabled(true);
          return { data: [], total: 0, page: 1, pageSize: params.pageSize ?? 10 };
        }
        throw error;
      }
    },
    ({ keyword, scope: scopeParam, ...rest }) => ({ ...rest, scope: scopeParam, keyword: keyword || undefined }),
  );

  const handleCreate = async (values: KnowledgeBaseCreateData) => {
    try {
      const kb = await knowledgeApi.createBase(values);
      message.success('知识库已创建');
      setCreateOpen(false);
      reload();
      history.push(`/knowledge/bases/${kb.id}`);
      return true;
    } catch (error: any) {
      message.error(error?.message || '创建失败');
      return false;
    }
  };

  const columns: ProColumns<KnowledgeBase>[] = [
    {
      title: '名称',
      dataIndex: 'keyword',
      render: (_, record) => (
        <a onClick={() => history.push(`/knowledge/bases/${record.id}`)} style={{ fontWeight: 500 }}>
          {record.name}
        </a>
      ),
      fieldProps: { placeholder: '按名称搜索' },
    },
    { title: '描述', dataIndex: 'description', ellipsis: true, search: false },
    {
      title: '可见性',
      dataIndex: 'visibility',
      width: 100,
      search: false,
      render: (_, record) => {
        const item = VISIBILITY_MAP[record.visibility];
        return <Tag color={item.color}>{item.text}</Tag>;
      },
    },
    {
      title: '我的权限',
      dataIndex: 'myPermission',
      width: 100,
      search: false,
      render: (_, record) => {
        const item = record.myPermission ? PERMISSION_MAP[record.myPermission] : null;
        return item ? <Tag color={item.color}>{item.text}</Tag> : '-';
      },
    },
    { title: '文档数', dataIndex: 'docCount', width: 90, search: false },
    { title: '切片数', dataIndex: 'chunkCount', width: 90, search: false },
    { title: '创建时间', dataIndex: 'createdAt', valueType: 'dateTime', width: 160, search: false },
    {
      title: '操作',
      valueType: 'option',
      width: 200,
      fixed: 'right',
      render: (_, record) => (
        <OperationGroup>
          <OperationButton type="view" label="进入" onClick={() => history.push(`/knowledge/bases/${record.id}`)} />
          {isOwner(record.myPermission) ? (
            <OperationButton
              type="custom"
              permission="knowledge:share"
              icon={<ShareAltOutlined />}
              label="共享"
              onClick={() => setShareTarget(record)}
            />
          ) : null}
          {isOwner(record.myPermission) ? (
            <OperationButton
              type="delete"
              permission="knowledge:delete"
              confirmText="删除后该库的文档、切片与共享记录将一并清除，确定删除？"
              onClick={() => handleDelete(record.id)}
            />
          ) : null}
        </OperationGroup>
      ),
    },
  ];

  if (featureDisabled) {
    return (
      <PageContainer>
        <Result
          status="404"
          title="知识库功能未启用"
          subTitle="服务端 KB_ENABLED 未开启。请联系平台管理员在部署配置中开启后刷新页面。"
        />
      </PageContainer>
    );
  }

  return (
    <PageContainer
      extra={[
        <Button key="search" icon={<SearchOutlined />} onClick={() => history.push('/knowledge/search')}>
          智能检索
        </Button>,
        access.hasPermission('knowledge:create') ? (
          <Button key="create" type="primary" icon={<PlusOutlined />} onClick={() => setCreateOpen(true)}>
            新建知识库
          </Button>
        ) : null,
      ]}
    >
      <ProTable<KnowledgeBase>
        actionRef={actionRef}
        rowKey="id"
        columns={columns}
        params={{ scope }}
        request={request}
        pagination={{ defaultPageSize: PAGINATION_CONFIG.DEFAULT_PAGE_SIZE }}
        search={{ labelWidth: 'auto' }}
        scroll={{ x: 960 }}
        headerTitle={
          <Space>
            <Segmented options={SCOPE_OPTIONS} value={scope} onChange={(value) => setScope(value as KnowledgeBaseScope)} />
            <Typography.Text type="secondary">按意思检索制度、SOP、药品说明等资料</Typography.Text>
          </Space>
        }
      />

      <ModalForm<KnowledgeBaseCreateData>
        title="新建知识库"
        open={createOpen}
        onOpenChange={setCreateOpen}
        onFinish={handleCreate}
        modalProps={{ destroyOnHidden: true }}
        initialValues={{ visibility: 'private' }}
      >
        <ProFormText name="name" label="名称" rules={[{ required: true, message: '请输入名称' }, { max: 100 }]} />
        <ProFormTextArea name="description" label="描述" fieldProps={{ rows: 3, maxLength: 2000, showCount: true }} />
        <ProFormRadio.Group
          name="visibility"
          label="可见性"
          options={[
            { label: '私有（仅自己与被共享者）', value: 'private' },
            { label: '租户公共（本机构所有管理员只读）', value: 'tenant' },
          ]}
        />
      </ModalForm>

      <ShareModal kbId={shareTarget?.id ?? null} kbName={shareTarget?.name} onClose={() => setShareTarget(null)} />
    </PageContainer>
  );
};

export default KnowledgeBasesPage;
