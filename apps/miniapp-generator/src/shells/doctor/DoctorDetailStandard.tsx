import { View, Text, Image, ScrollView, RichText, Button as TaroButton, Textarea } from '@tarojs/components';
import Taro, { useRouter, usePullDownRefresh } from '@tarojs/taro';
import { Button, Rate } from '@nutui/nutui-react-taro';
import { useState, useEffect, useMemo } from 'react';
import { doctorApi, scheduleApi, favoriteApi, settingsApi, doctorReviewApi } from '@hospital/api';
import type { AvailableSchedule, DoctorReviewItem } from '@hospital/api';
import type { Doctor } from '@hospital/shared';
import { APPOINTMENT_TYPE_MAP } from '@hospital/shared';
import { DoctorIcon, HeartIcon, HeartOutlineIcon, StarIcon } from '../../components/Icons';
import { getToken } from '../../utils/auth';
import { useThemePrimaryColor, useApplyThemeNavigationBar } from '../../utils/theme';
import { getImageUrl, formatTime } from '../../utils/url';
import './DoctorDetailStandard.less';

const WEEKDAY_NAMES = ['周日', '周一', '周二', '周三', '周四', '周五', '周六'];

// 患者姓名脱敏：保留首字符（两个字以上保留尾字符），中间以 * 代替
const maskPatientName = (name?: string | null): string => {
  const trimmed = (name || '').trim();
  if (!trimmed) return '匿名用户';
  if (trimmed.length === 1) return trimmed;
  if (trimmed.length === 2) return `${trimmed[0]}*`;
  return `${trimmed[0]}*${trimmed.slice(-1)}`;
};

// 评价日期展示：createdAt 取 YYYY-MM-DD
const formatReviewDate = (value?: string | null): string => {
  if (!value) return '';
  return value.substring(0, 10);
};

/**
 * 医生详情壳层 -- 标准版
 * 核心区域：医生信息头部 + 排班选择器（日期 + 时段 + 班次）
 */
export function DoctorDetailStandard() {
  const primaryColor = useThemePrimaryColor();
  useApplyThemeNavigationBar();
  const router = useRouter();
  const { id } = router.params;

  const [loading, setLoading] = useState(true);
  const [doctor, setDoctor] = useState<Doctor | null>(null);
  const [schedules, setSchedules] = useState<AvailableSchedule[]>([]);
  const [selectedDate, setSelectedDate] = useState<string>('');

  // 时段选择状态
  const [selectedSlot, setSelectedSlot] = useState<'morning' | 'afternoon' | null>(null);
  // 班次选择 Picker 状态
  const [showSlotPicker, setShowSlotPicker] = useState(false);
  // 选中的具体班次
  const [selectedScheduleId, setSelectedScheduleId] = useState<string | null>(null);
  // 当前时间（用于倒计时）
  const [currentTime, setCurrentTime] = useState(new Date());

  // 收藏相关状态
  const [isFavorited, setIsFavorited] = useState(false);
  const [favoriteId, setFavoriteId] = useState<string | null>(null);
  const [favoriteLoading, setFavoriteLoading] = useState(false);
  const [showLoginPopup, setShowLoginPopup] = useState(false);

  // 患者评价状态
  const [reviews, setReviews] = useState<DoctorReviewItem[]>([]);
  const [reviewsTotal, setReviewsTotal] = useState(0);
  // 写评价弹层状态
  const [showReviewSheet, setShowReviewSheet] = useState(false);
  const [reviewRating, setReviewRating] = useState(5);
  const [reviewContent, setReviewContent] = useState('');
  const [reviewSubmitting, setReviewSubmitting] = useState(false);

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
        const dates = [...new Set(scheduleData.map(s => s.scheduleDate))];
        if (dates.length > 0) {
          setSelectedDate(dates[0]);
        }
      }

      if (getToken()) {
        checkFavoriteStatus();
      }

      // 评价加载失败时静默降级为空态，不阻塞页面
      loadReviews();
    } catch (error) {
      console.error('[医生详情] 加载失败', error);
      Taro.showToast({ title: '加载失败', icon: 'none' });
    } finally {
      setLoading(false);
    }
  };

  // 患者评价（公开接口；接口失败或为空时保持空态）
  const loadReviews = async () => {
    if (!id) return;
    try {
      const result = await doctorReviewApi.getList({ doctorId: id, page: 1, pageSize: 10 });
      const items = Array.isArray(result?.items) ? result.items : [];
      setReviews(items);
      setReviewsTotal(typeof result?.total === 'number' ? result.total : items.length);
    } catch (error) {
      console.error('[医生详情] 加载患者评价失败', error);
      setReviews([]);
      setReviewsTotal(0);
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

  // 医生海报：本期占位
  const handleDoctorPoster = () => {
    Taro.showToast({ title: '建设中', icon: 'none' });
  };

  const handleOpenReviewSheet = () => {
    if (!getToken()) {
      Taro.showToast({ title: '请先登录', icon: 'none' });
      return;
    }
    setReviewRating(5);
    setReviewContent('');
    setShowReviewSheet(true);
  };

  const handleCloseReviewSheet = () => {
    setShowReviewSheet(false);
  };

  const handleSubmitReview = async () => {
    if (!id || reviewSubmitting) return;
    if (!reviewContent.trim()) {
      Taro.showToast({ title: '请输入评价内容', icon: 'none' });
      return;
    }
    setReviewSubmitting(true);
    try {
      await doctorReviewApi.create({ doctorId: id, rating: reviewRating, content: reviewContent.trim() });
      Taro.showToast({ title: '评价成功', icon: 'success' });
      setShowReviewSheet(false);
      loadReviews();
    } catch (error: any) {
      Taro.showToast({ title: error.message || '提交失败', icon: 'none' });
    } finally {
      setReviewSubmitting(false);
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

  // 时段汇总
  const timeSlotSummary = useMemo(() => {
    const morning = selectedDateSchedules.filter(s => s.timeSlot === 'morning');
    const afternoon = selectedDateSchedules.filter(s => s.timeSlot === 'afternoon');
    return {
      morning: { schedules: morning, available: morning.reduce((sum, s) => sum + s.availableSlots, 0) },
      afternoon: { schedules: afternoon, available: afternoon.reduce((sum, s) => sum + s.availableSlots, 0) },
    };
  }, [selectedDateSchedules]);

  // 选中日期信息
  const selectedDateInfo = useMemo(() => {
    if (!selectedDate) return null;
    const date = new Date(selectedDate);
    return {
      date: selectedDate,
      weekday: WEEKDAY_NAMES[date.getDay()],
      formatted: selectedDate.substring(5).replace('-', '/'),
    };
  }, [selectedDate]);

  // 选中时段的班次列表
  const selectedSlotSchedules = useMemo(() => {
    if (!selectedSlot) return [];
    return selectedSlot === 'morning'
      ? timeSlotSummary.morning.schedules
      : timeSlotSummary.afternoon.schedules;
  }, [selectedSlot, timeSlotSummary]);

  // 时段状态
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
      {/* 医生信息 */}
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
          {/* 右侧操作：收藏 + 医生海报 */}
          <View className="header-actions">
            <View
              className={`favorite-btn ${isFavorited ? 'active' : ''}`}
              onClick={handleToggleFavorite}
              aria-label={isFavorited ? '取消收藏' : '收藏医生'}
              role="button"
            >
              {isFavorited ? (
                <HeartIcon size={24} color="#EF4444" />
              ) : (
                <HeartOutlineIcon size={24} color="#94A3B8" />
              )}
            </View>
            <Text
              className="poster-btn"
              onClick={handleDoctorPoster}
              aria-label="医生海报"
            >
              医生海报
            </Text>
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

      {/* 排班选择 */}
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
            {/* 日期横向选择 */}
            <ScrollView className="date-scroll" scrollX enhanced showScrollbar={false}>
              <View className="date-list">
                {dateList.map(item => (
                  <View
                    key={item.date}
                    className={`date-item ${selectedDate === item.date ? 'active' : ''}`}
                    onClick={() => handleDateSelect(item.date)}
                    aria-label={`选择${item.weekday}${item.formatted}`}
                    role="button"
                  >
                    <Text className="date-weekday">{item.weekday}</Text>
                    <Text className="date-day">{item.formatted}</Text>
                  </View>
                ))}
              </View>
            </ScrollView>

            {/* 上午/下午时段 */}
            <View className="time-slots">
              {(['morning', 'afternoon'] as const).map(slot => {
                const summary = slot === 'morning' ? timeSlotSummary.morning : timeSlotSummary.afternoon;
                const slotStatus = getSlotSummary(summary.schedules);

                return (
                  <View
                    key={slot}
                    className={`time-slot-card ${slotStatus.disabled ? 'full' : ''} ${selectedSlot === slot ? 'selected' : ''}`}
                    onClick={() => !slotStatus.disabled && handleTimeSlotClick(slot)}
                    aria-label={slotStatus.disabled ? `${slot === 'morning' ? '上午' : '下午'}已约满` : `选择${slot === 'morning' ? '上午' : '下午'}时段`}
                    role={slotStatus.disabled ? undefined : 'button'}
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

      {/* 患者评价 */}
      <View className="reviews-section">
        <View className="section-header">
          <Text className="section-title">患者评价({reviewsTotal})</Text>
        </View>

        {reviews.length === 0 ? (
          <View className="reviews-empty">
            <StarIcon size={40} color="#D1D5DB" />
            <Text className="reviews-empty-text">暂无评价</Text>
          </View>
        ) : (
          <View className="reviews-list">
            {reviews.map(review => (
              <View key={review.id} className="review-item">
                <View className="review-item-header">
                  <Text className="review-name">{maskPatientName(review.patientName)}</Text>
                  {formatReviewDate(review.createdAt) && (
                    <Text className="review-date">{formatReviewDate(review.createdAt)}</Text>
                  )}
                </View>
                <Rate value={review.rating || 0} readOnly count={5} />
                {review.content && <Text className="review-content">{review.content}</Text>}
              </View>
            ))}
          </View>
        )}

        <View className="reviews-footer">
          <TaroButton className="contact-btn" openType="contact" aria-label="在线客服">
            在线客服
          </TaroButton>
          <Button
            type="primary"
            className="write-review-btn"
            onClick={handleOpenReviewSheet}
          >
            写评价
          </Button>
        </View>
      </View>

      {/* 班次选择 Picker */}
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
                    aria-label={isDisabled ? status.message : `选择${formatTime(schedule.startTime)}~${formatTime(schedule.endTime)}班次`}
                    role={isDisabled ? undefined : 'button'}
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

      {/* 写评价弹层 */}
      {showReviewSheet && (
        <View className="review-mask" onClick={handleCloseReviewSheet}>
          <View className="review-sheet" onClick={e => e.stopPropagation()}>
            <View className="slot-picker-indicator" />
            <View className="review-sheet-header">
              <Text className="review-sheet-title">写评价</Text>
              <Text className="review-sheet-close" onClick={handleCloseReviewSheet}>x</Text>
            </View>

            <View className="review-rating-row">
              <Text className="review-rating-label">总体评分</Text>
              <Rate value={reviewRating} onChange={val => setReviewRating(val)} count={5} />
            </View>

            <Textarea
              className="review-textarea"
              placeholder="说说您的就诊体验吧..."
              value={reviewContent}
              maxlength={300}
              onInput={e => setReviewContent(e.detail.value)}
              aria-label="评价内容"
            />
            <Text className="review-char-count">{reviewContent.length}/300</Text>

            <View className="review-footer">
              <Button
                type="primary"
                className="review-submit-btn"
                loading={reviewSubmitting}
                disabled={!reviewContent.trim()}
                onClick={handleSubmitReview}
              >
                提交评价
              </Button>
              <Text className="review-cancel-btn" onClick={handleCloseReviewSheet}>
                取消
              </Text>
            </View>
          </View>
        </View>
      )}
    </View>
  );
}
