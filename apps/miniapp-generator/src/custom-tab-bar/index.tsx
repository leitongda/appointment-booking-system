import { useEffect, useState } from 'react';
import { View, Text, Image } from '@tarojs/components';
import Taro from '@tarojs/taro';
import { useTemplate } from '../contexts/TemplateContext';
import type { NavTab } from '../templates/types';

import homeIcon from '../assets/tabbar/home.png';
import homeActiveIcon from '../assets/tabbar/home-active.png';
import appointmentIcon from '../assets/tabbar/appointment.png';
import appointmentActiveIcon from '../assets/tabbar/appointment-active.png';
import orgIcon from '../assets/tabbar/org.png';
import orgActiveIcon from '../assets/tabbar/org-active.png';
import profileIcon from '../assets/tabbar/profile.png';
import profileActiveIcon from '../assets/tabbar/profile-active.png';

const iconMap: Record<string, { normal: string; active: string }> = {
  home: { normal: homeIcon, active: homeActiveIcon },
  appointment: { normal: appointmentIcon, active: appointmentActiveIcon },
  org: { normal: orgIcon, active: orgActiveIcon },
  profile: { normal: profileIcon, active: profileActiveIcon },
};

/** 依据当前页面路由推导选中 tab；不在 navSchema 中（如非本模板的 tab 页）返回 -1（全部置灰） */
function indexFromRoute(tabs: NavTab[]): number {
  try {
    const pages = Taro.getCurrentPages();
    const current = pages[pages.length - 1];
    if (!current) return 0;
    const idx = tabs.findIndex((t) => t.pagePath === `/${current.route}`);
    return idx;
  } catch {
    return 0;
  }
}

export default function CustomTabBar() {
  const { template } = useTemplate();
  const tabs = template.navSchema.tabs;
  const [selectedIndex, setSelectedIndex] = useState(() => indexFromRoute(tabs));
  const [height, setHeight] = useState(template.navSchema.height || 100);

  useEffect(() => {
    setHeight(template.navSchema.height || 100);
  }, [template.code]);

  // 高亮跟随页面：各 tab 页 useDidShow 时触发 tabbar:change；挂载时按当前路由兜底校准。
  // 微信自定义 tabBar 每个 tab 页持有独立实例，仅靠点击态无法跨页保持高亮。
  useEffect(() => {
    setSelectedIndex(indexFromRoute(tabs));
    const handler = (index: number) => setSelectedIndex(index);
    Taro.eventCenter.on('tabbar:change', handler);
    return () => {
      Taro.eventCenter.off('tabbar:change', handler);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
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
      {tabs.map((tab, index) => {
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
