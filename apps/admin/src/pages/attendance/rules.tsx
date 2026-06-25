import { PageContainer, ProTable, ProColumns } from '@ant-design/pro-components';
import { Tag } from 'antd';
import { attendanceApi } from '@hospital/api';
import type { AttendanceRule } from '@hospital/api';
import { createListRequest } from '@/utils/proTable';
import { useListPage } from '@/hooks/useListPage';
import { CreateButton, OperationButton, OperationGroup } from '@/components/ListOperations';

/** 策略映射 */
const POLICY_MAP: Record<string, { text: string; color: string }> = {
  flexible: { text: '弹性', color: 'blue' },
  strict: { text: '严格', color: 'red' },
  ignore: { text: '忽略', color: 'default' },
};

/**
 * 考勤规则管理列表页
 */
const RuleListPage: React.FC = () => {
  const { actionRef, handleDelete } = useListPage({
    deleteFn: attendanceApi.deleteRule,
  });

  const columns: ProColumns<AttendanceRule>[] = [
    {
      title: '规则名称',
      dataIndex: 'name',
      width: 200,
      fixed: 'left',
    },
    {
      title: '关键词',
      dataIndex: 'keyword',
      hideInTable: true,
      fieldProps: {
        placeholder: '搜索规则名称',
      },
      search: {
        transform: (value: string) => ({ keyword: value }),
      },
    },
    {
      title: '迟到策略',
      dataIndex: 'latePolicy',
      width: 100,
      search: false,
      render: (_, record) => {
        const p = POLICY_MAP[record.latePolicy] || { text: record.latePolicy, color: 'default' };
        return <Tag color={p.color}>{p.text}</Tag>;
      },
    },
    {
      title: '早退策略',
      dataIndex: 'earlyPolicy',
      width: 100,
      search: false,
      render: (_, record) => {
        const p = POLICY_MAP[record.earlyPolicy] || { text: record.earlyPolicy, color: 'default' };
        return <Tag color={p.color}>{p.text}</Tag>;
      },
    },
    {
      title: '缺勤策略',
      dataIndex: 'absentPolicy',
      width: 100,
      search: false,
      render: (_, record) => {
        const p = POLICY_MAP[record.absentPolicy] || { text: record.absentPolicy, color: 'default' };
        return <Tag color={p.color}>{p.text}</Tag>;
      },
    },
    {
      title: '加班',
      dataIndex: 'overtimeEnabled',
      width: 80,
      search: false,
      render: (_, record) => (
        <Tag color={record.overtimeEnabled ? 'success' : 'default'}>
          {record.overtimeEnabled ? '开启' : '关闭'}
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
      title: '创建时间',
      dataIndex: 'createdAt',
      width: 180,
      search: false,
      valueType: 'dateTime',
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
            url={`/attendance/rules/${record.id}/edit`}
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
      title="考勤规则"
      content="管理考勤规则，配置迟到、早退、缺勤的处理策略"
    >
      <ProTable<AttendanceRule>
        actionRef={actionRef}
        rowKey="id"
        columns={columns}
        request={createListRequest(attendanceApi.getRuleList)}
        columnsState={{
          persistenceKey: 'attendance-rule-list-table',
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
        headerTitle="考勤规则列表"
        toolBarRender={() => [
          <CreateButton
            key="create"
            url="/attendance/rules/create"
            label="新增规则"
          />,
        ]}
      />
    </PageContainer>
  );
};

export default RuleListPage;
