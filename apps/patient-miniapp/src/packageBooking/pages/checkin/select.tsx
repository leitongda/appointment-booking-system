import { View, Text } from '@tarojs/components';
import Taro, { useRouter } from '@tarojs/taro';
import { useState, useEffect } from 'react';
import { Button, Empty } from '@nutui/nutui-react-taro';
import { appointmentApi } from '@hospital/api';
import { TIME_SLOT_MAP } from '@hospital/shared';
import type { PendingAppointment } from '@hospital/api';
import { DoctorIcon, CheckCircleIcon } from '../../../components/Icons';
import { getToken } from '../../../utils/auth';
import { getThemePrimaryColor } from '../../../utils/theme';
import LoginPopup from '../../../components/LoginPopup';
import CheckinSuccessModal from '../../components/CheckinSuccessModal';
import './select.less';

// 辅助函数：格式化剩余时间（智能显示天/时/分/秒）
const formatTimeRemaining = (seconds: number): string => {
  if (seconds <= 0) return '0秒';

  const days = Math.floor(seconds / 86400);
  const hours = Math.floor((seconds % 86400) / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const secs = seconds % 60;

  // 超过1天：显示 X天X小时
  if (days > 0) {
    if (hours > 0) {
      return `${days}天${hours}小时`;
    }
    return `${days}天`;
  }

  // 超过1小时：显示 X小时X分
  if (hours > 0) {
    if (minutes > 0) {
      return `${hours}小时${minutes}分`;
    }
    return `${hours}小时`;
  }

  // 超过1分钟：显示 X分X秒
  if (minutes > 0) {
    if (secs > 0) {
      return `${minutes}分${secs}秒`;
    }
    return `${minutes}分钟`;
  }

  // 小于1分钟：显示 X秒
  return `${secs}秒`;
};

// 辅助函数：格式化时间 HH:mm
const formatTime = (date: Date): string => {
  const hours = String(date.getHours()).padStart(2, '0');
  const minutes = String(date.getMinutes()).padStart(2, '0');
  return `${hours}:${minutes}`;
};

// 辅助函数：智能格式化签到时间窗口
const formatCheckinTimeWindow = (openAt: string, closeAt: string): string => {
  const openDate = new Date(openAt);
  const closeDate = new Date(closeAt);
  const now = new Date();
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const openDay = new Date(openDate.getFullYear(), openDate.getMonth(), openDate.getDate());
  const closeDay = new Date(closeDate.getFullYear(), closeDate.getMonth(), closeDate.getDate());

  const openTimeStr = formatTime(openDate);
  const closeTimeStr = formatTime(closeDate);

  // 都是今天
  if (openDay.getTime() === today.getTime() && closeDay.getTime() === today.getTime()) {
    return `今天 ${openTimeStr} - ${closeTimeStr}`;
  }

  // 判断是否是明天
  const tomorrow = new Date(today);
  tomorrow.setDate(tomorrow.getDate() + 1);

  // 开始时间是明天
  if (openDay.getTime() === tomorrow.getTime()) {
    if (closeDay.getTime() === tomorrow.getTime()) {
      return `明天 ${openTimeStr} - ${closeTimeStr}`;
    }
    return `明天 ${openTimeStr} - ${closeDate.getMonth() + 1}/${closeDate.getDate()} ${closeTimeStr}`;
  }

  // 其他情况：显示具体日期
  const formatDateStr = (d: Date) => `${d.getMonth() + 1}/${d.getDate()}`;

  if (openDay.getTime() === closeDay.getTime()) {
    return `${formatDateStr(openDate)} ${openTimeStr} - ${closeTimeStr}`;
  }

  return `${formatDateStr(openDate)} ${openTimeStr} - ${formatDateStr(closeDate)} ${closeTimeStr}`;
};

const CheckinSelectPage = () => {
  const router = useRouter();
  const { storeId } = router.params;

  const [loading, setLoading] = useState(true);
  const [appointments, setAppointments] = useState<PendingAppointment[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [showLoginPopup, setShowLoginPopup] = useState(false);

  // 新增：当前时间（用于智能倒计时）
  const [currentTime, setCurrentTime] = useState(new Date());

  // 新增：签到成功弹窗状态
  const [showSuccessModal, setShowSuccessModal] = useState(false);
  const [queueNumber, setQueueNumber] = useState(0);

  useEffect(() => {
    // 检查登录状态
    const token = getToken();
    if (!token) {
      Taro.showToast({ title: '请先登录', icon: 'none' });
      setShowLoginPopup(true);
      setLoading(false);
      return;
    }
    if (storeId) {
      loadAppointments();
    }
  }, [storeId]);

  // 登录成功后加载数据
  const handleLoginSuccess = () => {
    setShowLoginPopup(false);
    if (storeId) {
      loadAppointments();
    }
  };

  // 新增：智能倒计时（默认每分钟刷新，当有预约在1分钟内开放或关闭时切换为每秒刷新）
  useEffect(() => {
    if (appointments.length === 0) return;

    // 计算是否需要秒级刷新
    const needSecondPrecision = appointments.some(item => {
      if (item.minutesUntilOpen !== null && item.minutesUntilOpen < 1) return true;
      if (item.minutesUntilClose !== null && item.minutesUntilClose < 1) return true;
      return false;
    });

    const interval = needSecondPrecision ? 1000 : 60000;

    const timer = setInterval(() => {
      setCurrentTime(new Date());
    }, interval);

    return () => clearInterval(timer);
  }, [appointments]);

  const loadAppointments = async () => {
    try {
      const data = await appointmentApi.getTodayPending(storeId!);
      setAppointments(data);
      // 如果只有一个预约，自动选中
      if (data.length === 1) {
        setSelectedId(data[0].id);
      }
    } catch (error: any) {
      console.error('[选择预约] 加载失败:', error);
      Taro.showToast({
        title: error.message || '加载失败',
        icon: 'none',
      });
    } finally {
      setLoading(false);
    }
  };

  const handleSelect = (id: string, signInStatus?: string) => {
    // 只允许选择可签到的预约
    if (signInStatus === 'early' || signInStatus === 'late') {
      return;
    }
    setSelectedId(id);
  };

  const handleSignIn = async () => {
    if (!selectedId) {
      Taro.showToast({
        title: '请选择要签到的预约',
        icon: 'none',
      });
      return;
    }

    setSubmitting(true);

    try {
      const result = await appointmentApi.signIn(selectedId);

      // 设置排队号并显示签到成功弹窗
      setQueueNumber(result.queueNumber);
      setShowSuccessModal(true);
    } catch (error: any) {
      console.error('[签到] 失败:', error);
      Taro.showToast({
        title: error.message || '签到失败',
        icon: 'none',
      });
    } finally {
      setSubmitting(false);
    }
  };

  // 关闭签到成功弹窗
  const handleSuccessModalClose = () => {
    setShowSuccessModal(false);
    // 返回首页
    Taro.switchTab({ url: '/pages/appointment/index' });
  };

  if (loading) {
    return (
      <View className="checkin-select-page">
        <View className="loading-state">加载中...</View>
      </View>
    );
  }

  return (
    <View className="checkin-select-page">
      {appointments.length === 0 ? (
        <View className="empty-state">
          <Empty description="暂无待签到的预约" />
          <Text className="empty-tip">
            您在该门店今日没有待签到的预约，请确认预约信息
          </Text>
        </View>
      ) : (
        <>
          <View className="page-header">
            <Text className="header-title">选择要签到的预约</Text>
            <Text className="header-desc">
              您有 {appointments.length} 个待签到的预约
            </Text>
          </View>

          <View className="appointment-list">
            {appointments.map((item) => {
              const isDisabled = item.signInStatus === 'early' || item.signInStatus === 'late';

              // 计算实时倒计时
              let countdownInfo = null;
              if (item.checkinOpenAt && item.checkinCloseAt) {
                const openTime = new Date(item.checkinOpenAt);
                const closeTime = new Date(item.checkinCloseAt);
                const now = currentTime;

                if (now < openTime) {
                  const seconds = Math.floor((openTime.getTime() - now.getTime()) / 1000);
                  const text = formatTimeRemaining(seconds);
                  countdownInfo = {
                    type: 'waiting',
                    text,
                    percent: Math.max(0, Math.min(100, (seconds / ((item.minutesUntilOpen || 1) * 60)) * 100))
                  };
                } else if (now < closeTime) {
                  const seconds = Math.floor((closeTime.getTime() - now.getTime()) / 1000);
                  const text = formatTimeRemaining(seconds);
                  countdownInfo = {
                    type: 'available',
                    text,
                    percent: Math.max(0, Math.min(100, seconds / ((item.minutesUntilClose || 1) * 60) * 100))
                  };
                }
              }

              return (
                <View
                  key={item.id}
                  className={`appointment-card ${selectedId === item.id ? 'selected' : ''} ${isDisabled ? 'disabled' : ''}`}
                  data-status={item.signInStatus}
                  onClick={() => handleSelect(item.id, item.signInStatus)}
                >
                  <View className="card-icon">
                    <DoctorIcon size={40} color={getThemePrimaryColor()} />
                  </View>
                  <View className="card-content">
                    <View className="card-header">
                      <Text className="doctor-name">{item.doctorName || '医生'}</Text>
                      <Text className="dept-name">{item.departmentName}</Text>
                    </View>
                    <Text className="patient-name">就诊人：{item.patientName}</Text>
                    <View className="schedule-info">
                      <Text className="schedule-date">{item.scheduleDate}</Text>
                      <Text className="schedule-time">
                        {item.startTime ? item.startTime.substring(0, 5) : (item.timeSlot !== null ? TIME_SLOT_MAP[item.timeSlot] : '')}
                        {item.endTime ? ` ~ ${item.endTime.substring(0, 5)}` : ''}
                      </Text>
                    </View>

                    {/* 新增：时间窗口信息 */}
                    {item.checkinOpenAt && item.checkinCloseAt && (
                      <View className="time-window-info">
                        <Text className="window-label">签到时间：</Text>
                        <Text className="window-time">
                          {formatCheckinTimeWindow(item.checkinOpenAt, item.checkinCloseAt)}
                        </Text>
                      </View>
                    )}

                    {/* 签到状态 */}
                    {item.signInMessage && (
                      <View className={`signin-status ${item.signInStatus}`}>
                        <Text className="status-text">{item.signInMessage}</Text>
                      </View>
                    )}

                    {/* 新增：倒计时或时间进度条 */}
                    {countdownInfo && (
                      <View className={`countdown-container ${countdownInfo.type}`}>
                        {countdownInfo.type === 'waiting' ? (
                          <>
                            <Text className="countdown-label">等待签到：</Text>
                            <Text className="countdown-text">{countdownInfo.text}</Text>
                          </>
                        ) : (
                          <>
                            <Text className="countdown-label">剩余时间：</Text>
                            <Text className="countdown-text warning">{countdownInfo.text}</Text>
                          </>
                        )}
                        <View className="countdown-bar">
                          <View
                            className={`countdown-fill ${countdownInfo.type}`}
                            style={{ width: `${countdownInfo.percent}%` }}
                          />
                        </View>
                      </View>
                    )}
                  </View>
                  {selectedId === item.id && !isDisabled && (
                    <View className="selected-icon">
                      <CheckCircleIcon size={24} color="#10B981" />
                    </View>
                  )}
                </View>
              );
            })}
          </View>

          <View className="action-bar">
            <Button
              type="primary"
              block
              loading={submitting}
              disabled={!selectedId}
              onClick={handleSignIn}
            >
              确认签到
            </Button>
          </View>
        </>
      )}

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

      {/* 签到成功弹窗 */}
      <CheckinSuccessModal
        visible={showSuccessModal}
        queueNumber={queueNumber}
        onClose={handleSuccessModalClose}
      />
    </View>
  );
};

export default CheckinSelectPage;

