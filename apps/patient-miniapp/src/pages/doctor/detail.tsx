import { View, Text, Image } from '@tarojs/components';
import Taro, { useRouter } from '@tarojs/taro';
import { Button } from '@nutui/nutui-react-taro';
import { useState, useEffect } from 'react';
import { doctorApi, scheduleApi } from '@hospital/api';
import { TIME_SLOT_MAP } from '@hospital/shared';
import type { Doctor, AvailableSchedule } from '@hospital/shared';
import './detail.less';

const WEEKDAY_NAMES = ['周日', '周一', '周二', '周三', '周四', '周五', '周六'];

const DoctorDetailPage = () => {
  const router = useRouter();
  const { id } = router.params;

  const [loading, setLoading] = useState(true);
  const [doctor, setDoctor] = useState<Doctor | null>(null);
  const [schedules, setSchedules] = useState<AvailableSchedule[]>([]);

  useEffect(() => {
    if (id) {
      loadData();
    }
  }, [id]);

  const loadData = async () => {
    try {
      const [doctorData, scheduleData] = await Promise.all([
        doctorApi.getDetail(id!),
        scheduleApi.getAvailable(id!, 14),
      ]);
      setDoctor(doctorData);
      setSchedules(scheduleData);
    } catch (error) {
      console.error('加载数据失败', error);
      Taro.showToast({ title: '加载失败', icon: 'none' });
    } finally {
      setLoading(false);
    }
  };

  const handleBook = (schedule: AvailableSchedule) => {
    if (schedule.availableSlots <= 0) {
      Taro.showToast({ title: '该时段已约满', icon: 'none' });
      return;
    }
    Taro.navigateTo({
      url: `/pages/booking/index?doctorId=${id}&scheduleId=${schedule.id}&date=${schedule.scheduleDate}&timeSlot=${schedule.timeSlot}`,
    });
  };

  const getWeekday = (dateStr: string) => {
    const date = new Date(dateStr);
    return WEEKDAY_NAMES[date.getDay()];
  };

  const formatDate = (dateStr: string) => {
    return dateStr.substring(5).replace('-', '/');
  };

  // 按日期分组
  const groupedSchedules = schedules.reduce((acc, schedule) => {
    const date = schedule.scheduleDate;
    if (!acc[date]) {
      acc[date] = [];
    }
    acc[date].push(schedule);
    return acc;
  }, {} as Record<string, AvailableSchedule[]>);

  if (loading) {
    return (
      <View className="doctor-detail-page">
        <View className="loading">加载中...</View>
      </View>
    );
  }

  if (!doctor) {
    return (
      <View className="doctor-detail-page">
        <View className="loading">医生信息不存在</View>
      </View>
    );
  }

  return (
    <View className="doctor-detail-page">
      {/* 医生信息 */}
      <View className="doctor-info">
        <View className="info-header">
          <View className="avatar">
            {doctor.avatar ? (
              <Image src={doctor.avatar} mode="aspectFill" />
            ) : (
              <Text>👨‍⚕️</Text>
            )}
          </View>
          <View className="info-content">
            <View className="name-row">
              <Text className="name">{doctor.name}</Text>
              {doctor.title && <Text className="title">{doctor.title}</Text>}
            </View>
            <Text className="dept">{doctor.departmentName}</Text>
            <Text className="fee">挂号费：¥{doctor.registrationFee}</Text>
          </View>
        </View>

        <View className="info-section">
          <Text className="label">擅长领域</Text>
          <Text className="value">{doctor.specialty || '暂无信息'}</Text>
        </View>

        <View className="info-section">
          <Text className="label">医生简介</Text>
          <Text className="value">{doctor.introduction || '暂无简介'}</Text>
        </View>
      </View>

      {/* 排班信息 */}
      <View className="schedule-section">
        <Text className="section-title">选择就诊时间</Text>

        {Object.keys(groupedSchedules).length === 0 ? (
          <View className="no-schedule">
            <Text>暂无可预约时段</Text>
          </View>
        ) : (
          <View className="schedule-list">
            {Object.entries(groupedSchedules).map(([date, daySchedules]) => (
              <View key={date} className="schedule-row">
                <View className="schedule-date">
                  <Text className="date">{formatDate(date)}</Text>
                  <Text className="weekday">{getWeekday(date)}</Text>
                </View>
                <View className="schedule-slots">
                  {daySchedules.map((schedule) => (
                    <Button
                      key={schedule.id}
                      className={`slot-btn ${schedule.availableSlots > 0 ? 'available' : 'full'}`}
                      disabled={schedule.availableSlots === 0}
                      onClick={() => handleBook(schedule)}
                    >
                      <Text className="slot-time">{TIME_SLOT_MAP[schedule.timeSlot]}</Text>
                      <Text className="slot-count">
                        {schedule.availableSlots > 0 ? `余${schedule.availableSlots}` : '约满'}
                      </Text>
                    </Button>
                  ))}
                </View>
              </View>
            ))}
          </View>
        )}
      </View>
    </View>
  );
};

export default DoctorDetailPage;
