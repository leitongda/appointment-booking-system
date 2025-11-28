import { PageContainer, ProTable } from '@ant-design/pro-components';
import type { ProColumns } from '@ant-design/pro-components';
import { Tag, Modal, Descriptions, message } from 'antd';
import { useState } from 'react';
import { adminApi } from '@hospital/api';
import type { OperationLog } from '@hospital/api';

const moduleMap: Record<string, string> = {
  'auth': '认证',
  'department': '科室管理',
  'doctor': '医生管理',
  'schedule': '排班管理',
  'appointment': '预约管理',
  'patient': '患者管理',
  'content': '内容管理',
  'system': '系统管理',
  'admin': '权限管理',
};

const LogPage: React.FC = () => {
  const [detailVisible, setDetailVisible] = useState(false);
  const [currentLog, setCurrentLog] = useState<OperationLog | null>(null);

  const handleViewDetail = (record: OperationLog) => {
    setCurrentLog(record);
    setDetailVisible(true);
  };

  const columns: ProColumns<OperationLog>[] = [
    { title: '操作人', dataIndex: 'adminName', width: 100 },
    { 
      title: '模块', 
      dataIndex: 'module', 
      width: 100,
      valueEnum: moduleMap,
      render: (_, r) => <Tag>{moduleMap[r.module || ''] || r.module}</Tag>
    },
    { title: '操作', dataIndex: 'action', width: 120 },
    { 
      title: '方法', 
      dataIndex: 'method', 
      width: 80, 
      search: false,
      render: (_, r) => {
        const colorMap: Record<string, string> = { GET: 'green', POST: 'blue', PUT: 'orange', DELETE: 'red' };
        return <Tag color={colorMap[r.method || '']}>{r.method}</Tag>;
      }
    },
    { title: '路径', dataIndex: 'path', width: 200, ellipsis: true, search: false },
    { title: 'IP', dataIndex: 'ip', width: 130, search: false },
    { 
      title: '耗时', 
      dataIndex: 'duration', 
      width: 80, 
      search: false,
      render: (_, r) => r.duration ? `${r.duration}ms` : '-'
    },
    { 
      title: '结果', 
      dataIndex: 'result', 
      width: 80, 
      search: false,
      render: (_, r) => (
        <Tag color={r.result === '成功' ? 'green' : 'red'}>{r.result}</Tag>
      )
    },
    { 
      title: '操作时间', 
      dataIndex: 'createdAt', 
      width: 180, 
      valueType: 'dateTimeRange',
      search: { transform: (value) => ({ startTime: value[0], endTime: value[1] }) },
      render: (_, r) => r.createdAt
    },
    { 
      title: '操作', 
      valueType: 'option',
      width: 80, 
      render: (_, record) => <a onClick={() => handleViewDetail(record)}>详情</a>
    },
  ];

  const parseParams = (params?: string) => {
    if (!params) return {};
    try {
      return JSON.parse(params);
    } catch {
      return {};
    }
  };

  return (
    <PageContainer>
      <ProTable<OperationLog>
        rowKey="id"
        columns={columns}
        search={{ labelWidth: 'auto' }}
        request={async (params) => {
          try {
            const { current, pageSize, module, adminName, startTime, endTime } = params;
            const result = await adminApi.getLogs({
              module,
              startTime,
              endTime,
              page: current || 1,
              pageSize: pageSize || 20,
            });
            return { 
              data: result.data || [], 
              success: true, 
              total: result.total || 0 
            };
          } catch (error: any) {
            message.error(error.message || '获取数据失败');
            return { data: [], success: false, total: 0 };
          }
        }}
        pagination={{ pageSize: 20 }}
      />

      <Modal
        title="操作日志详情"
        open={detailVisible}
        onCancel={() => setDetailVisible(false)}
        footer={null}
        width={700}
      >
        {currentLog && (
          <Descriptions column={2} bordered size="small">
            <Descriptions.Item label="操作人">{currentLog.adminName || '-'}</Descriptions.Item>
            <Descriptions.Item label="操作时间">{currentLog.createdAt}</Descriptions.Item>
            <Descriptions.Item label="模块">{moduleMap[currentLog.module || ''] || currentLog.module}</Descriptions.Item>
            <Descriptions.Item label="操作">{currentLog.action}</Descriptions.Item>
            <Descriptions.Item label="请求方法">
              <Tag color={currentLog.method === 'GET' ? 'green' : 'blue'}>{currentLog.method}</Tag>
            </Descriptions.Item>
            <Descriptions.Item label="耗时">{currentLog.duration ? `${currentLog.duration}ms` : '-'}</Descriptions.Item>
            <Descriptions.Item label="请求路径" span={2}>{currentLog.path}</Descriptions.Item>
            <Descriptions.Item label="IP地址">{currentLog.ip}</Descriptions.Item>
            <Descriptions.Item label="结果">
              <Tag color={currentLog.result === '成功' ? 'green' : 'red'}>{currentLog.result}</Tag>
            </Descriptions.Item>
            <Descriptions.Item label="请求参数" span={2}>
              <pre style={{ margin: 0, maxHeight: 200, overflow: 'auto', background: '#f5f5f5', padding: 8, borderRadius: 4 }}>
                {JSON.stringify(parseParams(currentLog.params), null, 2)}
              </pre>
            </Descriptions.Item>
            <Descriptions.Item label="User-Agent" span={2}>{currentLog.userAgent || '-'}</Descriptions.Item>
          </Descriptions>
        )}
      </Modal>
    </PageContainer>
  );
};

export default LogPage;
