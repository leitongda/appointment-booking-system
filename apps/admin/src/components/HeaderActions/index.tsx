import { Space } from 'antd';
import TenantSwitcher from '@/components/TenantSwitcher';
import { StoreSwitcher } from './StoreSwitcher';
import { StoreQuickActions } from './StoreQuickActions';
import { NotificationButton } from './NotificationButton';
import { FullscreenButton } from './FullscreenButton';
import { RefreshButton } from './RefreshButton';
import styles from './index.less';

export const HeaderActions: React.FC = () => {
  return (
    <Space className={styles.headerActions} size={4}>
      <TenantSwitcher />
      <StoreSwitcher />
      <StoreQuickActions />
      <RefreshButton />
      <NotificationButton />
      <FullscreenButton />
    </Space>
  );
};

export default HeaderActions;

export { StoreSwitcher };
export { StoreQuickActions };
export { NotificationButton };
export { FullscreenButton };
export { RefreshButton };
export type { Message } from './types';
