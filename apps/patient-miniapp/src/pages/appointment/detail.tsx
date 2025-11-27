import { View, Text } from '@tarojs/components';
import Taro, { useRouter } from '@tarojs/taro';
import { Button } from '@nutui/nutui-react-taro';
import { useState, useEffect } from 'react';
import { appointmentApi } from '@hospital/api';
import { APPOINTMENT_STATUS_MAP, TIME_SLOT_MAP } from '@hospital/shared';
import type { AppointmentDetail } from '@hospital/shared';
import './detail.less';

const statusColorMap: Record<number, string> = {
  1: '#1890ff',
  2: '#52c41a',
  3: '#faad14',
  5: '#52c41a',
  6: '#999',
  7: '#ff4d4f',
};

const AppointmentDetailPage = () => {
  const router = useRouter();
  const { id, appointmentNo } = router.params;

  const [loading, setLoading] = useState(true);
  const [appointment, setAppointment] = useState<AppointmentDetail | null>(null);

  useEffect(() => {
    loadAppointment();
  }, []);

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

  if (loading || !appointment) {
    return <View className="loading">加载中...</View>;
  }

  return (
    <View className="appointment-detail-page">
      <View
        className="status-header"
        style={{ background: statusColorMap[appointment.status] }}
      >
        <Text className="status-text">{APPOINTMENT_STATUS_MAP[appointment.status]}</Text>
        {appointment.queueNumber && (
          <Text className="queue-text">排队号：第{appointment.queueNumber}号</Text>
        )}
      </View>

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
          <Text className="value">{TIME_SLOT_MAP[appointment.timeSlot || 'AM']}</Text>
        </View>
        <View className="info-row">
          <Text className="label">预约时间</Text>
          <Text className="value">{appointment.createdAt}</Text>
        </View>
      </View>

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
        <View className="info-row">
          <Text className="label">挂号费</Text>
          <Text className="value fee">¥{appointment.fee}</Text>
        </View>
      </View>

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

      {appointment.status === 1 && (
        <View className="actions">
          <Button block onClick={handleCancel}>取消预约</Button>
          <Button type="primary" block onClick={handleSignIn}>签到</Button>
        </View>
      )}
    </View>
  );
};

export default AppointmentDetailPage;

