import {
  FullscreenOutlined,
  FullscreenExitOutlined,
  BellOutlined,
  ReloadOutlined,
  CheckOutlined,
} from '@ant-design/icons';
import { history, useModel } from '@umijs/max';
import { Badge, Tooltip, Popover, List, Empty, Spin, Button, Typography, Space, App } from 'antd';
import React, { useState, useEffect, useCallback } from 'react';
import { messageApi } from '@hospital/api';
import dayjs from 'dayjs';
import relativeTime from 'dayjs/plugin/relativeTime';
import 'dayjs/locale/zh-cn';
import styles from './index.less';

dayjs.extend(relativeTime);
dayjs.locale('zh-cn');

const { Text } = Typography;

// 全屏按钮组件
export const FullscreenButton: React.FC = () => {
  const [isFullscreen, setIsFullscreen] = useState(false);

  useEffect(() => {
    const handleFullscreenChange = () => {
      setIsFullscreen(!!document.fullscreenElement);
    };

    document.addEventListener('fullscreenchange', handleFullscreenChange);
    return () => {
      document.removeEventListener('fullscreenchange', handleFullscreenChange);
    };
  }, []);

  const toggleFullscreen = useCallback(async () => {
    try {
      if (!document.fullscreenElement) {
        await document.documentElement.requestFullscreen();
      } else {
        await document.exitFullscreen();
      }
    } catch (error) {
      console.error('全屏切换失败:', error);
    }
  }, []);

  return (
    <Tooltip title={isFullscreen ? '退出全屏' : '全屏'}>
      <div className={styles.actionItem} onClick={toggleFullscreen}>
        {isFullscreen ? <FullscreenExitOutlined /> : <FullscreenOutlined />}
      </div>
    </Tooltip>
  );
};

// 刷新按钮组件
export const RefreshButton: React.FC = () => {
  const [spinning, setSpinning] = useState(false);

  const handleRefresh = useCallback(() => {
    setSpinning(true);
    // 给一个小延迟来展示动画效果
    setTimeout(() => {
      window.location.reload();
    }, 300);
  }, []);

  return (
    <Tooltip title="刷新页面">
      <div className={styles.actionItem} onClick={handleRefresh}>
        <ReloadOutlined spin={spinning} />
      </div>
    </Tooltip>
  );
};

// 消息通知组件
interface Message {
  id: string;
  title: string;
  content?: string;
  message_type: string;
  is_read: number;
  created_at: string;
}

export const NotificationButton: React.FC = () => {
  const { message } = App.useApp();
  const { initialState } = useModel('@@initialState');
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [unreadCount, setUnreadCount] = useState(0);
  const [messages, setMessages] = useState<Message[]>([]);

  const currentUser = initialState?.currentUser;

  // 获取未读消息数量
  const fetchUnreadCount = useCallback(async () => {
    if (!currentUser?.id) return;
    try {
      const res = await messageApi.getUnreadCount(currentUser.id, 'admin');
      setUnreadCount(res?.total || 0);
    } catch (error) {
      console.error('获取未读消息数量失败:', error);
    }
  }, [currentUser?.id]);

  // 获取消息列表
  const fetchMessages = useCallback(async () => {
    if (!currentUser?.id) return;
    setLoading(true);
    try {
      const res = await messageApi.getList({
        userId: currentUser.id,
        userType: 'admin',
        page: 1,
        pageSize: 5,
      });
      setMessages(res?.items || []);
    } catch (error) {
      console.error('获取消息列表失败:', error);
    } finally {
      setLoading(false);
    }
  }, [currentUser?.id]);

  // 初始化时获取未读数量
  useEffect(() => {
    fetchUnreadCount();
    // 每分钟刷新一次未读数量
    const timer = setInterval(fetchUnreadCount, 60000);
    return () => clearInterval(timer);
  }, [fetchUnreadCount]);

  // 打开弹窗时获取消息列表
  useEffect(() => {
    if (open) {
      fetchMessages();
    }
  }, [open, fetchMessages]);

  // 标记消息已读
  const handleMarkAsRead = useCallback(async (messageId: string) => {
    if (!currentUser?.id) return;
    try {
      await messageApi.markAsRead(messageId, currentUser.id);
      fetchMessages();
      fetchUnreadCount();
    } catch (error) {
      console.error('标记已读失败:', error);
    }
  }, [currentUser?.id, fetchMessages, fetchUnreadCount]);

  // 标记全部已读
  const handleMarkAllAsRead = useCallback(async () => {
    if (!currentUser?.id) return;
    try {
      await messageApi.markAllAsRead(currentUser.id, 'admin');
      message.success('已全部标记为已读');
      fetchMessages();
      fetchUnreadCount();
    } catch (error) {
      console.error('标记全部已读失败:', error);
    }
  }, [currentUser?.id, fetchMessages, fetchUnreadCount, message]);

  // 查看全部消息
  const handleViewAll = useCallback(() => {
    setOpen(false);
    history.push('/message');
  }, []);

  // 消息类型映射
  const messageTypeMap: Record<string, { color: string; text: string }> = {
    system: { color: '#1890ff', text: '系统' },
    appointment: { color: '#52c41a', text: '预约' },
    notification: { color: '#faad14', text: '通知' },
    reminder: { color: '#eb2f96', text: '提醒' },
  };

  const content = (
    <div className={styles.notificationPanel}>
      <div className={styles.panelHeader}>
        <span className={styles.panelTitle}>消息通知</span>
        {unreadCount > 0 && (
          <Button 
            type="link" 
            size="small" 
            icon={<CheckOutlined />}
            onClick={handleMarkAllAsRead}
          >
            全部已读
          </Button>
        )}
      </div>
      <Spin spinning={loading}>
        {messages.length > 0 ? (
          <List
            className={styles.messageList}
            dataSource={messages}
            renderItem={(item) => (
              <List.Item
                className={`${styles.messageItem} ${item.is_read ? '' : styles.unread}`}
                onClick={() => {
                  if (!item.is_read) {
                    handleMarkAsRead(item.id);
                  }
                }}
              >
                <div className={styles.messageContent}>
                  <div className={styles.messageHeader}>
                    <Badge 
                      color={messageTypeMap[item.message_type]?.color || '#999'} 
                      text={
                        <Text strong={!item.is_read} ellipsis className={styles.messageTitle}>
                          {item.title}
                        </Text>
                      }
                    />
                    {!item.is_read && <span className={styles.unreadDot} />}
                  </div>
                  {item.content && (
                    <Text type="secondary" ellipsis className={styles.messageDesc}>
                      {item.content}
                    </Text>
                  )}
                  <Text type="secondary" className={styles.messageTime}>
                    {dayjs(item.created_at).fromNow()}
                  </Text>
                </div>
              </List.Item>
            )}
          />
        ) : (
          <Empty 
            image={Empty.PRESENTED_IMAGE_SIMPLE} 
            description="暂无消息"
            className={styles.emptyState}
          />
        )}
      </Spin>
      <div className={styles.panelFooter}>
        <Button type="link" block onClick={handleViewAll}>
          查看全部消息
        </Button>
      </div>
    </div>
  );

  return (
    <Popover
      content={content}
      trigger="click"
      open={open}
      onOpenChange={setOpen}
      placement="bottomRight"
      overlayClassName={styles.notificationPopover}
      arrow={{ pointAtCenter: true }}
    >
      <Tooltip title="消息通知" open={open ? false : undefined}>
        <div className={styles.actionItem}>
          <Badge count={unreadCount} size="small" offset={[2, -2]}>
            <BellOutlined className={styles.bellIcon} />
          </Badge>
        </div>
      </Tooltip>
    </Popover>
  );
};

// 导出所有 Action 组件
export const HeaderActions: React.FC = () => {
  return (
    <Space className={styles.headerActions} size={4}>
      <RefreshButton />
      <NotificationButton />
      <FullscreenButton />
    </Space>
  );
};

export default HeaderActions;

