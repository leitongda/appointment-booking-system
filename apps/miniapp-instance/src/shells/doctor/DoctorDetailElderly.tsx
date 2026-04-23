import { View, Text, Image } from '@tarojs/components';
import Taro from '@tarojs/taro';
import { useState, useEffect } from 'react';
import { doctorApi, scheduleApi } from '@hospital/api';
import type { Doctor } from '@hospital/shared';
import { PageContainer } from '../../components/PageContainer';
import { useTemplate } from '../../contexts/TemplateContext';
import { getImageUrl } from '../../utils/url';

/** 排班日期 */
interface ScheduleSlot {
  date: string;
  dateLabel: string;
  period: string;
  hasSlots: boolean;
}

/** 医生详情壳层 -- 长辈友好版
 * 超大头像 120rpx、大字号信息、简化排班选择器（只显示有号的日期）、超大"立即预约"按钮 120rpx 高
 */
export function DoctorDetailElderly() {
  const { tokens, tone, template } = useTemplate();
  const [doctor, setDoctor] = useState<Doctor | null>(null);
  const [loading, setLoading] = useState(true);
  const [selectedSlot, setSelectedSlot] = useState<ScheduleSlot | null>(null);
  const [availableSlots, setAvailableSlots] = useState<ScheduleSlot[]>([]);

  useEffect(() => {
    const instance = Taro.getCurrentInstance();
    const doctorId = instance?.router?.params?.id;
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
    } catch {
      Taro.showToast({ title: '加载医生信息失败', icon: 'none' });
    } finally {
      setLoading(false);
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
      </View>
    </PageContainer>
  );
}
