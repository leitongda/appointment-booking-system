import { useState, useEffect } from 'react';
import { List, Badge, Tabs, Empty, PullToRefresh, InfiniteScroll, SwipeAction, Toast, Dialog } from 'antd-mobile';
import { history } from 'umi';
import { messageApi } from '@hospital/api';
import type { Message, UnreadCount } from '@hospital/shared';
import styles from './index.less';

const MessagePage: React.FC = () => {
  const [activeTab, setActiveTab] = useState('all');
  const [messages, setMessages] = useState<Message[]>([]);
  const [unreadCount, setUnreadCount] = useState<UnreadCount | null>(null);
  const [loading, setLoading] = useState(false);
  const [hasMore, setHasMore] = useState(true);
  const [page, setPage] = useState(1);
  
  // 模拟用户ID，实际应从登录状态获取
  const userId = localStorage.getItem('userId') || '';
  const userType = 'patient';

  useEffect(() => {
    loadUnreadCount();
    loadMessages(1, true);
  }, [activeTab]);

  const loadUnreadCount = async () => {
    try {
      const count = await messageApi.getUnreadCount(userId, userType);
      setUnreadCount(count);
    } catch (error) {
      console.error('获取未读数失败', error);
    }
  };

  const loadMessages = async (pageNum: number, reset: boolean = false) => {
    if (loading) return;
    setLoading(true);
    
    try {
      const messageType = activeTab === 'all' ? undefined : activeTab;
      const result = await messageApi.getList({
        userId,
        userType,
        messageType,
        page: pageNum,
        pageSize: 20,
      });
      
      if (reset) {
        setMessages(result.data);
      } else {
        setMessages(prev => [...prev, ...result.data]);
      }
      
      setPage(pageNum);
      setHasMore(result.data.length === 20);
    } catch (error) {
      console.error('加载消息失败', error);
    } finally {
      setLoading(false);
    }
  };

  const handleRefresh = async () => {
    await loadMessages(1, true);
    await loadUnreadCount();
  };

  const loadMore = async () => {
    await loadMessages(page + 1);
  };

  const handleRead = async (message: Message) => {
    if (message.isRead === 0) {
      try {
        await messageApi.markAsRead(message.id, userId);
        setMessages(prev => 
          prev.map(m => m.id === message.id ? { ...m, isRead: 1 } : m)
        );
        loadUnreadCount();
      } catch (error) {
        console.error('标记已读失败', error);
      }
    }
    
    // 跳转到详情或关联页面
    if (message.relatedId) {
      if (message.messageType === 'appointment') {
        history.push(`/appointment/${message.relatedId}`);
      } else if (message.messageType === 'consultation') {
        history.push(`/records/${message.relatedId}`);
      }
    }
  };

  const handleDelete = async (messageId: string) => {
    try {
      await messageApi.delete(messageId, userId);
      setMessages(prev => prev.filter(m => m.id !== messageId));
      Toast.show({ content: '删除成功' });
    } catch (error) {
      Toast.show({ content: '删除失败' });
    }
  };

  const handleReadAll = async () => {
    const result = await Dialog.confirm({
      content: '确定将所有消息标记为已读吗？',
    });
    
    if (result) {
      try {
        const messageType = activeTab === 'all' ? undefined : activeTab;
        await messageApi.markAllAsRead(userId, userType, messageType);
        setMessages(prev => prev.map(m => ({ ...m, isRead: 1 })));
        loadUnreadCount();
        Toast.show({ content: '已全部标记为已读' });
      } catch (error) {
        Toast.show({ content: '操作失败' });
      }
    }
  };

  const getMessageIcon = (type: string) => {
    switch (type) {
      case 'appointment': return '📅';
      case 'consultation': return '🏥';
      case 'schedule': return '📋';
      case 'stop_clinic': return '⚠️';
      default: return '📢';
    }
  };

  const formatTime = (time: string) => {
    const date = new Date(time);
    const now = new Date();
    const diff = now.getTime() - date.getTime();
    
    if (diff < 60000) return '刚刚';
    if (diff < 3600000) return `${Math.floor(diff / 60000)}分钟前`;
    if (diff < 86400000) return `${Math.floor(diff / 3600000)}小时前`;
    if (diff < 604800000) return `${Math.floor(diff / 86400000)}天前`;
    
    return `${date.getMonth() + 1}月${date.getDate()}日`;
  };

  const tabs = [
    { key: 'all', title: '全部', badge: unreadCount?.total },
    { key: 'appointment', title: '预约', badge: unreadCount?.appointment },
    { key: 'consultation', title: '就诊', badge: unreadCount?.consultation },
    { key: 'system', title: '系统', badge: unreadCount?.system },
  ];

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <Tabs 
          activeKey={activeTab} 
          onChange={setActiveTab}
          className={styles.tabs}
        >
          {tabs.map(tab => (
            <Tabs.Tab 
              key={tab.key} 
              title={
                <Badge content={tab.badge && tab.badge > 0 ? tab.badge : null}>
                  {tab.title}
                </Badge>
              }
            />
          ))}
        </Tabs>
        {unreadCount && unreadCount.total > 0 && (
          <span className={styles.readAll} onClick={handleReadAll}>
            全部已读
          </span>
        )}
      </div>

      <PullToRefresh onRefresh={handleRefresh}>
        {messages.length === 0 && !loading ? (
          <Empty description="暂无消息" style={{ padding: '60px 0' }} />
        ) : (
          <List>
            {messages.map(message => (
              <SwipeAction
                key={message.id}
                rightActions={[
                  {
                    key: 'delete',
                    text: '删除',
                    color: 'danger',
                    onClick: () => handleDelete(message.id),
                  },
                ]}
              >
                <List.Item
                  prefix={
                    <div className={styles.iconWrapper}>
                      <span className={styles.icon}>{getMessageIcon(message.messageType)}</span>
                      {message.isRead === 0 && <span className={styles.dot} />}
                    </div>
                  }
                  description={
                    <div className={styles.messageContent}>
                      <div className={styles.content}>{message.content}</div>
                      <div className={styles.time}>{formatTime(message.createdAt)}</div>
                    </div>
                  }
                  onClick={() => handleRead(message)}
                  className={message.isRead === 0 ? styles.unread : ''}
                >
                  {message.title}
                </List.Item>
              </SwipeAction>
            ))}
          </List>
        )}
        <InfiniteScroll loadMore={loadMore} hasMore={hasMore} />
      </PullToRefresh>
    </div>
  );
};

export default MessagePage;
