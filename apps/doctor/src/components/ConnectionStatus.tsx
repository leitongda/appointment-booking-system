import { Tag, Alert, Tooltip, Space } from 'antd';
import {
  WifiOutlined,
  DisconnectOutlined,
  CheckCircleOutlined,
  LoadingOutlined,
  CloseCircleOutlined,
  ReloadOutlined,
} from '@ant-design/icons';
import { ConnectionStatus } from '@/hooks';

interface ConnectionTagProps {
  status: ConnectionStatus;
  onReconnect?: () => void;
}

/** 小型连接状态 Tag，用于 PageContainer extra 区域 */
export const ConnectionTag: React.FC<ConnectionTagProps> = ({ status, onReconnect }) => {
  if (status === ConnectionStatus.CONNECTED) {
    return (
      <Tooltip title="实时连接正常">
        <Tag color="success" icon={<CheckCircleOutlined />} role="status" aria-live="polite">
          实时
        </Tag>
      </Tooltip>
    );
  }
  if (status === ConnectionStatus.CONNECTING || status === ConnectionStatus.RECONNECTING) {
    return (
      <Tooltip title="正在连接...">
        <Tag color="processing" icon={<LoadingOutlined />} role="status" aria-live="polite">
          连接中
        </Tag>
      </Tooltip>
    );
  }
  return (
    <Tooltip title="实时连接已断开，点击重连">
      <Tag
        color="error"
        icon={<CloseCircleOutlined />}
        style={{ cursor: 'pointer' }}
        onClick={onReconnect}
        role="status"
        aria-live="assertive"
      >
        离线
      </Tag>
    </Tooltip>
  );
};

interface ConnectionBannerProps {
  status: ConnectionStatus;
  onReconnect?: () => void;
}

/** 断连提示 Banner，在 WebSocket 连接断开或重连失败时显示 */
export const ConnectionBanner: React.FC<ConnectionBannerProps> = ({ status, onReconnect }) => {
  if (status === ConnectionStatus.CONNECTED || status === ConnectionStatus.CONNECTING) {
    return null;
  }

  const isReconnecting = status === ConnectionStatus.RECONNECTING;

  return (
    <Alert
      type={isReconnecting ? 'warning' : 'error'}
      showIcon
      banner
      message={
        <Space>
          <span>
            {isReconnecting
              ? '实时连接已断开，正在尝试重新连接...'
              : '实时连接已断开，部分功能可能无法及时更新'}
          </span>
          {!isReconnecting && onReconnect && (
            <a onClick={onReconnect}>
              <ReloadOutlined /> 立即重连
            </a>
          )}
        </Space>
      }
      style={{ marginBottom: 16 }}
    />
  );
};
