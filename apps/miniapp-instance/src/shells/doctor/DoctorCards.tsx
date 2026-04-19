import { View, Text, Image } from '@tarojs/components';
import Taro, { useRouter, usePullDownRefresh } from '@tarojs/taro';
import { useState, useEffect } from 'react';
import { doctorApi } from '@hospital/api';
import type { Doctor } from '@hospital/shared';
import { DoctorIcon } from '../../components/Icons';
import { getToken } from '../../utils/auth';
import { useThemePrimaryColor, useApplyThemeNavigationBar } from '../../utils/theme';
import { getImageUrl } from '../../utils/url';
import { DoctorEmptyState, LoadFailedErrorState } from '../../components/EmptyState';
import './DoctorCards.less';

/**
 * 医生列表壳层 -- 卡片布局
 * 医生卡片展示：头像 + 姓名 + 职称 + 科室 + 擅长 + 有号标签
 */
export function DoctorCards() {
  const primaryColor = useThemePrimaryColor();
  useApplyThemeNavigationBar();
  const router = useRouter();
  const { departmentId } = router.params;

  const [loading, setLoading] = useState(true);
  const [doctors, setDoctors] = useState<Doctor[]>([]);
  const [error, setError] = useState(false);

  useEffect(() => {
    if (departmentId) {
      loadDoctors();
    }
  }, [departmentId]);

  usePullDownRefresh(() => {
    if (departmentId) {
      loadDoctors().finally(() => {
        Taro.stopPullDownRefresh();
      });
    } else {
      Taro.stopPullDownRefresh();
    }
  });

  const loadDoctors = async () => {
    setError(false);
    try {
      const data = await doctorApi.getByDepartment(departmentId!);
      setDoctors(data);
    } catch (error) {
      console.error('[医生列表] 加载失败', error);
      setError(true);
    } finally {
      setLoading(false);
    }
  };

  const handleSelectDoctor = (doctorId: string) => {
    // 未登录提示
    if (!getToken()) {
      Taro.showToast({ title: '请先登录', icon: 'none' });
      return;
    }
    Taro.navigateTo({
      url: `/packageBooking/pages/doctor/detail?id=${doctorId}`,
    });
  };

  if (loading) {
    return (
      <View className="doctor-list-page">
        <View className="loading-state">加载中...</View>
      </View>
    );
  }

  return (
    <View className="doctor-list-page">
      {loading ? (
        <View className="loading-state">加载中...</View>
      ) : error ? (
        <LoadFailedErrorState onRetry={loadDoctors} />
      ) : doctors.length === 0 ? (
        <DoctorEmptyState />
      ) : (
        <View className="doctor-list">
          {doctors.map(doctor => (
            <View
              key={doctor.id}
              className="doctor-card"
              onClick={() => handleSelectDoctor(doctor.id)}
            >
              <View className="avatar-wrap">
                {doctor.avatar ? (
                  <Image className="avatar" src={getImageUrl(doctor.avatar)} mode="aspectFill" />
                ) : (
                  <DoctorIcon size={36} color={primaryColor} />
                )}
              </View>
              <View className="info">
                <View className="name-row">
                  <Text className="name">{doctor.name}</Text>
                  {doctor.title && <Text className="title">{doctor.title}</Text>}
                </View>
                <Text className="dept">{doctor.departmentName}</Text>
                <Text className="spec">擅长：{doctor.specialty || '暂无'}</Text>
              </View>
              <View className={`slot-tag ${doctor.hasAvailableSlots ? 'available' : 'unavailable'}`}>
                <Text>{doctor.hasAvailableSlots ? '有号' : '无号'}</Text>
              </View>
            </View>
          ))}
        </View>
      )}
    </View>
  );
}
