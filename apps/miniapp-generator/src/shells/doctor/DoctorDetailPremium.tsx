import { View, Text, Image, ScrollView, RichText } from '@tarojs/components';
import Taro, { useRouter, usePullDownRefresh } from '@tarojs/taro';
import { Button } from '@nutui/nutui-react-taro';
import { useState, useEffect, useMemo } from 'react';
import { doctorApi, scheduleApi, favoriteApi, settingsApi } from '@hospital/api';
import type { AvailableSchedule } from '@hospital/api';
import type { Doctor } from '@hospital/shared';
import { APPOINTMENT_TYPE_MAP } from '@hospital/shared';
import { DoctorIcon, HeartIcon, HeartOutlineIcon, CalendarIcon, ClockIcon } from '../../components/Icons';
import { getToken } from '../../utils/auth';
import { resolveDoctorIdFromParams } from '../../utils/scene';
import { useThemePrimaryColor, useApplyThemeNavigationBar } from '../../utils/theme';
import { getImageUrl, formatTime } from '../../utils/url';
import './DoctorDetailPremium.less';

const WEEKDAY_NAMES = ['周日', '周一', '周二', '周三', '周四', '周五', '周六'];

/**
 * 医生详情壳层 -- 高端版
 * 顶部大图/渐变背景区域 + 医生名片（职称、学术头衔、从业年限）+ 服务项目列表 + 患者评价区 + 排班选择 + 预约按钮
 */
export function DoctorDetailPremium() {
  const primaryColor = useThemePrimaryColor();
  useApplyThemeNavigationBar();
  const router = useRouter();
  // 支持扫码进入：显式 id 优先，其次解析 scene（海报小程序码契约见 utils/scene.ts）
  const id = resolveDoctorIdFromParams(router.params);

  const [loading, setLoading] = useState(true);
  const [doctor, setDoctor] = useState<Doctor | null>(null);
  const [schedules, setSchedules] = useState<AvailableSchedule[]>([]);
  const [selectedDate, setSelectedDate] = useState<string>('');
  const [currentTime, setCurrentTime] = useState(new Date());

  // 收藏相关状态
  const [isFavorited, setIsFavorited] = useState(false);
  const [favoriteId, setFavoriteId] = useState<string | null>(null);
  const [favoriteLoading, setFavoriteLoading] = useState(false);

  // 选中的排班
  const [selectedSchedule, setSelectedSchedule] = useState<AvailableSchedule | null>(null);
  const [showScheduleSheet, setShowScheduleSheet] = useState(false);

  useEffect(() => {
    if (id) {
      loadData();
    }
  }, [id]);

  // 智能倒计时
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
        const dates = [...new Set(scheduleData.map(s => s.scheduleDate))].sort();
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

  // 班次状态判断
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

  // 计算倒计时
  const getCountdown = (schedule: AvailableSchedule) => {
    if (!schedule.bookingCloseAt) return null;
    const closeTime = new Date(schedule.bookingCloseAt);
    const minutesLeft = Math.floor((closeTime.getTime() - currentTime.getTime()) / 60000);
    if (minutesLeft <= 0) return null;
    if (minutesLeft < 60) return { text: `${minutesLeft}分钟`, minutes: minutesLeft };
    const hours = Math.floor(minutesLeft / 60);
    const mins = minutesLeft % 60;
    return { text: `${hours}小时${mins}分钟`, minutes: minutesLeft };
  };

  // 日期列表
  const dateList = useMemo(() => {
    const dates = [...new Set(schedules.map(s => s.scheduleDate))].sort();
    return dates.map(date => ({
      date,
      weekday: WEEKDAY_NAMES[new Date(date).getDay()],
      formatted: date.substring(5).replace('-', '/'),
    }));
  }, [schedules]);

  // 选中日期的排班
  const selectedDateSchedules = useMemo(() => {
    return schedules.filter(s => s.scheduleDate === selectedDate);
  }, [schedules, selectedDate]);

  const handleDateSelect = (date: string) => {
    setSelectedDate(date);
    setSelectedSchedule(null);
  };

  const handleScheduleClick = (schedule: AvailableSchedule) => {
    const status = getScheduleStatus(schedule);
    if (status.disabled) {
      Taro.showToast({ title: status.message, icon: 'none' });
      return;
    }
    setSelectedSchedule(schedule);
    setShowScheduleSheet(true);
  };

  const handleBookingConfirm = () => {
    if (!selectedSchedule) return;
    setShowScheduleSheet(false);

    const params = new URLSearchParams();
    params.set('doctorId', id!);
    params.set('scheduleId', selectedSchedule.id);
    params.set('date', selectedSchedule.scheduleDate);
    params.set('timeSlot', selectedSchedule.timeSlot || '');
    if (selectedSchedule.startTime) params.set('startTime', formatTime(selectedSchedule.startTime));
    if (selectedSchedule.endTime) params.set('endTime', formatTime(selectedSchedule.endTime));
    Taro.navigateTo({ url: `/packageBooking/pages/booking/index?${params.toString()}` });
  };

  const handleCloseSheet = () => {
    setShowScheduleSheet(false);
  };

  if (loading) {
    return (
      <View className="doctor-detail-premium-page">
        <View className="loading-state">加载中...</View>
      </View>
    );
  }

  if (!doctor) {
    return (
      <View className="doctor-detail-premium-page">
        <View className="loading-state">医生信息不存在</View>
      </View>
    );
  }

  return (
    <View className="doctor-detail-premium-page">
      {/* 顶部大图/渐变背景区域 */}
      <View className="doctor-header">
        <View className="header-bg" />
        <View className="header-content">
          <View className="doctor-avatar-wrap">
            {doctor.avatar ? (
              <Image className="doctor-avatar" src={getImageUrl(doctor.avatar)} mode="aspectFill" />
            ) : (
              <View className="doctor-avatar-placeholder">
                <DoctorIcon size={56} color="#fff" />
              </View>
            )}
          </View>
          <Text className="doctor-name">{doctor.name}</Text>
          {doctor.title && <Text className="doctor-title">{doctor.title}</Text>}
          {doctor.departmentName && <Text className="doctor-dept">{doctor.departmentName}</Text>}
        </View>
        {/* 收藏按钮 */}
        <View className={`favorite-btn ${isFavorited ? 'active' : ''}`} onClick={handleToggleFavorite}>
          {isFavorited ? (
            <HeartIcon size={24} color="#EF4444" />
          ) : (
            <HeartOutlineIcon size={24} color="#fff" />
          )}
        </View>
      </View>

      <ScrollView className="content" scrollY enhanced>
        {/* 医生名片 */}
        <View className="doctor-card">
          {/* 基本信息 */}
          {doctor.yearsOfExperience && (
            <View className="info-row">
              <Text className="info-label">从业年限</Text>
              <Text className="info-value">{doctor.yearsOfExperience}年</Text>
            </View>
          )}
          {doctor.rating && (
            <View className="info-row">
              <Text className="info-label">好评率</Text>
              <Text className="info-value">{doctor.rating}%</Text>
            </View>
          )}
          {doctor.academicTitle && (
            <View className="info-row">
              <Text className="info-label">学术头衔</Text>
              <Text className="info-value">{doctor.academicTitle}</Text>
            </View>
          )}

          {/* 擅长领域 */}
          <View className="section-title">擅长领域</View>
          {doctor.specialty ? (
            <Text className="specialty-text">{doctor.specialty}</Text>
          ) : (
            <Text className="empty-text">暂无信息</Text>
          )}

          {/* 医生简介 */}
          <View className="section-title">医生简介</View>
          {doctor.introduction ? (
            <RichText className="intro-text" nodes={doctor.introduction} />
          ) : (
            <Text className="empty-text">暂无简介</Text>
          )}
        </View>

        {/* 服务项目 */}
        {doctor.services && doctor.services.length > 0 && (
          <View className="service-section">
            <View className="section-header">
              <Text className="section-title">服务项目</Text>
            </View>
            <View className="service-list">
              {doctor.services.map((service, index) => (
                <View key={index} className="service-item">
                  <Text className="service-name">{service.name}</Text>
                  <Text className="service-price">¥{service.price}</Text>
                </View>
              ))}
            </View>
          </View>
        )}

        {/* 患者评价区（预留） */}
        <View className="review-section">
          <View className="section-header">
            <Text className="section-title">患者评价</Text>
          </View>
          <View className="empty-reviews">
            <Text>暂无评价，期待您的反馈</Text>
          </View>
        </View>

        {/* 排班选择 */}
        <View className="schedule-section">
          <View className="section-header">
            <Text className="section-title">选择就诊时间</Text>
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

              <View className="schedule-list">
                {selectedDateSchedules.map(schedule => {
                  const status = getScheduleStatus(schedule);
                  const countdown = getCountdown(schedule);
                  return (
                    <View
                      key={schedule.id}
                      className={`schedule-item ${status.disabled ? 'disabled' : ''}`}
                      onClick={() => handleScheduleClick(schedule)}
                    >
                      <View className="schedule-time">
                        <View className="time-icon">
                          <ClockIcon size={16} color={primaryColor} />
                        </View>
                        <Text className="time-text">
                          {schedule.timeSlot === 'morning' ? '上午' : '下午'}
                          {' '}
                          {formatTime(schedule.startTime)}~{formatTime(schedule.endTime)}
                        </Text>
                      </View>
                      <View className="schedule-info">
                        <Text className="schedule-type">
                          {APPOINTMENT_TYPE_MAP[schedule.appointmentType || 'normal'] || '普通'}
                        </Text>
                        <Text className={`schedule-status ${status.className}`}>{status.message}</Text>
                      </View>
                      {countdown && countdown.minutes <= 120 && !status.disabled && (
                        <Text className="schedule-countdown">{countdown.text}后截止</Text>
                      )}
                    </View>
                  );
                })}
              </View>
            </>
          )}
        </View>
      </ScrollView>

      {/* 预约确认弹窗 */}
      {showScheduleSheet && selectedSchedule && (
        <View className="sheet-mask" onClick={handleCloseSheet}>
          <View className="sheet-content" onClick={e => e.stopPropagation()}>
            <View className="sheet-header">
              <Text className="sheet-title">确认预约信息</Text>
            </View>
            <View className="sheet-body">
              <View className="sheet-row">
                <Text className="sheet-label">医生</Text>
                <Text className="sheet-value">{doctor.name}</Text>
              </View>
              <View className="sheet-row">
                <Text className="sheet-label">日期</Text>
                <Text className="sheet-value">
                  {selectedDateSchedules.find(s => s.id === selectedSchedule.id)?.scheduleDate?.substring(5).replace('-', '/')}
                </Text>
              </View>
              <View className="sheet-row">
                <Text className="sheet-label">时段</Text>
                <Text className="sheet-value">
                  {selectedSchedule.timeSlot === 'morning' ? '上午' : '下午'}
                  {' '}
                  {formatTime(selectedSchedule.startTime)}~{formatTime(selectedSchedule.endTime)}
                </Text>
              </View>
            </View>
            <View className="sheet-footer">
              <Button type="primary" className="confirm-btn" onClick={handleBookingConfirm}>
                确认预约
              </Button>
              <Text className="cancel-btn" onClick={handleCloseSheet}>
                取消
              </Text>
            </View>
          </View>
        </View>
      )}
    </View>
  );
}
