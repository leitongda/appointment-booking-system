import { View, Text } from '@tarojs/components';
import Taro from '@tarojs/taro';
import { SideBar, SideBarItem } from '@nutui/nutui-react-taro';
import { useState, useEffect } from 'react';
import { departmentApi } from '@hospital/api';
import type { DepartmentTreeNode } from '@hospital/shared';
import './index.less';

const DepartmentPage = () => {
  const [loading, setLoading] = useState(true);
  const [departments, setDepartments] = useState<DepartmentTreeNode[]>([]);
  const [activeKey, setActiveKey] = useState<string>('0');

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

  const currentDept = departments[Number(activeKey)];

  const handleSelectDept = (deptId: string, deptName: string) => {
    Taro.navigateTo({
      url: `/pages/doctor/index?departmentId=${deptId}&departmentName=${encodeURIComponent(deptName)}`,
    });
  };

  return (
    <View className="department-page">
      <View className="search-bar">
        <View className="search-input" onClick={() => Taro.navigateTo({ url: '/pages/search/index' })}>
          <Text className="placeholder">搜索科室/医生</Text>
        </View>
      </View>

      <View className="content">
        <View className="sidebar">
          <SideBar
            value={activeKey}
            onChange={(value) => setActiveKey(value as string)}
          >
            {departments.map((dept, index) => (
              <SideBarItem key={dept.id} title={dept.name} value={String(index)} />
            ))}
          </SideBar>
        </View>

        <View className="main">
          {currentDept?.children?.map((child) => (
            <View
              key={child.id}
              className="dept-item"
              onClick={() => handleSelectDept(child.id, child.name)}
            >
              <Text className="dept-name">{child.name}</Text>
              <Text className="arrow">›</Text>
            </View>
          ))}
        </View>
      </View>
    </View>
  );
};

export default DepartmentPage;

