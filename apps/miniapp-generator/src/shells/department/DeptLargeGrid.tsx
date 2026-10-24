import { View, Text } from '@tarojs/components';
import Taro from '@tarojs/taro';
import { useState, useEffect } from 'react';
import { departmentApi } from '@hospital/api';
import type { Department } from '@hospital/shared';
import { PageContainer } from '../../components/PageContainer';
import { useTemplate } from '../../contexts/TemplateContext';
import { getDeptIcon as getSharedDeptIcon } from '../../components/Icons';

/** 科室列表壳层 -- 大尺寸 2 列网格
 * 每个科室占半屏宽，图标 80rpx + 文字 40rpx，充足内边距
 */
export function DeptLargeGrid() {
  const { tokens } = useTemplate();
  const [departments, setDepartments] = useState<Department[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadDepartments();
  }, []);

  const loadDepartments = async () => {
    try {
      const data = await departmentApi.getAll();
      setDepartments(data);
    } catch {
      Taro.showToast({ title: '加载科室失败', icon: 'none' });
    } finally {
      setLoading(false);
    }
  };

  const handleDeptClick = (dept: Department) => {
    Taro.navigateTo({
      url: `/pages/doctor/index?departmentId=${dept.id}&departmentName=${encodeURIComponent(dept.name)}`,
    });
  };

  return (
    <PageContainer>
      <View style={{ padding: '32rpx' }}>
        <Text style={{
          fontSize: '48rpx',
          fontWeight: 700,
          color: '#3D2B1F',
          marginBottom: '32rpx',
          display: 'block',
        }}>
          选择科室
        </Text>

        {!loading && departments.length === 0 && (
          <View style={{
            padding: '64rpx',
            backgroundColor: '#FFFFFF',
            borderRadius: '24rpx',
            textAlign: 'center',
          }}>
            <Text style={{ fontSize: '36rpx', color: '#9CA3AF' }}>暂无科室信息</Text>
          </View>
        )}

        <View style={{
          display: 'grid',
          gridTemplateColumns: '1fr 1fr',
          gap: '24rpx',
        }}>
          {departments.map((dept) => (
            <View
              key={dept.id}
              onClick={() => handleDeptClick(dept)}
              aria-label={`选择${dept.name}科室`}
              role="button"
              style={{
                backgroundColor: '#FFFFFF',
                borderRadius: '24rpx',
                padding: '40rpx 24rpx',
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
                minHeight: '200rpx',
                boxShadow: '0 2rpx 12rpx rgba(0,0,0,0.06)',
              }}
            >
              <View style={{ marginBottom: '16rpx', height: '80rpx', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                {(() => {
                  const DeptIcon = getSharedDeptIcon(dept.name);
                  return <DeptIcon size={40} color={tokens.primary} />;
                })()}
              </View>
              <Text style={{
                fontSize: '40rpx',
                fontWeight: 600,
                color: '#3D2B1F',
                textAlign: 'center',
              }}>
                {dept.name}
              </Text>
            </View>
          ))}
        </View>
      </View>
    </PageContainer>
  );
}
