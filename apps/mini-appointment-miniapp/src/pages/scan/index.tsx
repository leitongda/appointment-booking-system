import { View, Text, Button } from '@tarojs/components';
import { useState, useEffect } from 'react';
import Taro from '@tarojs/taro';
import { getTodayPendingAppointments, signInAppointment } from '@/services/appointment';
import { getStoreByCode } from '@/services/user';
import { setStoreId } from '@/utils/request';
import type { PendingSignInAppointment, Store } from '@/types/api';
import './index.scss';

export default function Scan() {
  const [store, setStore] = useState<Store | null>(null);
  const [appointments, setAppointments] = useState<PendingSignInAppointment[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    // 检查是否从扫码进入
    const { scene } = Taro.getLaunchOptionsSync();
    if (scene === 1047 || scene === 1048 || scene === 1049) {
      // 扫码进入
      handleScanResult();
    }
  }, []);

  // 扫码
  const handleScan = () => {
    Taro.scanCode({
      onlyFromCamera: true,
      scanType: ['qrCode'],
      success: (res) => {
        handleScanResult(res.result);
      },
      fail: (error) => {
        console.error('Scan failed:', error);
        Taro.showToast({
          title: '扫码失败',
          icon: 'none'
        });
      }
    });
  };

  // 处理扫码结果
  const handleScanResult = async (scanResult?: string) => {
    try {
      setLoading(true);

      let storeId = '';

      if (scanResult) {
        // 解析二维码内容：store-checkin:{storeId}
        const match = scanResult.match(/store-checkin:(.+)/);
        if (match) {
          storeId = match[1];
        } else {
          Taro.showToast({
            title: '无效的签到二维码',
            icon: 'none'
          });
          return;
        }
      } else {
        // 从环境变量或缓存获取门店ID
        storeId = process.env.TARO_APP_STORE_ID || Taro.getStorageSync('store_id') || '';
        if (!storeId) {
          Taro.showToast({
            title: '请先扫描门店二维码',
            icon: 'none'
          });
          return;
        }
      }

      // 保存门店ID
      setStoreId(storeId);

      // 获取门店信息
      const storeInfo = await getStoreByCode(storeId);
      setStore(storeInfo);

      // 获取今日待签到预约
      const pendingAppointments = await getTodayPendingAppointments(storeId);
      setAppointments(pendingAppointments);

      if (pendingAppointments.length === 0) {
        Taro.showToast({
          title: '今日没有待签到的预约',
          icon: 'none'
        });
      }
    } catch (error) {
      console.error('Handle scan result failed:', error);
    } finally {
      setLoading(false);
    }
  };

  // 签到
  const handleSignIn = async (appointment: PendingSignInAppointment) => {
    try {
      // 检查签到状态
      if (appointment.signInStatus === 'early') {
        Taro.showModal({
          title: '提示',
          content: `签到时间未到，请在 ${appointment.minutesUntilOpen} 分钟后再试`,
          showCancel: false
        });
        return;
      }

      if (appointment.signInStatus === 'late') {
        const { confirm } = await Taro.showModal({
          title: '提示',
          content: '您已超过签到时间，是否继续签到？',
          confirmText: '继续签到',
          cancelText: '取消'
        });
        if (!confirm) return;
      }

      // 执行签到
      const result = await signInAppointment(appointment.id);

      // 显示签到成功
      Taro.showModal({
        title: '签到成功',
        content: `${result.message}\n您的排队号：${result.queueNumber}`,
        showCancel: false,
        success: () => {
          // 刷新列表
          if (store) {
            handleScanResult();
          }
        }
      });
    } catch (error) {
      console.error('Sign in failed:', error);
    }
  };

  // 获取签到状态文本
  const getSignInStatusText = (appointment: PendingSignInAppointment) => {
    switch (appointment.signInStatus) {
      case 'early':
        return `${appointment.minutesUntilOpen} 分钟后可签到`;
      case 'available':
        return '可以签到';
      case 'late':
        return `已超时 ${Math.abs(appointment.minutesUntilClose)} 分钟`;
      default:
        return '';
    }
  };

  // 获取签到状态样式
  const getSignInStatusClass = (status: string) => {
    switch (status) {
      case 'early':
        return 'status-early';
      case 'available':
        return 'status-available';
      case 'late':
        return 'status-late';
      default:
        return '';
    }
  };

  return (
    <View className='scan-page'>
      <View className='scan-header'>
        <Text className='header-title'>扫码签到</Text>
        <Text className='header-desc'>请扫描门店签到二维码</Text>
      </View>

      <View className='scan-action'>
        <Button
          className='scan-button'
          onClick={handleScan}
          loading={loading}
        >
          {loading ? '处理中...' : '扫描二维码'}
        </Button>
      </View>

      {store && (
        <View className='store-info'>
          <Text className='store-name'>{store.name}</Text>
          {store.address && (
            <Text className='store-address'>{store.address}</Text>
          )}
        </View>
      )}

      {appointments.length > 0 && (
        <View className='appointments-section'>
          <View className='section-title'>今日预约</View>
          <View className='appointments-list'>
            {appointments.map((appointment) => (
              <View key={appointment.id} className='appointment-card'>
                <View className='card-header'>
                  <View className='patient-info'>
                    <Text className='patient-name'>{appointment.patientName}</Text>
                    <Text className='appointment-no'>预约号：{appointment.appointmentNo}</Text>
                  </View>
                  <View className={`sign-status ${getSignInStatusClass(appointment.signInStatus)}`}>
                    {getSignInStatusText(appointment)}
                  </View>
                </View>

                <View className='card-body'>
                  <View className='info-row'>
                    <Text className='info-label'>医生：</Text>
                    <Text className='info-value'>{appointment.doctorName}</Text>
                  </View>
                  <View className='info-row'>
                    <Text className='info-label'>时间：</Text>
                    <Text className='info-value'>
                      {appointment.scheduleDate} {appointment.timeSlot}
                    </Text>
                  </View>
                  <View className='info-row'>
                    <Text className='info-label'>签到时间：</Text>
                    <Text className='info-value'>
                      {appointment.checkinOpenAt} - {appointment.checkinCloseAt}
                    </Text>
                  </View>
                </View>

                <View className='card-footer'>
                  <Button
                    className='sign-button'
                    type='primary'
                    size='mini'
                    disabled={appointment.signInStatus === 'early'}
                    onClick={() => handleSignIn(appointment)}
                  >
                    立即签到
                  </Button>
                </View>
              </View>
            ))}
          </View>
        </View>
      )}

      {!loading && appointments.length === 0 && store && (
        <View className='empty-state'>
          <Text className='empty-text'>今日暂无待签到的预约</Text>
        </View>
      )}
    </View>
  );
}
