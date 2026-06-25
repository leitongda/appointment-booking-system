/** 代码预览弹窗 — 展示低代码 Schema 生成的源代码 */

import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Modal,
  Tabs,
  Button,
  Spin,
  message,
  Space,
  Tag,
  Typography,
  Empty,
  Alert,
} from 'antd';
import {
  CopyOutlined,
  DownloadOutlined,
  CodeOutlined,
  ReloadOutlined,
} from '@ant-design/icons';
import { useEditorStore, type StateVariable } from '../store';
import { request } from '@hospital/api';
import { getToken, getStorage, STORAGE_KEYS } from '@hospital/shared';
import type { LowCodeSchema, ApiDataSource } from '@hospital/shared';

const { Text } = Typography;

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface GeneratedFile {
  path: string;
  content: string;
  type: string;
}

interface CodegenResult {
  files: GeneratedFile[];
  warnings: Array<Record<string, any>>;
  dependencies: string[];
  metadata: Record<string, any>;
}

type TargetPlatform = 'taro' | 'native';

interface CodePreviewModalProps {
  /** 弹窗可见性 */
  open: boolean;
  /** 关闭回调 */
  onClose: () => void;
  /** 页面 ID (用于下载接口) */
  pageId: string | null;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** 根据文件扩展名返回标签颜色 */
function getFileColor(filePath: string): string {
  if (filePath.endsWith('.tsx') || filePath.endsWith('.ts')) return 'blue';
  if (filePath.endsWith('.css') || filePath.endsWith('.wxss')) return 'green';
  if (filePath.endsWith('.json')) return 'orange';
  if (filePath.endsWith('.wxml')) return 'cyan';
  if (filePath.endsWith('.js')) return 'gold';
  return 'default';
}

/** 提取文件名 (去掉目录前缀) */
function getFileName(filePath: string): string {
  const parts = filePath.split('/');
  return parts[parts.length - 1] || filePath;
}

/** 调用后端代码生成预览接口 */
async function fetchCodegenPreview(
  pageId: string,
  schema: LowCodeSchema,
  dataSources: ApiDataSource[],
  stateSchema: Record<string, StateVariable>,
  target: TargetPlatform,
): Promise<CodegenResult> {
  const payload = {
    schemaData: schema,
    dataSources: dataSources,
    stateSchema: stateSchema,
    target,
  };
  return request.post(`/lowcode/pages/${pageId}/codegen/preview`, payload);
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

const CodePreviewModal: React.FC<CodePreviewModalProps> = ({
  open,
  onClose,
  pageId,
}) => {
  const schema = useEditorStore((s) => s.schema);
  const dataSources = useEditorStore((s) => s.dataSources);
  const stateSchema = useEditorStore((s) => s.stateSchema);

  const [target, setTarget] = useState<TargetPlatform>('taro');
  const [loading, setLoading] = useState(false);
  const [downloading, setDownloading] = useState(false);
  const [result, setResult] = useState<CodegenResult | null>(null);
  const [activeFileKey, setActiveFileKey] = useState<string>('');
  const [error, setError] = useState<string | null>(null);

  /** 生成代码预览 */
  const generate = useCallback(async () => {
    if (!pageId) {
      setError('请先保存页面再生成代码');
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const res = await fetchCodegenPreview(pageId, schema, dataSources, stateSchema, target);
      setResult(res);
      if (res.files.length > 0) {
        setActiveFileKey(res.files[0].path);
      }
    } catch (err: any) {
      const msg = err?.response?.data?.detail || err?.message || '代码生成失败';
      setError(msg);
      setResult(null);
    } finally {
      setLoading(false);
    }
  }, [pageId, schema, dataSources, stateSchema, target]);

  /** 打开弹窗时自动生成 */
  useEffect(() => {
    if (open) {
      generate();
    }
  }, [open, generate]);

  /** 切换平台时重新生成 */
  const handleTargetChange = useCallback(
    (key: string) => {
      setTarget(key as TargetPlatform);
    },
    [],
  );

  /** 复制单个文件内容 */
  const handleCopyFile = useCallback(async (content: string) => {
    try {
      await navigator.clipboard.writeText(content);
      message.success('已复制到剪贴板');
    } catch {
      // 降级方案
      const textarea = document.createElement('textarea');
      textarea.value = content;
      document.body.appendChild(textarea);
      textarea.select();
      document.execCommand('copy');
      document.body.removeChild(textarea);
      message.success('已复制到剪贴板');
    }
  }, []);

  /** 复制全部文件 */
  const handleCopyAll = useCallback(async () => {
    if (!result?.files?.length) return;
    const allContent = result.files
      .map((f) => `// ====== ${f.path} ======\n${f.content}`)
      .join('\n\n');
    try {
      await navigator.clipboard.writeText(allContent);
      message.success(`已复制 ${result.files.length} 个文件`);
    } catch {
      const textarea = document.createElement('textarea');
      textarea.value = allContent;
      document.body.appendChild(textarea);
      textarea.select();
      document.execCommand('copy');
      document.body.removeChild(textarea);
      message.success(`已复制 ${result.files.length} 个文件`);
    }
  }, [result]);

  /** 下载压缩包 */
  const handleDownload = useCallback(async () => {
    if (!pageId) {
      message.warning('请先保存页面后再下载');
      return;
    }
    setDownloading(true);
    try {
      const url = `/lowcode/pages/${pageId}/codegen/download?target=${target}`;
      const headers: Record<string, string> = {};
      const token = getToken();
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }
      const tenantId = getStorage<string>(STORAGE_KEYS.CURRENT_TENANT_ID);
      if (tenantId) {
        headers['X-Tenant-ID'] = tenantId;
      }
      const response = await fetch(url, { credentials: 'include', headers });
      if (!response.ok) {
        throw new Error(`下载失败: ${response.status}`);
      }
      const blob = await response.blob();
      const suffix = target === 'native' ? 'native' : 'taro';
      const filename = `lowcode-${pageId}-${suffix}.zip`;
      const link = document.createElement('a');
      link.href = URL.createObjectURL(blob);
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(link.href);
      message.success('下载成功');
    } catch (err: any) {
      message.error(err?.message || '下载失败');
    } finally {
      setDownloading(false);
    }
  }, [pageId, target]);

  /** 构建文件列表标签页 */
  const fileTabItems = useMemo(() => {
    if (!result?.files?.length) return [];
    return result.files.map((file) => ({
      key: file.path,
      label: (
        <span>
          <Tag color={getFileColor(file.path)} style={{ marginRight: 4 }}>
            {file.type}
          </Tag>
          {getFileName(file.path)}
        </span>
      ),
      children: (
        <div style={{ position: 'relative' }}>
          <Button
            type="text"
            size="small"
            icon={<CopyOutlined />}
            style={{ position: 'absolute', top: 4, right: 4, zIndex: 1 }}
            onClick={() => handleCopyFile(file.content)}
          >
            复制
          </Button>
          <pre
            style={{
              margin: 0,
              padding: '12px 16px',
              background: '#fafafa',
              border: '1px solid #f0f0f0',
              borderRadius: 6,
              maxHeight: 480,
              overflow: 'auto',
              fontSize: 13,
              lineHeight: 1.6,
              fontFamily:
                "'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace",
              tabSize: 2,
            }}
          >
            <code>{file.content}</code>
          </pre>
        </div>
      ),
    }));
  }, [result, handleCopyFile]);

  /** 弹窗底部操作栏 */
  const modalFooter = (
    <div
      style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
      }}
    >
      <div>
        {result?.dependencies?.length ? (
          <Text type="secondary" style={{ fontSize: 12 }}>
            依赖: {result.dependencies.join(', ')}
          </Text>
        ) : null}
      </div>
      <Space>
        <Button
          icon={<ReloadOutlined />}
          onClick={generate}
          loading={loading}
        >
          重新生成
        </Button>
        <Button
          icon={<CopyOutlined />}
          onClick={handleCopyAll}
          disabled={!result?.files?.length}
        >
          复制全部
        </Button>
        <Button
          type="primary"
          icon={<DownloadOutlined />}
          onClick={handleDownload}
          loading={downloading}
          disabled={!pageId}
        >
          下载 ZIP
        </Button>
      </Space>
    </div>
  );

  return (
    <Modal
      title={
        <span>
          <CodeOutlined style={{ marginRight: 8 }} />
          代码预览
        </span>
      }
      open={open}
      onCancel={onClose}
      width={900}
      footer={modalFooter}
      destroyOnClose
    >
      {/* 平台切换 */}
      <Tabs
        activeKey={target}
        onChange={handleTargetChange}
        size="small"
        style={{ marginBottom: 12 }}
        items={[
          {
            key: 'taro',
            label: 'Taro 小程序',
          },
          {
            key: 'native',
            label: '原生小程序',
          },
        ]}
      />

      {/* 加载状态 */}
      {loading && (
        <div
          style={{
            display: 'flex',
            justifyContent: 'center',
            alignItems: 'center',
            minHeight: 300,
          }}
        >
          <Spin tip="正在生成代码...">
            <div style={{ padding: 50 }} />
          </Spin>
        </div>
      )}

      {/* 错误提示 */}
      {!loading && error && (
        <Alert
          type="error"
          message="代码生成失败"
          description={error}
          showIcon
          action={
            <Button size="small" onClick={generate}>
              重试
            </Button>
          }
          style={{ marginBottom: 16 }}
        />
      )}

      {/* 空状态 */}
      {!loading && !error && result && result.files.length === 0 && (
        <Empty description="未生成任何文件" style={{ padding: '40px 0' }} />
      )}

      {/* 文件内容展示 */}
      {!loading && !error && result && result.files.length > 0 && (
        <>
          <Tabs
            activeKey={activeFileKey}
            onChange={setActiveFileKey}
            size="small"
            type="card"
            items={fileTabItems}
          />

          {/* 警告信息 */}
          {result.warnings.length > 0 && (
            <div style={{ marginTop: 12 }}>
              {result.warnings.map((w, i) => (
                <Alert
                  key={i}
                  type="warning"
                  message={w.message || JSON.stringify(w)}
                  showIcon
                  banner
                  style={{ marginBottom: 4 }}
                />
              ))}
            </div>
          )}
        </>
      )}
    </Modal>
  );
};

export default CodePreviewModal;
export type { CodePreviewModalProps };
