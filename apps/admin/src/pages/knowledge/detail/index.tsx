/**
 * 知识库详情：左目录树 + 右文档表（拖拽上传、学习状态、失败原因与重试、预览/下载/删除）
 */
import type { ActionType, ProColumns } from '@ant-design/pro-components';
import { PageContainer, ProTable } from '@ant-design/pro-components';
import { App, Button, Card, Col, Input, Row, Space, Tag, Tooltip, Tree, Typography, Upload } from 'antd';
import type { DataNode } from 'antd/es/tree';
import {
  DeleteOutlined,
  EditOutlined,
  FolderAddOutlined,
  InboxOutlined,
  ReloadOutlined,
  SearchOutlined,
  ShareAltOutlined,
} from '@ant-design/icons';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { history, useAccess, useParams } from '@umijs/max';
import { knowledgeApi } from '@hospital/api';
import type { KnowledgeBase, KnowledgeDocument, KnowledgeFolder } from '@hospital/api';
import { createListRequest } from '@/utils/proTable';
import { OperationButton, OperationGroup } from '@/components/ListOperations';
import { PAGINATION_CONFIG } from '@/constants/pagination';
import { downloadBlob } from '@/utils/download';
import DocumentPreviewDrawer from '../components/DocumentPreviewDrawer';
import type { PreviewTarget } from '../components/DocumentPreviewDrawer';
import ShareModal from '../components/ShareModal';
import {
  ACCEPT_EXTENSIONS,
  COMPLIANCE_HINT,
  MAX_FILE_MB,
  PERMISSION_MAP,
  PROCESSING_STATUSES,
  STATUS_MAP,
  SUPPORTED_HINT,
  VISIBILITY_MAP,
  canEdit,
  fetchDocumentBlob,
  formatFileSize,
  isOwner,
} from '../shared';

const ALL_KEY = '__all__';
const ROOT_KEY = '__root__';

function buildTree(folders: KnowledgeFolder[]): DataNode[] {
  const byParent = new Map<string | null, KnowledgeFolder[]>();
  folders.forEach((folder) => {
    const key = folder.parentId ?? null;
    byParent.set(key, [...(byParent.get(key) ?? []), folder]);
  });
  const toNodes = (parentId: string | null): DataNode[] =>
    (byParent.get(parentId) ?? []).map((folder) => ({
      key: folder.id,
      title: folder.name,
      children: toNodes(folder.id),
    }));
  return toNodes(null);
}

const KnowledgeDetailPage: React.FC = () => {
  const params = useParams();
  const kbId = (params.id as string | undefined) ?? '';
  const { message, modal } = App.useApp();
  const access = useAccess();
  const actionRef = useRef<ActionType>(null);

  const [kb, setKb] = useState<KnowledgeBase | null>(null);
  const [folders, setFolders] = useState<KnowledgeFolder[]>([]);
  const [selectedKey, setSelectedKey] = useState<string>(ALL_KEY);
  const [hasProcessing, setHasProcessing] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [preview, setPreview] = useState<PreviewTarget | null>(null);
  const [shareOpen, setShareOpen] = useState(false);

  const editable = canEdit(kb?.myPermission);
  const owner = isOwner(kb?.myPermission);
  const selectedFolder = useMemo(() => folders.find((item) => item.id === selectedKey) ?? null, [folders, selectedKey]);

  const loadBase = useCallback(async () => {
    if (!kbId) return;
    try {
      const [base, folderList] = await Promise.all([knowledgeApi.getBase(kbId), knowledgeApi.listFolders(kbId)]);
      setKb(base);
      setFolders(folderList);
    } catch (error: any) {
      message.error(error?.message || '加载知识库失败');
    }
  }, [kbId, message]);

  useEffect(() => {
    void loadBase();
  }, [loadBase]);

  const reloadTable = () => actionRef.current?.reload();

  // ---------- 目录操作 ----------
  const promptFolderName = (title: string, initial = ''): Promise<string | null> =>
    new Promise((resolve) => {
      let value = initial;
      modal.confirm({
        title,
        icon: null,
        content: (
          <Input
            defaultValue={initial}
            maxLength={100}
            placeholder="目录名称"
            autoFocus
            onChange={(event) => {
              value = event.target.value;
            }}
            onPressEnter={() => undefined}
          />
        ),
        okText: '确定',
        cancelText: '取消',
        onOk: () => {
          const trimmed = value.trim();
          if (!trimmed) {
            message.warning('请输入目录名称');
            return Promise.reject();
          }
          resolve(trimmed);
          return Promise.resolve();
        },
        onCancel: () => resolve(null),
      });
    });

  const handleCreateFolder = async () => {
    const name = await promptFolderName(selectedFolder ? `在「${selectedFolder.name}」下新建目录` : '新建目录');
    if (!name) return;
    try {
      await knowledgeApi.createFolder(kbId, { name, parentId: selectedFolder?.id ?? null });
      message.success('目录已创建');
      await loadBase();
    } catch (error: any) {
      message.error(error?.message || '创建目录失败');
    }
  };

  const handleRenameFolder = async () => {
    if (!selectedFolder) return;
    const name = await promptFolderName('重命名目录', selectedFolder.name);
    if (!name || name === selectedFolder.name) return;
    try {
      await knowledgeApi.updateFolder(selectedFolder.id, { name });
      message.success('已重命名');
      await loadBase();
    } catch (error: any) {
      message.error(error?.message || '重命名失败');
    }
  };

  const handleDeleteFolder = () => {
    if (!selectedFolder) return;
    modal.confirm({
      title: `删除目录「${selectedFolder.name}」？`,
      content: '仅能删除空目录；目录内若有文档或子目录请先移走。',
      okButtonProps: { danger: true },
      onOk: async () => {
        try {
          await knowledgeApi.deleteFolder(selectedFolder.id);
          message.success('目录已删除');
          setSelectedKey(ALL_KEY);
          await loadBase();
        } catch (error: any) {
          message.error(error?.message || '删除失败');
        }
      },
    });
  };

  // ---------- 文档操作 ----------
  const handleUpload = async (file: File) => {
    if (file.size > MAX_FILE_MB * 1024 * 1024) {
      message.error(`「${file.name}」超过 ${MAX_FILE_MB}MB 上限`);
      return;
    }
    setUploading(true);
    try {
      await knowledgeApi.uploadDocument(kbId, file, { folderId: selectedFolder?.id ?? null });
      message.success(`「${file.name}」已上传，开始后台学习`);
      setHasProcessing(true);
      reloadTable();
      void loadBase();
    } catch (error: any) {
      message.error(error?.message || `「${file.name}」上传失败`);
    } finally {
      setUploading(false);
    }
  };

  const handleRetry = async (doc: KnowledgeDocument) => {
    try {
      await knowledgeApi.retryDocument(doc.id);
      message.success('已重新发起处理');
      setHasProcessing(true);
      reloadTable();
    } catch (error: any) {
      message.error(error?.message || '重试失败');
    }
  };

  const handleDelete = async (doc: KnowledgeDocument) => {
    try {
      await knowledgeApi.deleteDocument(doc.id);
      message.success('文档已删除');
      reloadTable();
      void loadBase();
    } catch (error: any) {
      message.error(error?.message || '删除失败');
    }
  };

  const handleDownload = async (doc: KnowledgeDocument) => {
    try {
      downloadBlob(await fetchDocumentBlob(doc.id, true), doc.fileName);
    } catch (error: any) {
      message.error(error?.message || '下载失败');
    }
  };

  const openPreview = (doc: KnowledgeDocument, pageNo?: number | null) =>
    setPreview({ docId: doc.id, title: doc.title, mimeType: doc.mimeType, fileName: doc.fileName, pageNo });

  const request = createListRequest<KnowledgeDocument>(
    (params: { folderKey?: string; keyword?: string; status?: string; page?: number; pageSize?: number }) =>
      knowledgeApi.listDocuments(kbId, {
        folderId: params.folderKey && params.folderKey !== ALL_KEY && params.folderKey !== ROOT_KEY ? params.folderKey : undefined,
        rootOnly: params.folderKey === ROOT_KEY,
        keyword: params.keyword || undefined,
        status: (params.status as KnowledgeDocument['status']) || undefined,
        page: params.page,
        pageSize: params.pageSize,
      }),
  );

  const columns: ProColumns<KnowledgeDocument>[] = [
    {
      title: '标题',
      dataIndex: 'keyword',
      fieldProps: { placeholder: '标题 / 文件名' },
      render: (_, record) =>
        record.status === 'ready' ? (
          <a onClick={() => openPreview(record)}>{record.title}</a>
        ) : (
          <span>{record.title}</span>
        ),
    },
    { title: '文件名', dataIndex: 'fileName', ellipsis: true, search: false, width: 200 },
    {
      title: '大小',
      dataIndex: 'sizeBytes',
      width: 90,
      search: false,
      render: (_, record) => formatFileSize(record.sizeBytes),
    },
    {
      title: '学习状态',
      dataIndex: 'status',
      width: 110,
      valueEnum: Object.fromEntries(Object.entries(STATUS_MAP).map(([key, value]) => [key, { text: value.text }])),
      render: (_, record) => {
        const item = STATUS_MAP[record.status];
        const tag = <Tag color={item.color}>{item.text}</Tag>;
        return record.status === 'failed' && record.errorMessage ? (
          <Tooltip title={record.errorMessage}>{tag}</Tooltip>
        ) : (
          tag
        );
      },
    },
    {
      title: '失败原因',
      dataIndex: 'errorMessage',
      ellipsis: true,
      search: false,
      width: 220,
      render: (_, record) => (record.status === 'failed' ? record.errorMessage || '-' : '-'),
    },
    { title: '页数', dataIndex: 'pageCount', width: 70, search: false, render: (_, r) => r.pageCount ?? '-' },
    { title: '切片', dataIndex: 'chunkCount', width: 70, search: false },
    { title: '上传时间', dataIndex: 'createdAt', valueType: 'dateTime', width: 160, search: false },
    {
      title: '操作',
      valueType: 'option',
      width: 220,
      fixed: 'right',
      render: (_, record) => (
        <OperationGroup>
          {record.status === 'ready' ? <OperationButton type="view" label="预览" onClick={() => openPreview(record)} /> : null}
          <OperationButton type="custom" label="下载" onClick={() => handleDownload(record)} />
          {editable && record.status === 'failed' ? (
            <OperationButton
              type="custom"
              permission="knowledge:update"
              icon={<ReloadOutlined />}
              label="重新处理"
              onClick={() => handleRetry(record)}
            />
          ) : null}
          {editable ? (
            <OperationButton
              type="delete"
              permission="knowledge:delete"
              confirmText="删除后原件与切片将一并清除，确定？"
              onClick={() => handleDelete(record)}
            />
          ) : null}
        </OperationGroup>
      ),
    },
  ];

  const treeData: DataNode[] = [
    { key: ALL_KEY, title: '全部文档', children: [{ key: ROOT_KEY, title: '未分类（根目录）' }, ...buildTree(folders)] },
  ];

  return (
    <PageContainer
      title={kb?.name ?? '知识库'}
      onBack={() => history.push('/knowledge/bases')}
      tags={
        kb ? (
          <Space size={4}>
            <Tag color={VISIBILITY_MAP[kb.visibility].color}>{VISIBILITY_MAP[kb.visibility].text}</Tag>
            {kb.myPermission ? <Tag color={PERMISSION_MAP[kb.myPermission].color}>{PERMISSION_MAP[kb.myPermission].text}</Tag> : null}
          </Space>
        ) : undefined
      }
      content={kb?.description ? <Typography.Text type="secondary">{kb.description}</Typography.Text> : undefined}
      extra={[
        <Button key="search" icon={<SearchOutlined />} onClick={() => history.push(`/knowledge/search?kb=${kbId}`)}>
          在本库检索
        </Button>,
        owner && access.hasPermission('knowledge:share') ? (
          <Button key="share" icon={<ShareAltOutlined />} onClick={() => setShareOpen(true)}>
            共享
          </Button>
        ) : null,
      ]}
    >
      <Row gutter={16}>
        <Col xs={24} md={6}>
          <Card
            size="small"
            title="目录"
            extra={
              editable && access.hasPermission('knowledge:update') ? (
                <Space size={0}>
                  <Tooltip title={selectedFolder ? '在所选目录下新建' : '新建根目录'}>
                    <Button type="text" size="small" icon={<FolderAddOutlined />} onClick={handleCreateFolder} />
                  </Tooltip>
                  <Tooltip title="重命名">
                    <Button type="text" size="small" icon={<EditOutlined />} disabled={!selectedFolder} onClick={handleRenameFolder} />
                  </Tooltip>
                  <Tooltip title="删除空目录">
                    <Button type="text" size="small" danger icon={<DeleteOutlined />} disabled={!selectedFolder} onClick={handleDeleteFolder} />
                  </Tooltip>
                </Space>
              ) : null
            }
          >
            <Tree
              showLine
              blockNode
              defaultExpandAll
              selectedKeys={[selectedKey]}
              treeData={treeData}
              onSelect={(keys) => {
                const next = (keys[0] as string | undefined) ?? ALL_KEY;
                setSelectedKey(next);
              }}
            />
          </Card>
        </Col>
        <Col xs={24} md={18}>
          {editable && access.hasPermission('knowledge:create') ? (
            <Upload.Dragger
              multiple
              accept={ACCEPT_EXTENSIONS}
              showUploadList={false}
              disabled={uploading}
              beforeUpload={(file) => {
                void handleUpload(file as File);
                return false;
              }}
              style={{ marginBottom: 16 }}
            >
              <p className="ant-upload-drag-icon">
                <InboxOutlined />
              </p>
              <p className="ant-upload-text">
                点击或拖拽文件到此处上传{selectedFolder ? `到「${selectedFolder.name}」` : ''}
              </p>
              <p className="ant-upload-hint">{SUPPORTED_HINT}</p>
              <p className="ant-upload-hint" style={{ color: 'var(--color-error, #cf1322)' }}>
                {COMPLIANCE_HINT}
              </p>
            </Upload.Dragger>
          ) : null}

          <ProTable<KnowledgeDocument>
            actionRef={actionRef}
            rowKey="id"
            columns={columns}
            params={{ folderKey: selectedKey }}
            request={request}
            polling={hasProcessing ? 3000 : undefined}
            postData={(rows: KnowledgeDocument[]) => {
              setHasProcessing(rows.some((row) => PROCESSING_STATUSES.includes(row.status)));
              return rows;
            }}
            pagination={{ defaultPageSize: PAGINATION_CONFIG.DEFAULT_PAGE_SIZE }}
            search={{ labelWidth: 'auto' }}
            scroll={{ x: 1100 }}
            headerTitle={
              <Space>
                <span>文档</span>
                {hasProcessing ? <Tag color="processing">后台学习中，自动刷新</Tag> : null}
              </Space>
            }
          />
        </Col>
      </Row>

      <DocumentPreviewDrawer target={preview} onClose={() => setPreview(null)} />
      <ShareModal kbId={shareOpen ? kbId : null} kbName={kb?.name} onClose={() => setShareOpen(false)} />
    </PageContainer>
  );
};

export default KnowledgeDetailPage;
