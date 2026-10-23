import { useState } from 'react';
import { View, Text, Image } from '@tarojs/components';
import Taro, { useDidShow } from '@tarojs/taro';
import { storeApi, contentApi } from '@hospital/api';
import type { Store } from '@hospital/shared';
import { PageContainer } from '../../components/PageContainer';
import { useTemplate } from '../../contexts/TemplateContext';
import { getStoreId } from '../../utils/store';

/** 机构中心壳层 -- 长辈友好/中医康养
 * 模块：门店照片 -> 名称/联系方式卡 -> 机构介绍（竞品「机构中心/机构简介」同构）
 * 数据：门店信息（名称/电话/地址/简介/经纬度）+ org 位 banner 作门店照片；无后端时展示空态
 */
export function OrgCenter() {
  const { tokens } = useTemplate();
  const [store, setStore] = useState<Store | null>(null);
  const [cover, setCover] = useState<string>('');
  const [loaded, setLoaded] = useState(false);

  useDidShow(() => {
    Taro.eventCenter.trigger('tabbar:change', 1);
    void loadData();
  });

  const loadData = async () => {
    try {
      const storeId = getStoreId();
      const [banners, detail] = await Promise.all([
        contentApi.getActiveBanners('org').catch(() => []),
        storeId ? storeApi.getDetail(storeId).catch(() => null) : Promise.resolve(null),
      ]);
      if (banners.length > 0 && banners[0].imageUrl) {
        setCover(banners[0].imageUrl);
      }
      setStore(detail);
    } catch {
      // 静默失败
    } finally {
      setLoaded(true);
    }
  };

  const handleCall = () => {
    if (!store?.phone) return;
    Taro.makePhoneCall({ phoneNumber: store.phone }).catch(() => {});
  };

  const handleAddress = () => {
    if (!store?.address) return;
    const lat = Number(store.latitude);
    const lng = Number(store.longitude);
    if (Number.isFinite(lat) && Number.isFinite(lng) && lat !== 0 && lng !== 0) {
      Taro.openLocation({ latitude: lat, longitude: lng, name: store.name, address: store.address }).catch(() => {});
      return;
    }
    Taro.setClipboardData({ data: store.address }).catch(() => {});
  };

  return (
    <PageContainer>
      <View style={{ padding: '32rpx' }}>
        {/* 模块 1: 门店照片 */}
        <View style={{
          height: '320rpx',
          borderRadius: '32rpx',
          overflow: 'hidden',
          marginBottom: '32rpx',
          backgroundColor: tokens.primarySoft,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
        }}>
          {cover ? (
            <Image src={cover} mode="aspectFill" style={{ width: '100%', height: '100%' }} />
          ) : (
            <Text style={{ fontSize: '88rpx' }}>{'\ud83c\udfe5'}</Text>
          )}
        </View>

        {/* 模块 2: 名称 + 联系方式卡 */}
        <View style={{
          backgroundColor: '#FFFFFF',
          borderRadius: '32rpx',
          padding: '32rpx',
          marginBottom: '32rpx',
          boxShadow: '0 2rpx 12rpx rgba(95, 143, 116, 0.12)',
        }}>
          <Text style={{
            fontSize: '44rpx',
            fontWeight: 700,
            color: '#22332B',
            display: 'block',
            marginBottom: loaded && !store ? '0' : '20rpx',
          }}>
            {store?.name || (loaded ? '机构名称待配置' : '加载中…')}
          </Text>

          {store?.phone ? (
            <View
              onClick={handleCall}
              aria-label={`致电 ${store.phone}`}
              role="button"
              style={{ display: 'flex', alignItems: 'center', gap: '16rpx', marginTop: '16rpx' }}
            >
              <Text style={{ fontSize: '36rpx' }}>{'\u260e\ufe0f'}</Text>
              <Text style={{ fontSize: '34rpx', color: tokens.primary }}>{store.phone}</Text>
              <Text style={{ fontSize: '30rpx', color: '#9CA3AF' }}>点击拨打</Text>
            </View>
          ) : null}

          {store?.address ? (
            <View
              onClick={handleAddress}
              aria-label={`地址 ${store.address}`}
              role="button"
              style={{ display: 'flex', alignItems: 'flex-start', gap: '16rpx', marginTop: '20rpx' }}
            >
              <Text style={{ fontSize: '36rpx' }}>{'\ud83d\udccd'}</Text>
              <Text style={{ fontSize: '34rpx', color: '#22332B', flex: 1 }}>{store.address}</Text>
            </View>
          ) : null}
        </View>

        {/* 模块 3: 机构介绍 */}
        <View>
          <Text style={{
            fontSize: '40rpx',
            fontWeight: 700,
            color: '#22332B',
            marginBottom: '24rpx',
            display: 'block',
          }}>
            机构介绍
          </Text>
          <View style={{
            backgroundColor: '#FFFFFF',
            borderRadius: '32rpx',
            padding: '32rpx',
          }}>
            <Text style={{ fontSize: '34rpx', color: '#4B5A52', lineHeight: '52rpx' }}>
              {store?.description || '机构介绍准备中，您可先通过电话与我们联系。'}
            </Text>
          </View>
        </View>
      </View>
    </PageContainer>
  );
}
