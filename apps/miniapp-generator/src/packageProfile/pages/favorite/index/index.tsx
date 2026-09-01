import { View, Text, Image } from '@tarojs/components';
import Taro, { usePullDownRefresh, useReachBottom } from '@tarojs/taro';
import { Button, Swipe, Empty } from '@nutui/nutui-react-taro';
import { useState, useCallback } from 'react';
import { favoriteApi } from '@hospital/api';
import type { Favorite } from '@hospital/api';
import { DoctorIcon } from '../../../../components/Icons';
import { getToken } from '../../../../utils/auth';
import { useProtectedPage } from '../../../../hooks/useProtectedPage';
import { useApplyThemeNavigationBar, useThemePrimaryColor } from '../../../../utils/theme';
import LoginPopup from '../../../../components/LoginPopup';
import { getImageUrl } from '../../../../utils/url';
import './index.less';

const PAGE_SIZE = 20;

const FavoritePage = () => {
  const primaryColor = useThemePrimaryColor();
  useApplyThemeNavigationBar();
  const [loading, setLoading] = useState(true);
  const [favorites, setFavorites] = useState<Favorite[]>([]);
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);

  // 上拉加载更多
  useReachBottom(() => {
    if (!loadingMore && hasMore) {
      loadMoreFavorites();
    }
  });

  // 下拉刷新
  usePullDownRefresh(() => {
    resetAndLoad().finally(() => {
      Taro.stopPullDownRefresh();
    });
  });

  const loadFavorites = useCallback(async () => {
    try {
      const result = await favoriteApi.getList({ targetType: 'doctor', page: 1, pageSize: PAGE_SIZE });
      setFavorites(result.data || []);
      setHasMore((result.data?.length || 0) < (result.total || 0));
    } catch (error) {
      console.error('加载收藏列表失败', error);
    } finally {
      setLoading(false);
    }
  }, []);

  // 重置并加载
  const resetAndLoad = useCallback(async () => {
    setPage(1);
    setHasMore(true);
    return loadFavorites();
  }, [loadFavorites]);

  const {
    showLoginPopup,
    handleLoginSuccess,
    handleLoginClose,
  } = useProtectedPage({
    load: resetAndLoad,
    clear: () => {
      setFavorites([]);
      setPage(1);
      setHasMore(true);
      setLoading(false);
    },
  });

  // 页面显示时刷新数据
  Taro.useDidShow(() => {
    if (getToken()) {
      void resetAndLoad();
    }
  });

  const loadMoreFavorites = async () => {
    if (loadingMore || !hasMore) return;

    setLoadingMore(true);
    try {
      const nextPage = page + 1;
      const result = await favoriteApi.getList({ targetType: 'doctor', page: nextPage, pageSize: PAGE_SIZE });
      const newFavorites = result.data || [];
      setFavorites(prev => [...prev, ...newFavorites]);
      setPage(nextPage);
      setHasMore(newFavorites.length < (result.total || 0) && newFavorites.length > 0);
    } catch (error) {
      console.error('加载更多收藏失败', error);
    } finally {
      setLoadingMore(false);
    }
  };

  const handleRemoveFavorite = async (favorite: Favorite) => {
    try {
      await favoriteApi.remove(favorite.id);
      setFavorites(prev => prev.filter(f => f.id !== favorite.id));
      Taro.showToast({ title: '已取消收藏', icon: 'none' });
    } catch (error: any) {
      Taro.showToast({ title: error.message || '操作失败', icon: 'none' });
    }
  };

  const handleViewDoctor = (doctorId: string) => {
    Taro.navigateTo({
      url: `/packageBooking/pages/doctor/detail?id=${doctorId}`,
    });
  };

  if (loading) {
    return (
      <View className="favorite-page">
        <View className="loading">加载中...</View>
      </View>
    );
  }

  return (
    <View className="favorite-page">
      {favorites.length === 0 ? (
        <View className="empty-wrapper">
          <Empty description="暂无收藏的医生" />
          <Button
            type="primary"
            size="small"
            style={{ marginTop: '16px' }}
            onClick={() => Taro.switchTab({ url: '/pages/index/index' })}
          >
            去首页看看
          </Button>
        </View>
      ) : (
        <View className="favorite-list">
          {favorites.map((favorite) => (
            <Swipe
              key={favorite.id}
              className="favorite-swipe-item"
              rightAction={
                <Button
                  type="danger"
                  onClick={() => handleRemoveFavorite(favorite)}
                >
                  取消收藏
                </Button>
              }
            >
              <View 
                className="doctor-card"
                onClick={() => handleViewDoctor(favorite.targetId)}
              >
                <View className="doctor-avatar">
                  {favorite.target?.avatar ? (
                    <Image src={getImageUrl(favorite.target.avatar)} mode="aspectFill" />
                  ) : (
                    <DoctorIcon size={32} color={primaryColor} />
                  )}
                </View>
                <View className="doctor-info">
                  <View className="doctor-name-row">
                    <Text className="doctor-name">{favorite.target?.name || '未知医生'}</Text>
                    {favorite.target?.title && (
                      <Text className="doctor-title">{favorite.target.title}</Text>
                    )}
                  </View>
                  <Text className="doctor-dept">{favorite.target?.departmentName || ''}</Text>
                </View>
                <View className="book-btn" onClick={(e) => {
                  e.stopPropagation();
                  handleViewDoctor(favorite.targetId);
                }}>
                  <Text>预约</Text>
                </View>
              </View>
            </Swipe>
          ))}
        </View>
      )}

      {/* 底部提示 - 仅在有收藏时显示 */}
      {favorites.length > 0 && (
        <View className="tip-text">
          <Text>左滑可取消收藏</Text>
        </View>
      )}

      {/* 加载状态 */}
      {loadingMore && (
        <View className="loading-more">
          <Text>加载中...</Text>
        </View>
      )}

      {/* 没有更多数据 */}
      {!hasMore && favorites.length > 0 && (
        <View className="no-more">
          <Text>没有更多了</Text>
        </View>
      )}

      {/* 登录弹窗 */}
      <LoginPopup
        visible={showLoginPopup}
        onClose={handleLoginClose}
        onSuccess={handleLoginSuccess}
      />
    </View>
  );
};

export default FavoritePage;
