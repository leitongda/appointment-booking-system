import { View, Text } from '@tarojs/components';
import Taro, { useDidShow } from '@tarojs/taro';
import { Tabs, Button, PullToRefresh } from '@nutui/nutui-react-taro';
import { useState, useEffect, useCallback } from 'react';
import { appointmentApi } from '@hospital/api';
import { APPOINTMENT_STATUS_MAP, TIME_SLOT_MAP } from '@hospital/shared';
import { AUTH_EVENTS, getToken, subscribeAuthChange } from '../../utils/auth';
import { getPaymentPreparationFailure, getPaymentRequestFailure, verifyPaymentResult } from '../../utils/payment';
import { formatTime, isAppointmentExpired } from '../../utils/url';
import { triggerCheckinScan } from '../../utils/checkin';
import { useApplyThemeNavigationBar } from '../../utils/theme';
import { CalendarIcon } from '../../components/Icons';
import { useTemplate } from '../../contexts/TemplateContext';
import { AppointmentEmptyState, LoadFailedErrorState } from '../../components/EmptyState';
import type { Appointment } from '@hospital/shared';
import './AppointTabs.less';

// 隐藏预约单号中间部分
const maskAppointmentNo = (no: string): string => {
  if (!no || no.length <= 8) return no;
  return `${no.slice(0, 4)}****${no.slice(-4)}`;
};

// 状态样式映射
const getStatusClass = (status: number): string => {
  const classMap: Record<number, string> = {
    0: 'status-warning',
    1: 'status-pending',
    2: 'status-confirmed',
    3: 'status-expired',
    4: 'status-processing',
    5: 'status-completed',
    6: 'status-cancelled',
    7: 'status-expired',
    8: 'status-cancelled',
  };
  return classMap[status] || '';
};

/**
 * 预约列表壳层 -- Tab 分类布局
 * Tab 分类（全部/待支付/待就诊/已完成/已取消） + 预约卡片列表 + 下拉刷新
 */
export function AppointTabs() {
  useApplyThemeNavigationBar();
  const { tone } = useTemplate();

  const [activeTab, setActiveTab] = useState('0');
  const [loading, setLoading] = useState(true);
  const [appointments, setAppointments] = useState<Appointment[]>([]);
  const [pendingPaymentCount, setPendingPaymentCount] = useState(0);
  const [isLoggedIn, setIsLoggedIn] = useState(false);

  const checkAndLoad = useCallback(() => {
    const token = getToken();
    if (!token) {
      setIsLoggedIn(false);
      setAppointments([]);
      setLoading(false);
      return;
    }
    setIsLoggedIn(true);
    void loadAppointments();
  }, [activeTab]);

  useEffect(() => {
    checkAndLoad();
  }, [checkAndLoad]);

  useEffect(
    () =>
      subscribeAuthChange(payload => {
        if (payload.type === AUTH_EVENTS.LOGOUT || payload.type === AUTH_EVENTS.EXPIRED) {
          setIsLoggedIn(false);
          setAppointments([]);
          setLoading(false);
          return;
        }
        if (payload.type === AUTH_EVENTS.LOGIN || payload.type === AUTH_EVENTS.UPDATED) {
          checkAndLoad();
        }
      }),
    [checkAndLoad]
  );

  useDidShow(() => {
    // -1 = 不落在任何 tab 上：本页不在 elderly-tcm 的 navSchema 内（见 AppointSimple 同注释）
    Taro.eventCenter.trigger('tabbar:change', -1);
    checkAndLoad();
  });

  const handleRefresh = async () => {
    if (isLoggedIn) {
      await loadAppointments();
    }
  };

  const loadAppointments = async () => {
    setLoading(true);
    try {
      const statusMap: Record<string, number | undefined> = {
        '0': undefined,    // 全部
        '1': 0,            // 待支付
        '2': 1,            // 待就诊
        '3': 5,            // 已完成
        '4': 6,            // 已取消
      };

      const result = await appointmentApi.getList({
        status: statusMap[activeTab],
        page: 1,
        pageSize: 20,
      });
      setAppointments(result.data);

      // 查询待支付数量
      if (statusMap[activeTab] !== 0) {
        try {
          const pendingResult = await appointmentApi.getList({ status: 0, page: 1, pageSize: 1 });
          setPendingPaymentCount(pendingResult.total || 0);
        } catch {
          setPendingPaymentCount(0);
        }
      } else {
        setPendingPaymentCount(0);
      }
    } catch (error) {
      console.error('[预约列表] 加载失败', error);
    } finally {
      setLoading(false);
    }
  };

  const handleCancel = async (id: string) => {
    const result = await Taro.showModal({
      title: '取消预约',
      content: '确定要取消预约吗？',
    });
    if (!result.confirm) return;

    try {
      await appointmentApi.cancel(id);
      Taro.showToast({ title: '取消成功', icon: 'success' });
      loadAppointments();
    } catch (error: any) {
      Taro.showToast({ title: error.message || '取消失败', icon: 'none' });
    }
  };

  const handlePay = async (appointment: Appointment) => {
    if (appointment.status !== 0) return;

    let paymentParams;
    try {
      paymentParams = await appointmentApi.getPaymentParams(appointment.id);
    } catch (error: any) {
      const result = getPaymentPreparationFailure(error);
      Taro.showToast({ title: result.message, icon: 'none' });
      return;
    }

    try {
      await Taro.requestPayment({
        timeStamp: paymentParams.timeStamp,
        nonceStr: paymentParams.nonceStr,
        package: paymentParams.package,
        signType: paymentParams.signType as any,
        paySign: paymentParams.paySign,
      });
      Taro.showToast({ title: '支付成功', icon: 'success' });
      loadAppointments();
    } catch (error: any) {
      const actuallyPaid = await verifyPaymentResult(appointmentApi.getPaymentStatus, appointment.id);
      if (actuallyPaid) {
        Taro.showToast({ title: '支付成功', icon: 'success' });
        loadAppointments();
        return;
      }
      const result = getPaymentRequestFailure(error);
      Taro.showToast({ title: result.message, icon: 'none' });
    }
  };

  const handleSignIn = () => {
    triggerCheckinScan();
  };

  const handleViewDetail = (id: string) => {
    Taro.navigateTo({ url: `/packageBooking/pages/appointment/detail?id=${id}` });
  };

  return (
    <View className="appointment-page">
      <View className="tabs-wrapper">
        <Tabs
          value={activeTab}
          onChange={(value) => setActiveTab(value as string)}
        >
          <Tabs.TabPane title="全部" value="0" />
          <Tabs.TabPane title="待支付" value="1" />
          <Tabs.TabPane title="待就诊" value="2" />
          <Tabs.TabPane title="已完成" value="3" />
          <Tabs.TabPane title="已取消" value="4" />
        </Tabs>
      </View>

      <PullToRefresh onRefresh={handleRefresh}>
        <View className="list">
          {/* 待支付提醒横幅 */}
          {isLoggedIn && !loading && pendingPaymentCount > 0 && activeTab !== '1' && (
            <View
              className="pending-payment-banner"
              onClick={() => setActiveTab('1')}
              aria-label={`查看${pendingPaymentCount}笔待支付订单`}
              role="button"
            >
              <Text className="banner-text">
                您有 {pendingPaymentCount} 笔待支付订单，请及时完成支付
              </Text>
              <Text className="banner-action">查看</Text>
            </View>
          )}

          {!isLoggedIn ? (
            <View className="login-guide-wrapper">
              <View className="login-guide-card">
                <View className="login-guide-icon">
                  <CalendarIcon size={48} color="#fff" />
                </View>
                <Text className="login-guide-title">登录后查看预约</Text>
                <Text className="login-guide-desc">登录后可查看和管理您的全部预约记录</Text>
              </View>
            </View>
          ) : loading ? (
            <View className="loading-wrapper">
              <Text>加载中...</Text>
            </View>
          ) : appointments.length === 0 ? (
            <View className="empty-wrapper">
              <AppointmentEmptyState onRetry={() => Taro.switchTab({ url: '/pages/index/index' })} />
            </View>
          ) : (
            appointments.map(item => (
              <View key={item.id} className="card" onClick={() => handleViewDetail(item.id)} aria-label={`查看预约详情，单号${maskAppointmentNo(item.appointmentNo)}`} role="button">
                <View className="card-header">
                  <Text className="appointment-no">预约单号：{maskAppointmentNo(item.appointmentNo)}</Text>
                  <Text className={`status ${getStatusClass(item.status)}`}>
                    {APPOINTMENT_STATUS_MAP[item.status]}
                  </Text>
                </View>

                <View className="card-body">
                  <View className="info">
                    <Text className="doctor-name">{item.doctorName}</Text>
                    <Text className="dept-name">{item.departmentName}</Text>
                  </View>
                  <View className="time">
                    <Text className="date">{item.scheduleDate}</Text>
                    <Text className="slot">
                      {TIME_SLOT_MAP[item.timeSlot || 'morning']}
                      {item.startTime && item.endTime && ` ${formatTime(item.startTime)}-${formatTime(item.endTime)}`}
                      {item.queueNumber && (
                        <Text className="queue-number">第{item.queueNumber}号</Text>
                      )}
                    </Text>
                  </View>
                  {/* 待支付金额 */}
                  {item.status === 0 && item.paymentAmount && item.paymentAmount > 0 && (
                    <View className="payment-info">
                      <Text className="payment-amount">¥{item.paymentAmount.toFixed(2)}</Text>
                    </View>
                  )}
                </View>

                {/* 待支付按钮 */}
                {item.status === 0 && (
                  <View className="card-footer">
                    <Button
                      className="pay-btn"
                      type="primary"
                      size="small"
                      onClick={e => { e.stopPropagation(); handlePay(item); }}
                    >
                      去支付
                    </Button>
                    <Button
                      className="cancel-btn"
                      size="small"
                      onClick={e => { e.stopPropagation(); handleCancel(item.id); }}
                    >
                      取消预约
                    </Button>
                  </View>
                )}

                {/* 已预约按钮 */}
                {item.status === 1 && !isAppointmentExpired(item.scheduleDate, item.endTime, item.timeSlot) && (
                  <View className="card-footer">
                    <Button
                      className="cancel-btn"
                      size="small"
                      onClick={e => { e.stopPropagation(); handleCancel(item.id); }}
                    >
                      取消预约
                    </Button>
                    <Button
                      className="signin-btn"
                      type="primary"
                      size="small"
                      onClick={e => { e.stopPropagation(); handleSignIn(); }}
                    >
                      扫码签到
                    </Button>
                  </View>
                )}
              </View>
            ))
          )}
        </View>
      </PullToRefresh>
    </View>
  );
}
