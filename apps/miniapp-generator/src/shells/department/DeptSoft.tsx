import { View, Text } from '@tarojs/components';
import Taro, { usePullDownRefresh } from '@tarojs/taro';
import { useState, useEffect } from 'react';
import { departmentApi } from '@hospital/api';
import type { DepartmentTreeNode } from '@hospital/shared';
import { SearchIcon, getDeptIcon } from '../../components/Icons';
import { useTemplate } from '../../contexts/TemplateContext';
import { useThemePrimaryColor, useApplyThemeNavigationBar } from '../../utils/theme';
import { LoadFailedErrorState, DepartmentEmptyState } from '../../components/EmptyState';
import './DeptSoft.less';

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

const isFlatStructure = (departments: DepartmentTreeNode[]): boolean => {
  return departments.every(dept => !dept.children || dept.children.length === 0);
};

export function DeptSoft() {
  useApplyThemeNavigationBar();
  const primaryColor = useThemePrimaryColor();

  const [loading, setLoading] = useState(true);
  const [departments, setDepartments] = useState<DepartmentTreeNode[]>([]);
  const [flatDepartments, setFlatDepartments] = useState<DepartmentTreeNode[]>([]);
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

      if (leaves.length === 1) {
        const leaf = leaves[0];
        setRedirecting(true);
        Taro.redirectTo({
          url: `/pages/doctor/index?departmentId=${leaf.id}&departmentName=${encodeURIComponent(leaf.name)}`,
        });
        return;
      }

      const flat = isFlatStructure(data);
      if (flat) {
        setFlatDepartments(data);
      } else {
        setFlatDepartments(leaves);
      }
      setDepartments(data);
    } catch (error) {
      console.error('[科室] 加载失败', error);
      setError(true);
    } finally {
      setLoading(false);
    }
  };

  const handleSelectDept = (deptId: string, deptName: string) => {
    Taro.navigateTo({
      url: `/pages/doctor/index?departmentId=${deptId}&departmentName=${encodeURIComponent(deptName)}`,
    });
  };

  const handleSearch = () => {
    Taro.navigateTo({ url: '/packageOther/pages/search/index' });
  };

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

  if (flatDepartments.length === 0) {
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

  return (
    <View className="department-page">
      <View className="search-bar">
        <View className="search-input" onClick={handleSearch} aria-label="搜索科室或医生" role="button">
          <View className="search-icon">
            <SearchIcon size={16} color="#9CA3AF" />
          </View>
          <Text className="placeholder">搜索科室/医生</Text>
        </View>
      </View>

      <View className="content">
        <View className="dept-grid">
          {flatDepartments.map(dept => {
            const IconComponent = getDeptIcon(dept.name);
            return (
              <View
                key={dept.id}
                className="dept-card"
                onClick={() => handleSelectDept(dept.id, dept.name)}
                aria-label={`选择${dept.name}科室`}
                role="button"
              >
                <View className="dept-icon">
                  <IconComponent size={24} color={primaryColor} />
                </View>
                <View className="dept-info">
                  <Text className="dept-name">{dept.name}</Text>
                  {dept.description && (
                    <Text className="dept-desc">{dept.description}</Text>
                  )}
                </View>
              </View>
            );
          })}
        </View>
      </View>
    </View>
  );
}
