import { View, Text, Image, Button as TaroButton, Textarea } from '@tarojs/components';
import Taro from '@tarojs/taro';
import { Rate } from '@nutui/nutui-react-taro';
import { useState, useEffect } from 'react';
import { doctorApi, scheduleApi, doctorReviewApi } from '@hospital/api';
import type { DoctorReviewItem } from '@hospital/api';
import type { Doctor } from '@hospital/shared';
import { PageContainer } from '../../components/PageContainer';
import { StarIcon } from '../../components/Icons';
import DoctorPoster from '../../components/DoctorPoster';
import { useTemplate } from '../../contexts/TemplateContext';
import { getToken } from '../../utils/auth';
import { resolveDoctorIdFromParams } from '../../utils/scene';
import { getImageUrl } from '../../utils/url';

/** 排班日期 */
interface ScheduleSlot {
  date: string;
  dateLabel: string;
  period: string;
  hasSlots: boolean;
}

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

/** 医生详情壳层 -- 长辈友好版
 * 超大头像 120rpx、大字号信息、简化排班选择器（只显示有号的日期）、超大"立即预约"按钮 120rpx 高
 */
export function DoctorDetailElderly() {
  const { tokens, tone, template } = useTemplate();
  const [doctor, setDoctor] = useState<Doctor | null>(null);
  const [loading, setLoading] = useState(true);
  const [selectedSlot, setSelectedSlot] = useState<ScheduleSlot | null>(null);
  const [availableSlots, setAvailableSlots] = useState<ScheduleSlot[]>([]);
  // 患者评价状态
  const [reviews, setReviews] = useState<DoctorReviewItem[]>([]);
  const [reviewsTotal, setReviewsTotal] = useState(0);
  // 写评价弹层状态
  const [showReviewSheet, setShowReviewSheet] = useState(false);
  const [reviewRating, setReviewRating] = useState(5);
  const [reviewContent, setReviewContent] = useState('');
  const [reviewSubmitting, setReviewSubmitting] = useState(false);
  // 医生海报弹层状态
  const [showPoster, setShowPoster] = useState(false);

  useEffect(() => {
    const instance = Taro.getCurrentInstance();
    // 支持扫码进入：显式 id 优先，其次解析 scene（海报小程序码契约见 utils/scene.ts）
    const doctorId = resolveDoctorIdFromParams(instance?.router?.params);
    if (doctorId) {
      void loadDoctor(doctorId);
    }
  }, []);

  const loadDoctor = async (doctorId: string) => {
    try {
      const data = await doctorApi.getDetail(doctorId);
      setDoctor(data);

      // 加载排班数据，筛选有号的日期
      const schedules = await scheduleApi.getAvailable(doctorId, 7);

      // 将排班数据转换为 Slot 格式
      const slots: ScheduleSlot[] = schedules
        .filter(s => s.availableSlots > 0) // 只显示有号的日期
        .map(s => {
          const date = new Date(s.scheduleDate);
          const weekdays = ['周日', '周一', '周二', '周三', '周四', '周五', '周六'];
          const dateLabel = `${date.getMonth() + 1}月${date.getDate()}日 ${weekdays[date.getDay()]}`;

          // 根据 timeSlot 确定时段
          let period = '上午';
          if (s.timeSlot === 'afternoon') period = '下午';
          else if (s.timeSlot === 'evening') period = '晚上';

          return {
            date: s.scheduleDate,
            dateLabel,
            period,
            hasSlots: s.availableSlots > 0,
          };
        });

      setAvailableSlots(slots);
      if (slots.length > 0) {
        setSelectedSlot(slots[0]);
      }

      // 评价加载失败时静默降级为空态，不阻塞页面
      void loadReviews(doctorId);
    } catch {
      Taro.showToast({ title: '加载医生信息失败', icon: 'none' });
    } finally {
      setLoading(false);
    }
  };

  // 患者评价（公开接口；接口失败或为空时保持空态）
  const loadReviews = async (doctorId: string) => {
    try {
      const result = await doctorReviewApi.getList({ doctorId, page: 1, pageSize: 10 });
      const items = Array.isArray(result?.items) ? result.items : [];
      setReviews(items);
      setReviewsTotal(typeof result?.total === 'number' ? result.total : items.length);
    } catch (error) {
      console.error('[医生详情] 加载患者评价失败', error);
      setReviews([]);
      setReviewsTotal(0);
    }
  };

  const handleBook = () => {
    if (!doctor || !selectedSlot) return;

    // 二次确认（模板约束 confirmBeforeAction）
    if (template.constraints.confirmBeforeAction) {
      Taro.showModal({
        title: tone.custom?.confirmBooking || '确认挂号',
        content: `确认预约 ${doctor.name} 医生 ${selectedSlot.dateLabel} ${selectedSlot.period} 的号源吗？`,
        confirmText: '确认',
        cancelText: '再想想',
        confirmColor: tokens.primary,
        success: (res) => {
          if (res.confirm) {
            doBooking();
          }
        },
      });
    } else {
      doBooking();
    }
  };

  const doBooking = () => {
    if (!doctor || !selectedSlot) return;
    Taro.navigateTo({
      url: `/packageBooking/pages/booking/index?doctorId=${doctor.id}&date=${selectedSlot.date}&period=${selectedSlot.period}`,
    });
  };

  // 医生海报：打开海报弹层（Canvas 生成，可保存到相册）
  const handleDoctorPoster = () => {
    setShowPoster(true);
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
    if (!doctor?.id || reviewSubmitting) return;
    if (!reviewContent.trim()) {
      Taro.showToast({ title: '请输入评价内容', icon: 'none' });
      return;
    }
    setReviewSubmitting(true);
    try {
      await doctorReviewApi.create({ doctorId: doctor.id, rating: reviewRating, content: reviewContent.trim() });
      Taro.showToast({ title: '评价成功', icon: 'success' });
      setShowReviewSheet(false);
      void loadReviews(doctor.id);
    } catch (error: any) {
      Taro.showToast({ title: error.message || '提交失败', icon: 'none' });
    } finally {
      setReviewSubmitting(false);
    }
  };

  if (loading) {
    return (
      <PageContainer>
        <View style={{ padding: '64rpx', textAlign: 'center' }}>
          <Text style={{ fontSize: '36rpx', color: '#9CA3AF' }}>加载中...</Text>
        </View>
      </PageContainer>
    );
  }

  if (!doctor) {
    return (
      <PageContainer>
        <View style={{ padding: '64rpx', textAlign: 'center' }}>
          <Text style={{ fontSize: '36rpx', color: '#9CA3AF' }}>医生信息不存在</Text>
        </View>
      </PageContainer>
    );
  }

  return (
    <PageContainer>
      <View style={{ padding: '32rpx' }}>
        {/* 医生基本信息 */}
        <View style={{
          backgroundColor: '#FFFFFF',
          borderRadius: '32rpx',
          padding: '40rpx',
          marginBottom: '32rpx',
          boxShadow: '0 2rpx 12rpx rgba(0,0,0,0.06)',
          display: 'flex',
          alignItems: 'center',
        }}>
          <View style={{
            width: '120rpx',
            height: '120rpx',
            borderRadius: '60rpx',
            backgroundColor: tokens.primarySoft,
            overflow: 'hidden',
            flexShrink: 0,
            marginRight: '32rpx',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}>
            {doctor.avatar ? (
              <Image
                src={getImageUrl(doctor.avatar)}
                mode="aspectFill"
                style={{ width: '120rpx', height: '120rpx', borderRadius: '60rpx' }}
              />
            ) : (
              <Text style={{ fontSize: '64rpx' }}>{'\ud83e\ude7a'}</Text>
            )}
          </View>
          <View style={{ flex: 1 }}>
            <Text style={{ fontSize: '44rpx', fontWeight: 700, color: '#3D2B1F', display: 'block', marginBottom: '8rpx' }}>
              {doctor.name}
            </Text>
            {doctor.title && (
              <Text style={{ fontSize: '36rpx', color: '#8B6F47', display: 'block', marginBottom: '4rpx' }}>
                {doctor.title}
              </Text>
            )}
            <Text style={{ fontSize: '36rpx', color: '#6B7280' }}>
              {doctor.departmentName}
            </Text>
            {/* 医生海报：打开海报弹层 */}
            <View
              onClick={handleDoctorPoster}
              aria-label="医生海报"
              role="button"
              style={{
                alignSelf: 'flex-start',
                marginTop: '16rpx',
                padding: '8rpx 24rpx',
                borderRadius: '9999rpx',
                border: `2rpx solid ${tokens.primary}`,
              }}
            >
              <Text style={{ fontSize: '30rpx', color: tokens.primary }}>医生海报</Text>
            </View>
          </View>
        </View>

        {/* 擅长领域 */}
        {doctor.specialty && (
          <View style={{
            backgroundColor: '#FFFFFF',
            borderRadius: '24rpx',
            padding: '32rpx',
            marginBottom: '32rpx',
            boxShadow: '0 2rpx 12rpx rgba(0,0,0,0.06)',
          }}>
            <Text style={{ fontSize: '36rpx', fontWeight: 600, color: '#3D2B1F', display: 'block', marginBottom: '16rpx' }}>
              擅长治疗
            </Text>
            <Text style={{ fontSize: '36rpx', color: '#4B5563', lineHeight: 1.6 }}>
              {doctor.specialty}
            </Text>
          </View>
        )}

        {/* 排班选择器 -- 只显示有号的日期 */}
        <View style={{
          backgroundColor: '#FFFFFF',
          borderRadius: '24rpx',
          padding: '32rpx',
          marginBottom: '40rpx',
          boxShadow: '0 2rpx 12rpx rgba(0,0,0,0.06)',
        }}>
          <Text style={{ fontSize: '36rpx', fontWeight: 600, color: '#3D2B1F', display: 'block', marginBottom: '24rpx' }}>
            选择就诊时间
          </Text>

          {availableSlots.length === 0 ? (
            <Text style={{ fontSize: '36rpx', color: '#9CA3AF' }}>暂无可预约的时间</Text>
          ) : (
            <View style={{ display: 'flex', flexWrap: 'wrap', gap: '20rpx' }}>
              {availableSlots.map((slot) => (
                <View
                  key={`${slot.date}-${slot.period}`}
                  onClick={() => setSelectedSlot(slot)}
                  aria-label={`选择${slot.dateLabel}${slot.period}`}
                  role="button"
                  style={{
                    padding: '24rpx 32rpx',
                    borderRadius: '24rpx',
                    border: selectedSlot === slot
                      ? `4rpx solid ${tokens.primary}`
                      : '2rpx solid #E5E7EB',
                    backgroundColor: selectedSlot === slot ? tokens.primarySoft : '#FFFFFF',
                    minHeight: '88rpx',
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                    justifyContent: 'center',
                  }}
                >
                  <Text style={{
                    fontSize: '36rpx',
                    fontWeight: selectedSlot === slot ? 700 : 400,
                    color: selectedSlot === slot ? '#3D2B1F' : '#6B7280',
                  }}>
                    {slot.dateLabel}
                  </Text>
                  <Text style={{
                    fontSize: '32rpx',
                    color: selectedSlot === slot ? tokens.primary : '#9CA3AF',
                    marginTop: '4rpx',
                  }}>
                    {slot.period}
                  </Text>
                </View>
              ))}
            </View>
          )}
        </View>

        {/* 超大预约按钮 */}
        <View
          onClick={handleBook}
          aria-label={selectedSlot ? '立即预约' : '请先选择时间'}
          role="button"
          style={{
            height: '120rpx',
            borderRadius: '9999rpx',
            backgroundColor: selectedSlot ? tokens.primary : '#D1D5DB',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            boxShadow: selectedSlot ? '0 4rpx 16rpx rgba(139, 111, 71, 0.3)' : 'none',
          }}
        >
          <Text style={{
            fontSize: '40rpx',
            fontWeight: 700,
            color: '#FFFFFF',
          }}>
            {selectedSlot ? '立即预约' : '请先选择时间'}
          </Text>
        </View>

        {/* 患者评价 */}
        <View style={{
          backgroundColor: '#FFFFFF',
          borderRadius: '24rpx',
          padding: '32rpx',
          marginTop: '32rpx',
          boxShadow: '0 2rpx 12rpx rgba(0,0,0,0.06)',
        }}>
          <Text style={{ fontSize: '36rpx', fontWeight: 600, color: '#3D2B1F', display: 'block', marginBottom: '24rpx' }}>
            患者评价({reviewsTotal})
          </Text>

          {reviews.length === 0 ? (
            <View style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', padding: '48rpx 0' }}>
              <StarIcon size={40} color="#D1D5DB" />
              <Text style={{ fontSize: '36rpx', color: '#9CA3AF', marginTop: '16rpx' }}>暂无评价</Text>
            </View>
          ) : (
            <View>
              {reviews.map((review, index) => (
                <View
                  key={review.id}
                  style={{
                    padding: '24rpx 0',
                    borderBottom: index < reviews.length - 1 ? '2rpx solid #F1F5F9' : 'none',
                  }}
                >
                  <View style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8rpx' }}>
                    <Text style={{ fontSize: '34rpx', fontWeight: 500, color: '#3D2B1F' }}>
                      {maskPatientName(review.patientName)}
                    </Text>
                    {formatReviewDate(review.createdAt) && (
                      <Text style={{ fontSize: '30rpx', color: '#9CA3AF' }}>
                        {formatReviewDate(review.createdAt)}
                      </Text>
                    )}
                  </View>
                  <Rate value={review.rating || 0} readOnly count={5} />
                  {review.content && (
                    <Text style={{ display: 'block', marginTop: '16rpx', fontSize: '34rpx', color: '#4B5563', lineHeight: 1.6 }}>
                      {review.content}
                    </Text>
                  )}
                </View>
              ))}
            </View>
          )}

          {/* 在线客服 + 写评价 */}
          <View style={{ display: 'flex', flexDirection: 'column', gap: '20rpx', marginTop: '32rpx' }}>
            <TaroButton
              openType="contact"
              aria-label="在线客服"
              style={{
                height: '96rpx',
                lineHeight: '96rpx',
                borderRadius: '9999rpx',
                background: '#FFFFFF',
                border: `2rpx solid ${tokens.primary}`,
                color: tokens.primary,
                fontSize: '36rpx',
                padding: 0,
              }}
            >
              在线客服
            </TaroButton>
            <View
              onClick={handleOpenReviewSheet}
              aria-label="写评价"
              role="button"
              style={{
                height: '96rpx',
                borderRadius: '9999rpx',
                backgroundColor: tokens.primarySoft,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              <Text style={{ fontSize: '36rpx', fontWeight: 600, color: tokens.primary }}>写评价</Text>
            </View>
          </View>
        </View>
      </View>

      {/* 写评价弹层 */}
      {showReviewSheet && (
        <View
          onClick={handleCloseReviewSheet}
          style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            background: 'rgba(0,0,0,0.5)',
            zIndex: 1000,
            display: 'flex',
            alignItems: 'flex-end',
          }}
        >
          <View
            onClick={e => e.stopPropagation()}
            style={{
              width: '100%',
              backgroundColor: '#FFFFFF',
              borderRadius: '32rpx 32rpx 0 0',
              padding: '32rpx',
              paddingBottom: 'calc(32rpx + env(safe-area-inset-bottom))',
            }}
          >
            <View style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '32rpx' }}>
              <Text style={{ fontSize: '40rpx', fontWeight: 600, color: '#3D2B1F' }}>写评价</Text>
              <Text
                onClick={handleCloseReviewSheet}
                aria-label="关闭"
                style={{ fontSize: '40rpx', color: '#9CA3AF', padding: '8rpx 16rpx' }}
              >
                x
              </Text>
            </View>

            <View style={{ display: 'flex', alignItems: 'center', gap: '24rpx', marginBottom: '24rpx' }}>
              <Text style={{ fontSize: '34rpx', color: '#6B7280' }}>总体评分</Text>
              <Rate value={reviewRating} onChange={val => setReviewRating(val)} count={5} />
            </View>

            <Textarea
              placeholder="说说您的就诊体验吧..."
              value={reviewContent}
              maxlength={300}
              onInput={e => setReviewContent(e.detail.value)}
              aria-label="评价内容"
              style={{
                width: '100%',
                minHeight: '200rpx',
                padding: '24rpx',
                background: tokens.primarySoft,
                borderRadius: '24rpx',
                fontSize: '34rpx',
                color: '#3D2B1F',
                boxSizing: 'border-box',
              }}
            />
            <Text style={{ display: 'block', textAlign: 'right', fontSize: '30rpx', color: '#9CA3AF', marginTop: '8rpx' }}>
              {reviewContent.length}/300
            </Text>

            <View
              onClick={handleSubmitReview}
              aria-label={reviewContent.trim() ? '提交评价' : '请输入评价内容'}
              role="button"
              style={{
                height: '96rpx',
                borderRadius: '9999rpx',
                backgroundColor: reviewContent.trim() && !reviewSubmitting ? tokens.primary : '#D1D5DB',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                marginTop: '32rpx',
              }}
            >
              <Text style={{ fontSize: '36rpx', fontWeight: 700, color: '#FFFFFF' }}>
                {reviewSubmitting ? '提交中...' : '提交评价'}
              </Text>
            </View>
          </View>
        </View>
      )}

      {/* 医生海报弹层 */}
      <DoctorPoster
        visible={showPoster}
        onClose={() => setShowPoster(false)}
        doctorName={doctor.name}
        doctorTitle={doctor.title}
        specialty={doctor.specialty}
        introduction={doctor.introduction}
        avatarUrl={doctor.avatar ? getImageUrl(doctor.avatar) : ''}
        doctorId={doctor.id}
      />
    </PageContainer>
  );
}
