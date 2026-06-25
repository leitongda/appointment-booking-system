import { PageContainer, ProTable, ProColumns } from '@ant-design/pro-components';
import { Tag } from 'antd';
import { attendanceApi } from '@hospital/api';
import type { AttendanceShift } from '@hospital/api';
import { createListRequest } from '@/utils/proTable';
import { useListPage } from '@/hooks/useListPage';
import { CreateButton, OperationButton, OperationGroup } from '@/components/ListOperations';

/**
 * 班次管理列表页
 */
const ShiftListPage: React.FC = () => {
  const { actionRef, handleDelete } = useListPage({
    deleteFn: attendanceApi.deleteShift,
  });

  const columns: ProColumns<AttendanceShift>[] = [
    {
      title: '班次名称',
      dataIndex: 'name',
      width: 150,
      fixed: 'left',
    },
    {
      title: '关键词',
      dataIndex: 'keyword',
      hideInTable: true,
      fieldProps: {
        placeholder: '搜索班次名称/编码',
      },
      search: {
        transform: (value: string) => ({ keyword: value }),
      },
    },
    {
      title: '班次编码',
      dataIndex: 'code',
      width: 120,
      search: false,
    },
    {
      title: '上班时间',
      dataIndex: 'startTime',
      width: 100,
      search: false,
    },
    {
      title: '下班时间',
      dataIndex: 'endTime',
      width: 100,
      search: false,
    },
    {
      title: '午休开始',
      dataIndex: 'breakStart',
      width: 100,
      search: false,
      render: (_, record) => record.breakStart || '-',
    },
    {
      title: '午休结束',
      dataIndex: 'breakEnd',
      width: 100,
      search: false,
      render: (_, record) => record.breakEnd || '-',
    },
    {
      title: '宽限(分)',
      dataIndex: 'graceMinutes',
      width: 90,
      search: false,
    },
    {
      title: '弹性',
      dataIndex: 'isFlexible',
      width: 80,
      search: false,
      render: (_, record) => (
        <Tag color={record.isFlexible ? 'blue' : 'default'}>
          {record.isFlexible ? '是' : '否'}
        </Tag>
      ),
    },
    {
      title: '状态',
      dataIndex: 'enabled',
      width: 80,
      search: false,
      render: (_, record) => (
        <Tag color={record.enabled ? 'success' : 'default'}>
          {record.enabled ? '启用' : '禁用'}
        </Tag>
      ),
    },
    {
      title: '操作',
      valueType: 'option',
      width: 160,
      fixed: 'right',
      render: (_, record) => (
        <OperationGroup>
          <OperationButton
            type="edit"
            url={`/attendance/shifts/${record.id}/edit`}
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
      title="班次管理"
      content="管理系统中的考勤班次，用于考勤规则和排班管理"
    >
      <ProTable<AttendanceShift>
        actionRef={actionRef}
        rowKey="id"
        columns={columns}
        request={createListRequest(attendanceApi.getShiftList)}
        columnsState={{
          persistenceKey: 'attendance-shift-list-table',
          persistenceType: 'localStorage',
        }}
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
        headerTitle="班次列表"
        toolBarRender={() => [
          <CreateButton
            key="create"
            url="/attendance/shifts/create"
            label="新增班次"
          />,
        ]}
      />
    </PageContainer>
  );
};

export default ShiftListPage;
