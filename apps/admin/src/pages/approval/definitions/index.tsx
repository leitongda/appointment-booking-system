import type { ProColumns } from '@ant-design/pro-components';
import { PageContainer, ProTable } from '@ant-design/pro-components';
import { Tag, Button, Space, Modal, message, Descriptions, Upload, Progress, Alert, List } from 'antd';
import {
  PlusOutlined, CopyOutlined, PlayCircleOutlined, PauseCircleOutlined,
  DeleteOutlined, EyeOutlined, DownloadOutlined, UploadOutlined, FileOutlined,
  CheckCircleOutlined, CloseCircleOutlined, FileTextOutlined, ExclamationCircleOutlined,
} from '@ant-design/icons';
import { useState, useRef } from 'react';
import type { ActionType } from '@ant-design/pro-components';
import { history } from '@umijs/max';
import { approvalFlowApi } from '@hospital/api';
import type { FlowDefinitionListItem, FlowDefinition } from '@hospital/shared';
import FlowChartViewer from '@/components/ApprovalFlowChart';

const STATUS_MAP: Record<string, { text: string; color: string }> = {
  draft: { text: '草稿', color: 'default' },
  active: { text: '已激活', color: 'success' },
  archived: { text: '已归档', color: 'warning' },
};

const BUSINESS_TYPE_OPTIONS = [
  { label: '停诊审批', value: 'leave_request' },
  { label: '加号审批', value: 'extra_quota' },
];

const FlowDefinitionsPage: React.FC = () => {
  const actionRef = useRef<ActionType>();
  const [detailOpen, setDetailOpen] = useState(false);
  const [currentFlow, setCurrentFlow] = useState<FlowDefinition | null>(null);
  const [importModalOpen, setImportModalOpen] = useState(false);
  const [bpmnImporting, setBpmnImporting] = useState(false);
  const [searchKeyword, setSearchKeyword] = useState('');
  // BPMN 导入进度状态
  const [importProgress, setImportProgress] = useState(0);
  const [importStatusText, setImportStatusText] = useState('');
  const [importResults, setImportResults] = useState<
    { filename: string; name?: string; success: boolean; error?: string }[]
  >([]);
  const [importDone, setImportDone] = useState(false);
  const [selectedRowKeys, setSelectedRowKeys] = useState<React.Key[]>([]);
  const [batchDeleting, setBatchDeleting] = useState(false);

  const fetchData = async (params: any) => {
    setSearchKeyword(params.name || '');
    try {
      const res = await approvalFlowApi.getList({
        page: params.current,
        pageSize: params.pageSize,
        name: params.name,
        businessType: params.businessType,
        status: params.status,
      });
      const items = (res as any).items || res.data || [];
      return { data: items, success: true, total: res.total ?? items.length };
    } catch {
      return { data: [], success: false, total: 0 };
    }
  };

  const handleViewDetail = async (id: string) => {
    try {
      const data = await approvalFlowApi.getDetail(id);
      setCurrentFlow(data);
      setDetailOpen(true);
    } catch (e: any) {
      message.error(e.message || '获取详情失败');
    }
  };

  const handleActivate = async (id: string) => {
    Modal.confirm({
      title: '确认激活',
      content: '激活后将替换同业务类型的其他激活流程，确认？',
      onOk: async () => {
        try {
          await approvalFlowApi.activate(id);
          message.success('激活成功');
          actionRef.current?.reload();
        } catch (e: any) {
          message.error(e.message || '激活失败');
        }
      },
    });
  };

  const handleArchive = async (id: string) => {
    Modal.confirm({
      title: '确认归档',
      content: '归档后此流程定义将不再使用，确认？',
      onOk: async () => {
        try {
          await approvalFlowApi.archive(id);
          message.success('已归档');
          actionRef.current?.reload();
        } catch (e: any) {
          message.error(e.message || '归档失败');
        }
      },
    });
  };

  const handleCopy = async (id: string) => {
    try {
      await approvalFlowApi.copy(id);
      message.success('复制成功');
      actionRef.current?.reload();
    } catch (e: any) {
      message.error(e.message || '复制失败');
    }
  };

  const handleExport = async (id: string, name: string) => {
    try {
      const data = await approvalFlowApi.export(id);
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${name}.json`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      message.success('导出成功');
    } catch (e: any) {
      message.error(e.message || '导出失败');
    }
  };

  const handleDelete = async (id: string) => {
    Modal.confirm({
      title: '确认删除',
      content: '仅草稿状态的流程可以删除，确认？',
      onOk: async () => {
        try {
          await approvalFlowApi.delete(id);
          message.success('已删除');
          actionRef.current?.reload();
        } catch (e: any) {
          message.error(e.message || '删除失败');
        }
      },
    });
  };

  const handleBatchDelete = () => {
    if (selectedRowKeys.length === 0) {
      message.warning('请先选择要删除的流程');
      return;
    }
    Modal.confirm({
      title: '批量删除确认',
      icon: <ExclamationCircleOutlined />,
      content: (
        <div>
          <div>已选择 <b>{selectedRowKeys.length}</b> 个流程，确认删除？</div>
          <div style={{ marginTop: 4, color: '#999', fontSize: 12 }}>
            仅草稿状态的流程可被删除，非草稿流程将跳过。
          </div>
        </div>
      ),
      okText: '删除',
      okButtonProps: { danger: true },
      onOk: async () => {
        setBatchDeleting(true);
        try {
          const result = await approvalFlowApi.batchDelete(selectedRowKeys as string[]);
          const deletedCount = result.deleted?.length || 0;
          const failedCount = result.failed?.length || 0;
          if (failedCount > 0) {
            const failedNames = result.failed
              .map((f) => `${f.name || f.id}：${f.error || '未知原因'}`)
              .join('\n');
            Modal.info({
              title: '批量删除完成（含失败项）',
              width: 520,
              content: (
                <div>
                  <div style={{ marginBottom: 8 }}>
                    成功 {deletedCount} 个，失败 {failedCount} 个：
                  </div>
                  <pre style={{ whiteSpace: 'pre-wrap', maxHeight: 260, overflow: 'auto', fontSize: 12 }}>
                    {failedNames}
                  </pre>
                </div>
              ),
            });
          } else {
            message.success(`已删除 ${deletedCount} 个流程`);
          }
          setSelectedRowKeys([]);
          actionRef.current?.reload();
        } catch (e: any) {
          message.error(e.message || '批量删除失败');
        } finally {
          setBatchDeleting(false);
        }
      },
    });
  };

  const handleImport = async (file: File) => {
    try {
      const text = await file.text();
      let data: any;
      try {
        data = JSON.parse(text);
      } catch {
        message.error('JSON 格式错误，请检查文件内容');
        return;
      }
      // 校验必填字段
      if (!data.name || !data.businessType) {
        message.error('导入数据缺少必填字段（name, businessType）');
        return;
      }
      await approvalFlowApi.import(data);
      message.success('导入成功，已创建为草稿状态');
      setImportModalOpen(false);
      actionRef.current?.reload();
    } catch (e: any) {
      message.error(e.message || '导入失败');
    }
  };

  const handleBpmnImport = async (files: File[]) => {
    setBpmnImporting(true);
    setImportDone(false);
    setImportProgress(0);
    setImportResults([]);
    setImportStatusText(`准备导入 ${files.length} 个文件...`);

    const results: { filename: string; name?: string; success: boolean; error?: string }[] = [];
    let successCount = 0;

    for (let i = 0; i < files.length; i++) {
      const file = files[i];
      setImportStatusText(`正在导入 ${i + 1}/${files.length}：${file.name}`);
      try {
        const result = await approvalFlowApi.importBpmn([file]);
        const imported = result.imported || [];
        const errors = result.errors || [];
        if (imported.length > 0) {
          results.push({ filename: file.name, name: imported[0].name, success: true });
          successCount++;
        } else if (errors.length > 0) {
          results.push({ filename: file.name, success: false, error: errors[0].error });
        } else {
          results.push({ filename: file.name, success: false, error: '未知结果' });
        }
      } catch (e: any) {
        results.push({ filename: file.name, success: false, error: e.message || '导入失败' });
      }
      setImportResults([...results]);
      setImportProgress(Math.round(((i + 1) / files.length) * 100));
    }

    setImportStatusText(
      `导入完成：成功 ${successCount} 个，失败 ${results.length - successCount} 个`
    );
    setBpmnImporting(false);
    setImportDone(true);

    // 仅在全部成功且单文件时跳转设计器
    if (successCount === 1 && results.length === 1) {
      const ok = results[0];
      // 通过返回结果拿到 id 需要接口配合，这里只刷新列表
      actionRef.current?.reload();
      setTimeout(() => {
        setImportModalOpen(false);
        resetImportState();
      }, 1200);
      return;
    }

    actionRef.current?.reload();
  };

  const resetImportState = () => {
    setImportProgress(0);
    setImportStatusText('');
    setImportResults([]);
    setImportDone(false);
  };

  const columns: ProColumns<FlowDefinitionListItem>[] = [
    {
      title: '流程名称',
      dataIndex: 'name',
      ellipsis: true,
      render: (text: any, record: any) => {
        const name = record?.name ?? text ?? '';
        const str = typeof name === 'string' ? name : JSON.stringify(name);
        if (!searchKeyword || !str) return str || '-';
        const idx = str.toLowerCase().indexOf(searchKeyword.toLowerCase());
        if (idx === -1) return str;
        return (
          <span>
            {str.slice(0, idx)}
            <span style={{ fontWeight: 700, color: '#1890ff' }}>
              {str.slice(idx, idx + searchKeyword.length)}
            </span>
            {str.slice(idx + searchKeyword.length)}
          </span>
        );
      },
    },
    {
      title: '业务类型',
      dataIndex: 'businessType',
      width: 120,
      valueEnum: Object.fromEntries(BUSINESS_TYPE_OPTIONS.map((o) => [o.value, { text: o.label }])),
      render: (_, r) => {
        const opt = BUSINESS_TYPE_OPTIONS.find((o) => o.value === r.businessType);
        return opt?.label || r.businessType;
      },
    },
    {
      title: '版本',
      dataIndex: 'version',
      width: 80,
      search: false,
    },
    {
      title: '状态',
      dataIndex: 'status',
      width: 100,
      valueEnum: Object.fromEntries(
        Object.entries(STATUS_MAP).map(([k, v]) => [k, { text: v.text }])
      ),
      render: (_, r) => {
        const s = STATUS_MAP[r.status] || { text: '未知', color: 'default' };
        return <Tag color={s.color}>{s.text}</Tag>;
      },
    },
    {
      title: '描述',
      dataIndex: 'description',
      ellipsis: true,
      search: false,
    },
    {
      title: '更新时间',
      dataIndex: 'updatedAt',
      valueType: 'dateTime',
      width: 160,
      search: false,
    },
    {
      title: '操作',
      valueType: 'option',
      width: 450,
      fixed: 'right',
      render: (_, record) => (
        <Space>
          <Button type="link" size="small" icon={<EyeOutlined />} onClick={() => handleViewDetail(record.id)}>
            查看
          </Button>
          <Button type="link" size="small" icon={<CopyOutlined />} onClick={() => handleCopy(record.id)}>
            复制
          </Button>
          <Button type="link" size="small" icon={<DownloadOutlined />} onClick={() => handleExport(record.id, record.name)}>
            导出
          </Button>
          {record.status === 'draft' && (
            <Button type="link" size="small" onClick={() => history.push(`/approval/definitions/designer/${record.id}`)}>
              编辑
            </Button>
          )}
          {record.status === 'draft' && (
            <>
              <Button type="link" size="small" style={{ color: '#52c41a' }} icon={<PlayCircleOutlined />} onClick={() => handleActivate(record.id)}>
                激活
              </Button>
              <Button type="link" size="small" danger icon={<DeleteOutlined />} onClick={() => handleDelete(record.id)}>
                删除
              </Button>
            </>
          )}
          {record.status === 'active' && (
            <Button type="link" size="small" icon={<PauseCircleOutlined />} onClick={() => handleArchive(record.id)}>
              归档
            </Button>
          )}
        </Space>
      ),
    },
  ];

  return (
    <PageContainer title="流程定义管理">
      <ProTable<FlowDefinitionListItem>
        actionRef={actionRef}
        rowKey="id"
        columns={columns}
        request={fetchData}
        pagination={{ defaultPageSize: 20 }}
        search={{ labelWidth: 'auto' }}
        scroll={{ x: 1400 }}
        rowSelection={{
          selectedRowKeys,
          onChange: (keys) => setSelectedRowKeys(keys),
        }}
        tableAlertRender={({ selectedRowKeys: keys }) => (
          <span>
            已选择 <a style={{ fontWeight: 600 }}>{keys.length}</a> 项
          </span>
        )}
        tableAlertOptionRender={() => (
          <Space size={16}>
            <Button
              type="link"
              danger
              icon={<DeleteOutlined />}
              loading={batchDeleting}
              onClick={handleBatchDelete}
            >
              批量删除
            </Button>
            <Button type="link" onClick={() => setSelectedRowKeys([])}>
              取消选择
            </Button>
          </Space>
        )}
        toolBarRender={() => [
          <Button
            key="import"
            icon={<UploadOutlined />}
            onClick={() => setImportModalOpen(true)}
          >
            导入
          </Button>,
          <Button
            key="create"
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => history.push('/approval/definitions/designer/new')}
          >
            新建流程
          </Button>,
        ]}
      />

      {/* 流程详情弹框 */}
      <Modal
        title={currentFlow?.name ? `流程详情：${currentFlow.name}` : '流程定义详情'}
        open={detailOpen}
        onCancel={() => setDetailOpen(false)}
        width={1100}
        footer={null}
        destroyOnClose
        styles={{ body: { padding: '16px 24px' } }}
      >
        {currentFlow && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            {/* 基本信息 */}
            <Descriptions column={3} size="small">
              <Descriptions.Item label="流程名称">{currentFlow.name}</Descriptions.Item>
              <Descriptions.Item label="业务类型">
                {BUSINESS_TYPE_OPTIONS.find((o) => o.value === currentFlow.businessType)?.label || currentFlow.businessType}
              </Descriptions.Item>
              <Descriptions.Item label="版本">v{currentFlow.version}</Descriptions.Item>
              <Descriptions.Item label="状态">
                <Tag color={STATUS_MAP[currentFlow.status]?.color}>
                  {STATUS_MAP[currentFlow.status]?.text}
                </Tag>
              </Descriptions.Item>
              {currentFlow.updatedAt && (
                <Descriptions.Item label="更新时间">{currentFlow.updatedAt}</Descriptions.Item>
              )}
              {currentFlow.description && (
                <Descriptions.Item label="描述">{currentFlow.description}</Descriptions.Item>
              )}
            </Descriptions>

            {/* 流程图 */}
            <div style={{ border: '1px solid #eee', borderRadius: 8, overflow: 'hidden' }}>
              <FlowChartViewer
                flowDefinition={currentFlow}
                mode="definition"
                height={500}
              />
            </div>
          </div>
        )}
      </Modal>

      {/* 导入流程 Modal */}
      <Modal
        title="导入流程定义"
        open={importModalOpen}
        onCancel={() => {
          if (!bpmnImporting) {
            setImportModalOpen(false);
            resetImportState();
          }
        }}
        footer={null}
        destroyOnClose
        width={760}
        maskClosable={!bpmnImporting}
        styles={{ body: { padding: '20px 24px' } }}
      >
        {/* 进度区（导入中或导入完成后显示） */}
        {(bpmnImporting || importDone || importProgress > 0) && (
          <div style={{ marginBottom: 20, padding: 16, background: '#fafafa', borderRadius: 8 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
              <span style={{ fontSize: 13, color: '#333' }}>{importStatusText}</span>
              <span style={{ fontSize: 13, fontWeight: 600, color: '#1890ff' }}>
                {importProgress}%
              </span>
            </div>
            <Progress
              percent={importProgress}
              status={
                bpmnImporting
                  ? 'active'
                  : importResults.some((r) => !r.success)
                  ? 'exception'
                  : 'success'
              }
              size="small"
              showInfo={false}
            />
          </div>
        )}

        {/* 导入结果列表 */}
        {importResults.length > 0 && (
          <div style={{ marginBottom: 20 }}>
            <List
              size="small"
              bordered
              dataSource={importResults}
              renderItem={(item) => (
                <List.Item>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, width: '100%' }}>
                    {item.success ? (
                      <CheckCircleOutlined style={{ color: '#52c41a', fontSize: 16 }} />
                    ) : (
                      <CloseCircleOutlined style={{ color: '#ff4d4f', fontSize: 16 }} />
                    )}
                    <FileTextOutlined style={{ color: '#999' }} />
                    <span style={{ flex: 1, fontSize: 13 }} title={item.filename}>
                      {item.filename}
                    </span>
                    {item.success ? (
                      <span style={{ fontSize: 12, color: '#52c41a' }}>
                        {item.name ? `已导入：${item.name}` : '导入成功'}
                      </span>
                    ) : (
                      <span style={{ fontSize: 12, color: '#ff4d4f' }} title={item.error}>
                        {item.error}
                      </span>
                    )}
                  </div>
                </List.Item>
              )}
            />
          </div>
        )}

        {/* 导入完成后操作按钮 */}
        {importDone && (
          <div style={{ marginBottom: 16 }}>
            <Alert
              type={importResults.some((r) => !r.success) ? 'warning' : 'success'}
              showIcon
              message={importStatusText}
              style={{ marginBottom: 0 }}
            />
            <div style={{ textAlign: 'right', marginTop: 12 }}>
              <Space>
                <Button onClick={() => resetImportState()} disabled={bpmnImporting}>
                  继续导入
                </Button>
                <Button
                  type="primary"
                  onClick={() => {
                    setImportModalOpen(false);
                    resetImportState();
                  }}
                >
                  完成
                </Button>
              </Space>
            </div>
          </div>
        )}

        {/* 文件选择区（未导入中且未完成时显示） */}
        {!bpmnImporting && !importDone && (
          <div style={{ display: 'flex', gap: 16 }}>
            <div style={{ flex: 1 }}>
              <p style={{ marginBottom: 12, color: '#666', fontSize: 13 }}>
                上传从系统导出的 JSON 文件
              </p>
              <Upload.Dragger
                accept=".json"
                showUploadList={false}
                style={{ height: 180 }}
                beforeUpload={(file) => {
                  handleImport(file);
                  return false;
                }}
              >
                <p style={{ fontSize: 28, color: '#1890ff' }}>
                  <UploadOutlined />
                </p>
                <p>JSON 文件</p>
              </Upload.Dragger>
            </div>
            <div style={{ flex: 1 }}>
              <p style={{ marginBottom: 12, color: '#666', fontSize: 13 }}>
                上传 Flowable BPMN XML 文件（支持多选）
              </p>
              <Upload.Dragger
                accept=".bpmn,.xml"
                showUploadList={false}
                disabled={bpmnImporting}
                multiple
                style={{ height: 180 }}
                beforeUpload={(_, fileList) => {
                  if (fileList.length > 0) {
                    handleBpmnImport(fileList as unknown as File[]);
                  }
                  return false;
                }}
              >
                <p style={{ fontSize: 28, color: '#52c41a' }}>
                  <FileOutlined />
                </p>
                <p>BPMN 文件（可多选）</p>
              </Upload.Dragger>
            </div>
          </div>
        )}
      </Modal>
    </PageContainer>
  );
};

export default FlowDefinitionsPage;
