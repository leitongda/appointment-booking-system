import { View, Text } from '@tarojs/components';
import Taro, { useReachBottom } from '@tarojs/taro';
import { Empty, Tabs, PullToRefresh } from '@nutui/nutui-react-taro';
import { useState, useEffect, useCallback } from 'react';
import { messageApi, userApi } from '@hospital/api';
import type { Message, MessageType } from '@hospital/shared';
import { PATIENT_MESSAGE_TABS, type PatientMessageTabKey } from '@hospital/shared';
import { formatRelativeTime } from '@hospital/shared';
import { BellIcon, CalendarIcon, InfoIcon, ClockIcon, CloseCircleIcon, ChatIcon } from '../../../components/Icons';
import { useProtectedPage } from '../../../hooks/useProtectedPage';
import { useApplyThemeNavigationBar, useThemePrimaryColor } from '../../../utils/theme';
import LoginPopup from '../../../components/LoginPopup';
import './index.less';

// 消息类型图标映射
const iconMap: Record<MessageType | string, React.ComponentType<{ size?: number; color?: string }>> = {
  appointment: CalendarIcon,
  schedule: ClockIcon,
  consultation: InfoIcon,
  system: InfoIcon,
  stop_clinic: CloseCircleIcon,
  feedback: ChatIcon,
};

// 消息类型名称映射
const typeNameMap: Record<MessageType | string, string> = {
  appointment: '预约通知',
  schedule: '排班通知',
  consultation: '咨询通知',
  system: '系统通知',
  stop_clinic: '停诊通知',
  feedback: '反馈回复',
};

const MessagePage = () => {
  const primaryColor = useThemePrimaryColor();
  useApplyThemeNavigationBar();
  const [activeTab, setActiveTab] = useState<PatientMessageTabKey>('all');
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(true);
  const [userId, setUserId] = useState('');
  const [unreadCounts, setUnreadCounts] = useState({
    total: 0,
    appointment: 0,
    consultation: 0,
    schedule: 0,
    system: 0,
    stop_clinic: 0,
    feedback: 0,
  });
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const PAGE_SIZE = 20;

  useEffect(() => {
    if (userId) {
      void resetAndLoad();
    }
  }, [activeTab, userId]);

  // 上拉加载更多
  useReachBottom(() => {
    if (!loadingMore && hasMore) {
      loadMoreMessages();
    }
  });

  // Tab 内容区下拉刷新
  const handleRefresh = async () => {
    if (!userId) return;
    await Promise.all([resetAndLoad(), loadUnreadCount()]);
  };

  const loadMessages = useCallback(async () => {
    if (!userId) return;
    setLoading(true);
    try {
      const params: { page: number; pageSize: number; messageType?: MessageType } = {
        page: 1,
        pageSize: PAGE_SIZE,
      };

      if (activeTab !== 'all') {
        params.messageType = activeTab;
      }

      const result = await messageApi.getUnifiedList(params);
      setMessages(result.data || []);
      setHasMore((result.data?.length || 0) < (result.total || 0));
    } catch (error) {
      console.error('加载消息列表失败', error);
      Taro.showToast({ title: '加载失败', icon: 'none' });
    } finally {
      setLoading(false);
    }
  }, [activeTab, userId]);

  const loadMoreMessages = async () => {
    if (loadingMore || !hasMore || !userId) return;

    setLoadingMore(true);
    try {
      const nextPage = page + 1;
      const params: { page: number; pageSize: number; messageType?: MessageType } = {
        page: nextPage,
        pageSize: PAGE_SIZE,
      };

      if (activeTab !== 'all') {
        params.messageType = activeTab;
      }

      const result = await messageApi.getUnifiedList(params);
      const newMessages = result.data || [];
      setMessages(prev => [...prev, ...newMessages]);
      setPage(nextPage);
      setHasMore(newMessages.length < (result.total || 0) && newMessages.length > 0);
    } catch (error) {
      console.error('加载更多消息失败', error);
    } finally {
      setLoadingMore(false);
    }
  };

  const loadUnreadCount = useCallback(async () => {
    try {
      const counts = await messageApi.getUnifiedUnreadCount();
      setUnreadCounts({
        total: counts.total || 0,
        appointment: counts.appointment || 0,
        consultation: counts.consultation || 0,
        schedule: counts.schedule || 0,
        system: counts.system || 0,
        stop_clinic: counts.stopClinic || 0,
        feedback: counts.feedback || 0,
      });
    } catch (error) {
      console.error('获取未读数量失败', error);
    }
  }, []);

  const resetAndLoad = useCallback(async () => {
    setPage(1);
    setHasMore(true);
    return loadMessages();
  }, [loadMessages]);

  const checkLoginAndLoad = useCallback(async () => {
    setLoading(true);
    try {
      const user = await userApi.getProfile();
      setUserId(user.id);
      await loadUnreadCount();
    } catch (error) {
      console.error('获取用户信息失败', error);
      setLoading(false);
    }
  }, [loadUnreadCount]);

  const {
    showLoginPopup,
    handleLoginSuccess,
    handleLoginClose,
  } = useProtectedPage({
    load: checkLoginAndLoad,
    clear: () => {
      setUserId('');
      setMessages([]);
      setUnreadCounts({ total: 0, appointment: 0, consultation: 0, schedule: 0, system: 0, stop_clinic: 0, feedback: 0 });
      setPage(1);
      setHasMore(true);
      setLoading(false);
    },
  });

  const handleMessageClick = async (message: Message) => {
    // 如果未读，标记为已读
    if (message.isRead === 0) {
      try {
        await messageApi.markAsReadUnified(message.id);
        // 更新本地状态
        setMessages((prev) =>
          prev.map((m) => (m.id === message.id ? { ...m, isRead: 1 } : m))
        );
        // 更新未读数
        loadUnreadCount();
      } catch (error) {
        console.error('标记已读失败', error);
      }
    }

    // 根据消息类型跳转
    if (message.relatedId) {
      switch (message.messageType) {
        case 'appointment':
        case 'stop_clinic':
          // 预约相关通知和停诊通知都跳转到预约详情
          Taro.navigateTo({ url: `/packageBooking/pages/appointment/detail?id=${message.relatedId}` });
          break;
        case 'consultation':
          // 就诊通知跳转到就诊记录详情
          Taro.navigateTo({ url: `/packageProfile/pages/records/detail?id=${message.relatedId}` });
          break;
        case 'feedback':
          // 跳转到反馈历史页面查看详情
          Taro.navigateTo({ url: `/packageProfile/pages/feedback/history?id=${message.relatedId}` });
          break;
        default:
          // 显示消息详情弹窗
          Taro.showModal({
            title: message.title,
            content: message.content || '暂无详情',
            showCancel: false,
          });
      }
    } else {
      Taro.showModal({
        title: message.title,
        content: message.content || '暂无详情',
        showCancel: false,
      });
    }
  };

  const handleMarkAllRead = async () => {
    if (unreadCounts.total === 0) {
      Taro.showToast({ title: '没有未读消息', icon: 'none' });
      return;
    }

    try {
      const result = await Taro.showModal({
        title: '确认操作',
        content: '确定将所有消息标记为已读吗？',
      });

      if (result.confirm) {
        const messageType = activeTab === 'all' ? undefined : activeTab;
        await messageApi.markAllAsReadUnified(messageType);
        Taro.showToast({ title: '已全部标记为已读', icon: 'success' });
        loadMessages();
        loadUnreadCount();
      }
    } catch (error) {
      Taro.showToast({ title: '操作失败', icon: 'none' });
    }
  };

  if (loading && messages.length === 0) {
    return (
      <View className="message-page">
        <View className="loading">加载中...</View>
      </View>
    );
  }

  return (
    <View className="message-page">
      {/* 头部操作栏 */}
      <View className="header-bar">
        <Text className="unread-count">
          {unreadCounts.total > 0 ? `${unreadCounts.total}条未读` : '无未读消息'}
        </Text>
        <Text
          className="mark-all-btn"
          onClick={handleMarkAllRead}
        >
          全部已读
        </Text>
      </View>

      {/* 分类标签 */}
      <View className="tabs-wrapper" role="tablist" aria-label="消息分类标签">
        <Tabs
          value={activeTab}
          onChange={(value) => setActiveTab(value as PatientMessageTabKey)}
        >
          {PATIENT_MESSAGE_TABS.map((tab) => {
            const badgeCount =
              tab.key === 'all' ? unreadCounts.total :
              tab.key === 'appointment' ? unreadCounts.appointment :
              tab.key === 'consultation' ? unreadCounts.consultation :
              tab.key === 'stop_clinic' ? unreadCounts.stop_clinic :
              tab.key === 'feedback' ? unreadCounts.feedback :
              unreadCounts.system;
            return (
              <Tabs.TabPane
                key={tab.key}
                title={badgeCount > 0 ? `${tab.label} ${badgeCount > 99 ? '99+' : badgeCount}` : tab.label}
                value={tab.key}
              />
            );
          })}
        </Tabs>
      </View>

      <PullToRefresh onRefresh={handleRefresh}>
        {/* 消息列表 */}
        {messages.length === 0 ? (
          <View className="empty-container">
            <Empty description="暂无消息" />
          </View>
        ) : (
          <View className="message-list" role="list" aria-label="消息列表">
            {messages.map((message) => {
              const IconComponent = iconMap[message.messageType] || BellIcon;
              const isRead = message.isRead === 1;
              return (
                <View
                  key={message.id}
                  className={`message-item ${isRead ? 'read' : 'unread'}`}
                  onClick={() => handleMessageClick(message)}
                  role="listitem"
                  aria-label={
                    !isRead
                      ? `未读消息：${message.title}，${message.content || typeNameMap[message.messageType]}，${formatRelativeTime(message.createdAt)}`
                      : `消息：${message.title}，${message.content || typeNameMap[message.messageType]}，${formatRelativeTime(message.createdAt)}`
                  }
                >
                  <View className="message-icon" aria-hidden="true">
                    <IconComponent size={24} color={isRead ? '#9CA3AF' : primaryColor} />
                  </View>
                  <View className="message-content">
                    <View className="message-header">
                      <Text className="message-title">
                        {message.title}
                        {!isRead && <Text style={{ fontSize: '12px', color: '#999' }}>（未读）</Text>}
                      </Text>
                      <Text className="message-time">{formatRelativeTime(message.createdAt)}</Text>
                    </View>
                    <Text className="message-text">{message.content || typeNameMap[message.messageType]}</Text>
                  </View>
                  {!isRead && (
                    <View className="unread-dot" aria-label="未读消息" />
                  )}
                </View>
              );
            })}
          </View>
        )}

        {/* 加载状态 */}
        {loadingMore && (
          <View className="loading-more">
            <Text>加载中...</Text>
          </View>
        )}

        {/* 没有更多数据 */}
        {!hasMore && messages.length > 0 && (
          <View className="no-more">
            <Text>没有更多了</Text>
          </View>
        )}
      </PullToRefresh>

      {/* 登录弹窗 */}
      <LoginPopup
        visible={showLoginPopup}
        onClose={handleLoginClose}
        onSuccess={handleLoginSuccess}
      />
    </View>
  );
};

export default MessagePage;
