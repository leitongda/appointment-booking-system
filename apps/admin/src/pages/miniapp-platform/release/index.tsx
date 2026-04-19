import type { ProColumns } from '@ant-design/pro-components';
import { PageContainer, ProTable } from '@ant-design/pro-components';
import { Tag, Modal, Descriptions, Button, Space, Typography, Badge } from 'antd';
import { useState } from 'react';
import {
  CloudUploadOutlined,
  AuditOutlined,
  SendOutlined,
  RollbackOutlined,
  EyeOutlined,
  LoadingOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  ClockCircleOutlined,
} from '@ant-design/icons';
import { useListPage } from '@/hooks/useListPage';
import { createOperationColumn } from '@/components/ListOperations';
import type { ReleaseJob } from '@hospital/api';
import { miniappPlatformApi } from '@hospital/api';
import { createListRequest } from '@/utils/proTable';

const { Text } = Typography;

const RELEASE_ACTION_TYPE_MAP: Record<string, {
  text: string;
  color: string;
  icon: React.ReactNode;
}> = {
  upload: { text: '上传代码', color: 'blue', icon: <CloudUploadOutlined /> },
  submit_audit: { text: '提交审核', color: 'orange', icon: <AuditOutlined /> },
  publish: { text: '正式发布', color: 'green', icon: <SendOutlined /> },
  rollback: { text: '版本回滚', color: 'red', icon: <RollbackOutlined /> },
};

const RELEASE_STATUS_MAP: Record<string, { text: string; color: string; icon: React.ReactNode }> = {
  pending: { text: '排队', color: 'default', icon: <ClockCircleOutlined /> },
  processing: { text: '处理中', color: 'blue', icon: <LoadingOutlined spin /> },
  success: { text: '成功', color: 'green', icon: <CheckCircleOutlined /> },
  failed: { text: '失败', color: 'red', icon: <CloseCircleOutlined /> },
};

const ReleasePage: React.FC = () => {
  const { actionRef } = useListPage({});
  const [detailModalVisible, setDetailModalVisible] = useState(false);
  const [currentRecord, setCurrentRecord] = useState<ReleaseJob | null>(null);

  const handleViewDetail = (record: ReleaseJob) => {
    setCurrentRecord(record);
    setDetailModalVisible(true);
  };

  const columns: ProColumns<ReleaseJob>[] = [
    {
      title: '实例名称',
      dataIndex: ['miniappInstance', 'name'],
      width: 180,
      render: (_, record) => record.miniappInstance?.name || '-',
    },
    {
      title: '操作类型',
      dataIndex: 'action',
      width: 120,
      render: (_, record) => {
        const actionInfo = RELEASE_ACTION_TYPE_MAP[record.action] || { text: record.action, color: 'default', icon: null };
        return (
          <Space>
            {actionInfo.icon}
            <Tag color={actionInfo.color}>{actionInfo.text}</Tag>
          </Space>
        );
      },
      valueEnum: {
        upload: { text: '上传代码', status: 'Default' },
        submit_audit: { text: '提交审核', status: 'Processing' },
        publish: { text: '正式发布', status: 'Success' },
        rollback: { text: '版本回滚', status: 'Error' },
      },
    },
    {
      title: '模板版本',
      dataIndex: 'targetVersion',
      width: 140,
      render: (_, record) => (
        record.targetVersion ? (
          <Space>
            <Tag color="purple">v{record.targetVersion}</Tag>
          </Space>
        ) : '-'
      ),
    },
    {
      title: '发布状态',
      dataIndex: 'status',
      width: 120,
      render: (_, record) => {
        const statusInfo = RELEASE_STATUS_MAP[record.status] || { text: record.status, color: 'default', icon: null };
        return (
          <Badge
            status={statusInfo.color === 'green' ? 'success' : statusInfo.color === 'red' ? 'error' : statusInfo.color === 'blue' ? 'processing' : 'default'}
            text={
              <Space>
                {statusInfo.icon}
                <span>{statusInfo.text}</span>
              </Space>
            }
          />
        );
      },
      valueEnum: {
        pending: { text: '排队', status: 'Default' },
        processing: { text: '处理中', status: 'Processing' },
        success: { text: '成功', status: 'Success' },
        failed: { text: '失败', status: 'Error' },
      },
    },
    {
      title: '创建时间',
      dataIndex: 'createdAt',
      valueType: 'dateTime',
      width: 170,
      search: false,
    },
    {
      title: '更新时间',
      dataIndex: 'updatedAt',
      valueType: 'dateTime',
      width: 170,
      search: false,
    },
    createOperationColumn<ReleaseJob>({
      width: 120,
      extraButtons: (record) => [
        <Button
          key="detail"
          type="link"
          size="small"
          icon={<EyeOutlined />}
          onClick={() => handleViewDetail(record)}
        >
          详情
        </Button>,
      ],
    }),
  ];

  return (
    <>
      <PageContainer>
        <ProTable<ReleaseJob>
          headerTitle="发布管理"
          actionRef={actionRef}
          rowKey="id"
          columns={columns}
          request={createListRequest(miniappPlatformApi.getReleaseJobs)}
          pagination={{ defaultPageSize: 10 }}
          search={{}}
        />
      </PageContainer>

      <Modal
        title={
          <Space>
            <SendOutlined />
            <span>发布详情</span>
          </Space>
        }
        open={detailModalVisible}
        onCancel={() => setDetailModalVisible(false)}
        footer={null}
        width={640}
      >
        {currentRecord && (
          <Descriptions column={2} bordered size="small">
            <Descriptions.Item label="实例名称" span={2}>
              <Space>
                <Text strong>{currentRecord.miniappInstance?.name || '-'}</Text>
                {currentRecord.miniappInstance?.id && (
                  <Text type="secondary" copyable={{ text: currentRecord.miniappInstance.id }} style={{ fontSize: '12px' }}>
                    ID
                  </Text>
                )}
              </Space>
            </Descriptions.Item>
            <Descriptions.Item label="操作类型">
              <Space>
                {RELEASE_ACTION_TYPE_MAP[currentRecord.action]?.icon}
                <Tag color={RELEASE_ACTION_TYPE_MAP[currentRecord.action]?.color}>
                  {RELEASE_ACTION_TYPE_MAP[currentRecord.action]?.text}
                </Tag>
              </Space>
            </Descriptions.Item>
            <Descriptions.Item label="模板版本">
              <Tag color="purple">v{currentRecord.targetVersion || '-'}</Tag>
            </Descriptions.Item>
            <Descriptions.Item label="发布状态">
              <Space>
                {RELEASE_STATUS_MAP[currentRecord.status]?.icon}
                <Tag color={RELEASE_STATUS_MAP[currentRecord.status]?.color}>
                  {RELEASE_STATUS_MAP[currentRecord.status]?.text}
                </Tag>
              </Space>
            </Descriptions.Item>
            <Descriptions.Item label="任务ID">
              <Text copyable={{ text: currentRecord.id }} style={{ fontSize: '12px' }}>
                {currentRecord.id.slice(0, 12)}...
              </Text>
            </Descriptions.Item>
            <Descriptions.Item label="构建产物" span={2}>
              {currentRecord.artifact ? (
                <Space>
                  <Tag color="cyan">产物已生成</Tag>
                  <Text type="secondary" style={{ fontSize: '12px' }}>
                    {currentRecord.artifact.filePath}
                  </Text>
                </Space>
              ) : (
                <Tag color="default">无产物</Tag>
              )}
            </Descriptions.Item>
            <Descriptions.Item label="创建时间" span={2}>{currentRecord.createdAt}</Descriptions.Item>
            <Descriptions.Item label="更新时间" span={2}>{currentRecord.updatedAt || '-'}</Descriptions.Item>
          </Descriptions>
        )}
      </Modal>
    </>
  );
};

export default ReleasePage;
