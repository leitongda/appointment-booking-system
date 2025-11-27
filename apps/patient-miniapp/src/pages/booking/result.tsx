import { View, Text } from '@tarojs/components';
import Taro, { useRouter } from '@tarojs/taro';
import { Button, Result } from '@nutui/nutui-react-taro';
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
      <Result
        status="success"
        title="预约成功"
        description={`预约单号：${appointmentNo}`}
      />

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

      <View className="actions">
        <Button block onClick={handleViewDetail}>
          查看预约详情
        </Button>
        <Button type="primary" block onClick={handleBackHome}>
          返回首页
        </Button>
      </View>
    </View>
  );
};

export default BookingResultPage;

