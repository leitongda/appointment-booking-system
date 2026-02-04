import { View } from '@tarojs/components';
import Taro from '@tarojs/taro';
import { useState, useEffect, useRef } from 'react';
import { getToken } from '../../../utils/auth';
import LoginPopup from '../../../components/LoginPopup';
import './scan.less';

const CheckinScanPage = () => {
  const [showLoginPopup, setShowLoginPopup] = useState(false);
  const hasTriggeredScan = useRef(false);

  const handleScan = async () => {
    try {
      // 调用微信扫码 API
      const result = await Taro.scanCode({
        onlyFromCamera: false,
        scanType: ['qrCode'],
      });

      console.log('[扫码签到] 扫码结果:', result);

      // 解析二维码内容
      const qrcodeContent = result.result;

      // 检查是否是门店签到二维码
      if (qrcodeContent && qrcodeContent.startsWith('store-checkin:')) {
        const storeId = qrcodeContent.replace('store-checkin:', '');

        // 跳转到选择预约页面（使用 redirectTo 避免返回空白页）
        Taro.redirectTo({
          url: `/packageBooking/pages/checkin/select?storeId=${storeId}`,
        });
      } else {
        Taro.showToast({
          title: '无效的签到二维码',
          icon: 'none',
        });
        // 扫码结果无效，返回上一页
        setTimeout(() => {
          Taro.navigateBack();
        }, 1500);
      }
    } catch (error: any) {
      console.error('[扫码签到] 扫码失败:', error);
      if (error.errMsg && !error.errMsg.includes('cancel')) {
        Taro.showToast({
          title: '扫码失败，请重试',
          icon: 'none',
        });
      }
      // 扫码取消或失败，返回上一页
      setTimeout(() => {
        Taro.navigateBack();
      }, 300);
    }
  };

  const triggerScan = () => {
    // 检查登录状态
    const token = getToken();
    if (!token) {
      setShowLoginPopup(true);
      return;
    }
    handleScan();
  };

  useEffect(() => {
    // 避免重复触发
    if (hasTriggeredScan.current) return;
    hasTriggeredScan.current = true;

    // 延迟一点触发扫码，确保页面已完成渲染
    const timer = setTimeout(() => {
      triggerScan();
    }, 100);

    return () => clearTimeout(timer);
  }, []);

  const handleLoginSuccess = () => {
    setShowLoginPopup(false);
    // 登录成功后直接触发扫码
    handleScan();
  };

  return (
    <View className="checkin-scan-page">
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

export default CheckinScanPage;

