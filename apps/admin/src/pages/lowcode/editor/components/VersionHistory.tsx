/**
 * 版本历史面板 - 以 Drawer 形式展示页面的版本历史列表，
 * 支持查看、回滚到指定版本。
 */

import React, { useCallback, useEffect, useState } from 'react';
import {
  Button,
  Drawer,
  Empty,
  List,
  Popconfirm,
  Skeleton,
  Space,
  Tag,
  Typography,
  message,
} from 'antd';
import {
  HistoryOutlined,
  RollbackOutlined,
  CheckCircleFilled,
} from '@ant-design/icons';
import dayjs from 'dayjs';
import { lowcodeApi, VersionItem } from '@hospital/api';
import { useEditorStore } from '../store';

interface VersionHistoryProps {
  /** Drawer 可见性 */
  open: boolean;
  /** 关闭 Drawer */
  onClose: () => void;
}

const VersionHistory: React.FC<VersionHistoryProps> = ({ open, onClose }) => {
  const [versions, setVersions] = useState<VersionItem[]>([]);
  const [currentVersion, setCurrentVersion] = useState(0);
  const [loading, setLoading] = useState(false);
  const [rollingBack, setRollingBack] = useState<string | null>(null);

  const pageId = useEditorStore((s) => s.pageId);
  const setSchema = useEditorStore((s) => s.setSchema);
  const markSaved = useEditorStore((s) => s.markSaved);

  /** 加载版本历史 */
  const fetchVersions = useCallback(async () => {
    if (!pageId || !open) return;
    setLoading(true);
    try {
      const res = await lowcodeApi.getVersions(pageId);
      setVersions(res.versions);
      setCurrentVersion(res.currentVersion);
    } catch (err) {
      message.error('加载版本历史失败');
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, [pageId, open]);

  useEffect(() => {
    fetchVersions();
  }, [fetchVersions]);

  /** 回滚到指定版本 */
  const handleRollback = useCallback(
    async (version: VersionItem) => {
      if (!pageId) return;
      setRollingBack(version.id);
      try {
        const page = await lowcodeApi.rollbackVersion(pageId, version.id);
        // 用回滚后的 schemaData 更新编辑器状态
        if (page.schemaData && Object.keys(page.schemaData).length > 0) {
          setSchema(page.schemaData as any);
        }
        markSaved();
        message.success(`已回滚到 v${version.version}`);
        // 自动刷新版本列表
        fetchVersions();
      } catch (err) {
        message.error('回滚失败');
        console.error(err);
      } finally {
        setRollingBack(null);
      }
    },
    [pageId, setSchema, markSaved, fetchVersions],
  );

  /** 格式化时间 */
  const formatTime = (iso?: string): string => {
    if (!iso) return '-';
    return dayjs(iso).format('YYYY-MM-DD HH:mm');
  };

  return (
    <Drawer
      title={
        <Space>
          <HistoryOutlined />
          <span>版本历史</span>
        </Space>
      }
      open={open}
      onClose={onClose}
      width={400}
      destroyOnClose
    >
      <Skeleton active loading={loading} paragraph={{ rows: 6 }}>
        {versions.length === 0 ? (
          <Empty description="暂无版本记录" image={Empty.PRESENTED_IMAGE_SIMPLE} />
        ) : (
          <List
            dataSource={versions}
            renderItem={(item) => {
              const isCurrent = item.version === currentVersion;
              const isRollingBack = rollingBack === item.id;
              return (
                <List.Item
                  style={{
                    backgroundColor: isCurrent ? '#f6ffed' : undefined,
                    borderLeft: isCurrent ? '3px solid #52c41a' : undefined,
                    padding: '12px 16px',
                  }}
                  actions={
                    !isCurrent
                      ? [
                          <Popconfirm
                            key="rollback"
                            title="确认回滚"
                            description={`确定要回滚到 v${item.version} 吗？当前未保存的更改将丢失。`}
                            onConfirm={() => handleRollback(item)}
                            okText="确认"
                            cancelText="取消"
                            okButtonProps={{ danger: true }}
                          >
                            <Button
                              type="link"
                              size="small"
                              icon={<RollbackOutlined />}
                              loading={isRollingBack}
                              danger
                            >
                              回滚
                            </Button>
                          </Popconfirm>,
                        ]
                      : undefined
                  }
                >
                  <List.Item.Meta
                    title={
                      <Space>
                        <Typography.Text strong>
                          v{item.version}
                        </Typography.Text>
                        {isCurrent && (
                          <Tag icon={<CheckCircleFilled />} color="success">
                            当前版本
                          </Tag>
                        )}
                        {item.snapshotLabel && (
                          <Tag>{item.snapshotLabel}</Tag>
                        )}
                      </Space>
                    }
                    description={
                      <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                        {formatTime(item.createdAt)}
                        {item.createdBy ? ` | ${item.createdBy}` : ''}
                      </Typography.Text>
                    }
                  />
                </List.Item>
              );
            }}
          />
        )}
      </Skeleton>

      <div style={{ marginTop: 16, textAlign: 'right' }}>
        <Button onClick={fetchVersions} loading={loading}>
          刷新
        </Button>
      </div>
    </Drawer>
  );
};

export default VersionHistory;
