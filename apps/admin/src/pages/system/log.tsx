import { PageContainer, ProTable } from '@ant-design/pro-components';
import type { ProColumns } from '@ant-design/pro-components';

interface LogRecord {
  id: string;
  adminName: string;
  module: string;
  action: string;
  content: string;
  ip: string;
  createdAt: string;
}

const LogPage: React.FC = () => {
  const columns: ProColumns<LogRecord>[] = [
    { title: '操作人', dataIndex: 'adminName', width: 100 },
    { title: '模块', dataIndex: 'module', width: 100 },
    { title: '操作', dataIndex: 'action', width: 100 },
    { title: '内容', dataIndex: 'content', width: 300, ellipsis: true, search: false },
    { title: 'IP', dataIndex: 'ip', width: 130, search: false },
    { title: '操作时间', dataIndex: 'createdAt', width: 180, valueType: 'dateTime' },
  ];

  return (
    <PageContainer>
      <ProTable<LogRecord>
        rowKey="id"
        columns={columns}
        search={{ labelWidth: 'auto' }}
        request={async () => ({ data: [], success: true, total: 0 })}
      />
    </PageContainer>
  );
};

export default LogPage;

