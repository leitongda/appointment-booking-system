import { View, Image, Text } from '@tarojs/components';
import Taro, { useDidShow } from '@tarojs/taro';
import { useState, useEffect } from 'react';
import './index.less';

// TabBar 配置
// 注意：使用相对路径引用图片资源，避免 base64 编码导致图片显示问题
// 路径相对于小程序根目录（dist 目录）
const tabBarList = [
  {
    pagePath: '/pages/index/index',
    text: '首页',
    iconPath: '/assets/tabbar/home.png',
    selectedIconPath: '/assets/tabbar/home-active.png',
  },
  {
    pagePath: '/pages/appointment/index',
    text: '预约',
    iconPath: '/assets/tabbar/appointment.png',
    selectedIconPath: '/assets/tabbar/appointment-active.png',
  },
  {
    pagePath: '/pages/profile/index',
    text: '我的',
    iconPath: '/assets/tabbar/profile.png',
    selectedIconPath: '/assets/tabbar/profile-active.png',
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

export default function CustomTabBar() {
  // 初始化时就根据当前路由设置正确的索引
  const [selected, setSelected] = useState(() => getSelectedIndex());

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

  // 每次页面显示时更新选中状态
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
      {tabBarList.map((item, index) => (
        <View
          key={item.pagePath}
          className="custom-tab-bar__item"
          onClick={() => handleSwitch(index, item.pagePath)}
        >
          <Image
            className="custom-tab-bar__icon"
            src={index === selected ? item.selectedIconPath : item.iconPath}
            mode="aspectFit"
          />
          <Text
            className={`custom-tab-bar__text ${
              index === selected ? 'custom-tab-bar__text--active' : ''
            }`}
          >
            {item.text}
          </Text>
        </View>
      ))}
    </View>
  );
}

