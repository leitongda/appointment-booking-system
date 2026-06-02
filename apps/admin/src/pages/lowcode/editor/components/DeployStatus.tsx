/**
 * 部署状态指示器 — 紧凑型部署状态展示组件。
 *
 * 功能:
 * 1. 状态徽章 + 颜色编码 (published=绿, building=蓝, auditing=橙, failed=红, idle=灰)
 * 2. 上次部署时间
 * 3. 点击展开详细状态
 * 4. 过渡状态自动轮询刷新
 */

import React, { useCallback, useEffect, useRef, useState } from 'react';
import { Badge, Popover, Space, Spin, Tag, Tooltip, Typography } from 'antd';
import {
  CheckCircleFilled,
  ClockCircleOutlined,
  CloseCircleFilled,
  CloudUploadOutlined,
  SyncOutlined,
  WarningOutlined,
} from '@ant-design/icons';
import dayjs from 'dayjs';
import relativeTime from 'dayjs/plugin/relativeTime';
import { lowcodeApi, type DeployStatus, type DeployStatusResponse } from '@hospital/api';

dayjs.extend(relativeTime);

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

/** 状态 -> 颜色映射 */
const STATUS_COLOR_MAP: Record<DeployStatus, { badge: 'success' | 'processing' | 'warning' | 'error' | 'default'; dot: string; label: string }> = {
  published: { badge: 'success', dot: '#52c41a', label: '已发布' },
  building: { badge: 'processing', dot: '#1677ff', label: '构建中' },
  built: { badge: 'processing', dot: '#13c2c2', label: '已构建' },
  uploading: { badge: 'processing', dot: '#1677ff', label: '上传中' },
  uploaded: { badge: 'processing', dot: '#13c2c2', label: '已上传' },
  auditing: { badge: 'warning', dot: '#faad14', label: '审核中' },
  failed: { badge: 'error', dot: '#ff4d4f', label: '构建失败' },
  idle: { badge: 'default', dot: '#bfbfbf', label: '待部署' },
};

/** 需要自动轮询的状态 (非终态) */
const TRANSITIONAL_STATUSES: Set<DeployStatus> = new Set([
  'building',
  'uploading',
  'uploaded',
  'auditing',
]);

const POLL_INTERVAL = 5000;

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function isTransitional(status: DeployStatus): boolean {
  return TRANSITIONAL_STATUSES.has(status);
}

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface DeployStatusIndicatorProps {
  /** 页面 ID */
  pageId: string;
}

// ---------------------------------------------------------------------------
// DeployStatusIndicator
// ---------------------------------------------------------------------------

const DeployStatusIndicator: React.FC<DeployStatusIndicatorProps> = ({ pageId }) => {
  const [status, setStatus] = useState<DeployStatusResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [popoverOpen, setPopoverOpen] = useState(false);
  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const currentStatus: DeployStatus = status?.deploy_status ?? 'idle';
  const statusCfg = STATUS_COLOR_MAP[currentStatus];
  const isPolling = isTransitional(currentStatus);

  // --- Fetch ---

  const fetchStatus = useCallback(async () => {
    if (!pageId) return;
    setLoading(true);
    try {
      const res = await lowcodeApi.getDeployStatus(pageId);
      setStatus(res);
    } catch (err) {
      console.error('获取部署状态失败:', err);
    } finally {
      setLoading(false);
    }
  }, [pageId]);

  // --- Effects ---

  /** 初始加载 */
  useEffect(() => {
    fetchStatus();
  }, [fetchStatus]);

  /** 过渡状态自动轮询 */
  useEffect(() => {
    if (pollingRef.current) {
      clearInterval(pollingRef.current);
      pollingRef.current = null;
    }

    if (isPolling) {
      pollingRef.current = setInterval(fetchStatus, POLL_INTERVAL);
    }

    return () => {
      if (pollingRef.current) {
        clearInterval(pollingRef.current);
        pollingRef.current = null;
      }
    };
  }, [isPolling, fetchStatus]);

  /** Popover 打开时刷新数据 */
  useEffect(() => {
    if (popoverOpen) {
      fetchStatus();
    }
  }, [popoverOpen, fetchStatus]);

  // --- Render helpers ---

  const formatTime = (iso?: string | null): string | null => {
    if (!iso) return null;
    const d = dayjs(iso);
    const now = dayjs();
    // 超过 24 小时显示绝对时间，否则显示相对时间
    if (now.diff(d, 'hour') > 24) {
      return d.format('MM-DD HH:mm');
    }
    return d.fromNow();
  };

  const getIcon = () => {
    if (loading && !status) return <Spin size="small" />;

    switch (currentStatus) {
      case 'published':
        return <CheckCircleFilled style={{ color: statusCfg.dot, fontSize: 14 }} />;
      case 'failed':
        return <CloseCircleFilled style={{ color: statusCfg.dot, fontSize: 14 }} />;
      case 'building':
      case 'uploading':
        return <SyncOutlined spin style={{ color: statusCfg.dot, fontSize: 14 }} />;
      case 'auditing':
        return <ClockCircleOutlined style={{ color: statusCfg.dot, fontSize: 14 }} />;
      default:
        return <CloudUploadOutlined style={{ color: statusCfg.dot, fontSize: 14 }} />;
    }
  };

  // --- Popover content (expanded detail) ---

  const popoverContent = (
    <div style={{ minWidth: 220, maxWidth: 320 }}>
      <Space direction="vertical" size={8} style={{ width: '100%' }}>
        {/* 状态标签 */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <Typography.Text type="secondary" style={{ fontSize: 12 }}>
            当前状态
          </Typography.Text>
          <Tag
            color={statusCfg.badge}
            icon={isPolling ? <SyncOutlined spin /> : undefined}
            style={{ margin: 0 }}
          >
            {statusCfg.label}
          </Tag>
        </div>

        {/* 上次部署时间 */}
        {status?.last_deploy_at && (
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <Typography.Text type="secondary" style={{ fontSize: 12 }}>
              上次部署
            </Typography.Text>
            <Tooltip title={dayjs(status.last_deploy_at).format('YYYY-MM-DD HH:mm:ss')}>
              <Typography.Text style={{ fontSize: 12 }}>
                {formatTime(status.last_deploy_at)}
              </Typography.Text>
            </Tooltip>
          </div>
        )}

        {/* 构建任务 ID */}
        {status?.build_job && (
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <Typography.Text type="secondary" style={{ fontSize: 12 }}>
              构建任务
            </Typography.Text>
            <Tooltip title={status.build_job.id}>
              <Typography.Text code style={{ fontSize: 11 }}>
                {status.build_job.id.slice(0, 10)}...
              </Typography.Text>
            </Tooltip>
          </div>
        )}

        {/* 构建失败日志摘要 */}
        {currentStatus === 'failed' && status?.build_job?.build_log && (
          <div style={{ marginTop: 4 }}>
            <Typography.Text type="danger" style={{ fontSize: 11 }}>
              <WarningOutlined style={{ marginRight: 4 }} />
              构建失败
            </Typography.Text>
            <pre
              style={{
                background: '#1e1e1e',
                color: '#d4d4d4',
                padding: 8,
                borderRadius: 4,
                fontSize: 10,
                maxHeight: 80,
                overflow: 'auto',
                margin: '4px 0 0 0',
              }}
            >
              {status.build_job.build_log.slice(0, 300)}
              {status.build_job.build_log.length > 300 ? '\n...' : ''}
            </pre>
          </div>
        )}

        {/* 轮询提示 */}
        {isPolling && (
          <Typography.Text type="secondary" style={{ fontSize: 11, display: 'block', textAlign: 'center' }}>
            自动刷新中，每 {POLL_INTERVAL / 1000}s 更新
          </Typography.Text>
        )}
      </Space>
    </div>
  );

  // --- Main render ---

  return (
    <Popover
      content={popoverContent}
      trigger="click"
      placement="bottomRight"
      open={popoverOpen}
      onOpenChange={setPopoverOpen}
      overlayStyle={{ padding: 0 }}
    >
      <div
        style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: 6,
          padding: '4px 10px',
          borderRadius: 6,
          border: '1px solid #f0f0f0',
          background: '#fafafa',
          cursor: 'pointer',
          transition: 'border-color 0.2s, background 0.2s',
          userSelect: 'none',
        }}
        onMouseEnter={(e) => {
          e.currentTarget.style.borderColor = '#d9d9d9';
          e.currentTarget.style.background = '#f5f5f5';
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.borderColor = '#f0f0f0';
          e.currentTarget.style.background = '#fafafa';
        }}
      >
        <Badge status={statusCfg.badge} />
        {getIcon()}
        <Typography.Text style={{ fontSize: 12, lineHeight: 1 }}>{statusCfg.label}</Typography.Text>
        {status?.last_deploy_at && (
          <Typography.Text type="secondary" style={{ fontSize: 11, lineHeight: 1 }}>
            {formatTime(status.last_deploy_at)}
          </Typography.Text>
        )}
      </div>
    </Popover>
  );
};

export default DeployStatusIndicator;
