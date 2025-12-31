import { View, Text, Image } from '@tarojs/components';
import Taro from '@tarojs/taro';
import { Button, Swipe, Empty } from '@nutui/nutui-react-taro';
import { useState, useEffect } from 'react';
import { favoriteApi } from '@hospital/api';
import type { Favorite } from '@hospital/api';
import { DoctorIcon } from '../../../components/Icons';
import './index.less';

const FavoritePage = () => {
  const [loading, setLoading] = useState(true);
  const [favorites, setFavorites] = useState<Favorite[]>([]);

  useEffect(() => {
    loadFavorites();
  }, []);

  // 页面显示时刷新数据
  Taro.useDidShow(() => {
    loadFavorites();
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
                    <Image src={favorite.target.avatar} mode="aspectFill" />
                  ) : (
                    <DoctorIcon size={32} color="#4F46E5" />
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
                  <Text className="doctor-fee">
                    挂号费：¥{favorite.target?.registrationFee || 0}
                  </Text>
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
    </View>
  );
};

export default FavoritePage;

