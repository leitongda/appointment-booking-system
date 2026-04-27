import { PageContainer, ProTable, ProColumns } from '@ant-design/pro-components';
import { Tag } from 'antd';
import { shiftTypeApi } from '@hospital/api';
import type { ShiftType } from '@hospital/shared';
import { createListRequest } from '@/utils/proTable';
import { useListPage } from '@/hooks/useListPage';
import { CreateButton, OperationButton, OperationGroup } from '@/components/ListOperations';

/**
 * 班次类型管理页面
 */
const ShiftTypeListPage: React.FC = () => {
  const { actionRef, message, handleDelete, reload } = useListPage({
    deleteFn: shiftTypeApi.delete,
  });

  const handleToggleStatus = async (record: ShiftType) => {
    try {
      await shiftTypeApi.update(record.id, {
        enabled: !record.enabled,
      });
      message.success('更新成功');
      reload();
    } catch (error: any) {
      message.error(error.message || '更新失败');
    }
  };

  const columns: ProColumns<ShiftType>[] = [
    {
      title: '类型代码',
      dataIndex: 'code',
      width: 150,
      fixed: 'left',
    },
    {
      title: '类型名称',
      dataIndex: 'name',
      width: 200,
    },
    {
      title: '描述',
      dataIndex: 'description',
      width: 300,
      ellipsis: true,
      search: false,
    },
    {
      title: '状态',
      dataIndex: 'enabled',
      width: 100,
      search: false,
      render: (_, record) => (
        <Tag color={record.enabled ? 'success' : 'default'}>
          {record.enabled ? '启用' : '禁用'}
        </Tag>
      ),
    },
    {
      title: '创建时间',
      dataIndex: 'createdAt',
      width: 180,
      search: false,
      valueType: 'dateTime',
    },
    {
      title: '操作',
      valueType: 'option',
      width: 200,
      fixed: 'right',
      render: (_, record) => (
        <OperationGroup>
          <OperationButton
            type="edit"
            url={`/organization/medical-config/shift-types/${record.id}/edit`}
          />
          <OperationButton
            type="custom"
            label={record.enabled ? '禁用' : '启用'}
            onClick={() => handleToggleStatus(record)}
          />
          <OperationButton
            type="delete"
            confirmText="确认删除"
            confirmDescription="删除后无法恢复，确定要删除吗？"
            onClick={() => handleDelete(record.id)}
          />
        </OperationGroup>
      ),
    },
  ];

  return (
    <PageContainer
      title="班次类型管理"
      content="管理系统中的班次类型，用于规则管理和排班管理"
    >
      <ProTable<ShiftType>
        actionRef={actionRef}
        rowKey="id"
        columns={columns}
        request={createListRequest(shiftTypeApi.getList, (params) => {
          const { code, name, ...rest } = params;
          return { ...rest, keyword: code || name };
        })}
        columnsState={{
          persistenceKey: 'shift-type-list-table',
          persistenceType: 'localStorage',
        }}
        rowClassName={(record) => (!record.enabled ? 'disabled-row' : '')}
        search={{
          labelWidth: 'auto',
        }}
        options={{
          density: false,
          fullScreen: false,
          reload: true,
          setting: true,
        }}
        pagination={{
          defaultPageSize: 10,
          showSizeChanger: true,
          showQuickJumper: true,
        }}
        dateFormatter="string"
        headerTitle="班次类型列表"
        toolBarRender={() => [
          <CreateButton
            key="create"
            url="/organization/medical-config/shift-types/create"
            label="新增班次类型"
          />,
        ]}
      />
    </PageContainer>
  );
};

export default ShiftTypeListPage;
