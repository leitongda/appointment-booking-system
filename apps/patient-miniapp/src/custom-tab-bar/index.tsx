import { View, Text } from '@tarojs/components';
import Taro, { useDidShow } from '@tarojs/taro';
import { useState, useEffect } from 'react';
import {
  HomeIcon,
  HomeOutlineIcon,
  AppointmentIcon,
  AppointmentOutlineIcon,
  ProfileIcon,
  ProfileOutlineIcon,
} from '../components/Icons';
import { useThemePrimaryColor } from '../utils/theme';
import './index.less';

// TabBar 配置
const tabBarList = [
  {
    pagePath: '/pages/index/index',
    text: '首页',
    Icon: HomeOutlineIcon,
    ActiveIcon: HomeIcon,
  },
  {
    pagePath: '/pages/appointment/index',
    text: '预约',
    Icon: AppointmentOutlineIcon,
    ActiveIcon: AppointmentIcon,
  },
  {
    pagePath: '/pages/profile/index',
    text: '我的',
    Icon: ProfileOutlineIcon,
    ActiveIcon: ProfileIcon,
  },
];

// 根据当前路由获取选中索引
function getSelectedIndex(): number {
  const pages = Taro.getCurrentPages();
  if (pages.length > 0) {
    const currentPage = pages[pages.length - 1];
    const currentPath = '/' + currentPage.route;
    const index = tabBarList.findIndex((item) => item.pagePath === currentPath);
    if (index !== -1) {
      return index;
    }
  }
  return 0;
}

// 事件名称常量
const TAB_CHANGE_EVENT = 'tabbar:change';

// 未选中颜色
const INACTIVE_COLOR = '#9CA3AF';

export default function CustomTabBar() {
  // 初始化时就根据当前路由设置正确的索引
  const [selected, setSelected] = useState(() => getSelectedIndex());
  const primaryColor = useThemePrimaryColor();

  // 监听来自页面的 TabBar 更新事件
  useEffect(() => {
    const handler = (index: number) => {
      setSelected(index);
    };
    Taro.eventCenter.on(TAB_CHANGE_EVENT, handler);
    return () => {
      Taro.eventCenter.off(TAB_CHANGE_EVENT, handler);
    };
  }, []);

  // 每次页面显示时更新选中状态和主题色
  useDidShow(() => {
    const index = getSelectedIndex();
    setSelected(index);
  });

  const handleSwitch = (index: number, pagePath: string) => {
    if (index === selected) return;

    // 立即更新状态
    setSelected(index);

    // 通知其他组件
    Taro.eventCenter.trigger(TAB_CHANGE_EVENT, index);

    // 跳转页面
    Taro.switchTab({
      url: pagePath,
    });
  };

  return (
    <View className="custom-tab-bar">
      {tabBarList.map((item, index) => {
        const isActive = index === selected;
        const IconComponent = isActive ? item.ActiveIcon : item.Icon;
        const iconColor = isActive ? primaryColor : INACTIVE_COLOR;

        return (
          <View
            key={item.pagePath}
            className="custom-tab-bar__item"
            onClick={() => handleSwitch(index, item.pagePath)}
          >
            <View className="custom-tab-bar__icon-wrap">
              <IconComponent size={28} color={iconColor} />
            </View>
            <Text
              className={`custom-tab-bar__text ${isActive ? 'custom-tab-bar__text--active' : ''
                }`}
              style={isActive ? { color: primaryColor } : undefined}
            >
              {item.text}
            </Text>
          </View>
        );
      })}
    </View>
  );
}
