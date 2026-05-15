import {
  BellOutlined,
  CheckOutlined,
  DownOutlined,
  EyeOutlined,
  DeleteOutlined,
  AppstoreOutlined,
  ClockCircleOutlined,
} from '@ant-design/icons';
import { history, useModel } from '@umijs/max';
import {
  Badge,
  Tooltip,
  Popover,
  List,
  Empty,
  Spin,
  Button,
  Typography,
  Space,
  App,
  Tag,
  Dropdown,
  Tabs,
  Divider,
} from 'antd';
import type { MenuProps } from 'antd';
import { useState, useCallback, useEffect, useMemo } from 'react';
import { messageApi } from '@hospital/api';
import type { Message } from './types';
import dayjs from 'dayjs';
import relativeTime from 'dayjs/plugin/relativeTime';
import 'dayjs/locale/zh-cn';
import styles from './index.less';

dayjs.extend(relativeTime);
dayjs.locale('zh-cn');

const { Text } = Typography;

export const NotificationButton: React.FC = () => {
  const { message } = App.useApp();
  const { initialState } = useModel('@@initialState');
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [unreadCount, setUnreadCount] = useState(0);
  const [messages, setMessages] = useState<Message[]>([]);
  const [activeTab, setActiveTab] = useState('all');

  const currentUser = initialState?.currentUser;

  const fetchUnreadCount = useCallback(async () => {
    if (!currentUser?.id) return;
    try {
      const res = await messageApi.getUnreadCount(currentUser.id, 'admin');
      setUnreadCount(res?.total || 0);
    } catch (error) {
      console.error('获取未读消息数量失败:', error);
    }
  }, [currentUser?.id]);

  const fetchMessages = useCallback(async () => {
    if (!currentUser?.id) return;
    setLoading(true);
    try {
      const res = await messageApi.getList({
        userId: currentUser.id,
        userType: 'admin',
        page: 1,
        pageSize: 10,
      });
      setMessages(res?.items || []);
    } catch (error) {
      console.error('获取消息列表失败:', error);
    } finally {
      setLoading(false);
    }
  }, [currentUser?.id]);

  useEffect(() => {
    fetchUnreadCount();
    const timer = setInterval(fetchUnreadCount, 60000);
    return () => clearInterval(timer);
  }, [fetchUnreadCount]);

  useEffect(() => {
    if (open) {
      fetchMessages();
    }
  }, [open, fetchMessages]);

  const handleMarkAsRead = useCallback(async (messageId: string, event?: React.MouseEvent) => {
    event?.stopPropagation();
    if (!currentUser?.id) return;
    try {
      await messageApi.markAsRead(messageId, currentUser.id);
      fetchMessages();
      fetchUnreadCount();
    } catch (error) {
      console.error('标记已读失败:', error);
    }
  }, [currentUser?.id, fetchMessages, fetchUnreadCount]);

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

  const handleMessageKeyDown = useCallback((item: Message, e: React.KeyboardEvent) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      if (!item.isRead) {
        handleMarkAsRead(item.id);
      }
    }
  }, [handleMarkAsRead]);

  const handleDeleteMessage = useCallback(async (messageId: string, event?: React.MouseEvent) => {
    event?.stopPropagation();
    if (!currentUser?.id) return;
    try {
      await messageApi.delete(messageId, currentUser.id);
      fetchMessages();
      fetchUnreadCount();
      message.success('删除成功');
    } catch (error) {
      console.error('删除消息失败:', error);
    }
  }, [currentUser?.id, fetchMessages, fetchUnreadCount, message]);

  const handleViewAll = useCallback(() => {
    setOpen(false);
    history.push('/content-center/message');
  }, []);

  const messageTypeConfig: Record<string, { color: string; text: string; icon: React.ReactNode }> = {
    system: { color: 'blue', text: '系统', icon: <BellOutlined /> },
    appointment: { color: 'green', text: '预约', icon: <CheckOutlined /> },
    consultation: { color: 'cyan', text: '就诊', icon: <EyeOutlined /> },
    schedule: { color: 'orange', text: '排班', icon: <ClockCircleOutlined /> },
    stop_clinic: { color: 'red', text: '停诊', icon: <ClockCircleOutlined /> },
    feedback: { color: 'purple', text: '反馈', icon: <BellOutlined /> },
  };

  const filteredMessages = useMemo(() => {
    if (activeTab === 'all') return messages;
    if (activeTab === 'unread') return messages.filter(m => !m.isRead);
    return messages.filter(m => m.messageType === activeTab);
  }, [messages, activeTab]);

  const messageCounts = useMemo(() => {
    const counts: Record<string, number> = {
      all: messages.length,
      unread: messages.filter(m => !m.isRead).length,
      system: 0,
      appointment: 0,
    };
    messages.forEach(m => {
      if (counts[m.messageType] !== undefined) {
        counts[m.messageType]++;
      }
    });
    return counts;
  }, [messages]);

  const renderMessageActions = (item: Message) => {
    const items: MenuProps['items'] = [
      !item.isRead && {
        key: 'read',
        icon: <EyeOutlined />,
        label: '标为已读',
        'aria-label': `标记消息"${item.title}"为已读`,
        onClick: (e) => handleMarkAsRead(item.id, e.domEvent),
      },
      {
        key: 'delete',
        icon: <DeleteOutlined />,
        label: '删除',
        danger: true,
        'aria-label': `删除消息"${item.title}"`,
        onClick: (e) => handleDeleteMessage(item.id, e.domEvent),
      },
    ].filter(Boolean);

    if (items.length === 0) return null;

    return (
      <Dropdown menu={{ items }} trigger={['click']} placement="bottomRight">
        <Button
          type="text"
          size="small"
          icon={<DownOutlined />}
          onClick={(e) => e.stopPropagation()}
          className={styles.messageActionBtn}
        />
      </Dropdown>
    );
  };

  const tabItems = [
    { key: 'all', label: '全部', count: messageCounts.all },
    { key: 'unread', label: '未读', count: messageCounts.unread },
    { key: 'system', label: '系统', count: messageCounts.system },
    { key: 'appointment', label: '预约', count: messageCounts.appointment },
  ].filter(tab => tab.count > 0 || tab.key === 'all' || tab.key === 'unread');

  const content = (
    <div className={styles.notificationPanel}>
      <div className={styles.panelHeader}>
        <Space size={12}>
          <BellOutlined className={styles.headerIcon} />
          <span className={styles.panelTitle}>消息通知</span>
          {unreadCount > 0 && (
            <Badge count={unreadCount} size="small" />
          )}
        </Space>
        {unreadCount > 0 && (
          <Button
            type="text"
            size="small"
            icon={<CheckOutlined />}
            onClick={handleMarkAllAsRead}
            className={styles.headerActionBtn}
            aria-label={`标记全部${unreadCount}条消息为已读`}
          >
            全部已读
          </Button>
        )}
      </div>

      <Divider className={styles.headerDivider} />

      <Tabs
        activeKey={activeTab}
        onChange={setActiveTab}
        className={styles.messageTabs}
        items={tabItems.map(tab => ({
          key: tab.key,
          label: (
            <Space size={4}>
              <span>{tab.label}</span>
              {tab.count > 0 && (
                <Badge count={tab.count} size="small" />
              )}
            </Space>
          ),
        }))}
      />

      <Spin spinning={loading}>
        {filteredMessages.length > 0 ? (
          <List
            className={styles.messageList}
            dataSource={filteredMessages}
            role="list"
            aria-label="消息列表"
            renderItem={(item) => {
              const config = messageTypeConfig[item.messageType] || messageTypeConfig.system;
              return (
                <List.Item
                  className={`${styles.messageItem} ${!item.isRead ? styles.unread : ''}`}
                  onClick={() => {
                    if (!item.isRead) {
                      handleMarkAsRead(item.id);
                    }
                  }}
                  onKeyDown={(e) => handleMessageKeyDown(item, e)}
                  tabIndex={0}
                  role="listitem"
                  aria-label={
                    !item.isRead
                      ? `未读消息: ${item.title}, ${item.content || ''}, ${config.text}`
                      : `消息: ${item.title}, ${item.content || ''}, ${config.text}`
                  }
                >
                  <div className={styles.messageContent}>
                    <div className={styles.messageHeader}>
                      <Space size={8}>
                        <Tag color={config.color} icon={config.icon} className={styles.messageTypeTag}>
                          {config.text}
                        </Tag>
                        {!item.isRead && <Badge status="processing" aria-label="未读" />}
                      </Space>
                      {renderMessageActions(item)}
                    </div>
                    <div className={styles.messageTitleWrapper}>
                      <Text
                        strong={!item.isRead}
                        className={styles.messageTitle}
                        ellipsis={{ tooltip: item.title }}
                      >
                        {item.title}
                        {!item.isRead && <span style={{ position: 'absolute', width: 1, height: 1, padding: 0, margin: '-1px', overflow: 'hidden', clip: 'rect(0,0,0,0)', whiteSpace: 'nowrap', borderWidth: 0 }}>（未读）</span>}
                      </Text>
                    </div>
                    {item.content && (
                      <Text
                        type="secondary"
                        ellipsis={{ tooltip: item.content }}
                        className={styles.messageDesc}
                      >
                        {item.content}
                      </Text>
                    )}
                    <Text type="secondary" className={styles.messageTime}>
                      {dayjs(item.createdAt).fromNow()}
                    </Text>
                  </div>
                </List.Item>
              );
            }}
          />
        ) : (
          <Empty
            image={Empty.PRESENTED_IMAGE_SIMPLE}
            description={
              activeTab === 'unread' ? '暂无未读消息' : '暂无消息'
            }
            className={styles.emptyState}
          />
        )}
      </Spin>

      <Divider className={styles.footerDivider} />

      <div className={styles.panelFooter}>
        <Button type="link" icon={<AppstoreOutlined />} onClick={handleViewAll}>
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
      onOpenChange={(visible) => {
        setOpen(visible);
        if (visible && filteredMessages.length > 0) {
          setTimeout(() => {
            const firstMessageItem = document.querySelector(`.${styles.messageItem}`) as HTMLElement;
            firstMessageItem?.focus();
          }, 100);
        }
      }}
      placement="bottomRight"
      classNames={{ root: styles.notificationPopover }}
      arrow={false}
      destroyOnHidden
    >
      <Tooltip title="消息通知" open={open ? false : undefined}>
        <div
          className={styles.actionItem}
          role="button"
          tabIndex={0}
          aria-label={`消息通知，${unreadCount}条未读`}
          onKeyDown={(e) => {
            if (e.key === 'Enter' || e.key === ' ') {
              e.preventDefault();
              setOpen(!open);
            } else if (e.key === 'Escape' && open) {
              setOpen(false);
            }
          }}
        >
          <Badge count={unreadCount} size="small" offset={[2, -2]}>
            <BellOutlined className={styles.bellIcon} />
          </Badge>
        </div>
      </Tooltip>
    </Popover>
  );
};
