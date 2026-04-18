import { View, Text, Image } from '@tarojs/components';
import Taro, { useRouter, usePullDownRefresh } from '@tarojs/taro';
import { useState, useEffect } from 'react';
import { doctorApi } from '@hospital/api';
import type { Doctor } from '@hospital/shared';
import { DoctorIcon } from '../../components/Icons';
import { getImageUrl } from '../../utils/url';
import { getToken } from '../../utils/auth';
import { useApplyThemeNavigationBar, useThemePrimaryColor } from '../../utils/theme';
import LoginPopup from '../../components/LoginPopup';
import './index.less';

const DoctorListPage = () => {
  const primaryColor = useThemePrimaryColor();
  useApplyThemeNavigationBar();
  const router = useRouter();
  const { departmentId } = router.params;

  const [loading, setLoading] = useState(true);
  const [doctors, setDoctors] = useState<Doctor[]>([]);
  const [showLoginPopup, setShowLoginPopup] = useState(false);

  useEffect(() => {
    if (departmentId) {
      loadDoctors();
    }
  }, [departmentId]);

  // 下拉刷新
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
    try {
      const data = await doctorApi.getByDepartment(departmentId!);
      setDoctors(data);
    } catch (error) {
      console.error('加载医生列表失败', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSelectDoctor = (doctorId: string) => {
    // 检查登录状态
    const token = getToken();
    if (!token) {
      Taro.showToast({ title: '请先登录', icon: 'none' });
      setShowLoginPopup(true);
      return;
    }

    Taro.navigateTo({
      url: `/packageBooking/pages/doctor/detail?id=${doctorId}`,
    });
  };

  // 登录成功回调
  const handleLoginSuccess = () => {
    setShowLoginPopup(false);
  };

  if (loading) {
    return (
      <View className="doctor-list-page">
        <View className="empty">加载中...</View>
      </View>
    );
  }

  return (
    <>
      <View className="doctor-list-page">
        {doctors.length === 0 ? (
          <View className="empty">
            <Text>暂无医生</Text>
          </View>
        ) : (
          <View className="doctor-list">
            {doctors.map((doctor) => (
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

      {/* 登录弹窗 */}
      <LoginPopup
        visible={showLoginPopup}
        onClose={() => setShowLoginPopup(false)}
        onSuccess={handleLoginSuccess}
      />
    </>
  );
};

export default DoctorListPage;
