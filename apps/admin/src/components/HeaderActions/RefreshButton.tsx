import { ReloadOutlined } from '@ant-design/icons';
import { Tooltip } from 'antd';
import { useState, useCallback } from 'react';
import styles from './index.less';

export const RefreshButton: React.FC = () => {
  const [spinning, setSpinning] = useState(false);

  const handleRefresh = useCallback(() => {
    setSpinning(true);
    setTimeout(() => {
      window.location.reload();
    }, 300);
  }, []);

  return (
    <Tooltip title="刷新页面">
      <div className={styles.actionItem} onClick={handleRefresh}>
        <ReloadOutlined spin={spinning} />
      </div>
    </Tooltip>
  );
};
