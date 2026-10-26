import type { ProColumns } from '@ant-design/pro-components';
import { PageContainer, ProTable } from '@ant-design/pro-components';
import { Tag, Button, message, Modal, Form, Select, Descriptions, Badge, Space, Typography, Steps } from 'antd';
import { useState } from 'react';
import {
  LoadingOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  ClockCircleOutlined,
  RocketOutlined,
  EyeOutlined,
  ReloadOutlined,
} from '@ant-design/icons';
import { useListPage } from '@/hooks/useListPage';
import { createOperationColumn } from '@/components/ListOperations';
import type { BuildJob, MiniappInstance } from '@hospital/api';
import { miniappPlatformApi } from '@hospital/api';
import { createListRequest } from '@/utils/proTable';

const { Text, Paragraph } = Typography;

const BUILD_STATUS_MAP: Record<string, {
  text: string;
  status: 'Processing' | 'Success' | 'Error' | 'Default' | 'Warning';
  icon: React.ReactNode;
  color: string;
}> = {
  pending: { text: '待构建', status: 'Default', icon: <ClockCircleOutlined />, color: 'default' },
  building: { text: '构建中', status: 'Processing', icon: <LoadingOutlined spin />, color: 'blue' },
  success: { text: '构建成功', status: 'Success', icon: <CheckCircleOutlined />, color: 'green' },
  failed: { text: '构建失败', status: 'Error', icon: <CloseCircleOutlined />, color: 'red' },
};

const BUILD_SOURCE_MAP: Record<string, { text: string; color: string }> = {
  manual: { text: '手动', color: 'blue' },
  api: { text: 'API', color: 'green' },
  webhook: { text: 'Webhook', color: 'orange' },
};

const getDisplayStatus = (status: string) => {
  return BUILD_STATUS_MAP[status] || { text: status, status: 'Default' as const, icon: <ClockCircleOutlined />, color: 'default' };
};

const BuildPage: React.FC = () => {
  const { actionRef, reload } = useListPage({});
  const [buildModalVisible, setBuildModalVisible] = useState(false);
  const [detailModalVisible, setDetailModalVisible] = useState(false);
  const [instances, setInstances] = useState<MiniappInstance[]>([]);
  const [currentRecord, setCurrentRecord] = useState<BuildJob | null>(null);
  const [building, setBuilding] = useState(false);
  const [form] = Form.useForm();

  const handleOpenBuildModal = async () => {
    try {
      const res = await miniappPlatformApi.getMiniappInstances({ page: 1, pageSize: 100 });
      setInstances((res as any).data || []);
      setBuildModalVisible(true);
    } catch (error: any) {
      message.error('加载实例列表失败');
    }
  };

  const handleBuild = async () => {
    try {
      const values = await form.validateFields();
      setBuilding(true);
      await miniappPlatformApi.createBuildJob({
        miniappInstanceId: values.instanceId,
        triggerSource: 'manual',
      });
      message.success('构建任务已创建');
      setBuildModalVisible(false);
      form.resetFields();
      reload();
    } catch (error: any) {
      message.error(error.message || '操作失败');
    } finally {
      setBuilding(false);
    }
  };

  const handleViewDetail = (record: BuildJob) => {
    setCurrentRecord(record);
    setDetailModalVisible(true);
  };

  const handleRetry = async (_id: string) => {
    try {
      await miniappPlatformApi.createBuildJob({
        miniappInstanceId: currentRecord?.miniappInstance?.id || '',
        triggerSource: 'manual',
      });
      message.success('已重新触发构建');
      reload();
    } catch (error: any) {
      message.error(error.message || '操作失败');
    }
  };

  const columns: ProColumns<BuildJob>[] = [
    {
      title: '实例名称',
      dataIndex: ['miniappInstance', 'name'],
      width: 180,
      render: (_, record) => record.miniappInstance?.name || '-',
    },
    {
      title: '模板版本',
      dataIndex: ['templateVersion', 'version'],
      width: 140,
      render: (_, record) => (
        <Space>
          <Tag color="purple">v{record.templateVersion?.version || '-'}</Tag>
          {record.templateVersion && (
            <Text type="secondary" style={{ fontSize: '12px' }}>
              {record.templateVersion.id.slice(0, 8)}
            </Text>
          )}
        </Space>
      ),
    },
    {
      title: '触发来源',
      dataIndex: 'triggerSource',
      width: 110,
      render: (_, record) => {
        const sourceInfo = BUILD_SOURCE_MAP[record.triggerSource || 'manual'] || { text: record.triggerSource || '手动', color: 'default' };
        return <Tag color={sourceInfo.color}>{sourceInfo.text}</Tag>;
      },
      valueEnum: {
        manual: { text: '手动', status: 'Default' },
        api: { text: 'API', status: 'Success' },
        webhook: { text: 'Webhook', status: 'Processing' },
      },
    },
    {
      title: '构建状态',
      dataIndex: 'status',
      width: 120,
      render: (_, record) => {
        const statusInfo = getDisplayStatus(record.status);
        return (
          <Badge
            status={statusInfo.status === 'Success' ? 'success' : statusInfo.status === 'Error' ? 'error' : statusInfo.status === 'Processing' ? 'processing' : 'default'}
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
        pending: { text: '待构建', status: 'Default' },
        building: { text: '构建中', status: 'Processing' },
        success: { text: '成功', status: 'Success' },
        failed: { text: '失败', status: 'Error' },
      },
    },
    {
      title: '开始时间',
      dataIndex: 'startedAt',
      valueType: 'dateTime',
      width: 170,
      search: false,
    },
    {
      title: '完成时间',
      dataIndex: 'finishedAt',
      valueType: 'dateTime',
      width: 170,
      search: false,
    },
    {
      title: '耗时',
      dataIndex: 'duration',
      width: 100,
      search: false,
      render: (_, record) => {
        if (!record.startedAt || !record.finishedAt) return '-';
        const start = new Date(record.startedAt).getTime();
        const end = new Date(record.finishedAt).getTime();
        const duration = Math.floor((end - start) / 1000);
        if (duration < 60) return `${duration}秒`;
        const minutes = Math.floor(duration / 60);
        const seconds = duration % 60;
        return `${minutes}分${seconds}秒`;
      },
    },
    createOperationColumn<BuildJob>({
      width: 150,
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
        (record.status === 'failed' || record.status === 'pending') && (
          <Button
            key="retry"
            type="link"
            size="small"
            icon={<ReloadOutlined />}
            onClick={() => handleRetry(record.id)}
          >
            重试
          </Button>
        ),
      ].filter(Boolean),
    }),
  ];

  const selectedInstance = instances.find(i => i.id === form.getFieldValue('instanceId'));

  return (
    <>
      <PageContainer>
        <ProTable<BuildJob>
          headerTitle="构建任务"
          actionRef={actionRef}
          rowKey="id"
          columns={columns}
          request={createListRequest(miniappPlatformApi.getBuildJobs)}
          toolBarRender={() => [
            <Button key="build" type="primary" icon={<RocketOutlined />} onClick={handleOpenBuildModal}>
              触发构建
            </Button>,
          ]}
          pagination={{ defaultPageSize: 10 }}
          search={{}}
        />
      </PageContainer>

      <Modal
        title="触发构建"
        open={buildModalVisible}
        onOk={handleBuild}
        onCancel={() => {
          setBuildModalVisible(false);
          form.resetFields();
        }}
        confirmLoading={building}
      >
        <Form form={form} layout="vertical">
          <Form.Item
            name="instanceId"
            label="选择实例"
            rules={[{ required: true, message: '请选择实例' }]}
          >
            <Select
              placeholder="请选择要构建的小程序实例"
              showSearch
              optionFilterProp="children"
              options={instances.map(i => ({ label: i.name, value: i.id }))}
            />
          </Form.Item>
          {selectedInstance && (
            <Descriptions column={1} size="small" bordered style={{ marginTop: 16 }} items={[
              { key: '0', label: '实例名称', children: selectedInstance.name },
              { key: '1', label: 'AppID', children: selectedInstance.appId },
            ]} />
          )}
        </Form>
      </Modal>

      <Modal
        title={
          <Space>
            <RocketOutlined />
            <span>构建详情</span>
          </Space>
        }
        open={detailModalVisible}
        onCancel={() => setDetailModalVisible(false)}
        footer={null}
        width={680}
      >
        {currentRecord && (
          <div>
            <Steps
              current={
                currentRecord.status === 'building' ? 1 :
                currentRecord.status === 'success' ? 2 :
                currentRecord.status === 'failed' ? 2 : 0
              }
              items={[
                { title: '待构建', icon: <ClockCircleOutlined /> },
                { title: '构建中', icon: currentRecord.status === 'building' ? <LoadingOutlined spin /> : undefined },
                { title: currentRecord.status === 'success' ? '完成' : '失败', icon: currentRecord.status === 'success' ? <CheckCircleOutlined /> : <CloseCircleOutlined /> },
              ]}
              style={{ marginBottom: '24px' }}
            />
            <Descriptions column={2} bordered size="small" items={[
              { key: '0', label: '实例名称', span: 2, children: (
                <Space>
                  <Text strong>{currentRecord.miniappInstance?.name || '-'}</Text>
                  {currentRecord.miniappInstance?.id && (
                    <Text type="secondary" copyable={{ text: currentRecord.miniappInstance.id }} style={{ fontSize: '12px' }}>
                      ID
                    </Text>
                  )}
                </Space>
              ) },
              { key: '1', label: '模板版本', children: (
                <Space>
                  <Tag color="purple">v{currentRecord.templateVersion?.version || '-'}</Tag>
                  {currentRecord.templateVersion?.id && (
                    <Text type="secondary" style={{ fontSize: '12px' }}>
                      {currentRecord.templateVersion.id.slice(0, 8)}
                    </Text>
                  )}
                </Space>
              ) },
              { key: '2', label: '触发来源', children: (
                <Tag color={BUILD_SOURCE_MAP[currentRecord.triggerSource || 'manual']?.color}>
                  {BUILD_SOURCE_MAP[currentRecord.triggerSource || 'manual']?.text}
                </Tag>
              ) },
              { key: '3', label: '构建状态', children: (
                <Space>
                  {getDisplayStatus(currentRecord.status).icon}
                  <Tag color={getDisplayStatus(currentRecord.status).color}>
                    {getDisplayStatus(currentRecord.status).text}
                  </Tag>
                </Space>
              ) },
              { key: '4', label: '任务ID', children: (
                <Text copyable={{ text: currentRecord.id }} style={{ fontSize: '12px' }}>
                  {currentRecord.id.slice(0, 12)}...
                </Text>
              ) },
              { key: '5', label: '开始时间', span: 2, children: currentRecord.startedAt || '-' },
              { key: '6', label: '完成时间', span: 2, children: currentRecord.finishedAt || '-' },
            ]} />
            {currentRecord.status === 'failed' && (
              <div style={{ marginTop: '16px', padding: '12px', background: 'var(--color-white)2f0', borderRadius: '4px', border: '1px solid #ffccc7' }}>
                <Text type="danger"><CloseCircleOutlined /> 构建失败</Text>
                <Paragraph type="secondary" style={{ marginTop: '8px', marginBottom: 0, fontSize: '12px' }}>
                  请检查模板配置和代码版本后重试。如持续失败，请联系技术支持。
                </Paragraph>
              </div>
            )}
            {currentRecord.buildParams && Object.keys(currentRecord.buildParams).length > 0 && (
              <div style={{ marginTop: '16px' }}>
                <Text strong>构建参数：</Text>
                <pre style={{ marginTop: '8px', padding: '8px', background: 'var(--color-bg-layout)', borderRadius: '4px', fontSize: '12px', overflow: 'auto' }}>
                  {JSON.stringify(currentRecord.buildParams, null, 2)}
                </pre>
              </div>
            )}
          </div>
        )}
      </Modal>
    </>
  );
};

export default BuildPage;
