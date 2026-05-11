import { ShopOutlined, DownOutlined, AppstoreOutlined, CheckOutlined } from '@ant-design/icons';
import { useModel, useAccess } from '@umijs/max';
import { Tooltip, Popover, Spin, Empty, Avatar, App, theme } from 'antd';
import { history } from '@umijs/max';
import { useState, useCallback, useEffect, useRef } from 'react';
import { adminApi } from '@hospital/api';
import type { StoreInfo } from '@hospital/api';
import { setStorage, STORAGE_KEYS } from '@hospital/shared';
import styles from './index.less';

const STORE_CACHE_TTL = 5 * 60 * 1000;

export const StoreSwitcher: React.FC = () => {
  const { message, modal } = App.useApp();
  const { initialState } = useModel('@@initialState');
  const { token } = theme.useToken();
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [stores, setStores] = useState<StoreInfo[]>([]);
  const [canSwitchStores, setCanSwitchStores] = useState(false);
  const [switching, setSwitching] = useState(false);
  const [switchingStoreName, setSwitchingStoreName] = useState('');

  const storesCacheRef = useRef<{ stores: StoreInfo[]; canSwitchStores: boolean; timestamp: number } | null>(null);

  const currentUser = initialState?.currentUser;
  const currentStore = initialState?.currentStore;
  const userStores = initialState?.userStores || [];
  const isSuperAdmin = currentUser?.isSuperAdmin || currentUser?.roleCode === 'SUPER_ADMIN';

  const hasMultipleStores = userStores.length > 1;

  const loadStores = useCallback(async () => {
    if (!currentUser?.id) return;

    const cache = storesCacheRef.current;
    if (cache && Date.now() - cache.timestamp < STORE_CACHE_TTL) {
      setStores(cache.stores);
      setCanSwitchStores(cache.canSwitchStores);
      return;
    }

    setLoading(true);
    try {
      const result = await adminApi.getMyStores();
      const fetchedStores = result.stores || [];
      setStores(fetchedStores);
      setCanSwitchStores(result.canSwitchStores);
      storesCacheRef.current = {
        stores: fetchedStores,
        canSwitchStores: result.canSwitchStores,
        timestamp: Date.now(),
      };
    } catch (error) {
      console.error('加载门店列表失败:', error);
    } finally {
      setLoading(false);
    }
  }, [currentUser?.id]);

  useEffect(() => {
    if (open) {
      loadStores();
    }
  }, [open, loadStores]);

  const isOnFormPage = useCallback(() => {
    const { pathname } = history.location;
    return /\/(create|edit)($|\/)/.test(pathname);
  }, []);

  const doSwitchStore = useCallback(async (storeId: string) => {
    const targetStore = stores.find(s => s.id === storeId);
    setSwitching(true);
    setSwitchingStoreName(targetStore?.name || '');
    setOpen(false);

    try {
      const result = await adminApi.switchStore(storeId);
      if (result.currentStore) {
        localStorage.setItem('hospital_current_store', JSON.stringify(result.currentStore));
      }
      storesCacheRef.current = null;

      const { pathname, search, hash } = history.location;
      if (!/\/(create|edit)($|\/)/.test(pathname)) {
        setStorage(STORAGE_KEYS.SWITCH_REDIRECT_PATH, pathname + (search || '') + (hash || ''));
      } else {
        const listPath = pathname.replace(/\/(create|edit)($|\/.*)/, '');
        setStorage(STORAGE_KEYS.SWITCH_REDIRECT_PATH, listPath || '/dashboard');
      }

      window.location.reload();
    } catch (error: any) {
      setSwitching(false);
      setSwitchingStoreName('');
      message.error(error.message || '切换门店失败');
    }
  }, [stores, message]);

  const doSelectAllStores = useCallback(() => {
    setSwitching(true);
    setSwitchingStoreName('全部门店');
    setOpen(false);
    localStorage.removeItem('hospital_current_store');
    storesCacheRef.current = null;

    const { pathname, search, hash } = history.location;
    if (!/\/(create|edit)($|\/)/.test(pathname)) {
      setStorage(STORAGE_KEYS.SWITCH_REDIRECT_PATH, pathname + (search || '') + (hash || ''));
    } else {
      const listPath = pathname.replace(/\/(create|edit)($|\/.*)/, '');
      setStorage(STORAGE_KEYS.SWITCH_REDIRECT_PATH, listPath || '/dashboard');
    }

    window.location.reload();
  }, []);

  const handleSelectAllStores = useCallback(() => {
    if (!currentStore) {
      setOpen(false);
      return;
    }
    if (isOnFormPage()) {
      modal.confirm({
        title: '切换门店',
        content: '切换到「全部门店」将导致当前页面未保存的更改丢失，是否继续？',
        okText: '确定切换',
        cancelText: '取消',
        onOk: doSelectAllStores,
      });
    } else {
      doSelectAllStores();
    }
  }, [currentStore, isOnFormPage, modal, doSelectAllStores]);

  const handleSwitchStore = useCallback((storeId: string) => {
    if (storeId === currentStore?.id) {
      setOpen(false);
      return;
    }
    if (switching) return;

    if (isOnFormPage()) {
      const targetStore = stores.find(s => s.id === storeId);
      modal.confirm({
        title: '切换门店',
        content: `切换到「${targetStore?.name || ''}」将导致当前页面未保存的更改丢失，是否继续？`,
        okText: '确定切换',
        cancelText: '取消',
        onOk: () => doSwitchStore(storeId),
      });
    } else {
      doSwitchStore(storeId);
    }
  }, [currentStore?.id, switching, isOnFormPage, stores, modal, doSwitchStore]);

  // 非超级管理员且没有门店时，不显示任何内容
  if (!isSuperAdmin && !currentStore) {
    return null;
  }

  const showStaticInfo = !hasMultipleStores && !isSuperAdmin;

  const renderCurrentStore = () => {
    if (!currentStore) {
      const label = isSuperAdmin ? '全部门店' : '请选择门店';
      const color = isSuperAdmin ? token.colorPrimary : token.colorTextTertiary;
      const textColor = isSuperAdmin ? token.colorText : token.colorTextTertiary;
      return (
        <>
          {isSuperAdmin ? (
            <AppstoreOutlined style={{ marginRight: 8, fontSize: 16, color }} />
          ) : (
            <ShopOutlined style={{ marginRight: 8, fontSize: 16, color }} />
          )}
          <span className={styles.storeName} style={{ color: textColor }}>{label}</span>
          <DownOutlined className={`${styles.storeDropdownIcon} ${open ? styles.storeDropdownIconOpen : ''}`} />
        </>
      );
    }

    return (
      <>
        {currentStore.logo ? (
          <Avatar src={currentStore.logo} size={24} style={{ marginRight: 8 }} />
        ) : (
          <ShopOutlined style={{ marginRight: 8, fontSize: 16, color: token.colorPrimary }} />
        )}
        <span className={styles.storeName}>{currentStore.name}</span>
        {!showStaticInfo && (
          <DownOutlined className={`${styles.storeDropdownIcon} ${open ? styles.storeDropdownIconOpen : ''}`} />
        )}
      </>
    );
  };

  if (showStaticInfo) {
    return (
      <Tooltip title={currentStore?.name || '未选择门店'}>
        <div className={styles.storeInfo}>
          {renderCurrentStore()}
        </div>
      </Tooltip>
    );
  }

  const content = (
    <div className={styles.storeSwitcherPanel}>
      <div className={styles.storeSwitcherHeader}>
        <span className={styles.headerTitle}>切换门店</span>
      </div>
      <Spin spinning={loading}>
        <div className={styles.storeList}>
          {stores.map((store) => (
            <div
              key={store.id}
              className={`${styles.storeItem} ${currentStore?.id === store.id ? styles.active : ''}`}
              onClick={() => handleSwitchStore(store.id)}
            >
              {store.logo ? (
                <Avatar src={store.logo} size={32} className={styles.storeItemLogo} />
              ) : (
                <Avatar icon={<ShopOutlined />} size={32} className={styles.storeItemLogo} />
              )}
              <span className={styles.storeItemName}>{store.name}</span>
              {currentStore?.id === store.id && <CheckOutlined className={styles.storeItemCheck} />}
            </div>
          ))}
          {stores.length === 0 && !loading && (
            <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无门店" />
          )}
        </div>
      </Spin>
    </div>
  );

  return (
    <>
      <Popover
        content={content}
        trigger="click"
        open={open}
        onOpenChange={setOpen}
        placement="bottomRight"
        overlayClassName={styles.storeSwitcherPopover}
        arrow={{ pointAtCenter: true }}
      >
        <Tooltip title={currentStore?.name || (isSuperAdmin ? '全部门店' : '未选择门店')} open={open ? false : undefined}>
          <div className={styles.storeInfo}>
            {renderCurrentStore()}
          </div>
        </Tooltip>
      </Popover>

      {switching && (
        <div className={styles.storeSwitchingOverlay}>
          <Spin size="large" />
          <div className={styles.switchingText}>
            正在切换到 {switchingStoreName}...
          </div>
        </div>
      )}
    </>
  );
};

export const StoreInfoDisplay = StoreSwitcher;
