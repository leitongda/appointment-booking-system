import { View, Text, Image, ScrollView } from '@tarojs/components';
import Taro, { usePullDownRefresh, useReachBottom } from '@tarojs/taro';
import { useState, useEffect } from 'react';
import { doctorApi, favoriteApi } from '@hospital/api';
import type { Doctor } from '@hospital/shared';
import { DoctorIcon, HeartIcon, HeartOutlineIcon } from '../../components/Icons';
import { getToken } from '../../utils/auth';
import { useApplyThemeNavigationBar } from '../../utils/theme';
import { useThemePrimaryColor } from '../../utils/theme';
import { getImageUrl } from '../../utils/url';
import './DoctorShowcase.less';

interface DoctorShowcaseProps {
  departmentId?: string;
  departmentName?: string;
}

// 筛选标签
const filterTags = [
  { id: 'all', label: '全部' },
  { id: 'recommended', label: '推荐' },
  { id: 'senior', label: '资深专家' },
  { id: 'available', label: '可预约' },
];

/**
 * 医生列表壳层 -- 展示版
 * 大卡片展示，强调头像、职称、服务亮点
 */
export function DoctorShowcase(props: DoctorShowcaseProps) {
  useApplyThemeNavigationBar();
  const primaryColor = useThemePrimaryColor();

  const { departmentId, departmentName } = props;

  const [loading, setLoading] = useState(true);
  const [doctors, setDoctors] = useState<Doctor[]>([]);
  const [hasMore, setHasMore] = useState(true);
  const [page, setPage] = useState(1);
  const [activeFilter, setActiveFilter] = useState('all');
  const [favorites, setFavorites] = useState<Set<string>>(new Set());

  useEffect(() => {
    loadDoctors(true);
  }, [departmentId, activeFilter]);

  usePullDownRefresh(() => {
    loadDoctors(true).finally(() => {
      Taro.stopPullDownRefresh();
    });
  });

  useReachBottom(() => {
    if (hasMore && !loading) {
      loadDoctors(false);
    }
  });

  const loadDoctors = async (refresh: boolean) => {
    if (refresh) {
      setLoading(true);
      setPage(1);
    }

    try {
      const currentPage = refresh ? 1 : page;
      const result = await doctorApi.getList({
        departmentId,
        page: currentPage,
        pageSize: 10,
        ...(activeFilter === 'recommended' && { isRecommended: true }),
        ...(activeFilter === 'available' && { hasAvailableSlots: true }),
      });

      const newDoctors = result.data || [];

      if (refresh) {
        setDoctors(newDoctors);
      } else {
        setDoctors(prev => [...prev, ...newDoctors]);
      }

      setHasMore(newDoctors.length >= 10);
      if (!refresh) {
        setPage(prev => prev + 1);
      }
    } catch (error) {
      console.error('[医生列表] 加载失败', error);
      Taro.showToast({ title: '加载失败', icon: 'none' });
    } finally {
      setLoading(false);
    }
  };

  const handleToggleFavorite = async (doctorId: string, e: any) => {
    e.stopPropagation();

    if (!getToken()) {
      Taro.showToast({ title: '请先登录', icon: 'none' });
      return;
    }

    const isFavorited = favorites.has(doctorId);
    try {
      if (isFavorited) {
        await favoriteApi.removeByTarget('doctor', doctorId);
        setFavorites(prev => {
          const next = new Set(prev);
          next.delete(doctorId);
          return next;
        });
        Taro.showToast({ title: '已取消收藏', icon: 'none' });
      } else {
        await favoriteApi.add({ targetType: 'doctor', targetId: doctorId });
        setFavorites(prev => new Set(prev).add(doctorId));
        Taro.showToast({ title: '收藏成功', icon: 'success' });
      }
    } catch (error) {
      Taro.showToast({ title: '操作失败', icon: 'none' });
    }
  };

  const handleDoctorClick = (doctorId: string) => {
    Taro.navigateTo({ url: `/packageBooking/pages/doctor/detail?id=${doctorId}` });
  };

  const handleFilterChange = (filterId: string) => {
    setActiveFilter(filterId);
  };

  return (
    <View className="doctor-showcase-page">
      {/* 部门标题 */}
      {departmentName && (
        <View className="dept-header">
          <Text className="dept-title">{departmentName}</Text>
        </View>
      )}

      {/* 筛选标签 */}
      <ScrollView className="filter-scroll" scrollX enhanced showScrollbar={false}>
        <View className="filter-list">
          {filterTags.map(tag => (
            <View
              key={tag.id}
              className={`filter-item ${activeFilter === tag.id ? 'active' : ''}`}
              onClick={() => handleFilterChange(tag.id)}
              aria-label={`筛选${tag.label}`}
              role="button"
            >
              <Text className="filter-label">{tag.label}</Text>
            </View>
          ))}
        </View>
      </ScrollView>

      {/* 医生列表 */}
      <View className="doctor-list">
        {doctors.length > 0 ? (
          doctors.map(doctor => (
            <View key={doctor.id} className="doctor-card" onClick={() => handleDoctorClick(doctor.id)} aria-label={`查看医生${doctor.name}的详情`} role="button">
              <View className="doctor-main">
                <View className="doctor-avatar-wrap">
                  {doctor.avatar ? (
                    <Image className="doctor-avatar" src={getImageUrl(doctor.avatar)} mode="aspectFill" />
                  ) : (
                    <View className="doctor-avatar-placeholder">
                      <DoctorIcon size={40} color={primaryColor} />
                    </View>
                  )}
                  {doctor.isRecommended && (
                    <View className="recommended-badge">
                      <Text>推荐</Text>
                    </View>
                  )}
                </View>

                <View className="doctor-info">
                  <View className="doctor-header">
                    <Text className="doctor-name">{doctor.name}</Text>
                    {doctor.title && <Text className="doctor-title">{doctor.title}</Text>}
                  </View>

                  <Text className="doctor-dept">{doctor.departmentName}</Text>

                  {doctor.yearsOfExperience && (
                    <View className="doctor-stats">
                      <Text className="stat-item">从业{doctor.yearsOfExperience}年</Text>
                      {/* 高端模板不显示评分 */}
                    </View>
                  )}

                  {doctor.highlights && doctor.highlights.length > 0 && (
                    <View className="doctor-highlights">
                      {doctor.highlights.slice(0, 3).map((highlight, index) => (
                        <Text key={index} className="highlight-tag">
                          {highlight}
                        </Text>
                      ))}
                    </View>
                  )}

                  {doctor.specialty && (
                    <Text className="doctor-specialty">擅长：{doctor.specialty}</Text>
                  )}
                </View>
              </View>

              {/* 收藏按钮 */}
              <View
                className="favorite-btn"
                onClick={(e) => handleToggleFavorite(doctor.id, e)}
                aria-label={favorites.has(doctor.id) ? '取消收藏' : '收藏'}
                role="button"
              >
                {favorites.has(doctor.id) ? (
                  <HeartIcon size={20} color="#EF4444" />
                ) : (
                  <HeartOutlineIcon size={20} color="#94A3B8" />
                )}
              </View>

              {/* 预约状态 */}
              <View className={`doctor-status ${doctor.hasAvailableSlots ? 'available' : 'unavailable'}`}>
                <Text>{doctor.hasAvailableSlots ? '可预约' : '暂无号'}</Text>
              </View>
            </View>
          ))
        ) : !loading ? (
          <View className="empty-state">
            <Text>暂无医生信息</Text>
          </View>
        ) : null}

        {loading && doctors.length === 0 && (
          <View className="loading-state">
            <Text>加载中...</Text>
          </View>
        )}

        {!hasMore && doctors.length > 0 && (
          <View className="no-more">
            <Text>没有更多了</Text>
          </View>
        )}
      </View>
    </View>
  );
}
