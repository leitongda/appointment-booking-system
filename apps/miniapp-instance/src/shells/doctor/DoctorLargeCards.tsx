import { View, Text, Image } from '@tarojs/components';
import Taro, { useDidShow } from '@tarojs/taro';
import { useState } from 'react';
import { doctorApi } from '@hospital/api';
import type { Doctor } from '@hospital/shared';
import { PageContainer } from '../../components/PageContainer';
import { useTemplate } from '../../contexts/TemplateContext';
import { getImageUrl } from '../../utils/url';
import { DoctorEmptyState, LoadFailedErrorState } from '../../components/EmptyState';

/** 医生列表壳层 -- 大尺寸卡片
 * 卡片高度 240rpx，所有文字 >= 32rpx，操作按钮超大 100rpx 高
 */
export function DoctorLargeCards() {
  const { tokens, tone } = useTemplate();
  const [doctors, setDoctors] = useState<Doctor[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [departmentName, setDepartmentName] = useState('');

  useDidShow(() => {
    // 从页面参数获取科室信息
    const instance = Taro.getCurrentInstance();
    const deptName = instance?.router?.params?.departmentName as string;
    const deptId = instance?.router?.params?.departmentId as string;
    if (deptName) setDepartmentName(deptName);
    void loadDoctors(deptId);
  });

  const loadDoctors = async (departmentId?: string) => {
    setError(false);
    try {
      const data = departmentId
        ? await doctorApi.getByDepartment(departmentId)
        : await doctorApi.getRecommended(20);
      setDoctors(data);
    } catch {
      setError(true);
    } finally {
      setLoading(false);
    }
  };

  const handleBookDoctor = (doctorId: string) => {
    Taro.navigateTo({ url: `/packageBooking/pages/doctor/detail?id=${doctorId}` });
  };

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
          {departmentName ? `${departmentName}医生` : '推荐医生'}
        </Text>

        {error && !loading && (
          <View style={{ marginBottom: '24rpx' }}>
            <LoadFailedErrorState onRetry={() => loadDoctors(Taro.getCurrentInstance().router?.params?.departmentId as string)} />
          </View>
        )}
        {!error && !loading && doctors.length === 0 && (
          <View style={{
            padding: '64rpx',
            backgroundColor: '#FFFFFF',
            borderRadius: '24rpx',
            textAlign: 'center',
          }}>
            <DoctorEmptyState />
          </View>
        )}

        {doctors.map((doctor) => (
          <View
            key={doctor.id}
            style={{
              minHeight: '240rpx',
              backgroundColor: '#FFFFFF',
              borderRadius: '24rpx',
              padding: '32rpx',
              marginBottom: '24rpx',
              boxShadow: '0 2rpx 12rpx rgba(0,0,0,0.06)',
            }}
          >
            {/* 医生信息区 */}
            <View style={{ display: 'flex', marginBottom: '24rpx' }}>
              <View style={{
                width: '120rpx',
                height: '120rpx',
                borderRadius: '60rpx',
                backgroundColor: tokens.primarySoft,
                overflow: 'hidden',
                flexShrink: 0,
                marginRight: '28rpx',
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
                  <Text style={{ fontSize: '56rpx' }}>{'\ud83e\ude7a'}</Text>
                )}
              </View>
              <View style={{ flex: 1, minWidth: 0 }}>
                <View style={{ display: 'flex', alignItems: 'baseline', marginBottom: '8rpx' }}>
                  <Text style={{ fontSize: '40rpx', fontWeight: 700, color: '#3D2B1F', marginRight: '16rpx' }}>
                    {doctor.name}
                  </Text>
                  {doctor.title && (
                    <Text style={{ fontSize: '32rpx', color: '#8B6F47' }}>{doctor.title}</Text>
                  )}
                </View>
                <Text style={{ fontSize: '32rpx', color: '#6B7280', marginBottom: '4rpx' }}>
                  {doctor.departmentName}
                </Text>
                {doctor.specialty && (
                  <Text style={{ fontSize: '32rpx', color: '#9CA3AF' }} numberOfLines={2}>
                    擅长：{doctor.specialty}
                  </Text>
                )}
              </View>
            </View>

            {/* 操作区 */}
            <View style={{ display: 'flex', justifyContent: 'flex-end' }}>
              <View
                onClick={() => handleBookDoctor(doctor.id)}
                aria-label={`为${doctor.name}医生${doctor.hasAvailableSlots ? tone.bookingLabel : '无号'}`}
                role="button"
                style={{
                  height: '100rpx',
                  paddingHorizontal: '48rpx',
                  borderRadius: '9999rpx',
                  backgroundColor: doctor.hasAvailableSlots ? tokens.primary : '#D1D5DB',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                }}
              >
                <Text style={{
                  fontSize: '36rpx',
                  fontWeight: 600,
                  color: '#FFFFFF',
                }}>
                  {doctor.hasAvailableSlots ? tone.bookingLabel : '无号'}
                </Text>
              </View>
            </View>
          </View>
        ))}
      </View>
    </PageContainer>
  );
}
