import { View, Text } from '@tarojs/components';
import Taro, { usePullDownRefresh } from '@tarojs/taro';
import { useState, useEffect } from 'react';
import { departmentApi } from '@hospital/api';
import type { DepartmentTreeNode } from '@hospital/shared';
import { SearchIcon, getDeptIcon } from '../../components/Icons';
import { useTemplate } from '../../contexts/TemplateContext';
import { useThemePrimaryColor, useApplyThemeNavigationBar } from '../../utils/theme';
import { DepartmentEmptyState, LoadFailedErrorState } from '../../components/EmptyState';
import './DeptSidebar.less';

// 获取所有叶子科室
const getLeafDepartments = (departments: DepartmentTreeNode[]): DepartmentTreeNode[] => {
  const leaves: DepartmentTreeNode[] = [];
  const traverse = (nodes: DepartmentTreeNode[]) => {
    nodes.forEach(node => {
      if (!node.children || node.children.length === 0) {
        leaves.push(node);
      } else {
        traverse(node.children);
      }
    });
  };
  traverse(departments);
  return leaves;
};

// 判断是否为单层结构
const isFlatStructure = (departments: DepartmentTreeNode[]): boolean => {
  return departments.every(dept => !dept.children || dept.children.length === 0);
};

/**
 * 科室壳层 -- 侧边栏布局
 * 支持多层（左右分栏）和单层（平铺网格）两种模式
 */
export function DeptSidebar() {
  useApplyThemeNavigationBar();
  const primaryColor = useThemePrimaryColor();
  const { tone } = useTemplate();

  const [loading, setLoading] = useState(true);
  const [departments, setDepartments] = useState<DepartmentTreeNode[]>([]);
  const [activeIndex, setActiveIndex] = useState<number>(0);
  const [isFlat, setIsFlat] = useState(false);
  const [redirecting, setRedirecting] = useState(false);
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
      const data = await departmentApi.getTree();
      const leaves = getLeafDepartments(data);

      // 只有一个叶子科室，直接跳转到医生列表
      if (leaves.length === 1) {
        const leaf = leaves[0];
        setRedirecting(true);
        Taro.redirectTo({
          url: `/pages/doctor/index?departmentId=${leaf.id}&departmentName=${encodeURIComponent(leaf.name)}`,
        });
        return;
      }

      const flat = isFlatStructure(data);
      setIsFlat(flat);
      setDepartments(data);
      setLoading(false);
    } catch (error) {
      console.error('[科室] 加载失败', error);
      setError(true);
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
    Taro.navigateTo({ url: '/packageOther/pages/search/index' });
  };

  // 加载中或跳转中
  if (loading || redirecting) {
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
          <View className="loading-state">{redirecting ? '正在跳转...' : '加载中...'}</View>
        </View>
      </View>
    );
  }

  // 加载失败
  if (error) {
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
          <LoadFailedErrorState onRetry={loadDepartments} />
        </View>
      </View>
    );
  }

  // 无科室数据
  if (departments.length === 0) {
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
          <DepartmentEmptyState />
        </View>
      </View>
    );
  }

  // 单层结构：平铺网格
  if (isFlat) {
    return (
      <View className="department-page">
        <View className="search-bar">
          <View className="search-input" onClick={handleSearch}>
            <View className="search-icon">
              <SearchIcon size={16} color="#9CA3AF" />
            </View>
            <Text className="placeholder">搜索科室/医生</Text>
          </View>
        </View>
        <View className="flat-content">
          <View className="flat-grid">
            {departments.map(dept => {
              const IconComponent = getDeptIcon(dept.name);
              return (
                <View
                  key={dept.id}
                  className="flat-item"
                  onClick={() => handleSelectDept(dept.id, dept.name)}
                >
                  <View className="flat-icon">
                    <IconComponent size={28} color={primaryColor} />
                  </View>
                  <Text className="flat-name">{dept.name}</Text>
                </View>
              );
            })}
          </View>
        </View>
      </View>
    );
  }

  // 多层结构：左右分栏
  return (
    <View className="department-page">
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
            currentDept.children.map(child => {
              const IconComponent = getDeptIcon(child.name);
              return (
                <View
                  key={child.id}
                  className="dept-item"
                  onClick={() => handleSelectDept(child.id, child.name)}
                >
                  <View className="dept-content">
                    <View className="dept-icon">
                      <IconComponent size={20} color={primaryColor} />
                    </View>
                    <View>
                      <Text className="dept-name">{child.name}</Text>
                    </View>
                  </View>
                  <Text className="arrow">></Text>
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
}
