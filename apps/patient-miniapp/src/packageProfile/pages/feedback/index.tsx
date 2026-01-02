import { View, Text, Textarea } from '@tarojs/components';
import Taro from '@tarojs/taro';
import { Button, Rate } from '@nutui/nutui-react-taro';
import { useState, useEffect } from 'react';
import { feedbackApi, userApi } from '@hospital/api';
import { getToken } from '../../../utils/auth';
import LoginPopup from '../../../components/LoginPopup';
import './index.less';

const FeedbackPage = () => {
  const [rating, setRating] = useState(5);
  const [content, setContent] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [userId, setUserId] = useState('');
  const [showLoginPopup, setShowLoginPopup] = useState(false);

  useEffect(() => {
    // 检查登录状态并获取用户信息
    const token = getToken();
    if (!token) {
      Taro.showToast({ title: '请先登录', icon: 'none' });
      setShowLoginPopup(true);
      return;
    }
    
    loadUserInfo();
  }, []);

  // 登录成功后加载用户信息
  const handleLoginSuccess = () => {
    setShowLoginPopup(false);
    loadUserInfo();
  };

  const loadUserInfo = async () => {
    try {
      const user = await userApi.getProfile();
      setUserId(user.id);
    } catch (error) {
      console.error('获取用户信息失败', error);
    }
  };

  const handleSubmit = async () => {
    if (!userId) {
      Taro.showToast({ title: '请先登录', icon: 'none' });
      return;
    }

    if (!content.trim()) {
      Taro.showToast({ title: '请输入反馈内容', icon: 'none' });
      return;
    }

    if (content.trim().length < 10) {
      Taro.showToast({ title: '反馈内容至少10个字', icon: 'none' });
      return;
    }

    setSubmitting(true);
    try {
      await feedbackApi.create({
        userId,
        userType: 'patient',
        feedbackType: 'suggestion',
        title: `用户反馈 (评分: ${rating}星)`,
        content: content.trim(),
      });
      
      Taro.showToast({ title: '感谢您的反馈', icon: 'success' });
      setContent('');
      setRating(5);
      
      // 延迟返回
      setTimeout(() => {
        Taro.navigateBack();
      }, 1500);
    } catch (error: any) {
      Taro.showToast({ title: error.message || '提交失败', icon: 'none' });
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <View className="feedback-page">
      {/* 评分区域 */}
      <View className="section">
        <Text className="section-title">整体评分</Text>
        <View className="rating-wrap">
          <Rate value={rating} onChange={(val) => setRating(val)} />
          <Text className="rating-text">
            {rating === 5 ? '非常满意' : rating === 4 ? '满意' : rating === 3 ? '一般' : rating === 2 ? '不满意' : '非常不满意'}
          </Text>
        </View>
      </View>

      {/* 反馈内容 */}
      <View className="section">
        <Text className="section-title">反馈内容</Text>
        <Textarea
          className="textarea"
          placeholder="请详细描述您的问题或建议，我们会认真处理每一条反馈..."
          value={content}
          onInput={(e) => setContent(e.detail.value)}
          maxlength={300}
        />
        <Text className="char-count">{content.length}/300</Text>
      </View>

      {/* 提交按钮 */}
      <View className="submit-wrap">
        <Button
          type="primary"
          block
          loading={submitting}
          disabled={!content.trim()}
          onClick={handleSubmit}
        >
          提交反馈
        </Button>
      </View>

      {/* 查看历史反馈 */}
      <View className="history-link" onClick={() => Taro.navigateTo({ url: '/packageProfile/pages/feedback/history' })}>
        <Text className="history-text">查看我的反馈历史</Text>
        <Text className="history-arrow">›</Text>
      </View>

      {/* 提示 */}
      <View className="tips">
        <Text className="tips-title">温馨提示</Text>
        <Text className="tips-content">• 您的反馈将帮助我们改进服务质量</Text>
        <Text className="tips-content">• 如有紧急问题，请直接联系医院客服</Text>
        <Text className="tips-content">• 提交后可在反馈历史中查看回复</Text>
      </View>

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

export default FeedbackPage;

