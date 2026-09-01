import { useEffect, useState } from 'react';
import { View, Text, Image } from '@tarojs/components';
import Taro from '@tarojs/taro';
import { useTemplate } from '../contexts/TemplateContext';
import type { NavTab } from '../templates/types';

import homeIcon from '../assets/tabbar/home.png';
import homeActiveIcon from '../assets/tabbar/home-active.png';
import appointmentIcon from '../assets/tabbar/appointment.png';
import appointmentActiveIcon from '../assets/tabbar/appointment-active.png';
import profileIcon from '../assets/tabbar/profile.png';
import profileActiveIcon from '../assets/tabbar/profile-active.png';

const iconMap: Record<string, { normal: string; active: string }> = {
  home: { normal: homeIcon, active: homeActiveIcon },
  appointment: { normal: appointmentIcon, active: appointmentActiveIcon },
  profile: { normal: profileIcon, active: profileActiveIcon },
};

export default function CustomTabBar() {
  const { template } = useTemplate();
  const [selectedIndex, setSelectedIndex] = useState(0);
  const [height, setHeight] = useState(template.navSchema.height || 100);

  useEffect(() => {
    setHeight(template.navSchema.height || 100);
  }, [template.code]);

  const handleTabClick = (tab: NavTab, index: number) => {
    setSelectedIndex(index);
    Taro.switchTab({ url: tab.pagePath });
  };

  return (
    <View style={{
      display: 'flex',
      flexDirection: 'row',
      height: `${height}rpx`,
      backgroundColor: '#fff',
      borderTop: '1rpx solid #E5E7EB',
      paddingBottom: 'env(safe-area-inset-bottom)',
      position: 'fixed',
      bottom: 0,
      left: 0,
      right: 0,
      zIndex: 500,
    }}>
      {template.navSchema.tabs.map((tab, index) => {
        const isActive = selectedIndex === index;
        const icons = iconMap[tab.iconKey] || iconMap['home'];
        return (
          <View
            key={tab.pagePath}
            onClick={() => handleTabClick(tab, index)}
            style={{
              flex: 1,
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '4rpx',
            }}
          >
            <Image
              src={isActive ? icons.active : icons.normal}
              style={{ width: '48rpx', height: '48rpx' }}
            />
            <Text style={{
              fontSize: '22rpx',
              color: isActive ? 'var(--theme-primary, #4D7CB8)' : '#9CA3AF',
            }}>
              {tab.text}
            </Text>
          </View>
        );
      })}
    </View>
  );
}
