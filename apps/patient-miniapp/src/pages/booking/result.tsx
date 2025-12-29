import { View, Text } from '@tarojs/components';
import Taro, { useRouter } from '@tarojs/taro';
import { Button } from '@nutui/nutui-react-taro';
import { CheckIcon } from '../../components/Icons';
import './result.less';

const BookingResultPage = () => {
  const router = useRouter();
  const { appointmentNo } = router.params;

  const handleViewDetail = () => {
    Taro.redirectTo({ url: `/pages/appointment/detail?appointmentNo=${appointmentNo}` });
  };

  const handleBackHome = () => {
    Taro.switchTab({ url: '/pages/index/index' });
  };

  return (
    <View className="result-page">
      {/* 成功图标 */}
      <View className="success-icon">
        <View className="icon-circle">
          <CheckIcon size={48} color="#fff" />
        </View>
        <Text className="success-title">预约成功</Text>
        <Text className="success-desc">预约单号：{appointmentNo}</Text>
      </View>

      {/* 温馨提示 */}
      <View className="notice">
        <Text className="notice-title">温馨提示</Text>
        <View className="notice-item">
          <Text>1. 请于就诊当天携带有效身份证件到院</Text>
        </View>
        <View className="notice-item">
          <Text>2. 就诊当天请提前30分钟到达医院进行签到</Text>
        </View>
        <View className="notice-item">
          <Text>3. 如需取消请提前24小时操作</Text>
        </View>
      </View>

      {/* 操作按钮 */}
      <View className="actions">
        <Button className="btn-secondary" block onClick={handleViewDetail}>
          查看预约详情
        </Button>
        <Button className="btn-primary" type="primary" block onClick={handleBackHome}>
          返回首页
        </Button>
      </View>
    </View>
  );
};

export default BookingResultPage;
