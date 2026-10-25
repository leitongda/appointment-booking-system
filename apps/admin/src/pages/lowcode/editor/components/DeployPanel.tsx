/**
 * 部署面板 — 管理低代码页面的小程序部署流水线。
 *
 * 功能:
 * 1. 当前部署状态展示 (idle/building/built/uploading/auditing/published/failed)
 * 2. 一键部署按钮，触发完整部署流水线
 * 3. 预览按钮，生成小程序体验二维码
 * 4. 回滚按钮，支持版本选择
 * 5. 部署历史列表，含时间戳和状态
 * 6. 构建中实时轮询 (每 5s)
 */

import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {Button, Card, Drawer, Empty, List, Popconfirm, QRCode, Select, Skeleton, Space, Spin, Tag, Timeline, Tooltip, Typography, message} from 'antd';
import {CloudUploadOutlined, HistoryOutlined, QrcodeOutlined, ReloadOutlined, RollbackOutlined, RocketOutlined, CheckCircleFilled, CloseCircleFilled, ClockCircleOutlined, SyncOutlined, WarningOutlined, FileTextOutlined} from '@ant-design/icons';
import dayjs from 'dayjs';
import {lowcodeApi, type DeployStatus, type DeployStatusResponse, type DeployHistoryItem, type PreviewQrResponse} from '@hospital/api';
import {useEditorStore} from '../store';

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

/** 部署状态配置: 标签颜色 + 显示文本 */
const DEPLOY_STATUS_MAP: Record<DeployStatus, { color: string; label: string }> = {
  idle: { color: 'default', label: '待部署' },
  building: { color: 'processing', label: '构建中' },
  built: { color: 'cyan', label: '已构建' },
  uploading: { color: 'processing', label: '上传中' },
  uploaded: { color: 'cyan', label: '已上传' },
  auditing: { color: 'warning', label: '审核中' },
  published: { color: 'success', label: '已发布' },
  failed: { color: 'error', label: '构建失败' },
};

/** 流水线阶段步骤（用于 Timeline 展示） */
const PIPELINE_STAGES: { key: DeployStatus; label: string }[] = [
  { key: 'building', label: '代码生成 & 构建' },
  { key: 'uploading', label: '上传到微信平台' },
  { key: 'auditing', label: '提交审核' },
  { key: 'published', label: '发布上线' },
];

/** 轮询间隔 (ms) */
const POLL_INTERVAL = 5000;

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** 获取某个阶段在当前状态下的 Timeline 节点颜色 */
function getStageColor(
  stageStatus: DeployStatus,
  currentStatus: DeployStatus,
): 'gray' | 'blue' | 'green' | 'red' {
  const stageOrder = PIPELINE_STAGES.map((s) => s.key);
  const currentIdx = stageOrder.indexOf(currentStatus);
  const stageIdx = stageOrder.indexOf(stageStatus);

  if (currentStatus === 'failed') {
    // failed 时，到当前阶段之前（含）标红
    if (stageIdx <= currentIdx) return 'red';
    return 'gray';
  }

  if (stageIdx < currentIdx) return 'green'; // 已完成
  if (stageIdx === currentIdx) return 'blue'; // 进行中
  return 'gray'; // 未开始
}

/** 是否处于终态 (部署完成或失败，停止轮询) */
function isTerminalStatus(status: DeployStatus): boolean {
  return status === 'published' || status === 'failed' || status === 'idle';
}

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface DeployPanelProps {
  /** Drawer 可见性 */
  open: boolean;
  /** 关闭 Drawer */
  onClose: () => void;
}

// ---------------------------------------------------------------------------
// DeployPanel
// ---------------------------------------------------------------------------

const DeployPanel: React.FC<DeployPanelProps> = ({ open, onClose }) => {
  // --- Store ---
  const pageId = useEditorStore((s) => s.pageId);

  // --- Local state ---
  const [deployStatus, setDeployStatus] = useState<DeployStatusResponse | null>(null);
  const [history, setHistory] = useState<DeployHistoryItem[]>([]);
  const [statusLoading, _setStatusLoading] = useState(false);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [deploying, setDeploying] = useState(false);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [previewData, setPreviewData] = useState<PreviewQrResponse | null>(null);
  const [showPreview, setShowPreview] = useState(false);
  const [rollbackTarget, setRollbackTarget] = useState<string | undefined>(undefined);
  const [rollingBack, setRollingBack] = useState(false);

  // 轮询 timer
  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // --- Derived ---
  const currentStatus: DeployStatus = deployStatus?.deploy_status ?? 'idle';
  const isPolling = !isTerminalStatus(currentStatus) && currentStatus !== 'idle';

  /** 可回滚的历史版本列表（已构建成功且非当前版本） */
  const rollbackOptions = useMemo(() => {
    return history
      .filter((h) => h.status === 'completed' && h.artifact_url)
      .map((h) => ({
        value: h.id,
        label: `${dayjs(h.created_at).format('MM-DD HH:mm')} (${h.artifact_url?.slice(0, 30) || 'unknown'})`,
      }));
  }, [history]);

  // --- Fetch helpers ---

  const fetchStatus = useCallback(async () => {
    if (!pageId || !open) return;
    try {
      const res = await lowcodeApi.getDeployStatus(pageId);
      setDeployStatus(res);
    } catch (err) {
      console.error('获取部署状态失败:', err);
    }
  }, [pageId, open]);

  const fetchHistory = useCallback(async () => {
    if (!pageId || !open) return;
    setHistoryLoading(true);
    try {
      const res = await lowcodeApi.getDeployHistory(pageId);
      setHistory(res.data);
    } catch (err) {
      console.error('获取部署历史失败:', err);
    } finally {
      setHistoryLoading(false);
    }
  }, [pageId, open]);

  /** 打开时加载数据 */
  useEffect(() => {
    if (open) {
      fetchStatus();
      fetchHistory();
      setPreviewData(null);
      setShowPreview(false);
      setRollbackTarget(undefined);
    }
  }, [open, fetchStatus, fetchHistory]);

  /** 轮询部署状态 */
  useEffect(() => {
    if (pollingRef.current) {
      clearInterval(pollingRef.current);
      pollingRef.current = null;
    }

    if (isPolling) {
      pollingRef.current = setInterval(() => {
        fetchStatus();
      }, POLL_INTERVAL);
    }

    return () => {
      if (pollingRef.current) {
        clearInterval(pollingRef.current);
        pollingRef.current = null;
      }
    };
  }, [isPolling, fetchStatus]);

  /** 状态变为终态时刷新历史 */
  useEffect(() => {
    if (isTerminalStatus(currentStatus) && currentStatus !== 'idle') {
      fetchHistory();
    }
  }, [currentStatus, fetchHistory]);

  // --- Actions ---

  /** 触发部署 */
  const handleDeploy = useCallback(async () => {
    if (!pageId) return;
    setDeploying(true);
    try {
      await lowcodeApi.triggerDeploy(pageId);
      message.success('部署流水线已启动');
      // 立即刷新状态以开始轮询
      await fetchStatus();
    } catch (err: any) {
      const msg = err?.message || '部署启动失败';
      message.error(msg);
    } finally {
      setDeploying(false);
    }
  }, [pageId, fetchStatus]);

  /** 生成预览二维码 */
  const handlePreview = useCallback(async () => {
    if (!pageId) return;
    setPreviewLoading(true);
    setShowPreview(true);
    try {
      const res = await lowcodeApi.generatePreviewQr(pageId);
      setPreviewData(res);
    } catch (err: any) {
      message.error(err?.message || '生成预览二维码失败');
      setShowPreview(false);
    } finally {
      setPreviewLoading(false);
    }
  }, [pageId]);

  /** 执行回滚 */
  const handleRollback = useCallback(async () => {
    if (!pageId || !rollbackTarget) return;
    setRollingBack(true);
    try {
      await lowcodeApi.rollbackDeploy(pageId, rollbackTarget);
      message.success('回滚成功');
      await fetchStatus();
      await fetchHistory();
      setRollbackTarget(undefined);
    } catch (err: any) {
      message.error(err?.message || '回滚失败');
    } finally {
      setRollingBack(false);
    }
  }, [pageId, rollbackTarget, fetchStatus, fetchHistory]);

  /** 格式化时间 */
  const formatTime = (iso?: string | null): string => {
    if (!iso) return '-';
    return dayjs(iso).format('YYYY-MM-DD HH:mm:ss');
  };

  // --- Timeline steps ---
  const timelineItems = useMemo(() => {
    return PIPELINE_STAGES.map((stage) => {
      const color = getStageColor(stage.key, currentStatus);
      const isActive = stage.key === currentStatus;
      const isFailed = currentStatus === 'failed' && color === 'red';

      return {
        color,
        dot: isFailed ? <CloseCircleFilled style={{ color: 'var(--color-error)' }} /> : undefined,
        children: (
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <span>{stage.label}</span>
            {isActive && !isFailed && (
              <SyncOutlined spin style={{ color: 'var(--color-primary)', fontSize: 12 }} />
            )}
            {color === 'green' && (
              <CheckCircleFilled style={{ color: 'var(--color-success)', fontSize: 12 }} />
            )}
          </div>
        ),
      };
    });
  }, [currentStatus]);

  // --- Render ---

  const statusConfig = DEPLOY_STATUS_MAP[currentStatus];

  return (
    <Drawer
      title={
        <Space>
          <CloudUploadOutlined />
          <span>部署管理</span>
          <Tag color={statusConfig.color}>{statusConfig.label}</Tag>
        </Space>
      }
      open={open}
      onClose={onClose}
      width={460}
      destroyOnClose
    >
      <Skeleton active loading={statusLoading && !deployStatus} paragraph={{ rows: 4 }}>
        {/* ===== 部署状态卡片 ===== */}
        <Card
          title="当前状态"
          size="small"
          style={{ marginBottom: 16 }}
          extra={
            <Tooltip title="刷新状态">
              <Button
                type="text"
                size="small"
                icon={<ReloadOutlined />}
                onClick={() => {
                  fetchStatus();
                  fetchHistory();
                }}
                loading={statusLoading}
              />
            </Tooltip>
          }
        >
          <div style={{ marginBottom: 16 }}>
            <Space direction="vertical" size={4} style={{ width: '100%' }}>
              <div>
                <span style={{ color: 'var(--color-text-tertiary)', fontSize: 12 }}>状态：</span>
                <Tag color={statusConfig.color} style={{ marginLeft: 4 }}>
                  {statusConfig.label}
                </Tag>
                {isPolling && (
                  <Tag icon={<SyncOutlined spin />} color="processing">
                    实时监控中
                  </Tag>
                )}
              </div>
              {deployStatus?.last_deploy_at && (
                <div>
                  <span style={{ color: 'var(--color-text-tertiary)', fontSize: 12 }}>
                    上次部署：{formatTime(deployStatus.last_deploy_at)}
                  </span>
                </div>
              )}
              {deployStatus?.build_job && (
                <div>
                  <span style={{ color: 'var(--color-text-tertiary)', fontSize: 12 }}>
                    构建任务：
                    <Tooltip title={deployStatus.build_job.id}>
                      <Typography.Text code style={{ fontSize: 11 }}>
                        {deployStatus.build_job.id.slice(0, 12)}...
                      </Typography.Text>
                    </Tooltip>
                  </span>
                </div>
              )}
            </Space>
          </div>

          {/* 流水线步骤进度 */}
          <div style={{ marginBottom: 16 }}>
            <div style={{ fontSize: 12, color: 'var(--color-text-tertiary)', marginBottom: 8 }}>流水线进度</div>
            <Timeline items={timelineItems} />
          </div>

          {/* 构建日志 (失败时展示) */}
          {currentStatus === 'failed' && deployStatus?.build_job?.build_log && (
            <div style={{ marginBottom: 16 }}>
              <div style={{ fontSize: 12, color: 'var(--color-text-tertiary)', marginBottom: 4 }}>
                <WarningOutlined style={{ color: 'var(--color-error)', marginRight: 4 }} />
                构建日志
              </div>
              <pre
                style={{
                  background: '#1e1e1e',
                  color: '#d4d4d4',
                  padding: 12,
                  borderRadius: 6,
                  fontSize: 11,
                  maxHeight: 160,
                  overflow: 'auto',
                  margin: 0,
                }}
              >
                {deployStatus.build_job.build_log}
              </pre>
            </div>
          )}
        </Card>

        {/* ===== 操作按钮 ===== */}
        <Card title="操作" size="small" style={{ marginBottom: 16 }}>
          <Space direction="vertical" style={{ width: '100%' }} size={12}>
            {/* 部署按钮 */}
            <Button
              type="primary"
              icon={<RocketOutlined />}
              onClick={handleDeploy}
              loading={deploying || isPolling}
              block
              disabled={!pageId}
            >
              {isPolling ? '部署进行中...' : currentStatus === 'failed' ? '重新部署' : '开始部署'}
            </Button>

            {/* 预览二维码按钮 */}
            <Button
              icon={<QrcodeOutlined />}
              onClick={handlePreview}
              loading={previewLoading}
              block
              disabled={!pageId}
            >
              生成预览二维码
            </Button>

            {/* 预览二维码展示 */}
            {showPreview && (
              <div
                style={{
                  textAlign: 'center',
                  padding: 16,
                  border: '1px solid var(--color-border-secondary)',
                  borderRadius: 8,
                  background: 'var(--color-bg-container)',
                }}
              >
                <Spin spinning={previewLoading}>
                  {previewData ? (
                    <Space direction="vertical" align="center" size={8}>
                      <QRCode value={previewData.qr_code_url} size={180} />
                      <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                        扫码预览小程序
                      </Typography.Text>
                      <Typography.Text type="secondary" style={{ fontSize: 11 }}>
                        {previewData.message}
                      </Typography.Text>
                    </Space>
                  ) : (
                    !previewLoading && (
                      <Typography.Text type="secondary">生成中...</Typography.Text>
                    )
                  )}
                </Spin>
              </div>
            )}

            {/* 回滚区域 */}
            <div
              style={{
                padding: 12,
                border: '1px solid var(--color-border-secondary)',
                borderRadius: 8,
                background: 'var(--color-bg-container)',
              }}
            >
              <div style={{ fontSize: 12, color: 'var(--color-text-tertiary)', marginBottom: 8 }}>版本回滚</div>
              <Space.Compact style={{ width: '100%' }}>
                <Select
                  placeholder="选择回滚目标版本"
                  options={rollbackOptions}
                  value={rollbackTarget}
                  onChange={setRollbackTarget}
                  style={{ flex: 1 }}
                  allowClear
                  disabled={rollbackOptions.length === 0}
                />
                <Popconfirm
                  title="确认回滚"
                  description="将部署回滚到所选版本，当前发布版本将被替换。"
                  onConfirm={handleRollback}
                  okText="确认回滚"
                  cancelText="取消"
                  okButtonProps={{ danger: true, loading: rollingBack }}
                  disabled={!rollbackTarget}
                >
                  <Button
                    icon={<RollbackOutlined />}
                    danger
                    disabled={!rollbackTarget || rollingBack}
                    loading={rollingBack}
                  >
                    回滚
                  </Button>
                </Popconfirm>
              </Space.Compact>
              {rollbackOptions.length === 0 && (
                <Typography.Text type="secondary" style={{ fontSize: 11, display: 'block', marginTop: 4 }}>
                  暂无可回滚的历史版本
                </Typography.Text>
              )}
            </div>
          </Space>
        </Card>

        {/* ===== 部署历史 ===== */}
        <Card
          title={
            <Space>
              <HistoryOutlined />
              <span>部署历史</span>
            </Space>
          }
          size="small"
        >
          <Skeleton active loading={historyLoading} paragraph={{ rows: 3 }}>
            {history.length === 0 ? (
              <Empty
                description="暂无部署记录"
                image={Empty.PRESENTED_IMAGE_SIMPLE}
              />
            ) : (
              <List
                dataSource={history}
                size="small"
                pagination={history.length > 10 ? { pageSize: 10, size: 'small' } : false}
                renderItem={(item) => {
                  const isCompleted = item.status === 'completed';
                  const isFailed = item.status === 'failed';
                  const isPending = item.status === 'pending';
                  const tagColor = isCompleted ? 'success' : isFailed ? 'error' : isPending ? 'processing' : 'default';
                  const tagLabel = isCompleted ? '成功' : isFailed ? '失败' : isPending ? '进行中' : item.status;

                  return (
                    <List.Item
                      style={{ padding: '8px 0' }}
                      extra={
                        <Tag color={tagColor} icon={isPending ? <SyncOutlined spin /> : undefined}>
                          {tagLabel}
                        </Tag>
                      }
                    >
                      <List.Item.Meta
                        avatar={
                          isCompleted ? (
                            <CheckCircleFilled style={{ color: 'var(--color-success)', fontSize: 16, marginTop: 4 }} />
                          ) : isFailed ? (
                            <CloseCircleFilled style={{ color: 'var(--color-error)', fontSize: 16, marginTop: 4 }} />
                          ) : (
                            <ClockCircleOutlined style={{ color: 'var(--color-primary)', fontSize: 16, marginTop: 4 }} />
                          )
                        }
                        title={
                          <span style={{ fontSize: 13 }}>
                            {dayjs(item.created_at).format('YYYY-MM-DD HH:mm:ss')}
                          </span>
                        }
                        description={
                          <div style={{ fontSize: 11, color: 'var(--color-text-tertiary)' }}>
                            {item.trigger_source && <span>来源: {item.trigger_source} | </span>}
                            {item.artifact_url && (
                              <Tooltip title={item.artifact_url}>
                                <span style={{ cursor: 'pointer' }}>
                                  <FileTextOutlined /> 构建产物
                                </span>
                              </Tooltip>
                            )}
                            {item.finished_at && item.started_at && (
                              <span style={{ marginLeft: 4 }}>
                                耗时: {((new Date(item.finished_at).getTime() - new Date(item.started_at).getTime()) / 1000).toFixed(0)}s
                              </span>
                            )}
                          </div>
                        }
                      />
                    </List.Item>
                  );
                }}
              />
            )}
          </Skeleton>
        </Card>
      </Skeleton>
    </Drawer>
  );
};

export default DeployPanel;
