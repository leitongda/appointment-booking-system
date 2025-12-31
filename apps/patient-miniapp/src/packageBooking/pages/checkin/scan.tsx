import { View, Text } from '@tarojs/components';
import Taro from '@tarojs/taro';
import { useState, useEffect } from 'react';
import { Button } from '@nutui/nutui-react-taro';
import { ScanIcon } from '../../../components/Icons';
import { getToken } from '../../../utils/auth';
import LoginPopup from '../../../components/LoginPopup';
import './scan.less';

const CheckinScanPage = () => {
  const [showLoginPopup, setShowLoginPopup] = useState(false);
  const [scanning, setScanning] = useState(false);

  useEffect(() => {
    // 检查登录状态
    const token = getToken();
    if (!token) {
      setShowLoginPopup(true);
    }
  }, []);

  const handleScan = async () => {
    // 检查登录状态
    const token = getToken();
    if (!token) {
      setShowLoginPopup(true);
      return;
    }

    setScanning(true);

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
        
        // 跳转到选择预约页面
        Taro.navigateTo({
          url: `/packageBooking/pages/checkin/select?storeId=${storeId}`,
        });
      } else {
        Taro.showToast({
          title: '无效的签到二维码',
          icon: 'none',
        });
      }
    } catch (error: any) {
      console.error('[扫码签到] 扫码失败:', error);
      if (error.errMsg && !error.errMsg.includes('cancel')) {
        Taro.showToast({
          title: '扫码失败，请重试',
          icon: 'none',
        });
      }
    } finally {
      setScanning(false);
    }
  };

  const handleLoginSuccess = () => {
    setShowLoginPopup(false);
  };

  return (
    <View className="checkin-scan-page">
      <View className="scan-area">
        <View className="scan-icon-wrap">
          <ScanIcon size={80} color="#4F46E5" />
        </View>
        <Text className="scan-title">扫码签到</Text>
        <Text className="scan-desc">
          请扫描门店提供的签到二维码，完成到店签到
        </Text>
      </View>

      <View className="scan-tips">
        <View className="tip-item">
          <Text className="tip-num">1</Text>
          <Text className="tip-text">确保您已有当日的预约</Text>
        </View>
        <View className="tip-item">
          <Text className="tip-num">2</Text>
          <Text className="tip-text">到达门店后扫描签到二维码</Text>
        </View>
        <View className="tip-item">
          <Text className="tip-num">3</Text>
          <Text className="tip-text">选择要签到的预约完成签到</Text>
        </View>
      </View>

      <View className="scan-action">
        <Button
          type="primary"
          block
          loading={scanning}
          onClick={handleScan}
        >
          {scanning ? '扫码中...' : '开始扫码'}
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

export default CheckinScanPage;

