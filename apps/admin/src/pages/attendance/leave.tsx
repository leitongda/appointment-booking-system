import { PageContainer, ProTable, ProColumns } from '@ant-design/pro-components';
import { Tag } from 'antd';
import { attendanceApi } from '@hospital/api';
import { createListRequest } from '@/utils/proTable';
import { useListPage } from '@/hooks/useListPage';
import { CreateButton, OperationButton, OperationGroup } from '@/components/ListOperations';

interface LeaveType {
  id: string;
  name: string;
  code: string;
  paid: boolean;
  defaultDays: number;
  enabled: boolean;
  sortOrder: number;
  createdAt?: string;
}

/**
 * 假期类型管理列表页
 *
 * 功能：假期类型的增删改查（如年假、事假、病假等）
 * 后端：apps/server/app/modules/attendance_leave/router.py
 */
const LeaveTypeListPage: React.FC = () => {
  const { actionRef, handleDelete } = useListPage({
    deleteFn: attendanceApi.deleteLeaveType,
  });

  const columns: ProColumns<LeaveType>[] = [
    {
      title: '类型名称',
      dataIndex: 'name',
      width: 150,
      fixed: 'left',
    },
    {
      title: '关键词',
      dataIndex: 'keyword',
      hideInTable: true,
      fieldProps: { placeholder: '搜索类型名称' },
      search: { transform: (value: string) => ({ keyword: value }) },
    },
    {
      title: '类型编码',
      dataIndex: 'code',
      width: 120,
      search: false,
    },
    {
      title: '是否带薪',
      dataIndex: 'paid',
      width: 100,
      search: false,
      render: (_, record) => (
        <Tag color={record.paid ? 'green' : 'default'}>
          {record.paid ? '带薪' : '无薪'}
        </Tag>
      ),
    },
    {
      title: '默认天数',
      dataIndex: 'defaultDays',
      width: 100,
      search: false,
    },
    {
      title: '状态',
      dataIndex: 'enabled',
      width: 100,
      search: false,
      render: (_, record) => (
        <Tag color={record.enabled ? 'green' : 'default'}>
          {record.enabled ? '启用' : '禁用'}
        </Tag>
      ),
    },
    {
      title: '排序',
      dataIndex: 'sortOrder',
      width: 80,
      search: false,
    },
    {
      title: '创建时间',
      dataIndex: 'createdAt',
      width: 160,
      search: false,
      valueType: 'dateTime',
    },
    {
      title: '操作',
      width: 150,
      valueType: 'option',
      render: (_, record) => (
        <OperationGroup>
          <OperationButton type="edit" onClick={() => {}} />
          <OperationButton type="delete" onClick={() => handleDelete(record.id)} />
        </OperationGroup>
      ),
    },
  ];

  return (
    <PageContainer
      title="假期类型管理"
      content="配置各类假期类型（年假、事假、病假等），用于假期申请和余额管理"
    >
      <ProTable<LeaveType>
        columns={columns}
        actionRef={actionRef}
        rowKey="id"
        request={createListRequest(attendanceApi.getLeaveTypeList)}
        columnsState={{ persistenceKey: 'attendance-leave-types', persistenceType: 'localStorage' }}
        search={{ labelWidth: 'auto' }}
        pagination={{ defaultPageSize: 10, showSizeChanger: true, showQuickJumper: true }}
        toolBarRender={() => [
          <CreateButton key="create" onClick={() => {}} />,
        ]}
      />
    </PageContainer>
  );
};

export default LeaveTypeListPage;
