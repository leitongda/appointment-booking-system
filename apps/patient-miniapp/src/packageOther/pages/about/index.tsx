import { View, Text } from '@tarojs/components';
import { 
  HospitalIcon, 
  CalendarIcon, 
  DoctorIcon, 
  RecordIcon, 
  TeamIcon 
} from '../../../components/Icons';
import './index.less';

const AboutPage = () => {
  return (
    <View className="about-page">
      {/* Logo 区域 */}
      <View className="logo-section">
        <View className="logo-wrap">
          <HospitalIcon size={64} color="#C41E3A" />
        </View>
        <Text className="app-name">医院挂号系统</Text>
        <Text className="version">版本 1.0.0</Text>
      </View>

      {/* 功能介绍 */}
      <View className="section">
        <Text className="section-title">产品功能</Text>
        <View className="feature-list">
          <View className="feature-item">
            <View className="feature-icon">
              <CalendarIcon size={32} color="#C41E3A" />
            </View>
            <View className="feature-content">
              <Text className="feature-title">在线预约</Text>
              <Text className="feature-desc">轻松预约专家门诊，省去排队烦恼</Text>
            </View>
          </View>
          <View className="feature-item">
            <View className="feature-icon">
              <DoctorIcon size={32} color="#C41E3A" />
            </View>
            <View className="feature-content">
              <Text className="feature-title">专家查询</Text>
              <Text className="feature-desc">查看医生简介、排班和患者评价</Text>
            </View>
          </View>
          <View className="feature-item">
            <View className="feature-icon">
              <RecordIcon size={32} color="#C41E3A" />
            </View>
            <View className="feature-content">
              <Text className="feature-title">就诊记录</Text>
              <Text className="feature-desc">随时查看历史就诊记录和病历</Text>
            </View>
          </View>
          <View className="feature-item">
            <View className="feature-icon">
              <TeamIcon size={32} color="#C41E3A" />
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
            <Text className="contact-value">400-888-8888</Text>
          </View>
          <View className="contact-item">
            <Text className="contact-label">工作时间</Text>
            <Text className="contact-value">周一至周日 8:00-20:00</Text>
          </View>
          <View className="contact-item">
            <Text className="contact-label">官方邮箱</Text>
            <Text className="contact-value">support@hospital.com</Text>
          </View>
        </View>
      </View>

      {/* 版权信息 */}
      <View className="copyright">
        <Text>© 2025 医院挂号系统</Text>
        <Text>保留所有权利</Text>
      </View>
    </View>
  );
};

export default AboutPage;
