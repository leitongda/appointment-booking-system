import { View, Text } from '@tarojs/components';
import Taro, { useRouter } from '@tarojs/taro';
import { useState, useEffect } from 'react';
import { Button } from '@nutui/nutui-react-taro';
import { CheckIcon } from '../../../components/Icons';
import { getToken } from '../../../utils/auth';
import LoginPopup from '../../../components/LoginPopup';
import './result.less';

const BookingResultPage = () => {
  const router = useRouter();
  const { appointmentNo } = router.params;
  const [showLoginPopup, setShowLoginPopup] = useState(false);

  useEffect(() => {
    // 检查登录状态，防止直接访问
    const token = getToken();
    if (!token) {
      Taro.showToast({ title: '请先登录', icon: 'none' });
      setShowLoginPopup(true);
    }
  }, []);

  // 登录成功回调
  const handleLoginSuccess = () => {
    setShowLoginPopup(false);
  };

  const handleViewDetail = () => {
    Taro.redirectTo({ url: `/packageBooking/pages/appointment/detail?appointmentNo=${appointmentNo}` });
  };

  const handleBackHome = () => {
    Taro.switchTab({ url: '/pages/index/index' });
  };

  return (
    <View className="result-page">
      {/* 成功图标 */}
      <View className="success-icon">
        <View className="icon-circle">
          <CheckIcon size={48} color="#fff" />
        </View>
        <Text className="success-title">预约成功</Text>
        <Text className="success-desc">预约单号：{appointmentNo}</Text>
      </View>

      {/* 温馨提示 */}
      <View className="notice">
        <Text className="notice-title">温馨提示</Text>
        <View className="notice-item">
          <Text>1. 请于就诊当天携带有效身份证件到院</Text>
        </View>
        <View className="notice-item">
          <Text>2. 就诊当天请提前30分钟到达医院进行签到</Text>
        </View>
        <View className="notice-item">
          <Text>3. 如需取消请提前24小时操作</Text>
        </View>
      </View>

      {/* 操作按钮 */}
      <View className="actions">
        <Button className="secondary-btn" block onClick={handleViewDetail}>
          查看预约详情
        </Button>
        <Button className="primary-btn" type="primary" block onClick={handleBackHome}>
          返回首页
        </Button>
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

export default BookingResultPage;
