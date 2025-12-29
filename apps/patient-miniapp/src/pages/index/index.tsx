import { View, Text, Swiper, SwiperItem } from '@tarojs/components';
import Taro from '@tarojs/taro';
import './index.less';

// 功能菜单配置
const menus = [
  { icon: '🏥', title: '预约挂号', path: '/pages/department/index' },
  { icon: '📋', title: '我的预约', path: '/pages/appointment/index' },
  { icon: '📝', title: '就诊记录', path: '/pages/records/index' },
  { icon: '👤', title: '个人中心', path: '/pages/profile/index' },
];

// 科室图标映射
const deptIcons: Record<string, string> = {
  '内科': '🫀',
  '外科': '🔪',
  '儿科': '👶',
  '妇科': '👩',
  '骨科': '🦴',
  '眼科': '👁️',
  '口腔': '🦷',
  '更多': '➕',
};

// 热门科室
const hotDepts = ['内科', '外科', '儿科', '妇科', '骨科', '眼科', '口腔', '更多'];

// 推荐医生模拟数据
const doctors = [
  { id: '1', name: '张医生', title: '主任医师', dept: '心内科', spec: '擅长：心血管疾病、高血压、冠心病' },
  { id: '2', name: '李医生', title: '副主任医师', dept: '神经内科', spec: '擅长：头痛、失眠、神经系统疾病' },
  { id: '3', name: '王医生', title: '主治医师', dept: '消化内科', spec: '擅长：胃肠疾病、肝胆疾病' },
];

// Banner 数据
const banners = [
  { id: 1, title: '智慧医疗', subtitle: '便捷预约，高效就医' },
  { id: 2, title: '专家团队', subtitle: '权威专家，精准诊疗' },
  { id: 3, title: '优质服务', subtitle: '以患者为中心，提供贴心服务' },
];

const IndexPage = () => {
  const navigateTo = (path: string) => {
    if (path === '/pages/profile/index') {
      Taro.switchTab({ url: path });
    } else {
      Taro.navigateTo({ url: path });
    }
  };

  return (
    <View className="container">
      {/* Banner 轮播 */}
      <Swiper className="banner" autoplay circular indicatorDots indicatorActiveColor="#fff">
        {banners.map((banner) => (
          <SwiperItem key={banner.id}>
            <View className="banner-item">
              <View className="banner-content">
                <Text className="banner-title">{banner.title}</Text>
                <Text className="banner-subtitle">{banner.subtitle}</Text>
              </View>
            </View>
          </SwiperItem>
        ))}
      </Swiper>

      {/* 功能菜单 */}
      <View className="menu-card">
        <View className="dept-grid">
          {menus.map((menu) => (
            <View key={menu.path} className="menu-item" onClick={() => navigateTo(menu.path)}>
              <View className="menu-icon-wrap">
                <Text className="menu-icon">{menu.icon}</Text>
              </View>
              <Text className="menu-title">{menu.title}</Text>
            </View>
          ))}
        </View>
      </View>

      {/* 快捷入口 */}
      <View className="quick-entry">
        <View className="quick-card" onClick={() => navigateTo('/pages/department/index')}>
          <Text className="quick-icon">⚡</Text>
          <Text className="quick-title">快速挂号</Text>
          <Text className="quick-desc">一键预约，省时省力</Text>
        </View>
        <View className="quick-card" onClick={() => navigateTo('/pages/search/index')}>
          <Text className="quick-icon">🔍</Text>
          <Text className="quick-title">找医生</Text>
          <Text className="quick-desc">搜索专家，精准就医</Text>
        </View>
      </View>

      {/* 热门科室 */}
      <View className="section">
        <View className="section-header">
          <Text className="section-title">热门科室</Text>
          <Text className="section-more" onClick={() => navigateTo('/pages/department/index')}>
            全部
          </Text>
        </View>
        <View className="dept-grid">
          {hotDepts.map((name) => (
            <View
              key={name}
              className="dept-item"
              onClick={() => navigateTo('/pages/department/index')}
            >
              <View className="dept-icon-wrap">
                <Text>{deptIcons[name] || '🏥'}</Text>
              </View>
              <Text className="dept-name">{name}</Text>
            </View>
          ))}
        </View>
      </View>

      {/* 推荐医生 */}
      <View className="section">
        <View className="section-header">
          <Text className="section-title">推荐医生</Text>
          <Text className="section-more" onClick={() => navigateTo('/pages/doctor/index')}>
            更多
          </Text>
        </View>
        <View className="doctor-list">
          {doctors.map((doctor) => (
            <View
              key={doctor.id}
              className="doctor-card"
              onClick={() => navigateTo(`/pages/doctor/detail?id=${doctor.id}`)}
            >
              <View className="doctor-avatar">
                <Text>👨‍⚕️</Text>
              </View>
              <View className="doctor-info">
                <View className="doctor-header">
                  <Text className="doctor-name">{doctor.name}</Text>
                  <Text className="doctor-title">{doctor.title}</Text>
                </View>
                <Text className="doctor-dept">{doctor.dept}</Text>
                <Text className="doctor-spec">{doctor.spec}</Text>
              </View>
            </View>
          ))}
        </View>
      </View>
    </View>
  );
};

export default IndexPage;
