import { View, Text } from '@tarojs/components';
import Taro, { usePullDownRefresh } from '@tarojs/taro';
import { useState, useEffect } from 'react';
import { departmentApi } from '@hospital/api';
import type { DepartmentTreeNode } from '@hospital/shared';
import { SearchIcon, getDeptIcon } from '../../components/Icons';
import { useApplyThemeNavigationBar } from '../../utils/theme';
import { useThemePrimaryColor } from '../../utils/theme';
import { LoadFailedErrorState, DepartmentEmptyState } from '../../components/EmptyState';
import './DeptMinimal.less';

/**
 * 科室壳层 -- 简洁版
 * 1级分类列表，无侧边栏，每行：图标 + 科室名 + 箭头
 */
export function DeptMinimal() {
  useApplyThemeNavigationBar();
  const primaryColor = useThemePrimaryColor();

  const [loading, setLoading] = useState(true);
  const [departments, setDepartments] = useState<DepartmentTreeNode[]>([]);
  const [searchKeyword, setSearchKeyword] = useState('');
  const [error, setError] = useState(false);

  useEffect(() => {
    loadDepartments();
  }, []);

  usePullDownRefresh(() => {
    loadDepartments().finally(() => {
      Taro.stopPullDownRefresh();
    });
  });

  const loadDepartments = async () => {
    setError(false);
    try {
      const data = await departmentApi.getList();
      setDepartments((data.data || []).map((department) => ({ ...department, children: [] })));
    } catch (error) {
      console.error('[科室] 加载失败', error);
      setError(true);
    } finally {
      setLoading(false);
    }
  };

  const handleSelectDept = (dept: DepartmentTreeNode) => {
    Taro.navigateTo({
      url: `/pages/doctor/index?departmentId=${dept.id}&departmentName=${encodeURIComponent(dept.name)}`,
    });
  };

  const handleSearch = () => {
    Taro.navigateTo({ url: '/packageOther/pages/search/index' });
  };

  // 过滤科室
  const filteredDepts = departments.filter(dept =>
    dept.name.toLowerCase().includes(searchKeyword.toLowerCase())
  );

  if (loading) {
    return (
      <View className="department-page">
        <View className="search-bar">
          <View className="search-input" onClick={handleSearch} aria-label="搜索科室" role="button">
            <View className="search-icon">
              <SearchIcon size={16} color="#9CA3AF" />
            </View>
            <Text className="placeholder">搜索科室</Text>
          </View>
        </View>
        <View className="content">
          <View className="loading-state">加载中...</View>
        </View>
      </View>
    );
  }

  if (error) {
    return (
      <View className="department-page">
        <View className="search-bar">
          <View className="search-input" onClick={handleSearch} aria-label="搜索科室" role="button">
            <View className="search-icon">
              <SearchIcon size={16} color="#9CA3AF" />
            </View>
            <Text className="placeholder">搜索科室</Text>
          </View>
        </View>
        <View className="content">
          <LoadFailedErrorState onRetry={loadDepartments} />
        </View>
      </View>
    );
  }

  return (
    <View className="department-page">
      <View className="search-bar">
        <View className="search-input" onClick={handleSearch}>
          <View className="search-icon">
            <SearchIcon size={16} color="#9CA3AF" />
          </View>
          <Text className="placeholder">搜索科室</Text>
        </View>
      </View>

      <View className="content">
        <View className="dept-list">
          {filteredDepts.length > 0 ? (
            filteredDepts.map(dept => {
              const IconComponent = getDeptIcon(dept.name);
              return (
                <View
                  key={dept.id}
                  className="dept-item"
                  onClick={() => handleSelectDept(dept)}
                  aria-label={`选择${dept.name}科室`}
                  role="button"
                >
                  <View className="dept-icon">
                    <IconComponent size={24} color={primaryColor} />
                  </View>
                  <Text className="dept-name">{dept.name}</Text>
                  <Text className="dept-arrow">{'>'}</Text>
                </View>
              );
            })
          ) : (
            <DepartmentEmptyState />
          )}
        </View>
      </View>
    </View>
  );
}
