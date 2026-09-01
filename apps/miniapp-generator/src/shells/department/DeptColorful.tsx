import { View, Text, ScrollView } from '@tarojs/components';
import Taro, { usePullDownRefresh } from '@tarojs/taro';
import { useState, useEffect } from 'react';
import { departmentApi } from '@hospital/api';
import type { DepartmentTreeNode } from '@hospital/shared';
import { SearchIcon, getDeptIcon } from '../../components/Icons';
import { useThemePrimaryColor, useApplyThemeNavigationBar } from '../../utils/theme';
import { LoadFailedErrorState, DepartmentEmptyState } from '../../components/EmptyState';
import './DeptColorful.less';

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

// 彩色背景色数组（活泼配色）
const colorfulBgColors = [
  '#FFB6C1', // 浅粉
  '#98D8C8', // 薄荷绿
  '#FFE66D', // 奶油黄
  '#B4E1FF', // 天空蓝
  '#DDA0DD', // 梅红
  '#F0E68C', // 卡其
  '#87CEFA', // 淡蓝
  '#FFA07A', // 浅橙
];

// 获取科室背景色（根据名称哈希）
const getDeptBgColor = (name: string): string => {
  let hash = 0;
  for (let i = 0; i < name.length; i++) {
    hash = name.charCodeAt(i) + ((hash << 5) - hash);
  }
  const index = Math.abs(hash) % colorfulBgColors.length;
  return colorfulBgColors[index];
};

/**
 * 科室壳层 -- 彩色图标网格版
 * 无侧边栏，大图标网格布局，彩色背景
 */
export function DeptColorful() {
  useApplyThemeNavigationBar();
  const primaryColor = useThemePrimaryColor();

  const [loading, setLoading] = useState(true);
  const [departments, setDepartments] = useState<DepartmentTreeNode[]>([]);
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

      setDepartments(leaves);
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

  // 加载中或跳转中
  if (loading || redirecting) {
    return (
      <View className="department-page dept-colorful">
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
      <View className="department-page dept-colorful">
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

  if (departments.length === 0) {
    return (
      <View className="department-page dept-colorful">
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
    <View className="department-page dept-colorful">
      <View className="search-bar">
        <View className="search-input" onClick={handleSearch}>
          <View className="search-icon">
            <SearchIcon size={16} color="#9CA3AF" />
          </View>
          <Text className="placeholder">搜索科室/医生</Text>
        </View>
      </View>

      <View className="content">
        <View className="colorful-grid">
          {departments.map(dept => {
            const IconComponent = getDeptIcon(dept.name);
            const bgColor = getDeptBgColor(dept.name);
            return (
              <View
                key={dept.id}
                className="colorful-item"
                style={{ backgroundColor: bgColor }}
                onClick={() => handleSelectDept(dept.id, dept.name)}
              >
                <View className="colorful-icon">
                  <IconComponent size={36} color="#fff" />
                </View>
                <Text className="colorful-name">{dept.name}</Text>
              </View>
            );
          })}
        </View>
      </View>
    </View>
  );
}
