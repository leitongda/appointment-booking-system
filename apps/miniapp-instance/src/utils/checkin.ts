import Taro from '@tarojs/taro';

/**
 * 直接触发扫码签到（不跳转中间页面）
 * @returns Promise<boolean> 是否成功触发扫码（用户取消返回 false）
 */
export const triggerCheckinScan = async (): Promise<boolean> => {
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
      return true;
    } else {
      Taro.showToast({
        title: '无效的签到二维码',
        icon: 'none',
      });
      return false;
    }
  } catch (error: any) {
    console.error('[扫码签到] 扫码失败:', error);
    // 用户取消扫码不显示错误提示
    if (error.errMsg && !error.errMsg.includes('cancel')) {
      Taro.showToast({
        title: '扫码失败，请重试',
        icon: 'none',
      });
    }
    return false;
  }
};
