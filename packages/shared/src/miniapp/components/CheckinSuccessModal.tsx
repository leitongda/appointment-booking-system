import { View, Text } from '@tarojs/components';
import { Popup } from '@nutui/nutui-react-taro';

interface CheckinSuccessModalProps {
  visible: boolean;
  queueNumber: number;
  onClose: () => void;
}

const CheckinSuccessModal = ({ visible, queueNumber, onClose }: CheckinSuccessModalProps) => {
  // 格式化排队号为3位数，补零
  const formattedQueueNumber = String(queueNumber).padStart(3, '0');

  return (
    <Popup
      visible={visible}
      position="center"
      style={{ borderRadius: '24rpx', padding: 0 }}
      closeable={false}
      overlay={true}
      onClose={onClose}
    >
      <View className="checkin-success-modal">
        {/* 成功图标 */}
        <View className="success-icon">
          <Text className="icon">✓</Text>
        </View>

        {/* 标题 */}
        <Text className="modal-title">签到成功</Text>

        {/* 排队号码 - 大号显示 */}
        <View className="queue-number-container">
          <Text className="queue-label">您的排队号码</Text>
          <View className="queue-number">
            <Text className="number">{formattedQueueNumber}</Text>
          </View>
          <Text className="queue-hint">请在候诊区等待叫号</Text>
        </View>

        {/* 温馨提示 */}
        <View className="tips">
          <Text className="tip-text">• 请留意叫号屏幕</Text>
          <Text className="tip-text">• 过号需重新排队</Text>
        </View>

        {/* 关闭按钮 */}
        <View className="close-btn" onClick={onClose}>
          <Text>我知道了</Text>
        </View>
      </View>
    </Popup>
  );
};

export default CheckinSuccessModal;
