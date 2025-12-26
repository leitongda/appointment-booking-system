import { useState, useEffect } from 'react';
import { Tabs, Badge, Empty, PullToRefresh, InfiniteScroll, SwipeAction, Toast, Dialog } from 'antd-mobile';
import { history } from 'umi';
import { motion } from 'framer-motion';
import { messageApi } from '@hospital/api';
import type { Message, UnreadCount } from '@hospital/shared';
import { Card } from '@/components/ui';
import { fadeInUp, stagger } from '@/components/ui/animations';

const MessagePage: React.FC = () => {
  const [activeTab, setActiveTab] = useState('all');
  const [messages, setMessages] = useState<Message[]>([]);
  const [unreadCount, setUnreadCount] = useState<UnreadCount | null>(null);
  const [loading, setLoading] = useState(false);
  const [hasMore, setHasMore] = useState(true);
  const [page, setPage] = useState(1);
  
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

  const tabs = [
    { key: 'all', title: '全部', badge: unreadCount?.total },
    { key: 'appointment', title: '预约', badge: unreadCount?.appointment },
    { key: 'consultation', title: '就诊', badge: unreadCount?.consultation },
    { key: 'system', title: '系统', badge: unreadCount?.system },
  ];

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
                    >
                      <div className="flex gap-3">
                        <div className={`
                          w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0
                          ${message.isRead === 0 ? 'bg-accent text-white' : 'bg-muted text-muted-foreground'}
                        `}>
                          {getMessageIcon(message.messageType)}
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center justify-between mb-1">
                            <h3 className={`font-medium truncate ${message.isRead === 0 ? 'text-foreground' : 'text-muted-foreground'}`}>
                              {message.title}
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
