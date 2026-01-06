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

  // 新增：当前时间（用于倒计时）
  const [currentTime, setCurrentTime] = useState(new Date());

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

  // 新增：智能倒计时（每分钟更新，当剩余<1分钟时切换为每秒刷新）
  useEffect(() => {
    // 计算是否需要秒级刷新
    const needSecondPrecision = schedules.some(s => {
      if (!s.bookingCloseAt) return false;
      const closeTime = new Date(s.bookingCloseAt);
      const now = new Date();
      const minutesUntil = (closeTime.getTime() - now.getTime()) / 60000;
      return minutesUntil > 0 && minutesUntil < 1;
    });

    const interval = needSecondPrecision ? 1000 : 60000;

    const timer = setInterval(() => {
      setCurrentTime(new Date());
    }, interval);

    return () => clearInterval(timer);
  }, [schedules]); // 移除 currentTime 依赖，避免无限循环

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

  // 判断班次是否已过截止时间（使用后端返回的状态）
  const getScheduleStatus = (schedule: AvailableSchedule): {
    disabled: boolean;
    message: string;
    className?: string;
    countdown?: { text: string; minutes: number };
  } => {
    // 优先使用后端返回的 bookingStatus
    if (schedule.bookingStatus) {
      switch (schedule.bookingStatus) {
        case 'not_open':
          const openTime = schedule.bookingOpenAt ? new Date(schedule.bookingOpenAt) : null;
          const minutesUntilOpen = openTime ? Math.floor((openTime.getTime() - currentTime.getTime()) / 60000) : 0;
          if (minutesUntilOpen > 0) {
            const hours = Math.floor(minutesUntilOpen / 60);
            const mins = minutesUntilOpen % 60;
            const text = hours > 0 ? `${hours}小时${mins}分钟` : `${mins}分钟`;
            return {
              disabled: true,
              message: `未开放`,
              className: 'not-open',
              countdown: { text, minutes: minutesUntilOpen }
            };
          }
          return { disabled: true, message: '未开放', className: 'not-open' };
        case 'closed':
          return { disabled: true, message: '已截止', className: 'closed' };
        case 'full':
          return { disabled: true, message: '约满', className: 'full' };
        case 'closing_soon':
          return { disabled: false, message: `余${schedule.availableSlots}`, className: 'closing-soon' };
        default:
          return { disabled: false, message: `余${schedule.availableSlots}` };
      }
    }

    // 兼容旧逻辑（如果没有后端状态）
    if (schedule.availableSlots <= 0) {
      return { disabled: true, message: '约满', className: 'full' };
    }

    return { disabled: false, message: `余${schedule.availableSlots}` };
  };

  // 计算倒计时（用于班次 Picker）
  const getCountdown = (schedule: AvailableSchedule): { text: string; minutes: number } | null => {
    if (!schedule.bookingCloseAt) return null;

    const closeTime = new Date(schedule.bookingCloseAt);
    const minutesLeft = Math.floor((closeTime.getTime() - currentTime.getTime()) / 60000);

    if (minutesLeft <= 0) return null;
    if (minutesLeft < 60) {
      return { text: `${minutesLeft}分钟`, minutes: minutesLeft };
    }
    const hours = Math.floor(minutesLeft / 60);
    const mins = minutesLeft % 60;
    return { text: `${hours}小时${mins}分钟`, minutes: minutesLeft };
  };

  // 保留旧函数名作为兼容
  const isScheduleExpired = (schedule: AvailableSchedule): boolean => {
    return getScheduleStatus(schedule).disabled;
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

  // 计算时段的状态和紧急程度
  const getSlotSummary = (slotSchedules: AvailableSchedule[]) => {
    if (slotSchedules.length === 0) {
      return { status: 'none', urgency: 'normal', message: '无班次', disabled: true };
    }

    // 检查是否有可预约的班次
    const availableSchedules = slotSchedules.filter(s => !getScheduleStatus(s).disabled);
    if (availableSchedules.length === 0) {
      return { status: 'full', urgency: 'critical', message: '约满', disabled: true };
    }

    // 计算总容量和平均紧急程度
    let totalSlots = 0;
    let totalAvailable = 0;
    let maxUrgency = 0; // 0=normal, 1=medium, 2=high, 3=critical

    for (const s of slotSchedules) {
      if (s.totalSlots) {
        totalSlots += s.totalSlots;
        totalAvailable += s.availableSlots;
      }
      if (s.urgencyLevel === 'critical') maxUrgency = Math.max(maxUrgency, 3);
      else if (s.urgencyLevel === 'high') maxUrgency = Math.max(maxUrgency, 2);
      else if (s.urgencyLevel === 'medium') maxUrgency = Math.max(maxUrgency, 1);
    }

    // 计算容量百分比
    const capacityPercent = totalSlots > 0 ? (totalAvailable / totalSlots) * 100 : 0;

    // 判断紧急程度
    let urgency = 'normal';
    if (capacityPercent < 20 || maxUrgency >= 3) urgency = 'critical';
    else if (capacityPercent < 50 || maxUrgency >= 2) urgency = 'high';
    else if (capacityPercent < 70 || maxUrgency >= 1) urgency = 'medium';

    return {
      status: 'available',
      urgency,
      message: `余${totalAvailable}`,
      disabled: false,
    };
  };

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

            {/* 上午/下午时段选择 - 两列布局（单选，增强版） */}
            <View className="time-slots">
              {['AM', 'PM'].map(slot => {
                const summary = slot === 'AM' ? timeSlotSummary.morning : timeSlotSummary.afternoon;
                const slotStatus = getSlotSummary(summary.schedules);
                const urgencyClass = slotStatus.urgency !== 'normal' ? `urgency-${slotStatus.urgency}` : '';

                return (
                  <View
                    key={slot}
                    className={`time-slot-card ${slotStatus.disabled ? 'full' : ''} ${selectedSlot === slot ? 'selected' : ''} ${slotStatus.status === 'closing-soon' ? 'closing-soon' : ''} ${urgencyClass}`}
                    data-urgency={slotStatus.urgency}
                    onClick={() => !slotStatus.disabled && handleTimeSlotClick(slot as 'AM' | 'PM')}
                  >
                    {/* 紧急程度徽章 */}
                    {slotStatus.urgency === 'high' && !slotStatus.disabled && (
                      <View className="slot-urgency-badge high">紧张</View>
                    )}
                    {slotStatus.urgency === 'critical' && !slotStatus.disabled && (
                      <View className="slot-urgency-badge critical">紧急</View>
                    )}

                    <Text className="slot-available">
                      {slotStatus.message}
                    </Text>
                    <Text className="slot-period">{slot === 'AM' ? '上午' : '下午'}</Text>
                    {doctor.departmentName && (
                      <Text className="slot-dept">{doctor.departmentName}</Text>
                    )}
                  </View>
                );
              })}
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
            
            {/* 班次列表 - 一行3个（增强版） */}
            <View className="slot-picker-list">
              {selectedSlotSchedules.map(schedule => {
                const isSelected = selectedScheduleId === schedule.id;
                const status = getScheduleStatus(schedule);
                const countdown = getCountdown(schedule);
                const urgency = schedule.urgencyLevel || 'normal';
                const isDisabled = status.disabled;

                // 计算容量百分比
                const capacityPercent = schedule.totalSlots && schedule.totalSlots > 0
                  ? ((schedule.totalSlots - schedule.availableSlots) / schedule.totalSlots) * 100
                  : 0;

                return (
                  <View
                    key={schedule.id}
                    className={`slot-picker-item ${isSelected ? 'selected' : ''} ${isDisabled ? 'disabled' : ''} ${status.className || ''} urgency-${urgency}`}
                    data-urgency={urgency}
                    onClick={() => !isDisabled && handleSelectSchedule(schedule.id)}
                  >
                    {/* 状态图标 */}
                    {(urgency === 'high' || urgency === 'critical') && !isDisabled && (
                      <View className={`slot-status-icon ${urgency === 'critical' ? 'alert' : 'warning'}`}>
                        {urgency === 'critical' ? '!' : '⚠'}
                      </View>
                    )}

                    {isSelected && <Text className="slot-check">✓</Text>}

                    <Text className="slot-time">
                      {formatTime(schedule.startTime) || '--:--'}~{formatTime(schedule.endTime) || '--:--'}
                    </Text>

                    <Text className="slot-remain">
                      {status.message}
                    </Text>

                    {/* 容量进度条 */}
                    {schedule.totalSlots && !isDisabled && schedule.totalSlots > 0 && (
                      <View className="slot-capacity-bar">
                        <View
                          className={`slot-capacity-fill ${urgency}`}
                          style={{ width: `${capacityPercent}%` }}
                        />
                      </View>
                    )}

                    {/* 倒计时 */}
                    {countdown && countdown.minutes <= 120 && !isDisabled && (
                      <Text className="slot-countdown">⏱ {countdown.text}</Text>
                    )}
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
