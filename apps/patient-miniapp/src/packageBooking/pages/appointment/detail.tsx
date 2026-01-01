import { View, Text } from '@tarojs/components';
import Taro, { useRouter } from '@tarojs/taro';
import { Button } from '@nutui/nutui-react-taro';
import { useState, useEffect } from 'react';
import { appointmentApi } from '@hospital/api';
import { APPOINTMENT_STATUS_MAP, TIME_SLOT_MAP } from '@hospital/shared';
import { getToken } from '../../../utils/auth';
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
  1: { background: 'linear-gradient(135deg, #4F46E5 0%, #7C3AED 100%)' },
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
      const data = id
        ? await appointmentApi.getDetail(id)
        : await appointmentApi.getDetailByNo(appointmentNo!);
      setAppointment(data);
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

  const handleSignIn = async () => {
    try {
      const result = await appointmentApi.signIn(appointment!.id);
      Taro.showToast({ title: `签到成功，您是第${result.queueNumber}号`, icon: 'success' });
      loadAppointment();
    } catch (error: any) {
      Taro.showToast({ title: error.message || '签到失败', icon: 'none' });
    }
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
        <View className="info-row">
          <Text className="label">预约单号</Text>
          <Text className="value">{appointment.appointmentNo}</Text>
        </View>
        <View className="info-row">
          <Text className="label">就诊日期</Text>
          <Text className="value">{appointment.scheduleDate}</Text>
        </View>
        <View className="info-row">
          <Text className="label">就诊时段</Text>
          <Text className="value">
            {TIME_SLOT_MAP[appointment.timeSlot || 'AM']}
            {appointment.startTime && appointment.endTime && ` (${appointment.startTime}-${appointment.endTime})`}
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
      {appointment.status === 1 && (
        <View className="actions">
          <Button className="btn-cancel" block onClick={handleCancel}>
            取消预约
          </Button>
          <Button className="btn-primary" type="primary" block onClick={handleSignIn}>
            签到
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
