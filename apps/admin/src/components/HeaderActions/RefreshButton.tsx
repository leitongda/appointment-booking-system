import { ReloadOutlined } from '@ant-design/icons';
import { Tooltip } from 'antd';
import { useState, useCallback } from 'react';
import { useModel } from '@umijs/max';
import styles from './index.less';

export const RefreshButton: React.FC = () => {
  const [spinning, setSpinning] = useState(false);
  const { refresh } = useModel('@@initialState');

  const handleRefresh = useCallback(() => {
    setSpinning(true);
    refresh?.().finally(() => {
      setSpinning(false);
    });
  }, [refresh]);

  return (
    <Tooltip title="刷新页面">
      <div className={styles.actionItem} onClick={handleRefresh}>
        <ReloadOutlined spin={spinning} />
      </div>
    </Tooltip>
  );
};
