import { View, Text, Image } from '@tarojs/components';
import Taro, { useRouter } from '@tarojs/taro';
import { useState, useEffect } from 'react';
import { doctorApi } from '@hospital/api';
import type { Doctor } from '@hospital/shared';
import './index.less';

const DoctorListPage = () => {
  const router = useRouter();
  const { departmentId, departmentName } = router.params;

  const [loading, setLoading] = useState(true);
  const [doctors, setDoctors] = useState<Doctor[]>([]);

  useEffect(() => {
    if (departmentId) {
      loadDoctors();
    }
  }, [departmentId]);

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
    Taro.navigateTo({
      url: `/pages/doctor/detail?id=${doctorId}`,
    });
  };

  if (loading) {
    return (
      <View className="doctor-list-page">
        <View className="empty">加载中...</View>
      </View>
    );
  }

  return (
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
                  <Image className="avatar" src={doctor.avatar} mode="aspectFill" />
                ) : (
                  <Text>👨‍⚕️</Text>
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
              <View className="fee">
                <Text className="price">¥{doctor.registrationFee}</Text>
                <Text className="book-btn">预约</Text>
              </View>
            </View>
          ))}
        </View>
      )}
    </View>
  );
};

export default DoctorListPage;
