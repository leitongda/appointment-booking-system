import type { ProColumns } from '@ant-design/pro-components';
import { PageContainer, ProTable } from '@ant-design/pro-components';
import { Tag, Modal, Typography, Space, Tooltip } from 'antd';
import { adminApi, dataApi } from '@hospital/api';
import { createListRequest } from '@/utils/proTable';
import { useListPage } from '@/hooks/useListPage';
import { OperationButton } from '@/components/ListOperations';
import type { OperationLog } from '@hospital/api';
import { useState } from 'react';
import ImportExport from '@/components/ImportExport';

const { Paragraph, Text } = Typography;

// 模块选项
const MODULE_OPTIONS = [
  { label: '角色管理', value: '角色管理' },
  { label: '管理员管理', value: '管理员管理' },
  { label: '医生管理', value: '医生管理' },
  { label: '科室管理', value: '科室管理' },
  { label: '门店管理', value: '门店管理' },
  { label: '预约管理', value: '预约管理' },
  { label: '排班管理', value: '排班管理' },
  { label: '排班模板', value: '排班模板' },
  { label: '停诊管理', value: '停诊管理' },
  { label: '患者管理', value: '患者管理' },
  { label: '黑名单管理', value: '黑名单管理' },
  { label: '新闻管理', value: '新闻管理' },
  { label: '公告管理', value: '公告管理' },
  { label: '消息管理', value: '消息管理' },
  { label: '系统设置', value: '系统设置' },
  { label: '其他', value: '其他' },
];

// 结果选项
const RESULT_OPTIONS = [
  { label: '成功', value: '成功' },
  { label: '失败', value: '失败' },
];

const LogPage: React.FC = () => {
  const { actionRef } = useListPage();
  const [detailVisible, setDetailVisible] = useState(false);
  const [currentLog, setCurrentLog] = useState<OperationLog | null>(null);

  const showDetail = (record: OperationLog) => {
    setCurrentLog(record);
    setDetailVisible(true);
  };

  const columns: ProColumns<OperationLog>[] = [
    {
      title: '操作人',
      dataIndex: 'adminName',
      width: 100,
      ellipsis: true,
    },
    {
      title: '模块',
      dataIndex: 'module',
      width: 100,
      valueType: 'select',
      fieldProps: {
        options: MODULE_OPTIONS,
        showSearch: true,
      },
      render: (_, record) => (
        <Tag>{record.module || '-'}</Tag>
      ),
    },
    {
      title: '操作',
      dataIndex: 'action',
      width: 100,
      search: false,
    },
    {
      title: '方法',
      dataIndex: 'method',
      width: 80,
      search: false,
      render: (val) => {
        const colors: Record<string, string> = {
          GET: 'blue',
          POST: 'green',
          PUT: 'orange',
          PATCH: 'gold',
          DELETE: 'red',
        };
        return <Tag color={colors[val as string] || 'default'}>{val}</Tag>;
      },
    },
    {
      title: '路径',
      dataIndex: 'path',
      width: 200,
      ellipsis: true,
      search: false,
      render: (val) => (
        <Tooltip title={val}>
          <Text style={{ maxWidth: 200 }} ellipsis>{val as string}</Text>
        </Tooltip>
      ),
    },
    {
      title: '结果',
      dataIndex: 'result',
      width: 80,
      valueType: 'select',
      fieldProps: {
        options: RESULT_OPTIONS,
      },
      render: (val) => (
        <Tag color={val === '成功' ? 'success' : 'error'}>{val}</Tag>
      ),
    },
    {
      title: 'IP',
      dataIndex: 'ip',
      width: 130,
      search: false,
      copyable: true,
    },
    {
      title: '耗时',
      dataIndex: 'duration',
      width: 80,
      search: false,
      render: (val) => {
        const ms = val as number;
        const color = ms > 1000 ? 'red' : ms > 500 ? 'orange' : 'green';
        return <Text type={color === 'green' ? 'success' : color === 'orange' ? 'warning' : 'danger'}>{ms}ms</Text>;
      },
    },
    {
      title: '时间',
      dataIndex: 'createdAt',
      valueType: 'dateTimeRange',
      width: 180,
      render: (_, record) => record.createdAt,
      search: {
        transform: (value) => ({
          startTime: value?.[0],
          endTime: value?.[1],
        }),
      },
    },
    {
      title: '操作',
      valueType: 'option',
      width: 80,
      fixed: 'right',
      render: (_, record) => (
        <OperationButton
          type="view"
          onClick={() => showDetail(record)}
        />
      ),
    },
  ];

  return (
    <PageContainer>
      <ProTable<OperationLog>
        headerTitle="操作日志"
        actionRef={actionRef}
        rowKey="id"
        columns={columns}
        scroll={{ x: 1200 }}
        request={createListRequest(adminApi.getLogs)}
        pagination={{ defaultPageSize: 20, showSizeChanger: true }}
        search={{
          labelWidth: 'auto',
          defaultCollapsed: false,
        }}
        dateFormatter="string"
        toolBarRender={() => [
          <ImportExport
            key="export"
            moduleName="操作日志"
            exportUrl={dataApi.getExportLogsUrl()}
            showImport={false}
          />,
        ]}
      />

      <Modal
        title="操作日志详情"
        open={detailVisible}
        onCancel={() => setDetailVisible(false)}
        footer={null}
        width={700}
      >
        {currentLog && (
          <Space direction="vertical" style={{ width: '100%' }} size="middle">
            <div>
              <Text type="secondary">操作人：</Text>
              <Text strong>{currentLog.adminName || '-'}</Text>
            </div>
            <div>
              <Text type="secondary">模块：</Text>
              <Tag>{currentLog.module || '-'}</Tag>
            </div>
            <div>
              <Text type="secondary">操作：</Text>
              <Text>{currentLog.action || '-'}</Text>
            </div>
            <div>
              <Text type="secondary">请求方法：</Text>
              <Tag color={
                currentLog.method === 'POST' ? 'green' :
                currentLog.method === 'PUT' ? 'orange' :
                currentLog.method === 'DELETE' ? 'red' : 'blue'
              }>
                {currentLog.method}
              </Tag>
            </div>
            <div>
              <Text type="secondary">请求路径：</Text>
              <Paragraph copyable style={{ marginBottom: 0 }}>{currentLog.path}</Paragraph>
            </div>
            <div>
              <Text type="secondary">结果：</Text>
              <Tag color={currentLog.result === '成功' ? 'success' : 'error'}>
                {currentLog.result}
              </Tag>
            </div>
            <div>
              <Text type="secondary">IP 地址：</Text>
              <Paragraph copyable style={{ marginBottom: 0 }}>{currentLog.ip}</Paragraph>
            </div>
            <div>
              <Text type="secondary">耗时：</Text>
              <Text>{currentLog.duration}ms</Text>
            </div>
            <div>
              <Text type="secondary">时间：</Text>
              <Text>{currentLog.createdAt}</Text>
            </div>
            <div>
              <Text type="secondary">请求参数：</Text>
              {currentLog.params ? (
                <Paragraph
                  copyable
                  style={{
                    background: '#f5f5f5',
                    padding: '12px',
                    borderRadius: '6px',
                    maxHeight: '300px',
                    overflow: 'auto',
                    marginTop: '8px',
                  }}
                >
                  <pre style={{ margin: 0, whiteSpace: 'pre-wrap', wordBreak: 'break-all' }}>
                    {JSON.stringify(JSON.parse(currentLog.params), null, 2)}
                  </pre>
                </Paragraph>
              ) : (
                <Text type="secondary">无</Text>
              )}
            </div>
            <div>
              <Text type="secondary">User-Agent：</Text>
              <Paragraph
                ellipsis={{ rows: 2, expandable: true }}
                style={{ marginBottom: 0 }}
              >
                {currentLog.userAgent || '-'}
              </Paragraph>
            </div>
          </Space>
        )}
      </Modal>
    </PageContainer>
  );
};

export default LogPage;
