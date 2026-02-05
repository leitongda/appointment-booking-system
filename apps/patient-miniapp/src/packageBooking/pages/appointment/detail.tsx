import { View, Text } from '@tarojs/components';
import Taro, { useRouter } from '@tarojs/taro';
import { Button } from '@nutui/nutui-react-taro';
import { useState, useEffect } from 'react';
import { appointmentApi, settingsApi } from '@hospital/api';
import type { TimePeriodConfig } from '@hospital/api';
import { APPOINTMENT_STATUS_MAP, TIME_SLOT_MAP, getPeriodNameFromTime } from '@hospital/shared';
import { getToken } from '../../../utils/auth';
import { getThemeGradient } from '../../../utils/theme';
import { formatTime, isAppointmentExpired } from '../../../utils/url';
import { triggerCheckinScan } from '../../../utils/checkin';
import LoginPopup from '../../../components/LoginPopup';
import type { AppointmentDetail } from '@hospital/shared';
import {
  CalendarIcon,
  CheckCircleIcon,
  ClockIcon,
  CheckIcon,
  CloseCircleIcon,
} from '../../../components/Icons';
import './detail.less';

// 状态图标映射
const StatusIconMap: Record<number, React.ComponentType<{ size?: number; color?: string }>> = {
  1: CalendarIcon,
  2: CheckCircleIcon,
  3: ClockIcon,
  5: CheckIcon,
  6: CloseCircleIcon,
  7: CloseCircleIcon,
};

// 状态颜色映射
const statusStyleMap: Record<number, { background: string }> = {
  1: { background: getThemeGradient() },
  2: { background: 'linear-gradient(135deg, #10B981 0%, #059669 100%)' },
  3: { background: 'linear-gradient(135deg, #F59E0B 0%, #D97706 100%)' },
  5: { background: 'linear-gradient(135deg, #10B981 0%, #059669 100%)' },
  6: { background: 'linear-gradient(135deg, #64748B 0%, #475569 100%)' },
  7: { background: 'linear-gradient(135deg, #EF4444 0%, #DC2626 100%)' },
};

const AppointmentDetailPage = () => {
  const router = useRouter();
  const { id, appointmentNo } = router.params;

  const [loading, setLoading] = useState(true);
  const [appointment, setAppointment] = useState<AppointmentDetail | null>(null);
  const [showLoginPopup, setShowLoginPopup] = useState(false);
  const [timePeriods, setTimePeriods] = useState<TimePeriodConfig[]>([]);

  useEffect(() => {
    // 检查登录状态
    const token = getToken();
    if (!token) {
      Taro.showToast({ title: '请先登录', icon: 'none' });
      setShowLoginPopup(true);
      setLoading(false);
      return;
    }
    loadAppointment();
  }, []);

  // 登录成功后加载数据
  const handleLoginSuccess = () => {
    setShowLoginPopup(false);
    loadAppointment();
  };

  const loadAppointment = async () => {
    try {
      const [data, timePeriodsRes] = await Promise.all([
        id
          ? appointmentApi.getDetail(id)
          : appointmentApi.getDetailByNo(appointmentNo!),
        settingsApi.getTimePeriods().catch(() => ({ periods: [], isCustom: false })),
      ]);
      setAppointment(data);
      setTimePeriods(timePeriodsRes.periods || []);
    } catch (error) {
      console.error('加载预约详情失败', error);
    } finally {
      setLoading(false);
    }
  };

  const handleCancel = async () => {
    const result = await Taro.showModal({
      title: '取消预约',
      content: '确定要取消预约吗？',
    });

    if (!result.confirm) return;

    try {
      await appointmentApi.cancel(appointment!.id);
      Taro.showToast({ title: '取消成功', icon: 'success' });
      loadAppointment();
    } catch (error: any) {
      Taro.showToast({ title: error.message || '取消失败', icon: 'none' });
    }
  };

  const handleSignIn = () => {
    // 直接触发扫码签到
    triggerCheckinScan();
  };

  // 复制预约单号到剪贴板
  const handleCopyAppointmentNo = () => {
    if (!appointment?.appointmentNo) return;
    Taro.setClipboardData({
      data: appointment.appointmentNo,
      success: () => {
        Taro.showToast({ title: '单号已复制', icon: 'success' });
      },
    });
  };

  if (loading) {
    return (
      <View className="appointment-detail-page">
        <View className="loading">加载中...</View>
      </View>
    );
  }

  if (!appointment) {
    return (
      <View className="appointment-detail-page">
        <View className="loading">预约信息不存在</View>
      </View>
    );
  }

  const StatusIcon = StatusIconMap[appointment.status] || CalendarIcon;

  return (
    <View className="appointment-detail-page">
      {/* 状态头部 */}
      <View
        className="status-header"
        style={statusStyleMap[appointment.status]}
      >
        <View className="status-content">
          <View className="status-icon">
            <StatusIcon size={32} color="#fff" />
          </View>
          <Text className="status-text">{APPOINTMENT_STATUS_MAP[appointment.status]}</Text>
          {appointment.queueNumber && (
            <Text className="queue-text">排队号：第{appointment.queueNumber}号</Text>
          )}
        </View>
      </View>

      {/* 预约信息 */}
      <View className="section">
        <Text className="section-title">预约信息</Text>
        <View className="info-row" onClick={handleCopyAppointmentNo}>
          <Text className="label">预约单号</Text>
          <Text className="value appointment-no-value">
            {appointment.appointmentNo}
            <Text className="copy-hint">点击复制</Text>
          </Text>
        </View>
        <View className="info-row">
          <Text className="label">就诊日期</Text>
          <Text className="value">{appointment.scheduleDate}</Text>
        </View>
        <View className="info-row">
          <Text className="label">就诊时段</Text>
          <Text className="value">
            {appointment.startTime 
              ? getPeriodNameFromTime(formatTime(appointment.startTime) || '', timePeriods) 
              : TIME_SLOT_MAP[appointment.timeSlot || 'AM']
            }
            {appointment.startTime && appointment.endTime && ` (${formatTime(appointment.startTime)}-${formatTime(appointment.endTime)})`}
          </Text>
        </View>
        <View className="info-row">
          <Text className="label">预约时间</Text>
          <Text className="value">{appointment.createdAt}</Text>
        </View>
      </View>

      {/* 医生信息 */}
      <View className="section">
        <Text className="section-title">医生信息</Text>
        <View className="info-row">
          <Text className="label">医生</Text>
          <Text className="value">{appointment.doctorName}</Text>
        </View>
        <View className="info-row">
          <Text className="label">科室</Text>
          <Text className="value">{appointment.departmentName}</Text>
        </View>
      </View>

      {/* 就诊人信息 */}
      <View className="section">
        <Text className="section-title">就诊人信息</Text>
        <View className="info-row">
          <Text className="label">姓名</Text>
          <Text className="value">{appointment.patientName}</Text>
        </View>
        <View className="info-row">
          <Text className="label">手机</Text>
          <Text className="value">
            {appointment.patientPhone?.replace(/(\d{3})\d{4}(\d{4})/, '$1****$2')}
          </Text>
        </View>
      </View>

      {/* 底部操作 */}
      {appointment.status === 1 && !isAppointmentExpired(appointment.scheduleDate, appointment.endTime, appointment.timeSlot) && (
        <View className="actions">
          <Button className="cancel-btn" block onClick={handleCancel}>
            取消预约
          </Button>
          <Button className="primary-btn" type="primary" block onClick={handleSignIn}>
            扫码签到
          </Button>
        </View>
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
    </View>
  );
};

export default AppointmentDetailPage;
