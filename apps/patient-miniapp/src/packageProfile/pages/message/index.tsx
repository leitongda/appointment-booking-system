import { View, Text } from '@tarojs/components';
import Taro, { usePullDownRefresh } from '@tarojs/taro';
import { Empty, Tabs, Button } from '@nutui/nutui-react-taro';
import { useState, useEffect } from 'react';
import { messageApi, userApi } from '@hospital/api';
import type { Message, MessageType } from '@hospital/shared';
import { BellIcon, CalendarIcon, InfoIcon, ClockIcon, CloseCircleIcon, ChatIcon } from '../../../components/Icons';
import { getToken } from '../../../utils/auth';
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

// 格式化时间
const formatTime = (dateStr: string) => {
  if (!dateStr) return '';
  const date = new Date(dateStr);
  const now = new Date();
  const diff = now.getTime() - date.getTime();
  
  // 1小时内
  if (diff < 3600000) {
    const minutes = Math.floor(diff / 60000);
    return minutes <= 0 ? '刚刚' : `${minutes}分钟前`;
  }
  // 24小时内
  if (diff < 86400000) {
    const hours = Math.floor(diff / 3600000);
    return `${hours}小时前`;
  }
  // 7天内
  if (diff < 604800000) {
    const days = Math.floor(diff / 86400000);
    return `${days}天前`;
  }
  // 超过7天显示日期
  return dateStr.substring(0, 10);
};

const MessagePage = () => {
  const [activeTab, setActiveTab] = useState('all');
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(true);
  const [userId, setUserId] = useState('');
  const [unreadCounts, setUnreadCounts] = useState({
    total: 0,
    appointment: 0,
    system: 0,
  });
  const [showLoginPopup, setShowLoginPopup] = useState(false);

  useEffect(() => {
    checkLoginAndLoad();
  }, []);

  useEffect(() => {
    if (userId) {
      loadMessages();
    }
  }, [activeTab, userId]);

  const checkLoginAndLoad = async () => {
    const token = getToken();
    if (!token) {
      Taro.showToast({ title: '请先登录', icon: 'none' });
      setShowLoginPopup(true);
      setLoading(false);
      return;
    }

    try {
      const user = await userApi.getProfile();
      setUserId(user.id);
      loadUnreadCount(user.id);
    } catch (error) {
      console.error('获取用户信息失败', error);
      setLoading(false);
    }
  };

  // 登录成功后加载数据
  const handleLoginSuccess = () => {
    setShowLoginPopup(false);
    checkLoginAndLoad();
  };

  // 下拉刷新
  usePullDownRefresh(() => {
    if (userId) {
      Promise.all([loadMessages(), loadUnreadCount(userId)]).finally(() => {
        Taro.stopPullDownRefresh();
      });
    } else {
      Taro.stopPullDownRefresh();
    }
  });

  const loadMessages = async () => {
    setLoading(true);
    try {
      const params: { page: number; pageSize: number; messageType?: string } = {
        page: 1,
        pageSize: 50,
      };
      
      if (activeTab !== 'all') {
        params.messageType = activeTab;
      }

      const result = await messageApi.getList(params);
      setMessages(result.data || []);
    } catch (error) {
      console.error('加载消息列表失败', error);
      Taro.showToast({ title: '加载失败', icon: 'none' });
    } finally {
      setLoading(false);
    }
  };

  const loadUnreadCount = async (uid: string) => {
    try {
      const counts = await messageApi.getUnreadCount(uid, 'patient');
      setUnreadCounts({
        total: counts.total || 0,
        appointment: counts.appointment || 0,
        system: counts.system || 0,
      });
    } catch (error) {
      console.error('获取未读数量失败', error);
    }
  };

  const handleMessageClick = async (message: Message) => {
    // 如果未读，标记为已读
    if (message.isRead === 0) {
      try {
        await messageApi.markAsRead(message.id, userId);
        // 更新本地状态
        setMessages((prev) =>
          prev.map((m) => (m.id === message.id ? { ...m, isRead: 1 } : m))
        );
        // 更新未读数
        loadUnreadCount(userId);
      } catch (error) {
        console.error('标记已读失败', error);
      }
    }

    // 根据消息类型跳转
    if (message.relatedId) {
      switch (message.messageType) {
        case 'appointment':
          Taro.navigateTo({ url: `/packageBooking/pages/appointment/detail?id=${message.relatedId}` });
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
      await messageApi.markAllAsRead(userId, 'patient');
      Taro.showToast({ title: '已全部标记为已读', icon: 'success' });
      loadMessages();
      loadUnreadCount(userId);
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
        <Text className="mark-all-btn" onClick={handleMarkAllRead}>
          全部已读
        </Text>
      </View>

      {/* 分类标签 */}
      <View className="tabs-wrapper">
        <Tabs
          value={activeTab}
          onChange={(value) => setActiveTab(value as string)}
        >
          <Tabs.TabPane title="全部" value="all" />
          <Tabs.TabPane title="预约" value="appointment" />
          <Tabs.TabPane title="反馈" value="feedback" />
          <Tabs.TabPane title="系统" value="system" />
        </Tabs>
      </View>

      {/* 消息列表 */}
      {messages.length === 0 ? (
        <View className="empty-container">
          <Empty description="暂无消息" />
        </View>
      ) : (
        <View className="message-list">
          {messages.map((message) => {
            const IconComponent = iconMap[message.messageType] || BellIcon;
            const isRead = message.isRead === 1;
            return (
              <View
                key={message.id}
                className={`message-item ${isRead ? 'read' : 'unread'}`}
                onClick={() => handleMessageClick(message)}
              >
                <View className="message-icon">
                  <IconComponent size={24} color={isRead ? '#9CA3AF' : '#C41E3A'} />
                </View>
                <View className="message-content">
                  <View className="message-header">
                    <Text className="message-title">{message.title}</Text>
                    <Text className="message-time">{formatTime(message.createdAt)}</Text>
                  </View>
                  <Text className="message-text">{message.content || typeNameMap[message.messageType]}</Text>
                </View>
                {!isRead && <View className="unread-dot" />}
              </View>
            );
          })}
        </View>
      )}

      {/* 登录弹窗 */}
      <LoginPopup
        visible={showLoginPopup}
        onClose={() => {
          setShowLoginPopup(false);
          if (!getToken()) {
            Taro.navigateBack();
          }
        }}
        onSuccess={handleLoginSuccess}
      />
    </View>
  );
};

export default MessagePage;
