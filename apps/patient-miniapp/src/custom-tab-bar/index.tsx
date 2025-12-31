import { View, Image, Text } from '@tarojs/components';
import Taro from '@tarojs/taro';
import { useState, useEffect } from 'react';
import './index.less';

// 导入图标资源（让 webpack 正确处理路径）
import homeIcon from '../assets/tabbar/home.png';
import homeActiveIcon from '../assets/tabbar/home-active.png';
import appointmentIcon from '../assets/tabbar/appointment.png';
import appointmentActiveIcon from '../assets/tabbar/appointment-active.png';
import profileIcon from '../assets/tabbar/profile.png';
import profileActiveIcon from '../assets/tabbar/profile-active.png';

// TabBar 配置
const tabBarList = [
  {
    pagePath: '/pages/index/index',
    text: '首页',
    iconPath: homeIcon,
    selectedIconPath: homeActiveIcon,
  },
  {
    pagePath: '/pages/appointment/index',
    text: '预约',
    iconPath: appointmentIcon,
    selectedIconPath: appointmentActiveIcon,
  },
  {
    pagePath: '/pages/profile/index',
    text: '我的',
    iconPath: profileIcon,
    selectedIconPath: profileActiveIcon,
  },
];

export default function CustomTabBar() {
  const [selected, setSelected] = useState(0);

  useEffect(() => {
    // 监听页面显示，更新选中状态
    const updateSelected = () => {
      const pages = Taro.getCurrentPages();
      if (pages.length > 0) {
        const currentPage = pages[pages.length - 1];
        const currentPath = '/' + currentPage.route;
        const index = tabBarList.findIndex((item) => item.pagePath === currentPath);
        if (index !== -1) {
          setSelected(index);
        }
      }
    };

    updateSelected();
  }, []);

  const handleSwitch = (index: number, pagePath: string) => {
    if (index === selected) return;
    
    setSelected(index);
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

