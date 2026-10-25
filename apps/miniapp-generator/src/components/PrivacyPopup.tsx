import { View, Text, Button } from '@tarojs/components';
import Taro from '@tarojs/taro';
import { useTemplate } from '../contexts/TemplateContext';

export interface PrivacyPopupProps {
  visible: boolean;
  /** 用户点击「同意」后回调（组件内部负责写入本地标记） */
  onAgree: () => void;
  /** 机构名，用于弹窗文案；缺省用「本」 */
  orgName?: string;
}

const STORAGE_KEY = 'privacy_agreed_v1';

/** 是否已同意过隐私指引（本地标记） */
export function hasAgreedPrivacy(): boolean {
  try {
    return Taro.getStorageSync(STORAGE_KEY) === '1';
  } catch {
    return false;
  }
}

/**
 * 用户隐私保护提示弹窗 -- 对齐竞品首次使用流程
 * 首次进入时强制弹出；点「同意」记录本地标记，点「拒绝」提示后可退出或继续浏览受限功能
 */
const PrivacyPopup: React.FC<PrivacyPopupProps> = ({ visible, onAgree, orgName }) => {
  const { tokens } = useTemplate();

  if (!visible) return null;

  const handleAgree = () => {
    try {
      Taro.setStorageSync(STORAGE_KEY, '1');
    } catch {
      // 存储失败不阻塞使用
    }
    onAgree();
  };

  const handleReject = () => {
    Taro.showToast({ title: '未同意隐私指引，部分功能不可用', icon: 'none', duration: 2000 });
  };

  return (
    <View style={{
      position: 'fixed',
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
      backgroundColor: 'rgba(0, 0, 0, 0.5)',
      zIndex: 2000,
      display: 'flex',
      alignItems: 'flex-end',
    }}>
      <View style={{
        width: '100%',
        backgroundColor: '#FFFFFF',
        borderTopLeftRadius: '32rpx',
        borderTopRightRadius: '32rpx',
        padding: '48rpx 32rpx calc(env(safe-area-inset-bottom) + 40rpx)',
      }}>
        <Text style={{ fontSize: '40rpx', fontWeight: 700, color: '#3D2B1F', display: 'block', marginBottom: '32rpx' }}>
          用户隐私保护提示
        </Text>
        <Text style={{ fontSize: '32rpx', color: '#4B5563', lineHeight: '52rpx', display: 'block', marginBottom: '16rpx' }}>
          在你使用{orgName || '本'}小程序服务之前，请仔细阅读
          <Text
            style={{ color: tokens.primary }}
            onClick={() => Taro.navigateTo({ url: '/packageOther/pages/agreement/index' }).catch(() => {})}
          >
            《用户隐私保护指引》
          </Text>
        </Text>
        <Text style={{ fontSize: '32rpx', color: '#4B5563', lineHeight: '52rpx', display: 'block', marginBottom: '40rpx' }}>
          如你同意该指引，请点击「同意」开始使用本小程序。
        </Text>
        <View style={{ display: 'flex', gap: '24rpx' }}>
          <Button
            onClick={handleReject}
            style={{
              flex: 1,
              height: '96rpx',
              borderRadius: '9999rpx',
              backgroundColor: '#F3F4F6',
              margin: 0,
              padding: 0,
              border: 'none',
              lineHeight: '96rpx',
            }}
          >
            <Text style={{ fontSize: '36rpx', color: '#4B5563' }}>拒绝</Text>
          </Button>
          <Button
            onClick={handleAgree}
            style={{
              flex: 1,
              height: '96rpx',
              borderRadius: '9999rpx',
              backgroundColor: tokens.primary,
              margin: 0,
              padding: 0,
              border: 'none',
              lineHeight: '96rpx',
            }}
          >
            <Text style={{ fontSize: '36rpx', color: '#FFFFFF', fontWeight: 600 }}>同意</Text>
          </Button>
        </View>
      </View>
    </View>
  );
};

export default PrivacyPopup;
