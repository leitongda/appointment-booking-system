import { PlusOutlined } from '@ant-design/icons';
import type { ActionType, ProColumns } from '@ant-design/pro-components';
import { PageContainer, ProTable } from '@ant-design/pro-components';
import { Button, App, Popconfirm, Space } from 'antd';
import { useRef } from 'react';
import { history, useAccess } from '@umijs/max';
import { consultationFeeTypeApi } from '@hospital/api';
import type { ConsultationFeeType } from '@hospital/shared';

const ConsultationFeeTypesPage: React.FC = () => {
  const { message } = App.useApp();
  const access = useAccess();
  const actionRef = useRef<ActionType>();

  const handleDelete = async (id: string) => {
    try {
      await consultationFeeTypeApi.delete(id);
      message.success('删除成功');
      actionRef.current?.reload();
    } catch (error: any) {
      message.error(error.message || '删除失败');
    }
  };

  const columns: ProColumns<ConsultationFeeType>[] = [
    {
      title: '类型名称',
      dataIndex: 'name',
      ellipsis: true,
    },
    {
      title: '类型编码',
      dataIndex: 'code',
      ellipsis: true,
      search: false,
    },
    {
      title: '描述',
      dataIndex: 'description',
      ellipsis: true,
      search: false,
    },
    {
      title: '排序',
      dataIndex: 'sortOrder',
      width: 80,
      search: false,
    },
    {
      title: '状态',
      dataIndex: 'status',
      width: 80,
      valueType: 'select',
      valueEnum: {
        1: { text: '启用', status: 'Success' },
        0: { text: '禁用', status: 'Default' },
      },
    },
    {
      title: '创建时间',
      dataIndex: 'createdAt',
      valueType: 'dateTime',
      width: 160,
      search: false,
    },
    {
      title: '操作',
      valueType: 'option',
      width: 120,
      render: (_, record) => (
        <Space>
          {access.hasPermission('system:consultation-fee') && (
            <a onClick={() => history.push(`/system/consultation-fee-types/${record.id}/edit`)}>
              编辑
            </a>
          )}
          {access.hasPermission('system:consultation-fee') && (
            <Popconfirm
              title="确定删除该诊费类型吗？"
              description="删除后相关诊费配置也会受影响"
              onConfirm={() => handleDelete(record.id)}
            >
              <a style={{ color: '#ff4d4f' }}>删除</a>
            </Popconfirm>
          )}
        </Space>
      ),
    },
  ];

  return (
    <PageContainer>
      <ProTable<ConsultationFeeType>
        headerTitle="诊费类型列表"
        actionRef={actionRef}
        rowKey="id"
        columns={columns}
        search={false}
        request={async (params) => {
          const list = await consultationFeeTypeApi.getList({ status: params.status });
          return {
            data: list,
            success: true,
            total: list.length,
          };
        }}
        toolBarRender={() => [
          access.hasPermission('system:consultation-fee') && (
            <Button
              key="add"
              type="primary"
              icon={<PlusOutlined />}
              onClick={() => history.push('/system/consultation-fee-types/create')}
            >
              新增诊费类型
            </Button>
          ),
        ]}
        pagination={false}
      />
    </PageContainer>
  );
};

export default ConsultationFeeTypesPage;
