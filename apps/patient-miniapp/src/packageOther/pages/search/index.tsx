import { View, Text } from '@tarojs/components';
import Taro from '@tarojs/taro';
import { SearchBar, Empty } from '@nutui/nutui-react-taro';
import { useState } from 'react';
import { doctorApi, departmentApi } from '@hospital/api';
import type { Doctor, Department } from '@hospital/shared';
import { useApplyThemeNavigationBar } from '../../../utils/theme';
import './index.less';

const SearchPage = () => {
  useApplyThemeNavigationBar();
  const [keyword, setKeyword] = useState('');
  const [searching, setSearching] = useState(false);
  const [doctors, setDoctors] = useState<Doctor[]>([]);
  const [departments, setDepartments] = useState<Department[]>([]);

  const handleSearch = async (value: string) => {
    if (!value.trim()) {
      setDoctors([]);
      setDepartments([]);
      return;
    }

    setSearching(true);
    try {
      const [doctorResult, deptResult] = await Promise.all([
        doctorApi.search(value),
        departmentApi.search(value),
      ]);
      setDoctors(doctorResult);
      setDepartments(deptResult);
    } catch (error) {
      console.error('搜索失败', error);
    } finally {
      setSearching(false);
    }
  };

  const handleSelectDoctor = (id: string) => {
    Taro.navigateTo({ url: `/packageBooking/pages/doctor/detail?id=${id}` });
  };

  const handleSelectDept = (id: string, name: string) => {
    Taro.navigateTo({
      url: `/pages/doctor/index?departmentId=${id}&departmentName=${encodeURIComponent(name)}`,
    });
  };

  return (
    <View className="search-page">
      <View className="search-header">
        <SearchBar
          placeholder="搜索科室/医生"
          autoFocus
          value={keyword}
          onChange={(value) => {
            setKeyword(value);
            handleSearch(value);
          }}
        />
      </View>

      <View className="search-result">
        {!keyword && (
          <View className="tip">输入关键词搜索科室或医生</View>
        )}

        {keyword && departments.length === 0 && doctors.length === 0 && !searching && (
          <Empty description="未找到相关结果" />
        )}

        {departments.length > 0 && (
          <View className="result-section">
            <Text className="section-title">科室</Text>
            {departments.map((dept) => (
              <View
                key={dept.id}
                className="result-item"
                onClick={() => handleSelectDept(dept.id, dept.name)}
              >
                <Text className="item-name">{dept.name}</Text>
                <Text className="arrow">›</Text>
              </View>
            ))}
          </View>
        )}

        {doctors.length > 0 && (
          <View className="result-section">
            <Text className="section-title">医生</Text>
            {doctors.map((doctor) => (
              <View
                key={doctor.id}
                className="result-item doctor-item"
                onClick={() => handleSelectDoctor(doctor.id)}
              >
                <View className="doctor-info">
                  <Text className="item-name">{doctor.name}</Text>
                  <Text className="doctor-title">{doctor.title}</Text>
                </View>
                <Text className="doctor-dept">{doctor.departmentName}</Text>
              </View>
            ))}
          </View>
        )}
      </View>
    </View>
  );
};

export default SearchPage;
