import { View, Text } from '@tarojs/components';
import Taro, { useDidShow } from '@tarojs/taro';
import { Tabs, Button, Empty, PullToRefresh } from '@nutui/nutui-react-taro';
import { useState, useEffect, useCallback } from 'react';
import { appointmentApi } from '@hospital/api';
import { APPOINTMENT_STATUS_MAP, TIME_SLOT_MAP } from '@hospital/shared';
import { AUTH_EVENTS, getToken, subscribeAuthChange } from '../../utils/auth';
import { getPaymentPreparationFailure, getPaymentRequestFailure, verifyPaymentResult } from '../../utils/payment';
import { formatTime, isAppointmentExpired } from '../../utils/url';
import { triggerCheckinScan } from '../../utils/checkin';
import { useApplyThemeNavigationBar } from '../../utils/theme';
import LoginPopup from '../../components/LoginPopup';
import { CalendarIcon } from '../../components/Icons';
import type { Appointment } from '@hospital/shared';
import './index.less';

// 隐藏预约单号中间部分（保留前4位和后4位）
const maskAppointmentNo = (no: string): string => {
  if (!no || no.length <= 8) return no;
  const prefix = no.slice(0, 4);
  const suffix = no.slice(-4);
  return `${prefix}****${suffix}`;
};

// 状态样式映射
const getStatusClass = (status: number): string => {
  const classMap: Record<number, string> = {
    0: 'status-warning',     // 待支付 - 橙色
    1: 'status-pending',     // 已预约 - 红色
    2: 'status-confirmed',   // 已签到 - 绿色
    3: 'status-expired',     // 历史候诊 - 灰色兼容态
    4: 'status-processing',  // 就诊中 - 蓝色
    5: 'status-completed',   // 已完成 - 绿色
    6: 'status-cancelled',   // 已取消 - 灰色
    7: 'status-expired',     // 已过期 - 浅灰色
    8: 'status-cancelled',   // 已爽约 - 灰色
  };
  return classMap[status] || '';
};

const AppointmentPage = () => {
  useApplyThemeNavigationBar();
  const [activeTab, setActiveTab] = useState('0');
  const [loading, setLoading] = useState(true);
  const [appointments, setAppointments] = useState<Appointment[]>([]);
  const [pendingPaymentCount, setPendingPaymentCount] = useState(0);
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [showLoginPopup, setShowLoginPopup] = useState(false);

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
      subscribeAuthChange((payload) => {
        if (payload.type === AUTH_EVENTS.LOGOUT || payload.type === AUTH_EVENTS.EXPIRED) {
          setIsLoggedIn(false);
          setAppointments([]);
          setLoading(false);
          setShowLoginPopup(false);
          return;
        }

        if (payload.type === AUTH_EVENTS.LOGIN || payload.type === AUTH_EVENTS.UPDATED) {
          checkAndLoad();
        }
      }),
    [checkAndLoad]
  );

  // 页面显示时更新 TabBar 选中状态
  useDidShow(() => {
    Taro.eventCenter.trigger('tabbar:change', 1);
    checkAndLoad();
  });

  // 登录成功后刷新数据
  const handleLoginSuccess = () => {
    setIsLoggedIn(true);
    setShowLoginPopup(false);
    checkAndLoad();
  };

  // 下拉刷新处理
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

      // 非"待支付"Tab 时查询待支付数量，用于显示提醒横幅
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
      console.error('加载预约列表失败', error);
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
      // 二次确认：微信支付可能实际成功但本地 Promise reject
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
    // 直接触发扫码签到
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
          {/* 待支付提醒横幅：在非"待支付"Tab 下展示 */}
          {isLoggedIn && !loading && pendingPaymentCount > 0 && activeTab !== '1' && (
            <View
              className="pending-payment-banner"
              onClick={() => setActiveTab('1')}
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
                <Button
                  className="login-guide-btn"
                  type="primary"
                  onClick={() => setShowLoginPopup(true)}
                >
                  立即登录
                </Button>
              </View>
            </View>
          ) : loading ? (
            <View className="loading-wrapper">
              <Text>加载中...</Text>
            </View>
          ) : appointments.length === 0 ? (
            <View className="empty-wrapper">
              <Empty description="暂无预约记录" />
            </View>
          ) : (
            appointments.map((item) => (
              <View key={item.id} className="card" onClick={() => handleViewDetail(item.id)}>
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
                  {/* 待支付状态显示金额 */}
                  {item.status === 0 && item.paymentAmount && item.paymentAmount > 0 && (
                    <View className="payment-info">
                      <Text className="payment-amount">¥{item.paymentAmount.toFixed(2)}</Text>
                    </View>
                  )}
                </View>

                {/* 待支付状态：显示去支付按钮 */}
                {item.status === 0 && (
                  <View className="card-footer">
                    <Button
                      className="pay-btn"
                      type="primary"
                      size="small"
                      onClick={(e) => {
                        e.stopPropagation();
                        handlePay(item);
                      }}
                    >
                      去支付
                    </Button>
                    <Button
                      className="cancel-btn"
                      size="small"
                      onClick={(e) => {
                        e.stopPropagation();
                        handleCancel(item.id);
                      }}
                    >
                      取消预约
                    </Button>
                  </View>
                )}

                {/* 已预约状态：显示签到和取消按钮 */}
                {item.status === 1 && !isAppointmentExpired(item.scheduleDate, item.endTime, item.timeSlot) && (
                  <View className="card-footer">
                    <Button
                      className="cancel-btn"
                      size="small"
                      onClick={(e) => { e.stopPropagation(); handleCancel(item.id); }}
                    >
                      取消预约
                    </Button>
                    <Button
                      className="signin-btn"
                      type="primary"
                      size="small"
                      onClick={(e) => { e.stopPropagation(); handleSignIn(); }}
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

      {/* 登录弹窗 */}
      <LoginPopup
        visible={showLoginPopup}
        onClose={() => setShowLoginPopup(false)}
        onSuccess={handleLoginSuccess}
      />
    </View>
  );
};

export default AppointmentPage;
