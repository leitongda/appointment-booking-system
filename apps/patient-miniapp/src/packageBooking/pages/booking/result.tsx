import { View, Text } from '@tarojs/components';
import Taro, { useRouter } from '@tarojs/taro';
import { useCallback } from 'react';
import { Button } from '@nutui/nutui-react-taro';
import { CheckIcon, CloseIcon } from '../../../components/Icons';
import { useProtectedPage } from '../../../hooks/useProtectedPage';
import { useApplyThemeNavigationBar } from '../../../utils/theme';
import LoginPopup from '../../../components/LoginPopup';
import './result.less';

const BookingResultPage = () => {
  useApplyThemeNavigationBar();
  const router = useRouter();
  const { appointmentNo, status = 'success', message } = router.params;

  const noop = useCallback(async () => {}, []);
  const { showLoginPopup, handleLoginSuccess, handleLoginClose } = useProtectedPage({
    load: noop,
    deps: [appointmentNo, status],
  });

  const resultMessage = message ? decodeURIComponent(message) : '';
  const isSuccess = status === 'success' || status === 'confirmed';
  const isFailed = status === 'failed';
  const isCancelled = status === 'cancelled';
  const isConfirmed = status === 'confirmed';
  const isUnavailable = status === 'unavailable';

  const handleViewDetail = () => {
    if (!appointmentNo) return;
    Taro.redirectTo({ url: `/packageBooking/pages/appointment/detail?appointmentNo=${appointmentNo}` });
  };

  const handleRetryPay = () => {
    if (!appointmentNo) return;
    // 跳转到预约详情页进行支付
    Taro.redirectTo({ url: `/packageBooking/pages/appointment/detail?appointmentNo=${appointmentNo}` });
  };

  const handleBackHome = () => {
    Taro.switchTab({ url: '/pages/index/index' });
  };

  return (
    <View className="result-page">
      {/* 图标区域 */}
      <View className={`result-icon ${isSuccess ? 'success' : 'failed'}`}>
        <View className={`icon-circle ${isSuccess ? 'success' : 'failed'}`}>
          {isSuccess ? (
            <CheckIcon size={48} color="#fff" />
          ) : (
            <CloseIcon size={48} color="#fff" />
          )}
        </View>
        <Text className={`result-title ${isSuccess ? 'success' : 'failed'}`}>
          {isConfirmed
            ? '预约成功'
            : status === 'success'
              ? '支付成功'
              : isCancelled
                ? '支付已取消'
                : isUnavailable
                  ? '暂无法发起支付'
                  : '支付失败'}
        </Text>
        {appointmentNo && (
          <Text className="result-desc">预约单号：{appointmentNo}</Text>
        )}
      </View>

      {/* 温馨提示 */}
      {isSuccess && (
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
      )}

      {/* 支付失败提示 */}
      {isFailed && (
        <View className="notice">
          <Text className="notice-title">支付说明</Text>
          <View className="notice-item">
            <Text>{resultMessage || '支付失败，订单已保留。您可以前往“我的预约”页面重新发起支付。'}</Text>
          </View>
        </View>
      )}

      {/* 支付取消提示 */}
      {isCancelled && (
        <View className="notice">
          <Text className="notice-title">支付说明</Text>
          <View className="notice-item">
            <Text>{resultMessage || '您已取消支付，订单已保留。您可以前往“我的预约”页面重新发起支付。'}</Text>
          </View>
        </View>
      )}

      {isUnavailable && (
        <View className="notice">
          <Text className="notice-title">支付说明</Text>
          <View className="notice-item">
            <Text>{resultMessage || '订单已创建，但当前暂时无法拉起支付。请进入预约详情稍后重试。'}</Text>
          </View>
        </View>
      )}

      {/* 操作按钮 */}
      <View className="actions">
        {(isFailed || isCancelled) && (
          <>
            <Button className="primary-btn" type="primary" block onClick={handleRetryPay}>
              重新支付
            </Button>
            <Button className="secondary-btn" block onClick={handleBackHome}>
              返回首页
            </Button>
          </>
        )}
        {isSuccess && (
          <>
            <Button className="secondary-btn" block onClick={handleViewDetail}>
              查看预约详情
            </Button>
            <Button className="primary-btn" type="primary" block onClick={handleBackHome}>
              返回首页
            </Button>
          </>
        )}
        {isUnavailable && (
          <>
            <Button className="primary-btn" type="primary" block onClick={handleViewDetail}>
              查看预约详情
            </Button>
            <Button className="secondary-btn" block onClick={handleBackHome}>
              返回首页
            </Button>
          </>
        )}
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

export default BookingResultPage;
