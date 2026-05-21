import { useState, useEffect, useCallback } from 'react';
import { Tabs, Badge, Empty, PullToRefresh, InfiniteScroll, SwipeAction, Toast, Dialog } from 'antd-mobile';
import { history } from 'umi';
import { motion } from 'framer-motion';
import { messageApi } from '@hospital/api';
import type { Message, UnreadCount } from '@hospital/shared';
import { PATIENT_MESSAGE_TABS } from '@hospital/shared';
import { Card } from '@/components/ui';
import { fadeInUp, stagger } from '@/components/ui/animations';
import { announce } from '@/components/ui/toast-live';
import { usePatientWebSocket } from '@/hooks/usePatientWebSocket';

const MessagePage: React.FC = () => {
  const [activeTab, setActiveTab] = useState('all');
  const [messages, setMessages] = useState<Message[]>([]);
  const [unreadCount, setUnreadCount] = useState<UnreadCount | null>(null);
  const [loading, setLoading] = useState(false);
  const [hasMore, setHasMore] = useState(true);
  const [page, setPage] = useState(1);
  
  const userId = localStorage.getItem('userId') || '';
  const userType = 'patient';

  // WebSocket 实时消息推送
  const handleNewMessage = useCallback((data: any) => {
    // 新消息到达，刷新列表和未读数
    loadMessages(1, true);
    loadUnreadCount();
    if (data?.title) {
      Toast.show({ content: `新消息: ${data.title}`, position: 'top' });
      announce(`收到新消息: ${data.title}`);
    }
  }, []);

  usePatientWebSocket({
    patientId: userId,
    onNewMessage: handleNewMessage,
  });

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
    
    if (message.relatedId) {
      if (message.messageType === 'appointment' || message.messageType === 'stop_clinic') {
        // 预约相关通知和停诊通知都跳转到预约详情
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
        announce('已将全部消息标记为已读');
      } catch (error) {
        Toast.show({ content: '操作失败' });
      }
    }
  };

  // 键盘导航处理
  const handleMessageKeyDown = useCallback((message: Message, e: React.KeyboardEvent) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      handleRead(message);
    } else if (e.key === 'Delete' || e.key === 'Backspace') {
      e.preventDefault();
      handleDelete(message.id);
    }
  }, [handleRead, handleDelete]);

  const getMessageIcon = (type: string) => {
    const icons: Record<string, React.ReactNode> = {
      appointment: (
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
        </svg>
      ),
      consultation: (
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
        </svg>
      ),
      stop_clinic: (
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728A9 9 0 015.636 5.636m12.728 12.728L5.636 5.636" />
        </svg>
      ),
      system: (
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
        </svg>
      ),
    };
    return icons[type] || icons.system;
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

  const tabs = PATIENT_MESSAGE_TABS.map(tab => ({
    key: tab.key,
    title: tab.label,
    badge: tab.key === 'all' ? unreadCount?.total :
           tab.key === 'appointment' ? unreadCount?.appointment :
           tab.key === 'consultation' ? unreadCount?.consultation :
           unreadCount?.system,
  }));

  return (
    <div className="min-h-screen bg-background">
      {/* Header with Tabs */}
      <div className="bg-card border-b border-border">
        <div className="flex items-center justify-between px-4 pt-12 pb-2">
          <h1 className="font-display text-xl text-foreground">消息中心</h1>
          {unreadCount && unreadCount.total > 0 && (
            <button
              onClick={handleReadAll}
              className="text-sm text-accent hover:text-accent-secondary transition-colors"
              aria-label={`标记全部${unreadCount.total}条消息为已读`}
            >
              全部已读
            </button>
          )}
        </div>
        <Tabs
          activeKey={activeTab}
          onChange={setActiveTab}
          style={{
            '--active-line-color': '#0052FF',
            '--active-title-color': '#0052FF',
          } as React.CSSProperties}
          aria-label="消息分类标签"
        >
          {tabs.map(tab => (
            <Tabs.Tab
              key={tab.key}
              title={
                <Badge content={tab.badge && tab.badge > 0 ? tab.badge : null}>
                  <span aria-label={`${tab.title}, ${tab.badge && tab.badge > 0 ? `${tab.badge}条未读` : '无未读消息'}`}>
                    {tab.title}
                  </span>
                </Badge>
              }
              aria-label={tab.badge && tab.badge > 0 ? `${tab.title}, ${tab.badge}条未读` : tab.title}
              aria-selected={activeTab === tab.key}
            />
          ))}
        </Tabs>
      </div>

      <PullToRefresh onRefresh={handleRefresh}>
        <div className="p-4">
          {messages.length === 0 && !loading ? (
            <div className="flex items-center justify-center h-64">
              <Empty description="暂无消息" />
            </div>
          ) : (
            <motion.div
              className="space-y-3"
              variants={stagger}
              initial="hidden"
              animate="visible"
            >
              {messages.map(message => (
                <motion.div key={message.id} variants={fadeInUp}>
                  <SwipeAction
                    rightActions={[
                      {
                        key: 'delete',
                        text: '删除',
                        color: 'danger',
                        onClick: () => handleDelete(message.id),
                      },
                    ]}
                  >
                    <Card
                      variant={message.isRead === 0 ? 'default' : 'flat'}
                      padding="md"
                      animated={false}
                      className={`cursor-pointer ${message.isRead === 0 ? 'border-l-4 border-l-accent' : ''}`}
                      onClick={() => handleRead(message)}
                      tabIndex={0}
                      onKeyDown={(e) => handleMessageKeyDown(message, e)}
                      role="button"
                      aria-label={
                        message.isRead === 0
                          ? `未读消息: ${message.title}, ${message.content}, ${formatTime(message.createdAt)}`
                          : `消息: ${message.title}, ${message.content}, ${formatTime(message.createdAt)}`
                      }
                      aria-selected={message.isRead === 0}
                    >
                      <div className="flex gap-3">
                        <div className={`
                          w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0
                          ${message.isRead === 0 ? 'bg-accent text-white' : 'bg-muted text-muted-foreground'}
                        `} aria-hidden="true">
                          {getMessageIcon(message.messageType)}
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center justify-between mb-1">
                            <h3 className={`font-medium truncate ${message.isRead === 0 ? 'text-foreground' : 'text-muted-foreground'}`}>
                              {message.title}
                              {message.isRead === 0 && (
                                <span className="sr-only">（未读）</span>
                              )}
                            </h3>
                            <span className="text-xs text-muted-foreground ml-2 flex-shrink-0">
                              {formatTime(message.createdAt)}
                            </span>
                          </div>
                          <p className="text-sm text-muted-foreground line-clamp-2">
                            {message.content}
                          </p>
                        </div>
                      </div>
                    </Card>
                  </SwipeAction>
                </motion.div>
              ))}
            </motion.div>
          )}
          <InfiniteScroll loadMore={loadMore} hasMore={hasMore} />
        </div>
      </PullToRefresh>
    </div>
  );
};

export default MessagePage;
