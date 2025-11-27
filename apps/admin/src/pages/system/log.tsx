import { PageContainer, ProTable } from '@ant-design/pro-components';
import type { ProColumns } from '@ant-design/pro-components';
import { Tag, Modal, Descriptions } from 'antd';
import { useState } from 'react';

interface LogRecord {
  id: string;
  adminId: string;
  adminName: string;
  module: string;
  action: string;
  method: string;
  path: string;
  params: string;
  result: string;
  ip: string;
  userAgent: string;
  duration: number;
  createdAt: string;
}

const moduleMap: Record<string, string> = {
  'auth': '认证',
  'department': '科室管理',
  'doctor': '医生管理',
  'schedule': '排班管理',
  'appointment': '预约管理',
  'patient': '患者管理',
  'content': '内容管理',
  'system': '系统管理',
};

const LogPage: React.FC = () => {
  const [detailVisible, setDetailVisible] = useState(false);
  const [currentLog, setCurrentLog] = useState<LogRecord | null>(null);

  const handleViewDetail = (record: LogRecord) => {
    setCurrentLog(record);
    setDetailVisible(true);
  };

  const columns: ProColumns<LogRecord>[] = [
    { title: '操作人', dataIndex: 'adminName', width: 100 },
    { 
      title: '模块', 
      dataIndex: 'module', 
      width: 100,
      valueEnum: moduleMap,
      render: (_, r) => <Tag>{moduleMap[r.module] || r.module}</Tag>
    },
    { title: '操作', dataIndex: 'action', width: 120 },
    { 
      title: '方法', 
      dataIndex: 'method', 
      width: 80, 
      search: false,
      render: (_, r) => {
        const colorMap: Record<string, string> = { GET: 'green', POST: 'blue', PUT: 'orange', DELETE: 'red' };
        return <Tag color={colorMap[r.method]}>{r.method}</Tag>;
      }
    },
    { title: '路径', dataIndex: 'path', width: 200, ellipsis: true, search: false },
    { title: 'IP', dataIndex: 'ip', width: 130, search: false },
    { 
      title: '耗时', 
      dataIndex: 'duration', 
      width: 80, 
      search: false,
      render: (_, r) => `${r.duration}ms`
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

  const mockData: LogRecord[] = [
    { id: '1', adminId: '1', adminName: '系统管理员', module: 'doctor', action: '新增医生', method: 'POST', path: '/api/v1/doctors', params: '{"name":"张医生"}', result: '成功', ip: '192.168.1.100', userAgent: 'Chrome/120', duration: 156, createdAt: '2024-11-27 10:30:00' },
    { id: '2', adminId: '1', adminName: '系统管理员', module: 'department', action: '编辑科室', method: 'PUT', path: '/api/v1/departments/1', params: '{"name":"内科"}', result: '成功', ip: '192.168.1.100', userAgent: 'Chrome/120', duration: 89, createdAt: '2024-11-27 10:25:00' },
    { id: '3', adminId: '2', adminName: '张三', module: 'schedule', action: '批量排班', method: 'POST', path: '/api/v1/schedules/batch', params: '{"doctorId":"1"}', result: '成功', ip: '192.168.1.101', userAgent: 'Chrome/120', duration: 234, createdAt: '2024-11-27 09:15:00' },
    { id: '4', adminId: '1', adminName: '系统管理员', module: 'auth', action: '登录', method: 'POST', path: '/api/v1/auth/login', params: '{"phone":"138****8000"}', result: '成功', ip: '192.168.1.100', userAgent: 'Chrome/120', duration: 45, createdAt: '2024-11-27 09:00:00' },
  ];

  return (
    <PageContainer>
      <ProTable<LogRecord>
        rowKey="id"
        columns={columns}
        search={{ labelWidth: 'auto' }}
        request={async () => ({ data: mockData, success: true, total: mockData.length })}
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
            <Descriptions.Item label="操作人">{currentLog.adminName}</Descriptions.Item>
            <Descriptions.Item label="操作时间">{currentLog.createdAt}</Descriptions.Item>
            <Descriptions.Item label="模块">{moduleMap[currentLog.module]}</Descriptions.Item>
            <Descriptions.Item label="操作">{currentLog.action}</Descriptions.Item>
            <Descriptions.Item label="请求方法">
              <Tag color={currentLog.method === 'GET' ? 'green' : 'blue'}>{currentLog.method}</Tag>
            </Descriptions.Item>
            <Descriptions.Item label="耗时">{currentLog.duration}ms</Descriptions.Item>
            <Descriptions.Item label="请求路径" span={2}>{currentLog.path}</Descriptions.Item>
            <Descriptions.Item label="IP地址">{currentLog.ip}</Descriptions.Item>
            <Descriptions.Item label="结果">{currentLog.result}</Descriptions.Item>
            <Descriptions.Item label="请求参数" span={2}>
              <pre style={{ margin: 0, maxHeight: 200, overflow: 'auto', background: '#f5f5f5', padding: 8, borderRadius: 4 }}>
                {JSON.stringify(JSON.parse(currentLog.params || '{}'), null, 2)}
              </pre>
            </Descriptions.Item>
            <Descriptions.Item label="User-Agent" span={2}>{currentLog.userAgent}</Descriptions.Item>
          </Descriptions>
        )}
      </Modal>
    </PageContainer>
  );
};

export default LogPage;
