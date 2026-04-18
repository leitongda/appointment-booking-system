import { View, Text, Image } from '@tarojs/components';
import { useState, useEffect } from 'react';
import { storeApi } from '@hospital/api';
import type { Store } from '@hospital/shared';
import {
  HospitalIcon,
  CalendarIcon,
  DoctorIcon,
  RecordIcon,
  TeamIcon
} from '../../../components/Icons';
import { useApplyThemeNavigationBar, useThemePrimaryColor } from '../../../utils/theme';
import { getStoreCode, getStoreName } from '../../../utils/store';
import './index.less';

/**
 * 格式化工作日描述
 * @param workingDays 工作日字符串，如 "1,2,3,4,5,6,7"
 */
const formatWorkingDays = (workingDays?: string): string => {
  if (!workingDays) return '周一至周日';
  
  const days = workingDays.split(',').map(d => parseInt(d, 10)).sort((a, b) => a - b);
  const dayNames = ['', '周一', '周二', '周三', '周四', '周五', '周六', '周日'];
  
  // 检查是否是连续的工作日
  if (days.length === 7) return '周一至周日';
  if (days.length === 5 && days.join(',') === '1,2,3,4,5') return '周一至周五';
  if (days.length === 6 && days.join(',') === '1,2,3,4,5,6') return '周一至周六';
  
  // 其他情况列出所有工作日
  return days.map(d => dayNames[d]).join('、');
};

/**
 * 格式化工作时间描述
 */
const formatWorkingHours = (store: Store): string => {
  const days = formatWorkingDays(store.workingDays);
  
  if (store.openingTime && store.closingTime) {
    // 时间格式如 "08:00:00" 转为 "8:00"
    const formatTime = (t: string) => {
      const [h, m] = t.split(':');
      return `${parseInt(h, 10)}:${m}`;
    };
    return `${days} ${formatTime(store.openingTime)}-${formatTime(store.closingTime)}`;
  }
  
  return `${days} 8:00-20:00`;
};

const AboutPage = () => {
  const primaryColor = useThemePrimaryColor();
  useApplyThemeNavigationBar();
  const [store, setStore] = useState<Store | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadStoreInfo();
  }, []);

  const loadStoreInfo = async () => {
    const storeCode = getStoreCode();
    if (!storeCode) {
      setLoading(false);
      return;
    }

    try {
      const storeData = await storeApi.getByCode(storeCode);
      setStore(storeData);
    } catch (error) {
      console.error('获取门店信息失败', error);
    } finally {
      setLoading(false);
    }
  };

  // 获取显示名称（优先使用API返回的门店名称，其次是构建时配置的名称）
  const displayName = store?.name || getStoreName() || '医院挂号系统';
  
  return (
    <View className="about-page">
      {/* Logo 区域 */}
      <View className="logo-section">
        <View className="logo-wrap">
          {store?.logo ? (
            <Image className="store-logo" src={store.logo} mode="aspectFit" />
          ) : (
            <HospitalIcon size={64} color={primaryColor} />
          )}
        </View>
        <Text className="app-name">{displayName}</Text>
        <Text className="version">版本 1.0.0</Text>
      </View>

      {/* 功能介绍 */}
      <View className="section">
        <Text className="section-title">产品功能</Text>
        <View className="feature-list">
          <View className="feature-item">
            <View className="feature-icon">
              <CalendarIcon size={32} color={primaryColor} />
            </View>
            <View className="feature-content">
              <Text className="feature-title">在线预约</Text>
              <Text className="feature-desc">轻松预约专家门诊，省去排队烦恼</Text>
            </View>
          </View>
          <View className="feature-item">
            <View className="feature-icon">
              <DoctorIcon size={32} color={primaryColor} />
            </View>
            <View className="feature-content">
              <Text className="feature-title">专家查询</Text>
              <Text className="feature-desc">查看医生简介、排班和患者评价</Text>
            </View>
          </View>
          <View className="feature-item">
            <View className="feature-icon">
              <RecordIcon size={32} color={primaryColor} />
            </View>
            <View className="feature-content">
              <Text className="feature-title">就诊记录</Text>
              <Text className="feature-desc">随时查看历史就诊记录和病历</Text>
            </View>
          </View>
          <View className="feature-item">
            <View className="feature-icon">
              <TeamIcon size={32} color={primaryColor} />
            </View>
            <View className="feature-content">
              <Text className="feature-title">就诊人管理</Text>
              <Text className="feature-desc">添加家人信息，为家人预约挂号</Text>
            </View>
          </View>
        </View>
      </View>

      {/* 联系信息 */}
      <View className="section">
        <Text className="section-title">联系我们</Text>
        <View className="contact-list">
          <View className="contact-item">
            <Text className="contact-label">客服电话</Text>
            <Text className="contact-value">{store?.phone || '暂未设置'}</Text>
          </View>
          <View className="contact-item">
            <Text className="contact-label">工作时间</Text>
            <Text className="contact-value">
              {loading ? '加载中...' : (store ? formatWorkingHours(store) : '暂未设置')}
            </Text>
          </View>
          <View className="contact-item">
            <Text className="contact-label">官方邮箱</Text>
            <Text className="contact-value">{store?.email || '暂未设置'}</Text>
          </View>
          {store?.address && (
            <View className="contact-item">
              <Text className="contact-label">门店地址</Text>
              <Text className="contact-value">{store.address}</Text>
            </View>
          )}
        </View>
      </View>

      {/* 版权信息 */}
      <View className="copyright">
        <Text>© 2025 {displayName}</Text>
        <Text>保留所有权利</Text>
      </View>
    </View>
  );
};

export default AboutPage;
