import { View, Text } from '@tarojs/components';
import Taro, { useDidShow, usePullDownRefresh, useRouter } from '@tarojs/taro';
import { Empty, Button, Tag } from '@nutui/nutui-react-taro';
import { useState, useCallback } from 'react';
import { feedbackApi, userApi } from '@hospital/api';
import type { Feedback } from '@hospital/shared';
import { getToken } from '../../../../utils/auth';
import { useProtectedPage } from '../../../../hooks/useProtectedPage';
import { useApplyThemeNavigationBar } from '../../../../utils/theme';
import LoginPopup from '../../../../components/LoginPopup';
import './index.less';

// 反馈状态映射
const statusMap: Record<string, { text: string; color: string }> = {
  pending: { text: '待处理', color: '#faad14' },
  processing: { text: '处理中', color: '#1890ff' },
  resolved: { text: '已解决', color: '#52c41a' },
  closed: { text: '已关闭', color: '#999' },
};

// 格式化时间
const formatTime = (dateStr: string) => {
  if (!dateStr) return '';
  const date = new Date(dateStr);
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  const hour = String(date.getHours()).padStart(2, '0');
  const minute = String(date.getMinutes()).padStart(2, '0');
  return `${year}-${month}-${day} ${hour}:${minute}`;
};

const FeedbackHistoryPage = () => {
  useApplyThemeNavigationBar();
  const router = useRouter();
  const highlightId = router.params.id; // 从消息点击跳转时的反馈ID
  
  const [feedbacks, setFeedbacks] = useState<Feedback[]>([]);
  const [loading, setLoading] = useState(true);
  const [userId, setUserId] = useState('');
  const [expandedId, setExpandedId] = useState<string | null>(highlightId || null);

  usePullDownRefresh(() => {
    if (userId) {
      loadFeedbacks(userId).finally(() => {
        Taro.stopPullDownRefresh();
      });
    } else {
      Taro.stopPullDownRefresh();
    }
  });

  const loadFeedbacks = useCallback(async (uid: string) => {
    setLoading(true);
    try {
      const result = await feedbackApi.getMyList(uid);
      setFeedbacks(result || []);
      
      // 如果有高亮ID，自动滚动到该反馈
      if (highlightId) {
        setTimeout(() => {
          Taro.pageScrollTo({
            selector: `#feedback-${highlightId}`,
            duration: 300,
          });
        }, 100);
      }
    } catch (error) {
      console.error('加载反馈列表失败', error);
      Taro.showToast({ title: '加载失败', icon: 'none' });
    } finally {
      setLoading(false);
    }
  }, [highlightId]);

  const checkLoginAndLoad = useCallback(async () => {
    setLoading(true);
    try {
      const user = await userApi.getProfile();
      setUserId(user.id);
      await loadFeedbacks(user.id);
    } catch (error) {
      console.error('获取用户信息失败', error);
      setLoading(false);
    }
  }, [loadFeedbacks]);

  const { showLoginPopup, handleLoginSuccess, handleLoginClose } = useProtectedPage({
    load: checkLoginAndLoad,
    clear: () => {
      setUserId('');
      setFeedbacks([]);
      setLoading(false);
    },
  });

  useDidShow(() => {
    if (getToken()) {
      void checkLoginAndLoad();
    }
  });

  const handleToggleExpand = (id: string) => {
    setExpandedId(expandedId === id ? null : id);
  };

  const goToSubmit = () => {
    Taro.navigateTo({ url: '/packageProfile/pages/feedback/index' });
  };

  if (loading && feedbacks.length === 0) {
    return (
      <View className="history-page">
        <View className="loading">加载中...</View>
      </View>
    );
  }

  return (
    <View className="history-page">
      {/* 反馈列表 */}
      {feedbacks.length === 0 ? (
        <View className="empty-container">
          <Empty description="暂无反馈记录" />
        </View>
      ) : (
        <View className="feedback-list">
          {feedbacks.map((feedback) => {
            const status = statusMap[feedback.status] || statusMap.pending;
            const isExpanded = expandedId === feedback.id;
            const isHighlighted = highlightId === feedback.id;
            
            return (
              <View
                key={feedback.id}
                id={`feedback-${feedback.id}`}
                className={`feedback-item ${isHighlighted ? 'highlighted' : ''}`}
                onClick={() => handleToggleExpand(feedback.id)}
              >
                <View className="feedback-header">
                  <View className="feedback-title-row">
                    <Text className="feedback-title">{feedback.title}</Text>
                    <Tag type="primary" style={{ backgroundColor: status.color, borderColor: status.color }}>
                      {status.text}
                    </Tag>
                  </View>
                  <Text className="feedback-time">{formatTime(feedback.createdAt)}</Text>
                </View>
                
                <View className="feedback-content">
                  <Text className={`content-text ${isExpanded ? 'expanded' : ''}`}>
                    {feedback.content}
                  </Text>
                </View>
                
                {/* 回复内容 */}
                {feedback.reply && (
                  <View className={`reply-section ${isExpanded ? 'expanded' : ''}`}>
                    <View className="reply-header">
                      <Text className="reply-label">客服回复</Text>
                      {feedback.handledAt && (
                        <Text className="reply-time">{formatTime(feedback.handledAt)}</Text>
                      )}
                    </View>
                    <Text className="reply-content">{feedback.reply}</Text>
                  </View>
                )}
                
                {/* 展开/收起提示 */}
                <View className="expand-hint">
                  <Text className="expand-text">
                    {isExpanded ? '点击收起' : (feedback.reply ? '点击查看回复' : '点击展开')}
                  </Text>
                </View>
              </View>
            );
          })}
        </View>
      )}

      {/* 提交新反馈按钮 */}
      <View className="submit-wrap">
        <Button className="submit-btn" type="primary" block onClick={goToSubmit}>
          提交新反馈
        </Button>
      </View>

      {/* 登录弹窗 */}
      <LoginPopup
        visible={showLoginPopup}
        onClose={handleLoginClose}
        onSuccess={handleLoginSuccess}
      />
    </View>
  );
};

export default FeedbackHistoryPage;
