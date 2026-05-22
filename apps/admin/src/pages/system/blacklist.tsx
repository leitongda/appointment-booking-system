import { PlusOutlined, StopOutlined } from '@ant-design/icons';
import type { ActionType, ProColumns } from '@ant-design/pro-components';
import { PageContainer, ProTable, ModalForm, ProFormText, ProFormSelect, ProFormTextArea, ProFormDateTimePicker } from '@ant-design/pro-components';
import { App, Tag, Popconfirm, Button } from 'antd';
import { useRef, useState, useCallback, useMemo } from 'react';
import { useAccess, useModel } from '@umijs/max';
import { blacklistApi, storeApi } from '@hospital/api';
import type { BlacklistItem, BlacklistCreateData } from '@hospital/api';
import type { Store } from '@hospital/shared';
import { createListRequest } from '@/utils/proTable';
import { PAGINATION_CONFIG } from '@/constants/pagination';

const SOURCE_MAP: Record<number, string> = {
  1: '手动',
  2: '自动',
};

const STATUS_MAP: Record<number, { text: string; color: string }> = {
  1: { text: '生效中', color: 'error' },
  0: { text: '已解禁', color: 'default' },
};

const BlacklistPage: React.FC = () => {
  const { message } = App.useApp();
  const access = useAccess();
  const actionRef = useRef<ActionType>();
  const [addOpen, setAddOpen] = useState(false);

  const { initialState } = useModel('@@initialState');
  const userStores = initialState?.userStores || [];
  const isSuperAdmin = access.canSuperAdmin;
  const showStoreFilter = isSuperAdmin || userStores.length > 1;

  const handleRemove = useCallback(async (id: string) => {
    try {
      await blacklistApi.remove(id);
      message.success('解禁成功');
      actionRef.current?.reload();
    } catch (error: any) {
      message.error(error.message || '解禁失败');
    }
  }, [message]);

  const handleAdd = useCallback(async (values: BlacklistCreateData) => {
    try {
      await blacklistApi.add(values);
      message.success('添加成功');
      setAddOpen(false);
      actionRef.current?.reload();
      return true;
    } catch (error: any) {
      message.error(error.message || '添加失败');
      return false;
    }
  }, [message]);

  const columns = useMemo<ProColumns<BlacklistItem>[]>(() => [
    {
      title: '关键字',
      dataIndex: 'keyword',
      hideInTable: true,
      fieldProps: {
        placeholder: '姓名/手机号/身份证',
      },
    },
    ...(showStoreFilter
      ? [
          {
            title: '门店',
            dataIndex: 'storeId',
            hideInTable: true,
            valueType: 'select',
            request: async () => {
              try {
                const stores = await storeApi.getAll();
                let storeList = stores ?? [];
                if (!isSuperAdmin && userStores.length > 0) {
                  storeList = storeList.filter((s: Store) =>
                    userStores.some((us: { id: string }) => us.id === s.id)
                  );
                }
                return [
                  { label: '全部门店', value: '' },
                  ...storeList.map((s: Store) => ({ label: s.name, value: s.id })),
                ];
              } catch {
                return [];
              }
            },
          } as ProColumns<BlacklistItem>,
        ]
      : []),
    {
      title: '状态',
      dataIndex: 'status',
      hideInTable: true,
      valueType: 'select',
      valueEnum: {
        1: { text: '生效中' },
        0: { text: '已解禁' },
      },
    },
    // 表格列
    {
      title: '用户姓名',
      dataIndex: 'userName',
      width: 100,
      search: false,
      render: (_, record) => record.userName || record.keyword || '-',
    },
    {
      title: '手机号',
      dataIndex: 'userPhone',
      width: 120,
      search: false,
      render: (_, record) => record.userPhone || '-',
    },
    {
      title: '拉黑原因',
      dataIndex: 'reason',
      ellipsis: true,
      search: false,
      render: (val) => val || '-',
    },
    {
      title: '爽约次数',
      dataIndex: 'noShowCount',
      width: 80,
      search: false,
    },
    {
      title: '来源',
      dataIndex: 'source',
      width: 70,
      search: false,
      render: (_, record) => SOURCE_MAP[record.source] || '-',
    },
    {
      title: '到期时间',
      dataIndex: 'expireAt',
      width: 160,
      valueType: 'dateTime',
      search: false,
      render: (_, record) => {
        if (!record.expireAt) return '永久';
        return record.expireAt;
      },
    },
    {
      title: '状态',
      dataIndex: 'status',
      width: 80,
      search: false,
      render: (_, record) => {
        const info = STATUS_MAP[record.status] || { text: '未知', color: 'default' };
        return <Tag color={info.color}>{info.text}</Tag>;
      },
    },
    {
      title: '创建时间',
      dataIndex: 'createdAt',
      width: 160,
      valueType: 'dateTime',
      search: false,
    },
    {
      title: '操作',
      valueType: 'option',
      width: 80,
      fixed: 'right',
      render: (_, record) => {
        if (record.status === 0) return '-';
        return (
          <Popconfirm
            title="确定解禁该用户吗？"
            onConfirm={() => handleRemove(record.id)}
          >
            <a style={{ color: '#ff4d4f', fontSize: 13 }}>
              <StopOutlined /> 解禁
            </a>
          </Popconfirm>
        );
      },
    },
  ], [showStoreFilter, isSuperAdmin, userStores, handleRemove]);

  return (
    <PageContainer>
      <ProTable<BlacklistItem>
        headerTitle="黑名单管理"
        actionRef={actionRef}
        rowKey="id"
        columns={columns}
        request={createListRequest(blacklistApi.getList, ({ keyword, storeId, status, ...params }) => ({
          ...params,
          keyword: keyword || undefined,
          storeId: storeId || undefined,
          status: status !== undefined && status !== '' ? Number(status) : undefined,
        }))}
        toolBarRender={() => [
          access.hasPermission('blacklist:create') && (
            <Button
              key="add"
              type="primary"
              icon={<PlusOutlined />}
              onClick={() => setAddOpen(true)}
            >
              添加黑名单
            </Button>
          ),
        ]}
        pagination={{ defaultPageSize: PAGINATION_CONFIG.DEFAULT_PAGE_SIZE }}
      />

      <ModalForm
        title="添加黑名单"
        open={addOpen}
        onOpenChange={setAddOpen}
        onFinish={handleAdd}
        width={520}
        modalProps={{ destroyOnHidden: true }}
      >
        <ProFormText
          name="keyword"
          label="手机号/身份证"
          placeholder="请输入手机号或身份证号"
          rules={[{ required: true, message: '请输入手机号或身份证号' }]}
          extra="填写用户手机号或身份证号，用于识别拉黑对象"
        />
        <ProFormSelect
          name="storeId"
          label="拉黑门店"
          placeholder="请选择门店（可选）"
          request={async () => {
            try {
              const stores = await storeApi.getAll();
              return (stores ?? []).map((s: any) => ({
                label: s.name,
                value: s.id,
              }));
            } catch {
              return [];
            }
          }}
        />
        <ProFormTextArea
          name="reason"
          label="拉黑原因"
          placeholder="请输入拉黑原因"
          rules={[{ required: true, message: '请输入拉黑原因' }]}
        />
        <ProFormDateTimePicker
          name="expireAt"
          label="到期时间"
          placeholder="留空则永久拉黑"
          extra="不填到期时间表示永久拉黑"
        />
      </ModalForm>
    </PageContainer>
  );
};

export default BlacklistPage;
