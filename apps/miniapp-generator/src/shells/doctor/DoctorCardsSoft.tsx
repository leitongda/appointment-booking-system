import { View, Text, Image } from '@tarojs/components';
import Taro, { useRouter, usePullDownRefresh } from '@tarojs/taro';
import { useState, useEffect } from 'react';
import { doctorApi } from '@hospital/api';
import type { Doctor } from '@hospital/shared';
import { DoctorIcon, StarIcon, HeartIcon } from '../../components/Icons';
import { getToken } from '../../utils/auth';
import { useThemePrimaryColor, useApplyThemeNavigationBar } from '../../utils/theme';
import { getImageUrl } from '../../utils/url';
import { DoctorEmptyState, LoadFailedErrorState } from '../../components/EmptyState';
import './DoctorCardsSoft.less';

// 女性健康模板专用评价标签
const WOMEN_HEALTH_TAGS = ['温柔耐心', '专业细致', '态度很好', '经验丰富'];

// 随机获取评价标签
const getRandomTags = (count: number = 1): string[] => {
  const shuffled = [...WOMEN_HEALTH_TAGS].sort(() => 0.5 - Math.random());
  return shuffled.slice(0, count);
};

export function DoctorCardsSoft() {
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

  if (error) {
    return (
      <View className="doctor-list-page">
        <LoadFailedErrorState onRetry={loadDoctors} />
      </View>
    );
  }

  return (
    <View className="doctor-list-page">
      {doctors.length === 0 ? (
        <DoctorEmptyState />
      ) : (
        <View className="doctor-list">
          {doctors.map(doctor => (
            <View
              key={doctor.id}
              className="doctor-card"
              onClick={() => handleSelectDoctor(doctor.id)}
              aria-label={`选择医生${doctor.name}`}
              role="button"
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
                <View className="tags-row">
                  {getRandomTags(2).map((tag, idx) => (
                    <View key={idx} className="tag-item">
                      <HeartIcon size={10} color="#C4908D" />
                      <Text className="tag-text">{tag}</Text>
                    </View>
                  ))}
                </View>
              </View>
              <View className="right-info">
                {doctor.rating && (
                  <View className="rating">
                    <StarIcon size={14} color="#F5C542" />
                    <Text className="rating-text">{doctor.rating.toFixed(1)}</Text>
                  </View>
                )}
                <View className={`slot-tag ${doctor.hasAvailableSlots ? 'available' : 'unavailable'}`}>
                  <Text>{doctor.hasAvailableSlots ? '有号' : '无号'}</Text>
                </View>
              </View>
            </View>
          ))}
        </View>
      )}
    </View>
  );
}
