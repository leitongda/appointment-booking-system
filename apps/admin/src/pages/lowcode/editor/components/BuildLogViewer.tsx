/**
 * 构建日志查看器 -- 展示低代码页面构建过程的日志输出。
 *
 * 功能:
 * 1. 等宽字体展示构建日志
 * 2. 自动滚动到底部
 * 3. 一键复制日志
 * 4. 错误行高亮
 * 5. 刷新日志按钮
 */

import React, { useCallback, useEffect, useMemo, useRef } from 'react';
import { Modal, Button, Typography, message, Space, Spin, Tag } from 'antd';
import {
  CopyOutlined,
  ReloadOutlined,
  FileTextOutlined,
  WarningOutlined,
} from '@ant-design/icons';

const { Text } = Typography;

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface BuildLogViewerProps {
  /** 弹窗可见性 */
  open: boolean;
  /** 关闭回调 */
  onClose: () => void;
  /** 日志文本内容 */
  logs: string | null;
  /** 是否正在加载 */
  loading?: boolean;
  /** 是否正在构建 (true 时显示实时构建标识) */
  building?: boolean;
  /** 刷新日志回调 */
  onRefresh?: () => void;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** 将日志文本按行拆分，每行附带是否为错误行的标记 */
function parseLogLines(raw: string): Array<{ text: string; isError: boolean }> {
  if (!raw) return [];
  const lines = raw.split('\n');
  return lines.map((line) => ({
    text: line,
    isError: /\berror\b|\bfailed\b|\bexception\b|\btraceback\b|\bfatal\b|\bcritical\b/i.test(line),
  }));
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

const BuildLogViewer: React.FC<BuildLogViewerProps> = ({
  open,
  onClose,
  logs,
  loading = false,
  building = false,
  onRefresh,
}) => {
  const logContainerRef = useRef<HTMLDivElement>(null);

  /** 解析日志行 */
  const logLines = useMemo(() => parseLogLines(logs ?? ''), [logs]);

  /** 错误行数统计 */
  const errorCount = useMemo(
    () => logLines.filter((l) => l.isError).length,
    [logLines],
  );

  /** 自动滚动到底部 */
  useEffect(() => {
    if (!open) return;
    // 在 DOM 更新后滚动
    const timer = setTimeout(() => {
      const el = logContainerRef.current;
      if (el) {
        el.scrollTop = el.scrollHeight;
      }
    }, 100);
    return () => clearTimeout(timer);
  }, [open, logs]);

  /** 复制日志 */
  const handleCopy = useCallback(async () => {
    if (!logs) return;
    try {
      await navigator.clipboard.writeText(logs);
      message.success('日志已复制到剪贴板');
    } catch {
      // 降级方案
      const textarea = document.createElement('textarea');
      textarea.value = logs;
      document.body.appendChild(textarea);
      textarea.select();
      document.execCommand('copy');
      document.body.removeChild(textarea);
      message.success('日志已复制到剪贴板');
    }
  }, [logs]);

  /** 刷新 */
  const handleRefresh = useCallback(() => {
    onRefresh?.();
  }, [onRefresh]);

  // --- Footer ---
  const modalFooter = (
    <div
      style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
      }}
    >
      <div>
        {errorCount > 0 && (
          <Tag icon={<WarningOutlined />} color="error">
            {errorCount} 条错误
          </Tag>
        )}
        {building && (
          <Tag color="processing" style={{ marginLeft: errorCount > 0 ? 4 : 0 }}>
            构建中...
          </Tag>
        )}
        {!building && logs && (
          <Text type="secondary" style={{ fontSize: 12 }}>
            共 {logLines.length} 行
          </Text>
        )}
      </div>
      <Space>
        {onRefresh && (
          <Button
            icon={<ReloadOutlined />}
            onClick={handleRefresh}
            loading={loading}
          >
            刷新
          </Button>
        )}
        <Button
          icon={<CopyOutlined />}
          onClick={handleCopy}
          disabled={!logs}
        >
          复制日志
        </Button>
      </Space>
    </div>
  );

  return (
    <Modal
      title={
        <span>
          <FileTextOutlined style={{ marginRight: 8 }} />
          构建日志
        </span>
      }
      open={open}
      onCancel={onClose}
      width={800}
      footer={modalFooter}
      destroyOnClose
    >
      <Spin spinning={loading && !logs}>
        {/* 加载中占位 */}
        {loading && !logs && (
          <div
            style={{
              display: 'flex',
              justifyContent: 'center',
              alignItems: 'center',
              minHeight: 200,
            }}
          >
            <Text type="secondary">正在获取日志...</Text>
          </div>
        )}

        {/* 空状态 */}
        {!loading && !logs && (
          <div
            style={{
              display: 'flex',
              justifyContent: 'center',
              alignItems: 'center',
              minHeight: 200,
            }}
          >
            <Text type="secondary">暂无构建日志</Text>
          </div>
        )}

        {/* 日志内容 */}
        {logs && (
          <div
            ref={logContainerRef}
            style={{
              background: '#1e1e1e',
              color: '#d4d4d4',
              padding: 12,
              borderRadius: 6,
              maxHeight: 480,
              overflow: 'auto',
              fontSize: 12,
              lineHeight: 1.7,
              fontFamily:
                "'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace",
            }}
          >
            {logLines.map((line, idx) => (
              <div
                key={idx}
                style={{
                  background: line.isError
                    ? 'rgba(255, 77, 79, 0.15)'
                    : 'transparent',
                  color: line.isError ? '#ff7875' : '#d4d4d4',
                  padding: '1px 4px',
                  borderRadius: 2,
                  whiteSpace: 'pre-wrap',
                  wordBreak: 'break-all',
                }}
              >
                {line.text || ' '}
              </div>
            ))}
          </div>
        )}
      </Spin>
    </Modal>
  );
};

export default BuildLogViewer;
