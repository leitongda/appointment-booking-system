import { View, Text } from '@tarojs/components';
import Taro from '@tarojs/taro';
import { useState, useEffect } from 'react';
import { departmentApi } from '@hospital/api';
import type { DepartmentTreeNode } from '@hospital/shared';
import { SearchIcon, getDeptIcon } from '../../components/Icons';
import './index.less';

const DepartmentPage = () => {
  const [loading, setLoading] = useState(true);
  const [departments, setDepartments] = useState<DepartmentTreeNode[]>([]);
  const [activeIndex, setActiveIndex] = useState<number>(0);

  useEffect(() => {
    loadDepartments();
  }, []);

  const loadDepartments = async () => {
    try {
      const data = await departmentApi.getTree();
      setDepartments(data);
    } catch (error) {
      console.error('加载科室失败', error);
    } finally {
      setLoading(false);
    }
  };

  const currentDept = departments[activeIndex];

  const handleSelectDept = (deptId: string, deptName: string) => {
    Taro.navigateTo({
      url: `/pages/doctor/index?departmentId=${deptId}&departmentName=${encodeURIComponent(deptName)}`,
    });
  };

  const handleSearch = () => {
    Taro.navigateTo({ url: '/pages/search/index' });
  };

  if (loading) {
    return (
      <View className="department-page">
        <View className="search-bar">
          <View className="search-input">
            <View className="search-icon">
              <SearchIcon size={16} color="#9CA3AF" />
            </View>
            <Text className="placeholder">搜索科室/医生</Text>
          </View>
        </View>
        <View className="content">
          <View className="loading-state">加载中...</View>
        </View>
      </View>
    );
  }

  return (
    <View className="department-page">
      {/* 搜索栏 */}
      <View className="search-bar">
        <View className="search-input" onClick={handleSearch}>
          <View className="search-icon">
            <SearchIcon size={16} color="#9CA3AF" />
          </View>
          <Text className="placeholder">搜索科室/医生</Text>
        </View>
      </View>

      <View className="content">
        {/* 侧边栏 */}
        <View className="sidebar">
          {departments.map((dept, index) => (
            <View
              key={dept.id}
              className={`sidebar-item ${index === activeIndex ? 'active' : ''}`}
              onClick={() => setActiveIndex(index)}
            >
              <Text>{dept.name}</Text>
            </View>
          ))}
        </View>

        {/* 主内容区 */}
        <View className="main">
          {currentDept?.children?.length ? (
            currentDept.children.map((child) => {
              const IconComponent = getDeptIcon(child.name);
              return (
                <View
                  key={child.id}
                  className="dept-item"
                  onClick={() => handleSelectDept(child.id, child.name)}
                >
                  <View className="dept-content">
                    <View className="dept-icon">
                      <IconComponent size={20} color="#4F46E5" />
                    </View>
                    <View>
                      <Text className="dept-name">{child.name}</Text>
                    </View>
                  </View>
                  <Text className="arrow">›</Text>
                </View>
              );
            })
          ) : (
            <View className="empty-state">
              <Text>暂无子科室</Text>
            </View>
          )}
        </View>
      </View>
    </View>
  );
};

export default DepartmentPage;
