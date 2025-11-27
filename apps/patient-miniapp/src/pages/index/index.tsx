import { View, Text, Swiper, SwiperItem, Image } from '@tarojs/components';
import Taro from '@tarojs/taro';
import { Grid, GridItem } from '@nutui/nutui-react-taro';
import './index.less';

const menus = [
  { icon: '🏥', title: '预约挂号', path: '/pages/department/index' },
  { icon: '📋', title: '我的预约', path: '/pages/appointment/index' },
  { icon: '📝', title: '就诊记录', path: '/pages/records/index' },
  { icon: '👤', title: '个人中心', path: '/pages/profile/index' },
];

const IndexPage = () => {
  const navigateTo = (path: string) => {
    Taro.navigateTo({ url: path });
  };

  return (
    <View className="container">
      <Swiper className="banner" autoplay circular indicatorDots>
        {[1, 2, 3].map((i) => (
          <SwiperItem key={i}>
            <View className="banner-item">Banner {i}</View>
          </SwiperItem>
        ))}
      </Swiper>

      <View className="menu-card">
        <Grid columns={4}>
          {menus.map((menu) => (
            <GridItem key={menu.path} onClick={() => navigateTo(menu.path)}>
              <View className="menu-item">
                <Text className="menu-icon">{menu.icon}</Text>
                <Text className="menu-title">{menu.title}</Text>
              </View>
            </GridItem>
          ))}
        </Grid>
      </View>

      <View className="section">
        <View className="section-title">热门科室</View>
        <Grid columns={4}>
          {['内科', '外科', '儿科', '妇科', '骨科', '眼科', '口腔', '更多'].map((name) => (
            <GridItem key={name} onClick={() => navigateTo('/pages/department/index')}>
              <View className="dept-item">{name}</View>
            </GridItem>
          ))}
        </Grid>
      </View>

      <View className="section">
        <View className="section-title">推荐医生</View>
        {[1, 2, 3].map((i) => (
          <View key={i} className="doctor-card" onClick={() => navigateTo(`/pages/doctor/detail?id=${i}`)}>
            <View className="doctor-avatar" />
            <View className="doctor-info">
              <View className="doctor-name">医生{i} <Text className="doctor-title">主任医师</Text></View>
              <View className="doctor-dept">心内科</View>
              <View className="doctor-spec">擅长：心血管疾病</View>
            </View>
          </View>
        ))}
      </View>
    </View>
  );
};

export default IndexPage;

