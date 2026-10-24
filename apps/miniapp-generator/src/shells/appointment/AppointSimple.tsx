import { View, Text } from '@tarojs/components';
import Taro, { useDidShow, usePullDownRefresh } from '@tarojs/taro';
import { useState } from 'react';
import { appointmentApi } from '@hospital/api';
import type { Appointment } from '@hospital/shared';
import { PageContainer } from '../../components/PageContainer';
import { useTemplate } from '../../contexts/TemplateContext';
import { getToken } from '../../utils/auth';
import LoginPopup from '../../components/LoginPopup';

/** 预约状态 (数字编码) -> 中文标签 & 颜色 */
const statusMap: Record<number, { label: string; color: string; bgColor: string }> = {
  0: { label: '待确认', color: '#E8A838', bgColor: '#FEF3C7' },
  1: { label: '已确认', color: '#52C41A', bgColor: '#ECFDF5' },
  2: { label: '已签到', color: '#3B82F6', bgColor: '#EFF6FF' },
  3: { label: '已完成', color: '#6B7280', bgColor: '#F3F4F6' },
  4: { label: '已取消', color: '#D32F2F', bgColor: '#FEF2F2' },
  5: { label: '爽约', color: '#D32F2F', bgColor: '#FEF2F2' },
};

const DEFAULT_STATUS = { label: '未知', color: '#6B7280', bgColor: '#F3F4F6' };

/** 预约列表壳层 -- 简化版
 * 取消 Tab 分类，单列表，卡片更大更明显，操作按钮更大
 */
export function AppointSimple() {
  const { tokens, tone, template } = useTemplate();
  const [appointments, setAppointments] = useState<Appointment[]>([]);
  const [loading, setLoading] = useState(true);
  const [showLoginPopup, setShowLoginPopup] = useState(false);

  useDidShow(() => {
    // -1 = 不落在任何 tab 上：本页不在 elderly-tcm 的 navSchema（首页/机构中心/我的）内，
    // 是从首页四宫格进入的导航页（竞品同形态）；其它模板的 navSchema 含「预约」tab 时，
    // 挂载时按路由推导的选中态依然生效
    Taro.eventCenter.trigger('tabbar:change', -1);
    const token = getToken();
    if (!token) {
      setShowLoginPopup(true);
      setLoading(false);
      return;
    }
    void loadAppointments();
  });

  usePullDownRefresh(() => {
    loadAppointments().finally(() => Taro.stopPullDownRefresh());
  });

  const loadAppointments = async () => {
    try {
      const result = await appointmentApi.getList({ pageSize: 50 });
      setAppointments(result.data || []);
    } catch {
      Taro.showToast({ title: '加载预约失败', icon: 'none' });
    } finally {
      setLoading(false);
    }
  };

  const handleLoginSuccess = () => {
    setShowLoginPopup(false);
    void loadAppointments();
  };

  const handleCancel = (appointment: Appointment) => {
    if (template.constraints.confirmBeforeAction) {
      Taro.showModal({
        title: '确认取消',
        content: `确定要取消 ${appointment.doctorName} 医生 ${appointment.scheduleDate} 的预约吗？`,
        confirmText: '确认取消',
        cancelText: '再想想',
        confirmColor: '#D32F2F',
        success: async (res) => {
          if (res.confirm) {
            try {
              await appointmentApi.cancel(appointment.id);
              Taro.showToast({ title: '已取消', icon: 'success' });
              void loadAppointments();
            } catch {
              Taro.showToast({ title: '取消失败', icon: 'none' });
            }
          }
        },
      });
    }
  };

  const handleCheckin = (appointment: Appointment) => {
    Taro.navigateTo({
      url: `/packageBooking/pages/checkin/scan?appointmentId=${appointment.id}`,
    });
  };

  const handleDetail = (appointment: Appointment) => {
    Taro.navigateTo({
      url: `/packageBooking/pages/appointment/detail?id=${appointment.id}`,
    });
  };

  const formatDate = (dateStr: string) => {
    if (!dateStr) return '';
    return dateStr;
  };

  const getStatus = (appointment: Appointment) => {
    return statusMap[appointment.status] || DEFAULT_STATUS;
  };

  // 未登录
  if (showLoginPopup) {
    return (
      <PageContainer>
        <View style={{ padding: '64rpx', textAlign: 'center' }}>
          <Text style={{ fontSize: '36rpx', color: '#9CA3AF' }}>请先登录查看预约</Text>
        </View>
        <LoginPopup
          visible={showLoginPopup}
          onClose={() => setShowLoginPopup(false)}
          onSuccess={handleLoginSuccess}
        />
      </PageContainer>
    );
  }

  return (
    <PageContainer>
      <View style={{ padding: '32rpx' }}>
        <Text style={{
          fontSize: '48rpx',
          fontWeight: 700,
          color: '#3D2B1F',
          marginBottom: '32rpx',
          display: 'block',
        }}>
          我的预约
        </Text>

        {!loading && appointments.length === 0 && (
          <View style={{
            padding: '64rpx',
            backgroundColor: '#FFFFFF',
            borderRadius: '24rpx',
            textAlign: 'center',
          }}>
            <Text style={{ fontSize: '36rpx', color: '#9CA3AF', display: 'block', marginBottom: '24rpx' }}>
              {tone.emptyBookingText}
            </Text>
            <View
              onClick={() => Taro.switchTab({ url: '/pages/index/index' })}
              aria-label={tone.custom?.guideText || '去挂号'}
              role="button"
              style={{
                display: 'inline-flex',
                padding: '24rpx 48rpx',
                borderRadius: '9999rpx',
                backgroundColor: tokens.primary,
              }}
            >
              <Text style={{ fontSize: '36rpx', color: '#FFFFFF', fontWeight: 600 }}>
                {tone.custom?.guideText || '去挂号'}
              </Text>
            </View>
          </View>
        )}

        {appointments.map((apt) => {
          const statusInfo = getStatus(apt);
          return (
            <View
              key={apt.id}
              onClick={() => handleDetail(apt)}
              aria-label={`查看${apt.doctorName}医生的预约详情，状态为${statusInfo.label}`}
              role="button"
              style={{
                backgroundColor: '#FFFFFF',
                borderRadius: '24rpx',
                padding: '32rpx',
                marginBottom: '24rpx',
                boxShadow: '0 2rpx 12rpx rgba(0,0,0,0.06)',
              }}
            >
              {/* 状态标签 + 医生名 */}
              <View style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20rpx' }}>
                <Text style={{
                  fontSize: '40rpx',
                  fontWeight: 700,
                  color: '#3D2B1F',
                }}>
                  {apt.doctorName} 医生
                </Text>
                <View style={{
                  padding: '8rpx 24rpx',
                  borderRadius: '9999rpx',
                  backgroundColor: statusInfo.bgColor,
                }}>
                  <Text style={{ fontSize: '28rpx', color: statusInfo.color, fontWeight: 600 }}>
                    {statusInfo.label}
                  </Text>
                </View>
              </View>

              {/* 预约详情 */}
              <View style={{
                borderTop: '2rpx solid #F3F4F6',
                borderBottom: '2rpx solid #F3F4F6',
                padding: '20rpx 0',
                marginBottom: '20rpx',
              }}>
                <Text style={{ fontSize: '36rpx', color: '#4B5563', display: 'block', marginBottom: '8rpx' }}>
                  {apt.departmentName || ''}
                </Text>
                <Text style={{ fontSize: '36rpx', color: '#4B5563' }}>
                  {formatDate(apt.scheduleDate || '')} {apt.startTime || ''}
                </Text>
              </View>

              {/* 操作按钮 */}
              <View style={{ display: 'flex', justifyContent: 'flex-end', gap: '20rpx' }}>
                {(apt.status === 1 || apt.status === 0) && (
                  <>
                    <View
                      onClick={(e) => { e.stopPropagation(); handleCheckin(apt); }}
                      aria-label="扫码签到"
                      role="button"
                      style={{
                        height: '88rpx',
                        paddingLeft: '40rpx',
                        paddingRight: '40rpx',
                        borderRadius: '9999rpx',
                        backgroundColor: tokens.primary,
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                      }}
                    >
                      <Text style={{ fontSize: '32rpx', color: '#FFFFFF', fontWeight: 600 }}>扫码签到</Text>
                    </View>
                    <View
                      onClick={(e) => { e.stopPropagation(); handleCancel(apt); }}
                      aria-label="取消预约"
                      role="button"
                      style={{
                        height: '88rpx',
                        paddingLeft: '40rpx',
                        paddingRight: '40rpx',
                        borderRadius: '9999rpx',
                        border: '2rpx solid #D1D5DB',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                      }}
                    >
                      <Text style={{ fontSize: '32rpx', color: '#6B7280' }}>取消</Text>
                    </View>
                  </>
                )}
              </View>
            </View>
          );
        })}
      </View>
    </PageContainer>
  );
}
