/**
 * 文档预览抽屉：PDF 内嵌浏览器查看器并按页码定位；文本类直接展示；Word/Excel 展示抽取文本（切片）
 */
import { useEffect, useState } from 'react';
import { Alert, Button, Drawer, Empty, List, Space, Spin, Tag, Typography } from 'antd';
import { DownloadOutlined } from '@ant-design/icons';
import { knowledgeApi } from '@hospital/api';
import type { KnowledgeChunk } from '@hospital/api';
import { downloadBlob } from '@/utils/download';
import { fetchDocumentBlob } from '../shared';

export interface PreviewTarget {
  docId: string;
  title: string;
  mimeType: string;
  fileName: string;
  pageNo?: number | null;
}

interface DocumentPreviewDrawerProps {
  target: PreviewTarget | null;
  onClose: () => void;
}

const TEXT_MIME = new Set(['text/plain', 'text/markdown']);

const DocumentPreviewDrawer: React.FC<DocumentPreviewDrawerProps> = ({ target, onClose }) => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [objectUrl, setObjectUrl] = useState<string | null>(null);
  const [text, setText] = useState<string | null>(null);
  const [chunks, setChunks] = useState<KnowledgeChunk[]>([]);

  useEffect(() => {
    if (!target) return undefined;
    let revoked: string | null = null;
    let cancelled = false;
    setLoading(true);
    setError(null);
    setObjectUrl(null);
    setText(null);
    setChunks([]);

    const load = async () => {
      try {
        if (target.mimeType === 'application/pdf') {
          const blob = await fetchDocumentBlob(target.docId);
          revoked = URL.createObjectURL(blob);
          if (!cancelled) setObjectUrl(revoked);
        } else if (TEXT_MIME.has(target.mimeType)) {
          const blob = await fetchDocumentBlob(target.docId);
          const content = await blob.text();
          if (!cancelled) setText(content);
        } else {
          const result = await knowledgeApi.listChunks(target.docId, { page: 1, pageSize: 200 });
          if (!cancelled) setChunks(result.data ?? []);
        }
      } catch (err: any) {
        if (!cancelled) setError(err?.message || '预览加载失败');
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    void load();

    return () => {
      cancelled = true;
      if (revoked) URL.revokeObjectURL(revoked);
    };
  }, [target]);

  const handleDownload = async () => {
    if (!target) return;
    try {
      const blob = await fetchDocumentBlob(target.docId, true);
      downloadBlob(blob, target.fileName);
    } catch (err: any) {
      setError(err?.message || '下载失败');
    }
  };

  const renderBody = () => {
    if (loading) return <Spin style={{ display: 'block', margin: '80px auto' }} />;
    if (error) return <Alert type="error" showIcon message={error} />;
    if (objectUrl) {
      const src = target?.pageNo ? `${objectUrl}#page=${target.pageNo}` : objectUrl;
      return <iframe title={target?.title} src={src} style={{ width: '100%', height: 'calc(100vh - 160px)', border: 0 }} />;
    }
    if (text !== null) {
      return (
        <Typography.Paragraph style={{ whiteSpace: 'pre-wrap', fontFamily: 'inherit', maxHeight: 'calc(100vh - 160px)', overflow: 'auto' }}>
          {text}
        </Typography.Paragraph>
      );
    }
    if (chunks.length) {
      return (
        <List
          size="small"
          dataSource={chunks}
          style={{ maxHeight: 'calc(100vh - 160px)', overflow: 'auto' }}
          renderItem={(chunk) => (
            <List.Item key={chunk.id}>
              <div style={{ width: '100%' }}>
                <Space size={4} style={{ marginBottom: 4 }}>
                  <Tag>#{chunk.seq + 1}</Tag>
                  {chunk.section ? <Tag color="blue">{chunk.section}</Tag> : null}
                </Space>
                <div style={{ whiteSpace: 'pre-wrap' }}>{chunk.content}</div>
              </div>
            </List.Item>
          )}
        />
      );
    }
    return <Empty description="暂无可预览内容（文档可能尚未处理完成）" />;
  };

  return (
    <Drawer
      title={target?.title}
      open={!!target}
      onClose={onClose}
      width={900}
      destroyOnHidden
      extra={
        <Space>
          {target?.pageNo ? <Tag color="blue">第 {target.pageNo} 页</Tag> : null}
          <Button icon={<DownloadOutlined />} onClick={handleDownload}>
            下载原件
          </Button>
        </Space>
      }
    >
      {renderBody()}
    </Drawer>
  );
};

export default DocumentPreviewDrawer;
