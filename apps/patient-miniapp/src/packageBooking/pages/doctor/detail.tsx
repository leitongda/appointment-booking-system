import { View, Text, Image, ScrollView, RichText } from '@tarojs/components';
import Taro, { useRouter, usePullDownRefresh } from '@tarojs/taro';
import { Button } from '@nutui/nutui-react-taro';
import { useState, useEffect, useMemo } from 'react';
import { doctorApi, scheduleApi, favoriteApi, settingsApi } from '@hospital/api';
import type { Doctor, AvailableSchedule } from '@hospital/shared';
import { DoctorIcon, HeartIcon, HeartOutlineIcon } from '../../../components/Icons';
import { getToken } from '../../../utils/auth';
import { getImageUrl, formatTime } from '../../../utils/url';
import LoginPopup from '../../../components/LoginPopup';
import './detail.less';

const WEEKDAY_NAMES = ['周日', '周一', '周二', '周三', '周四', '周五', '周六'];

const DoctorDetailPage = () => {
  const router = useRouter();
  const { id } = router.params;

  const [loading, setLoading] = useState(true);
  const [doctor, setDoctor] = useState<Doctor | null>(null);
  const [schedules, setSchedules] = useState<AvailableSchedule[]>([]);
  const [advanceDays, setAdvanceDays] = useState<number>(10); // 可提前预约天数
  const [selectedDate, setSelectedDate] = useState<string>('');
  const [bookingRules, setBookingRules] = useState<any>({}); // 预约规则

  // 时段选择状态（单选）
  const [selectedSlot, setSelectedSlot] = useState<'AM' | 'PM' | null>(null);
  // 班次选择 Picker 状态
  const [showSlotPicker, setShowSlotPicker] = useState(false);
  // 选中的具体班次
  const [selectedScheduleId, setSelectedScheduleId] = useState<string | null>(null);

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

  // 下拉刷新
  usePullDownRefresh(() => {
    if (id) {
      loadData().finally(() => {
        Taro.stopPullDownRefresh();
      });
    } else {
      Taro.stopPullDownRefresh();
    }
  });

  const loadData = async () => {
    try {
      // 先获取医生信息，以便获取门店ID
      const doctorData = await doctorApi.getDetail(id!);
      setDoctor(doctorData);

      // 获取预约规则配置（使用医生所属门店的配置）
      const rules = await settingsApi.getBookingRules(doctorData.storeId).catch(() => ({
        advanceDays: 10,
        advanceBookingMinutes: 0,
        advanceBookingDirection: 'before',
        advanceBookingReference: 'end',
      }));
      setBookingRules(rules);
      const days = rules.advanceDays || 10;
      setAdvanceDays(days);

      // 使用配置的预约天数获取可用排班
      const scheduleData = await scheduleApi.getAvailable(id!, days);
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

  // 判断班次是否已过截止时间
  const isScheduleExpired = (schedule: AvailableSchedule): boolean => {
    const { advanceBookingMinutes = 0, advanceBookingDirection = 'before', advanceBookingReference = 'end' } = bookingRules;

    // 配置为0表示不限制
    if (!advanceBookingMinutes || advanceBookingMinutes <= 0) {
      return false;
    }

    // 只判断当天班次 - 使用本地日期格式 YYYY-MM-DD
    const today = new Date();
    const year = today.getFullYear();
    const month = String(today.getMonth() + 1).padStart(2, '0');
    const day = String(today.getDate()).padStart(2, '0');
    const todayStr = `${year}-${month}-${day}`;

    if (schedule.scheduleDate !== todayStr) {
      return false; // 非当天班次不限制
    }

    // 解析班次时间 - 支持 HH:mm 或 HH:mm:ss 格式
    const getMinutes = (timeStr?: string): number | null => {
      if (!timeStr) return null;
      const [hours, minutes] = timeStr.split(':').map(Number);
      if (isNaN(hours) || isNaN(minutes)) return null;
      return hours * 60 + minutes;
    };

    const startMinutes = getMinutes(schedule.startTime);
    const endMinutes = getMinutes(schedule.endTime);

    if (startMinutes === null || endMinutes === null) {
      return false; // 无时间信息的班次不限制
    }

    // 确定基准时间
    const baseMinutes = advanceBookingReference === 'start' ? startMinutes : endMinutes;

    // 计算截止时间
    const cutoffMinutes = advanceBookingDirection === 'before'
      ? baseMinutes - advanceBookingMinutes
      : baseMinutes + advanceBookingMinutes;

    // 获取当前时间（分钟数）
    const nowMinutes = today.getHours() * 60 + today.getMinutes();

    // 判断是否已过截止时间
    return nowMinutes >= cutoffMinutes;
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

  // 获取选中日期的星期几
  const selectedDateInfo = useMemo(() => {
    if (!selectedDate) return null;
    const date = new Date(selectedDate);
    return {
      date: selectedDate,
      weekday: WEEKDAY_NAMES[date.getDay()],
      formatted: selectedDate.substring(5).replace('-', '/'),
    };
  }, [selectedDate]);

  // 获取选中时段的班次列表（用于 Picker 展示）
  const selectedSlotSchedules = useMemo(() => {
    if (!selectedSlot) return [];
    return selectedSlot === 'AM' 
      ? timeSlotSummary.morning.schedules 
      : timeSlotSummary.afternoon.schedules;
  }, [selectedSlot, timeSlotSummary]);

  const handleDateSelect = (date: string) => {
    setSelectedDate(date);
    // 切换日期时重置时段选择和班次选择
    setSelectedSlot(null);
    setSelectedScheduleId(null);
  };

  // 点击时段卡片 - 弹出班次选择 Picker
  const handleTimeSlotClick = (slot: 'AM' | 'PM') => {
    const summary = slot === 'AM' ? timeSlotSummary.morning : timeSlotSummary.afternoon;

    // 检查是否有可预约的班次
    if (summary.available <= 0 || summary.schedules.length === 0) {
      Taro.showToast({ title: '该时段已约满', icon: 'none' });
      return;
    }

    // 检查是否所有班次都已过截止时间
    const availableSchedules = summary.schedules.filter(s => !isScheduleExpired(s));
    if (availableSchedules.length === 0) {
      Taro.showToast({ title: '该时段已过预约截止时间', icon: 'none' });
      return;
    }

    // 设置选中的时段
    setSelectedSlot(slot);
    setSelectedScheduleId(null);

    // 如果只有一个可用班次，直接选中并跳转
    if (availableSchedules.length === 1) {
      const schedule = availableSchedules[0];
      navigateToBooking(schedule);
    } else {
      // 多个班次，弹出班次选择 Picker
      setShowSlotPicker(true);
    }
  };

  // 关闭班次选择 Picker
  const handleCloseSlotPicker = () => {
    setShowSlotPicker(false);
  };

  // 选择具体班次
  const handleSelectSchedule = (scheduleId: string) => {
    setSelectedScheduleId(scheduleId);
  };

  // 跳转到预约确认页
  const navigateToBooking = (schedule: AvailableSchedule) => {
    // 构建 URL 参数，包含具体班次时间
    const params = new URLSearchParams({
      doctorId: id!,
      scheduleId: schedule.id,
      date: schedule.scheduleDate,
      timeSlot: schedule.timeSlot,
    });
    if (schedule.startTime) {
      params.set('startTime', formatTime(schedule.startTime));
    }
    if (schedule.endTime) {
      params.set('endTime', formatTime(schedule.endTime));
    }
    
    Taro.navigateTo({
      url: `/packageBooking/pages/booking/index?${params.toString()}`,
    });
  };

  // 班次选择后点击下一步
  const handleSlotPickerNext = () => {
    if (!selectedScheduleId) {
      Taro.showToast({ title: '请选择就诊班次', icon: 'none' });
      return;
    }
    
    const schedule = schedules.find(s => s.id === selectedScheduleId);
    if (!schedule) {
      Taro.showToast({ title: '班次信息错误', icon: 'none' });
      return;
    }
    
    setShowSlotPicker(false);
    navigateToBooking(schedule);
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
              <Image src={getImageUrl(doctor.avatar)} mode="aspectFill" />
            ) : (
              <DoctorIcon size={48} color="#C41E3A" />
            )}
          </View>
          <View className="info-content">
            <View className="name-row">
              <Text className="name">{doctor.name}</Text>
              {doctor.title && <Text className="title">{doctor.title}</Text>}
            </View>
            <Text className="dept">{doctor.departmentName}</Text>
          </View>
          {/* 收藏按钮 */}
          <View 
            className={`favorite-btn ${isFavorited ? 'active' : ''} ${favoriteLoading ? 'loading' : ''}`}
            onClick={handleToggleFavorite}
          >
            {isFavorited ? (
              <HeartIcon size={24} color="#EF4444" />
            ) : (
              <HeartOutlineIcon size={24} color="#94A3B8" />
            )}
          </View>
        </View>

        <View className="info-section">
          <Text className="label">擅长领域</Text>
          <Text className="value">{doctor.specialty || '暂无信息'}</Text>
        </View>

        <View className="info-section">
          <Text className="label">医生简介</Text>
          {doctor.introduction ? (
            <RichText className="value rich-text-value" nodes={doctor.introduction} />
          ) : (
            <Text className="value">暂无简介</Text>
          )}
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

            {/* 上午/下午时段选择 - 两列布局（单选） */}
            <View className="time-slots">
              <View 
                className={`time-slot-card ${timeSlotSummary.morning.available <= 0 ? 'full' : ''} ${selectedSlot === 'AM' ? 'selected' : ''}`}
                onClick={() => handleTimeSlotClick('AM')}
              >
                <Text className="slot-available">
                  {timeSlotSummary.morning.available > 0 ? `余${timeSlotSummary.morning.available}` : '约满'}
                </Text>
                <Text className="slot-period">上午</Text>
                {doctor.departmentName && (
                  <Text className="slot-dept">{doctor.departmentName}</Text>
                )}
              </View>
              
              <View 
                className={`time-slot-card ${timeSlotSummary.afternoon.available <= 0 ? 'full' : ''} ${selectedSlot === 'PM' ? 'selected' : ''}`}
                onClick={() => handleTimeSlotClick('PM')}
              >
                <Text className="slot-available">
                  {timeSlotSummary.afternoon.available > 0 ? `余${timeSlotSummary.afternoon.available}` : '约满'}
                </Text>
                <Text className="slot-period">下午</Text>
                {doctor.departmentName && (
                  <Text className="slot-dept">{doctor.departmentName}</Text>
                )}
              </View>
            </View>
          </>
        )}
      </View>

      {/* 班次选择 Picker */}
      {showSlotPicker && (
        <View className="slot-picker-mask" onClick={handleCloseSlotPicker}>
          <View className="slot-picker-sheet" onClick={(e) => e.stopPropagation()}>
            {/* 顶部指示条 */}
            <View className="slot-picker-indicator" />
            
            {/* 头部 */}
            <View className="slot-picker-header">
              <Text className="slot-picker-title">选择就诊班次</Text>
              <Text className="slot-picker-subtitle">
                {selectedDateInfo?.formatted} {selectedDateInfo?.weekday} · {selectedSlot === 'AM' ? '上午' : '下午'}
              </Text>
            </View>
            
            {/* 医生信息 */}
            <View className="slot-picker-doctor">
              <View className="slot-picker-doctor-avatar">
                {doctor?.avatar ? (
                  <Image src={getImageUrl(doctor.avatar)} mode="aspectFill" />
                ) : (
                  <DoctorIcon size={32} color="#C41E3A" />
                )}
              </View>
              <View className="slot-picker-doctor-info">
                <View className="slot-picker-doctor-name-row">
                  <Text className="slot-picker-doctor-name">{doctor?.name}</Text>
                  {doctor?.title && <Text className="slot-picker-doctor-title">{doctor.title}</Text>}
                </View>
                {doctor?.departmentName && (
                  <Text className="slot-picker-doctor-dept">{doctor.departmentName}</Text>
                )}
              </View>
            </View>
            
            {/* 班次列表 - 一行3个 */}
            <View className="slot-picker-list">
              {selectedSlotSchedules.map(schedule => {
                const isSelected = selectedScheduleId === schedule.id;
                const isFull = schedule.availableSlots <= 0;
                const isExpired = isScheduleExpired(schedule);
                const isDisabled = isFull || isExpired;

                return (
                  <View
                    key={schedule.id}
                    className={`slot-picker-item ${isSelected ? 'selected' : ''} ${isDisabled ? 'disabled' : ''}`}
                    onClick={() => !isDisabled && handleSelectSchedule(schedule.id)}
                  >
                    <Text className="slot-time">
                      {formatTime(schedule.startTime) || '--:--'}~{formatTime(schedule.endTime) || '--:--'}
                    </Text>
                    {isSelected && <Text className="slot-check">✓</Text>}
                    <Text className="slot-remain">
                      {isFull ? '约满' : isExpired ? '已截止' : `余${schedule.availableSlots}`}
                    </Text>
                  </View>
                );
              })}
            </View>
            
            {/* 底部按钮 */}
            <View className="slot-picker-footer">
              <Button 
                type="primary" 
                className="slot-picker-next-btn"
                disabled={!selectedScheduleId}
                onClick={handleSlotPickerNext}
              >
                下一步
              </Button>
              <Text className="slot-picker-cancel-btn" onClick={handleCloseSlotPicker}>
                取消
              </Text>
            </View>
          </View>
        </View>
      )}

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
