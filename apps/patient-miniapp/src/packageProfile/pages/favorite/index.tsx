import { View, Text, Image } from '@tarojs/components';
import Taro, { usePullDownRefresh } from '@tarojs/taro';
import { Button, Swipe, Empty } from '@nutui/nutui-react-taro';
import { useState, useEffect } from 'react';
import { favoriteApi } from '@hospital/api';
import type { Favorite } from '@hospital/api';
import { DoctorIcon } from '../../../components/Icons';
import { getToken } from '../../../utils/auth';
import LoginPopup from '../../../components/LoginPopup';
import { getImageUrl } from '../../../utils/url';
import './index.less';

const FavoritePage = () => {
  const [loading, setLoading] = useState(true);
  const [favorites, setFavorites] = useState<Favorite[]>([]);
  const [showLoginPopup, setShowLoginPopup] = useState(false);

  useEffect(() => {
    // 检查登录状态
    const token = getToken();
    if (!token) {
      Taro.showToast({ title: '请先登录', icon: 'none' });
      setShowLoginPopup(true);
      setLoading(false);
      return;
    }
    loadFavorites();
  }, []);

  // 页面显示时刷新数据
  Taro.useDidShow(() => {
    if (getToken()) {
      loadFavorites();
    }
  });

  // 登录成功后加载数据
  const handleLoginSuccess = () => {
    setShowLoginPopup(false);
    loadFavorites();
  };

  // 下拉刷新
  usePullDownRefresh(() => {
    loadFavorites().finally(() => {
      Taro.stopPullDownRefresh();
    });
  });

  const loadFavorites = async () => {
    try {
      const result = await favoriteApi.getList({ targetType: 'doctor', pageSize: 100 });
      setFavorites(result.data || []);
    } catch (error) {
      console.error('加载收藏列表失败', error);
    } finally {
      setLoading(false);
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
              rightAction={
                <Button
                  type="danger"
                  shape="square"
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
                    <DoctorIcon size={32} color="#C41E3A" />
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

      <View className="tip-text">
        <Text>左滑可取消收藏</Text>
      </View>

      {/* 登录弹窗 */}
      <LoginPopup
        visible={showLoginPopup}
        onClose={() => {
          setShowLoginPopup(false);
          if (!getToken()) {
            Taro.navigateBack();
          }
        }}
        onSuccess={handleLoginSuccess}
      />
    </View>
  );
};

export default FavoritePage;

