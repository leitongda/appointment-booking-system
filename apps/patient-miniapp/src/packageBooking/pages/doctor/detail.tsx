import { View, Text, Image, ScrollView } from '@tarojs/components';
import Taro, { useRouter } from '@tarojs/taro';
import { Picker } from '@nutui/nutui-react-taro';
import { useState, useEffect, useMemo } from 'react';
import { doctorApi, scheduleApi, favoriteApi } from '@hospital/api';
import { TIME_SLOT_MAP } from '@hospital/shared';
import type { Doctor, AvailableSchedule } from '@hospital/shared';
import { DoctorIcon, HeartIcon, HeartOutlineIcon } from '../../../components/Icons';
import { getToken } from '../../../utils/auth';
import LoginPopup from '../../../components/LoginPopup';
import './detail.less';

const WEEKDAY_NAMES = ['周日', '周一', '周二', '周三', '周四', '周五', '周六'];

const DoctorDetailPage = () => {
  const router = useRouter();
  const { id } = router.params;

  const [loading, setLoading] = useState(true);
  const [doctor, setDoctor] = useState<Doctor | null>(null);
  const [schedules, setSchedules] = useState<AvailableSchedule[]>([]);
  const [selectedDate, setSelectedDate] = useState<string>('');
  const [showTimePicker, setShowTimePicker] = useState(false);
  const [selectedTimeSlot, setSelectedTimeSlot] = useState<'AM' | 'PM' | null>(null);
  
  // 收藏相关状态
  const [isFavorited, setIsFavorited] = useState(false);
  const [favoriteId, setFavoriteId] = useState<string | null>(null);
  const [favoriteLoading, setFavoriteLoading] = useState(false);
  const [showLoginPopup, setShowLoginPopup] = useState(false);

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
      
      // 默认选中第一个日期
      if (scheduleData.length > 0) {
        const dates = [...new Set(scheduleData.map(s => s.scheduleDate))];
        if (dates.length > 0) {
          setSelectedDate(dates[0]);
        }
      }
      
      // 检查收藏状态
      if (getToken()) {
        checkFavoriteStatus();
      }
    } catch (error) {
      console.error('加载数据失败', error);
      Taro.showToast({ title: '加载失败', icon: 'none' });
    } finally {
      setLoading(false);
    }
  };

  // 检查收藏状态
  const checkFavoriteStatus = async () => {
    if (!id) return;
    try {
      const result = await favoriteApi.check('doctor', id);
      setIsFavorited(result.isFavorited);
      setFavoriteId(result.favoriteId || null);
    } catch (error) {
      console.error('检查收藏状态失败', error);
    }
  };

  // 切换收藏状态
  const handleToggleFavorite = async () => {
    // 未登录时弹出登录弹窗
    if (!getToken()) {
      setShowLoginPopup(true);
      return;
    }

    if (!id || favoriteLoading) return;

    setFavoriteLoading(true);
    try {
      if (isFavorited && favoriteId) {
        // 取消收藏
        await favoriteApi.remove(favoriteId);
        setIsFavorited(false);
        setFavoriteId(null);
        Taro.showToast({ title: '已取消收藏', icon: 'none' });
      } else {
        // 添加收藏
        const result = await favoriteApi.add({ targetType: 'doctor', targetId: id });
        setIsFavorited(true);
        setFavoriteId(result.id);
        Taro.showToast({ title: '收藏成功', icon: 'success' });
      }
    } catch (error: any) {
      Taro.showToast({ title: error.message || '操作失败', icon: 'none' });
    } finally {
      setFavoriteLoading(false);
    }
  };

  // 登录成功后的回调
  const handleLoginSuccess = () => {
    setShowLoginPopup(false);
    checkFavoriteStatus();
  };

  // 获取所有日期列表
  const dateList = useMemo(() => {
    const dates = [...new Set(schedules.map(s => s.scheduleDate))].sort();
    return dates.map(date => ({
      date,
      weekday: WEEKDAY_NAMES[new Date(date).getDay()],
      formatted: date.substring(5).replace('-', '/'),
    }));
  }, [schedules]);

  // 获取选中日期的排班
  const selectedDateSchedules = useMemo(() => {
    return schedules.filter(s => s.scheduleDate === selectedDate);
  }, [schedules, selectedDate]);

  // 获取上午/下午的排班汇总
  const timeSlotSummary = useMemo(() => {
    const morning = selectedDateSchedules.filter(s => s.timeSlot === 'AM' || s.timeSlot === 'morning');
    const afternoon = selectedDateSchedules.filter(s => s.timeSlot === 'PM' || s.timeSlot === 'afternoon');
    
    const morningTotal = morning.reduce((sum, s) => sum + s.availableSlots, 0);
    const afternoonTotal = afternoon.reduce((sum, s) => sum + s.availableSlots, 0);
    
    return {
      morning: { schedules: morning, available: morningTotal },
      afternoon: { schedules: afternoon, available: afternoonTotal },
    };
  }, [selectedDateSchedules]);

  // Picker 选项
  const pickerOptions = useMemo(() => {
    if (!selectedTimeSlot) return [];
    
    const slotSchedules = selectedTimeSlot === 'AM' 
      ? timeSlotSummary.morning.schedules 
      : timeSlotSummary.afternoon.schedules;
    
    return slotSchedules
      .filter(s => s.availableSlots > 0)
      .map(s => ({
        value: s.id,
        text: `${TIME_SLOT_MAP[s.timeSlot]} (余${s.availableSlots})`,
        schedule: s,
      }));
  }, [selectedTimeSlot, timeSlotSummary]);

  const handleDateSelect = (date: string) => {
    setSelectedDate(date);
  };

  const handleTimeSlotClick = (slot: 'AM' | 'PM') => {
    const summary = slot === 'AM' ? timeSlotSummary.morning : timeSlotSummary.afternoon;
    
    if (summary.available <= 0) {
      Taro.showToast({ title: '该时段已约满', icon: 'none' });
      return;
    }
    
    // 如果只有一个可选项，直接跳转
    const availableSchedules = summary.schedules.filter(s => s.availableSlots > 0);
    if (availableSchedules.length === 1) {
      handleBook(availableSchedules[0]);
      return;
    }
    
    // 多个选项时显示Picker
    setSelectedTimeSlot(slot);
    setShowTimePicker(true);
  };

  const handlePickerConfirm = (_options: any, values: any[]) => {
    const scheduleId = values[0];
    const schedule = schedules.find(s => s.id === scheduleId);
    if (schedule) {
      handleBook(schedule);
    }
    setShowTimePicker(false);
    setSelectedTimeSlot(null);
  };

  const handleBook = (schedule: AvailableSchedule) => {
    if (schedule.availableSlots <= 0) {
      Taro.showToast({ title: '该时段已约满', icon: 'none' });
      return;
    }
    Taro.navigateTo({
      url: `/packageBooking/pages/booking/index?doctorId=${id}&scheduleId=${schedule.id}&date=${schedule.scheduleDate}&timeSlot=${schedule.timeSlot}`,
    });
  };

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
              <DoctorIcon size={48} color="#4F46E5" />
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
          {/* 收藏按钮 */}
          <View 
            className={`favorite-btn ${isFavorited ? 'active' : ''} ${favoriteLoading ? 'loading' : ''}`}
            onClick={handleToggleFavorite}
          >
            {isFavorited ? (
              <HeartIcon size={20} color="#EF4444" />
            ) : (
              <HeartOutlineIcon size={20} color="#94A3B8" />
            )}
            <Text className="favorite-text">{isFavorited ? '已收藏' : '收藏'}</Text>
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

      {/* 排班信息 - 新布局 */}
      <View className="schedule-section">
        <View className="section-header">
          <Text className="section-title">选择就诊时间</Text>
          {dateList.length > 3 && (
            <Text className="scroll-hint">左右滑动查看更多 →</Text>
          )}
        </View>

        {dateList.length === 0 ? (
          <View className="no-schedule">
            <Text>暂无可预约时段</Text>
          </View>
        ) : (
          <>
            {/* 日期横向滑动选择 */}
            <ScrollView 
              className="date-scroll" 
              scrollX 
              enhanced 
              showScrollbar={false}
            >
              <View className="date-list">
                {dateList.map(item => (
                  <View
                    key={item.date}
                    className={`date-item ${selectedDate === item.date ? 'active' : ''}`}
                    onClick={() => handleDateSelect(item.date)}
                  >
                    <Text className="date-weekday">{item.weekday}</Text>
                    <Text className="date-day">{item.formatted}</Text>
                  </View>
                ))}
              </View>
            </ScrollView>

            {/* 上午/下午时段选择 - 两列布局 */}
            <View className="time-slots">
              <View 
                className={`time-slot-card ${timeSlotSummary.morning.available > 0 ? 'available' : 'full'}`}
                onClick={() => handleTimeSlotClick('AM')}
              >
                <Text className="slot-period">上午</Text>
                <Text className="slot-available">
                  {timeSlotSummary.morning.available > 0 ? `余 ${timeSlotSummary.morning.available}` : '约满'}
                </Text>
                {doctor.departmentName && (
                  <Text className="slot-dept">{doctor.departmentName}</Text>
                )}
              </View>
              
              <View 
                className={`time-slot-card ${timeSlotSummary.afternoon.available > 0 ? 'available' : 'full'}`}
                onClick={() => handleTimeSlotClick('PM')}
              >
                <Text className="slot-period">下午</Text>
                <Text className="slot-available">
                  {timeSlotSummary.afternoon.available > 0 ? `余 ${timeSlotSummary.afternoon.available}` : '约满'}
                </Text>
                {doctor.departmentName && (
                  <Text className="slot-dept">{doctor.departmentName}</Text>
                )}
              </View>
            </View>
          </>
        )}
      </View>

      {/* 时段选择 Picker */}
      <Picker
        visible={showTimePicker}
        options={[pickerOptions]}
        onConfirm={handlePickerConfirm}
        onClose={() => {
          setShowTimePicker(false);
          setSelectedTimeSlot(null);
        }}
      />

      {/* 登录弹窗 */}
      <LoginPopup
        visible={showLoginPopup}
        onClose={() => setShowLoginPopup(false)}
        onSuccess={handleLoginSuccess}
      />
    </View>
  );
};

export default DoctorDetailPage;
