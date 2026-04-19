import { View, Text, Image, ScrollView, RichText } from '@tarojs/components';
import Taro, { useRouter, usePullDownRefresh } from '@tarojs/taro';
import { Button } from '@nutui/nutui-react-taro';
import { useState, useEffect, useMemo } from 'react';
import { doctorApi, scheduleApi, favoriteApi, settingsApi } from '@hospital/api';
import type { AvailableSchedule } from '@hospital/api';
import type { Doctor } from '@hospital/shared';
import { APPOINTMENT_TYPE_MAP } from '@hospital/shared';
import { DoctorIcon, HeartIcon, HeartOutlineIcon, ServiceIcon, TipIcon } from '../../components/Icons';
import { getToken } from '../../utils/auth';
import { useThemePrimaryColor, useApplyThemeNavigationBar } from '../../utils/theme';
import { getImageUrl, formatTime } from '../../utils/url';
import './DoctorDetailWomens.less';

const WEEKDAY_NAMES = ['周日', '周一', '周二', '周三', '周四', '周五', '周六'];

// 患者评价示例数据（女性健康模板）
const patientReviews = [
  { content: '医生态度很好，很温柔', date: '2026-03-15' },
  { content: '检查很仔细，解释很清楚', date: '2026-03-10' },
  { content: '非常有耐心，值得推荐', date: '2026-03-05' },
];

const serviceItems = [
  { name: '妇科检查', desc: '常规妇科检查' },
  { name: '产前检查', desc: '孕期健康管理' },
  { name: '产后康复', desc: '产后恢复指导' },
  { name: '健康咨询', desc: '女性健康咨询' },
];

const tips = [
  { title: '就诊前', content: '请携带身份证件和相关检查报告' },
  { title: '就诊时', content: '如实告知症状和病史，配合医生检查' },
  { title: '就诊后', content: '遵医嘱服药，注意休息，按时复诊' },
];

export function DoctorDetailWomens() {
  const primaryColor = useThemePrimaryColor();
  useApplyThemeNavigationBar();
  const router = useRouter();
  const { id } = router.params;

  const [loading, setLoading] = useState(true);
  const [doctor, setDoctor] = useState<Doctor | null>(null);
  const [schedules, setSchedules] = useState<AvailableSchedule[]>([]);
  const [selectedDate, setSelectedDate] = useState<string>('');
  const [selectedSlot, setSelectedSlot] = useState<'morning' | 'afternoon' | null>(null);
  const [showSlotPicker, setShowSlotPicker] = useState(false);
  const [selectedScheduleId, setSelectedScheduleId] = useState<string | null>(null);
  const [currentTime, setCurrentTime] = useState(new Date());
  const [isFavorited, setIsFavorited] = useState(false);
  const [favoriteId, setFavoriteId] = useState<string | null>(null);
  const [favoriteLoading, setFavoriteLoading] = useState(false);

  useEffect(() => {
    if (id) {
      loadData();
    }
  }, [id]);

  useEffect(() => {
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
  }, [schedules]);

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
      const doctorData = await doctorApi.getDetail(id!);
      setDoctor(doctorData);

      const rules = await settingsApi.getBookingRules(doctorData.storeId).catch(() => ({
        advanceDays: 10,
        advanceBookingMinutes: 0,
        advanceBookingDirection: 'before',
        advanceBookingReference: 'end',
      }));
      const days = rules.advanceDays || 10;

      const scheduleData = await scheduleApi.getAvailable(id!, days);
      setSchedules(scheduleData);

      if (scheduleData.length > 0) {
        const dates = [...new Set(scheduleData.map(s => s.scheduleDate))];
        if (dates.length > 0) {
          setSelectedDate(dates[0]);
        }
      }

      if (getToken()) {
        checkFavoriteStatus();
      }
    } catch (error) {
      console.error('[医生详情] 加载失败', error);
      Taro.showToast({ title: '加载失败', icon: 'none' });
    } finally {
      setLoading(false);
    }
  };

  const checkFavoriteStatus = async () => {
    if (!id) return;
    try {
      const result = await favoriteApi.check('doctor', id);
      setIsFavorited(result.isFavorited);
      setFavoriteId(result.favoriteId || null);
    } catch (error) {
      console.error('[医生详情] 检查收藏状态失败', error);
    }
  };

  const handleToggleFavorite = async () => {
    if (!getToken()) {
      Taro.showToast({ title: '请先登录', icon: 'none' });
      return;
    }
    if (!id || favoriteLoading) return;

    setFavoriteLoading(true);
    try {
      if (isFavorited && favoriteId) {
        await favoriteApi.remove(favoriteId);
        setIsFavorited(false);
        setFavoriteId(null);
        Taro.showToast({ title: '已取消收藏', icon: 'none' });
      } else {
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

  const getScheduleStatus = (schedule: AvailableSchedule) => {
    if (schedule.bookingStatus) {
      switch (schedule.bookingStatus) {
        case 'not_open':
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
    if (schedule.availableSlots <= 0) {
      return { disabled: true, message: '约满', className: 'full' };
    }
    return { disabled: false, message: `余${schedule.availableSlots}` };
  };

  const getCountdown = (schedule: AvailableSchedule) => {
    if (!schedule.bookingCloseAt) return null;
    const closeTime = new Date(s.bookingCloseAt);
    const minutesLeft = Math.floor((closeTime.getTime() - currentTime.getTime()) / 60000);
    if (minutesLeft <= 0) return null;
    if (minutesLeft < 60) return { text: `${minutesLeft}分钟`, minutes: minutesLeft };
    const hours = Math.floor(minutesLeft / 60);
    const mins = minutesLeft % 60;
    return { text: `${hours}小时${mins}分钟`, minutes: minutesLeft };
  };

  const dateList = useMemo(() => {
    const dates = [...new Set(schedules.map(s => s.scheduleDate))].sort();
    return dates.map(date => ({
      date,
      weekday: WEEKDAY_NAMES[new Date(date).getDay()],
      formatted: date.substring(5).replace('-', '/'),
    }));
  }, [schedules]);

  const selectedDateSchedules = useMemo(() => {
    return schedules.filter(s => s.scheduleDate === selectedDate);
  }, [schedules, selectedDate]);

  const timeSlotSummary = useMemo(() => {
    const morning = selectedDateSchedules.filter(s => s.timeSlot === 'morning');
    const afternoon = selectedDateSchedules.filter(s => s.timeSlot === 'afternoon');
    return {
      morning: { schedules: morning, available: morning.reduce((sum, s) => sum + s.availableSlots, 0) },
      afternoon: { schedules: afternoon, available: afternoon.reduce((sum, s) => sum + s.availableSlots, 0) },
    };
  }, [selectedDateSchedules]);

  const selectedDateInfo = useMemo(() => {
    if (!selectedDate) return null;
    const date = new Date(selectedDate);
    return {
      date: selectedDate,
      weekday: WEEKDAY_NAMES[date.getDay()],
      formatted: selectedDate.substring(5).replace('-', '/'),
    };
  }, [selectedDate]);

  const selectedSlotSchedules = useMemo(() => {
    if (!selectedSlot) return [];
    return selectedSlot === 'morning'
      ? timeSlotSummary.morning.schedules
      : timeSlotSummary.afternoon.schedules;
  }, [selectedSlot, timeSlotSummary]);

  const getSlotSummary = (slotSchedules: AvailableSchedule[]) => {
    if (slotSchedules.length === 0) {
      return { status: 'none', disabled: true, message: '无班次' };
    }
    const availableSchedules = slotSchedules.filter(s => !getScheduleStatus(s).disabled);
    if (availableSchedules.length === 0) {
      return { status: 'full', disabled: true, message: '约满' };
    }
    const totalAvailable = availableSchedules.reduce((sum, s) => sum + s.availableSlots, 0);
    return { status: 'available', disabled: false, message: `余${totalAvailable}` };
  };

  const handleDateSelect = (date: string) => {
    setSelectedDate(date);
    setSelectedSlot(null);
    setSelectedScheduleId(null);
  };

  const handleTimeSlotClick = (slot: 'morning' | 'afternoon') => {
    const summary = slot === 'morning' ? timeSlotSummary.morning : timeSlotSummary.afternoon;
    if (summary.available <= 0 || summary.schedules.length === 0) {
      Taro.showToast({ title: '该时段已约满', icon: 'none' });
      return;
    }
    const availableSchedules = summary.schedules.filter(s => !getScheduleStatus(s).disabled);
    if (availableSchedules.length === 0) {
      Taro.showToast({ title: '该时段已过预约截止时间', icon: 'none' });
      return;
    }
    setSelectedSlot(slot);
    setSelectedScheduleId(null);

    if (availableSchedules.length === 1) {
      navigateToBooking(availableSchedules[0]);
    } else {
      setShowSlotPicker(true);
    }
  };

  const navigateToBooking = (schedule: AvailableSchedule) => {
    const params = new URLSearchParams();
    params.set('doctorId', id!);
    params.set('scheduleId', schedule.id);
    params.set('date', schedule.scheduleDate);
    params.set('timeSlot', schedule.timeSlot || '');
    if (schedule.startTime) params.set('startTime', formatTime(schedule.startTime));
    if (schedule.endTime) params.set('endTime', formatTime(schedule.endTime));
    Taro.navigateTo({ url: `/packageBooking/pages/booking/index?${params.toString()}` });
  };

  const handleSelectSchedule = (scheduleId: string) => {
    setSelectedScheduleId(scheduleId);
  };

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

  const handleCloseSlotPicker = () => {
    setShowSlotPicker(false);
  };

  if (loading) {
    return (
      <View className="doctor-detail-page">
        <View className="loading-state">加载中...</View>
      </View>
    );
  }

  if (!doctor) {
    return (
      <View className="doctor-detail-page">
        <View className="loading-state">医生信息不存在</View>
      </View>
    );
  }

  return (
    <View className="doctor-detail-page">
      <View className="doctor-info">
        <View className="info-header">
          <View className="avatar">
            {doctor.avatar ? (
              <Image src={getImageUrl(doctor.avatar)} mode="aspectFill" />
            ) : (
              <DoctorIcon size={56} color={primaryColor} />
            )}
          </View>
          <View className="info-content">
            <View className="name-row">
              <Text className="name">{doctor.name}</Text>
              {doctor.title && <Text className="title">{doctor.title}</Text>}
            </View>
            <Text className="dept">{doctor.departmentName}</Text>
          </View>
          <View
            className={`favorite-btn ${isFavorited ? 'active' : ''}`}
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
            <RichText className="value" nodes={doctor.introduction} />
          ) : (
            <Text className="value">暂无简介</Text>
          )}
        </View>
      </View>

      {/* 患者评价模块 */}
      <View className="reviews-section">
        <View className="section-header">
          <Text className="section-title">患者评价</Text>
        </View>
        <View className="reviews-list">
          {patientReviews.slice(0, 3).map((review, index) => (
            <View key={index} className="review-item">
              <View className="review-content">
                <Text className="review-text">{review.content}</Text>
                <Text className="review-date">{review.date}</Text>
              </View>
            </View>
          ))}
        </View>
      </View>

      <View className="service-section">
        <View className="section-header">
          <ServiceIcon size={18} color={primaryColor} />
          <Text className="section-title">服务项目</Text>
        </View>
        <View className="service-list">
          {serviceItems.map((item, index) => (
            <View key={index} className="service-item">
              <Text className="service-name">{item.name}</Text>
              <Text className="service-desc">{item.desc}</Text>
            </View>
          ))}
        </View>
      </View>

      <View className="tips-section">
        <View className="section-header">
          <TipIcon size={18} color={primaryColor} />
          <Text className="section-title">温馨提示</Text>
        </View>
        <View className="tips-list">
          {tips.map((tip, index) => (
            <View key={index} className="tip-item">
              <View className="tip-badge">{tip.title}</View>
              <Text className="tip-content">{tip.content}</Text>
            </View>
          ))}
        </View>
      </View>

      <View className="schedule-section">
        <View className="section-header">
          <Text className="section-title">选择就诊时间</Text>
          {dateList.length > 3 && (
            <Text className="scroll-hint">左右滑动查看更多</Text>
          )}
        </View>

        {dateList.length === 0 ? (
          <View className="no-schedule">
            <Text>暂无可预约时段</Text>
          </View>
        ) : (
          <>
            <ScrollView className="date-scroll" scrollX enhanced showScrollbar={false}>
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

            <View className="time-slots">
              {(['morning', 'afternoon'] as const).map(slot => {
                const summary = slot === 'morning' ? timeSlotSummary.morning : timeSlotSummary.afternoon;
                const slotStatus = getSlotSummary(summary.schedules);

                return (
                  <View
                    key={slot}
                    className={`time-slot-card ${slotStatus.disabled ? 'full' : ''} ${selectedSlot === slot ? 'selected' : ''}`}
                    onClick={() => !slotStatus.disabled && handleTimeSlotClick(slot)}
                  >
                    <Text className="slot-available">{slotStatus.message}</Text>
                    <Text className="slot-period">{slot === 'morning' ? '上午' : '下午'}</Text>
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

      {showSlotPicker && (
        <View className="slot-picker-mask" onClick={handleCloseSlotPicker}>
          <View className="slot-picker-sheet" onClick={e => e.stopPropagation()}>
            <View className="slot-picker-indicator" />
            <View className="slot-picker-header">
              <Text className="slot-picker-title">选择就诊班次</Text>
              <Text className="slot-picker-subtitle">
                {selectedDateInfo?.formatted} {selectedDateInfo?.weekday} -- {selectedSlot === 'morning' ? '上午' : '下午'}
              </Text>
            </View>

            <View className="slot-picker-doctor">
              <View className="slot-picker-doctor-avatar">
                {doctor?.avatar ? (
                  <Image src={getImageUrl(doctor.avatar)} mode="aspectFill" />
                ) : (
                  <DoctorIcon size={32} color={primaryColor} />
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

            <View className="slot-picker-list">
              {selectedSlotSchedules.map(schedule => {
                const isSelected = selectedScheduleId === schedule.id;
                const status = getScheduleStatus(schedule);
                const countdown = getCountdown(schedule);
                const isDisabled = status.disabled;

                return (
                  <View
                    key={schedule.id}
                    className={`slot-picker-item ${isSelected ? 'selected' : ''} ${isDisabled ? 'disabled' : ''}`}
                    onClick={() => !isDisabled && handleSelectSchedule(schedule.id)}
                  >
                    <Text className="slot-time">
                      {formatTime(schedule.startTime) || '--:--'}~{formatTime(schedule.endTime) || '--:--'}
                    </Text>
                    <Text className="slot-remain">
                      {APPOINTMENT_TYPE_MAP[schedule.appointmentType || 'normal'] || '普通'} {status.message}
                    </Text>
                    {countdown && countdown.minutes <= 120 && !isDisabled && (
                      <Text className="slot-countdown">{countdown.text}</Text>
                    )}
                  </View>
                );
              })}
            </View>

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
    </View>
  );
}
