import type { ProColumns } from '@ant-design/pro-components';
import { PageContainer, ProTable } from '@ant-design/pro-components';
import { Tag } from 'antd';
import { adminApi } from '@hospital/api';
import type { OperationLog } from '@hospital/api';

const LogPage: React.FC = () => {
  const columns: ProColumns<OperationLog>[] = [
    { title: '操作人', dataIndex: 'adminName', width: 100 },
    { title: '模块', dataIndex: 'module', width: 100 },
    { title: '操作', dataIndex: 'action', width: 100 },
    {
      title: '方法',
      dataIndex: 'method',
      width: 80,
      search: false,
      render: (val) => {
        const colors: Record<string, string> = { GET: 'blue', POST: 'green', PUT: 'orange', DELETE: 'red' };
        return <Tag color={colors[val as string] || 'default'}>{val}</Tag>;
      },
    },
    { title: '路径', dataIndex: 'path', ellipsis: true, search: false },
    { title: 'IP', dataIndex: 'ip', width: 130, search: false },
    { title: '耗时', dataIndex: 'duration', width: 80, search: false, render: (val) => `${val}ms` },
    { title: '时间', dataIndex: 'createdAt', valueType: 'dateTime', width: 160, search: false },
  ];

  return (
    <PageContainer>
      <ProTable<OperationLog>
        headerTitle="操作日志"
        rowKey="id"
        columns={columns}
        request={async (params) => {
          const { current, pageSize, ...rest } = params;
          const result = await adminApi.getLogs({ ...rest, page: current, pageSize });
          return { data: result.data, total: result.total, success: true };
        }}
        pagination={{ defaultPageSize: 20 }}
        search={{ labelWidth: 'auto' }}
      />
    </PageContainer>
  );
};

export default LogPage;
