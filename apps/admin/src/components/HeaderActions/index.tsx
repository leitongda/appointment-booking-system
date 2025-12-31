import {
  FullscreenOutlined,
  FullscreenExitOutlined,
  BellOutlined,
  ReloadOutlined,
  CheckOutlined,
  ShopOutlined,
  DownOutlined,
  AppstoreOutlined,
  ColumnWidthOutlined,
} from '@ant-design/icons';
import { history, useModel } from '@umijs/max';
import { Badge, Tooltip, Popover, List, Empty, Spin, Button, Typography, Space, App, Avatar, Tag, Dropdown } from 'antd';
import type { MenuProps } from 'antd';
import { getSpacingMode, setSpacingMode, applySpacingCSSVariables, SPACING_LABELS } from '@/utils/spacing';
import type { SpacingMode } from '@/utils/spacing';
import React, { useState, useEffect, useCallback } from 'react';
import { messageApi, adminApi } from '@hospital/api';
import type { StoreInfo } from '@hospital/api';
import dayjs from 'dayjs';
import relativeTime from 'dayjs/plugin/relativeTime';
import 'dayjs/locale/zh-cn';
import styles from './index.less';

dayjs.extend(relativeTime);
dayjs.locale('zh-cn');

const { Text } = Typography;

// 门店切换器组件
export const StoreSwitcher: React.FC = () => {
  const { message } = App.useApp();
  const { initialState, setInitialState } = useModel('@@initialState');
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [stores, setStores] = useState<StoreInfo[]>([]);
  const [canViewAllStores, setCanViewAllStores] = useState(false);
  
  const currentUser = initialState?.currentUser;
  const currentStore = initialState?.currentStore;
  const isSuperAdmin = currentUser?.isSuperAdmin || currentUser?.roleCode === 'SUPER_ADMIN';

  // 加载门店列表
  const loadStores = useCallback(async () => {
    if (!currentUser?.id) return;
    setLoading(true);
    try {
      const result = await adminApi.getMyStores();
      setStores(result.stores || []);
      setCanViewAllStores(result.canViewAllStores);
    } catch (error) {
      console.error('加载门店列表失败:', error);
    } finally {
      setLoading(false);
    }
  }, [currentUser?.id]);

  // 打开时加载门店列表
  useEffect(() => {
    if (open) {
      loadStores();
    }
  }, [open, loadStores]);

  // 切换门店
  const handleSwitchStore = async (storeId: string | null) => {
    try {
      if (storeId === null) {
        // 切换到"全部门店"模式
        localStorage.removeItem('currentStore');
        setInitialState((prev) => ({
          ...prev,
          currentStore: undefined,
          isAggregateMode: true,
        }));
        message.success('已切换到全部门店模式');
      } else {
        const result = await adminApi.switchStore(storeId);
        if (result.currentStore) {
          localStorage.setItem('currentStore', JSON.stringify(result.currentStore));
          setInitialState((prev) => ({
            ...prev,
            currentStore: result.currentStore,
            isAggregateMode: false,
          }));
          message.success(`已切换到 ${result.currentStore.name}`);
        }
      }
      setOpen(false);
      // 刷新页面数据
      window.location.reload();
    } catch (error: any) {
      message.error(error.message || '切换门店失败');
    }
  };

  // 超级管理员或只有一个门店的用户：显示静态信息
  const showStaticInfo = !canViewAllStores && stores.length <= 1;

  // 渲染当前门店信息
  const renderCurrentStore = () => {
    if (isSuperAdmin && !currentStore) {
      return (
        <Tag color="purple" style={{ margin: 0 }}>
          <ShopOutlined style={{ marginRight: 4 }} />
          全局管理
        </Tag>
      );
    }

    if (!currentStore) {
      return (
        <Tag color="geekblue" style={{ margin: 0 }}>
          <AppstoreOutlined style={{ marginRight: 4 }} />
          全部门店
        </Tag>
      );
    }

    return (
      <>
        {currentStore.logo ? (
          <Avatar src={currentStore.logo} size={24} style={{ marginRight: 8 }} />
        ) : (
          <ShopOutlined style={{ marginRight: 8, fontSize: 16, color: '#1890ff' }} />
        )}
        <span className={styles.storeName}>{currentStore.name}</span>
        {!showStaticInfo && <DownOutlined className={styles.storeDropdownIcon} />}
      </>
    );
  };

  // 静态显示（不可切换）
  if (showStaticInfo) {
    return (
      <Tooltip title={isSuperAdmin ? "超级管理员 - 可管理所有门店" : currentStore?.name}>
        <div className={styles.storeInfo}>
          {renderCurrentStore()}
        </div>
      </Tooltip>
    );
  }

  // 门店切换面板
  const content = (
    <div className={styles.storeSwitcherPanel}>
      <div className={styles.storeSwitcherHeader}>
        <span className={styles.headerTitle}>切换门店</span>
      </div>
      <Spin spinning={loading}>
        <div className={styles.storeList}>
          {/* 全部门店选项（仅多门店用户可见） */}
          {canViewAllStores && (
            <div
              className={`${styles.storeItem} ${styles.allStoresItem} ${!currentStore ? styles.active : ''}`}
              onClick={() => handleSwitchStore(null)}
            >
              <AppstoreOutlined className={styles.allStoresIcon} />
              <span className={styles.storeItemName}>全部门店</span>
              {!currentStore && <CheckOutlined className={styles.storeItemCheck} />}
            </div>
          )}
          {/* 门店列表 */}
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
    <Popover
      content={content}
      trigger="click"
      open={open}
      onOpenChange={setOpen}
      placement="bottomRight"
      overlayClassName={styles.storeSwitcherPopover}
      arrow={{ pointAtCenter: true }}
    >
      <div className={styles.storeInfo}>
        {renderCurrentStore()}
      </div>
    </Popover>
  );
};

// 保留旧的组件名作为别名
export const StoreInfoDisplay = StoreSwitcher;

// 全屏按钮组件
export const FullscreenButton: React.FC = () => {
  const [isFullscreen, setIsFullscreen] = useState(false);

  useEffect(() => {
    const handleFullscreenChange = () => {
      setIsFullscreen(!!document.fullscreenElement);
    };

    document.addEventListener('fullscreenchange', handleFullscreenChange);
    return () => {
      document.removeEventListener('fullscreenchange', handleFullscreenChange);
    };
  }, []);

  const toggleFullscreen = useCallback(async () => {
    try {
      if (!document.fullscreenElement) {
        await document.documentElement.requestFullscreen();
      } else {
        await document.exitFullscreen();
      }
    } catch (error) {
      console.error('全屏切换失败:', error);
    }
  }, []);

  return (
    <Tooltip title={isFullscreen ? '退出全屏' : '全屏'}>
      <div className={styles.actionItem} onClick={toggleFullscreen}>
        {isFullscreen ? <FullscreenExitOutlined /> : <FullscreenOutlined />}
      </div>
    </Tooltip>
  );
};

// 刷新按钮组件
export const RefreshButton: React.FC = () => {
  const [spinning, setSpinning] = useState(false);

  const handleRefresh = useCallback(() => {
    setSpinning(true);
    // 给一个小延迟来展示动画效果
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

// 消息通知组件
interface Message {
  id: string;
  title: string;
  content?: string;
  message_type: string;
  is_read: number;
  created_at: string;
}

export const NotificationButton: React.FC = () => {
  const { message } = App.useApp();
  const { initialState } = useModel('@@initialState');
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [unreadCount, setUnreadCount] = useState(0);
  const [messages, setMessages] = useState<Message[]>([]);

  const currentUser = initialState?.currentUser;

  // 获取未读消息数量
  const fetchUnreadCount = useCallback(async () => {
    if (!currentUser?.id) return;
    try {
      const res = await messageApi.getUnreadCount(currentUser.id, 'admin');
      setUnreadCount(res?.total || 0);
    } catch (error) {
      console.error('获取未读消息数量失败:', error);
    }
  }, [currentUser?.id]);

  // 获取消息列表
  const fetchMessages = useCallback(async () => {
    if (!currentUser?.id) return;
    setLoading(true);
    try {
      const res = await messageApi.getList({
        userId: currentUser.id,
        userType: 'admin',
        page: 1,
        pageSize: 5,
      });
      setMessages(res?.items || []);
    } catch (error) {
      console.error('获取消息列表失败:', error);
    } finally {
      setLoading(false);
    }
  }, [currentUser?.id]);

  // 初始化时获取未读数量
  useEffect(() => {
    fetchUnreadCount();
    // 每分钟刷新一次未读数量
    const timer = setInterval(fetchUnreadCount, 60000);
    return () => clearInterval(timer);
  }, [fetchUnreadCount]);

  // 打开弹窗时获取消息列表
  useEffect(() => {
    if (open) {
      fetchMessages();
    }
  }, [open, fetchMessages]);

  // 标记消息已读
  const handleMarkAsRead = useCallback(async (messageId: string) => {
    if (!currentUser?.id) return;
    try {
      await messageApi.markAsRead(messageId, currentUser.id);
      fetchMessages();
      fetchUnreadCount();
    } catch (error) {
      console.error('标记已读失败:', error);
    }
  }, [currentUser?.id, fetchMessages, fetchUnreadCount]);

  // 标记全部已读
  const handleMarkAllAsRead = useCallback(async () => {
    if (!currentUser?.id) return;
    try {
      await messageApi.markAllAsRead(currentUser.id, 'admin');
      message.success('已全部标记为已读');
      fetchMessages();
      fetchUnreadCount();
    } catch (error) {
      console.error('标记全部已读失败:', error);
    }
  }, [currentUser?.id, fetchMessages, fetchUnreadCount, message]);

  // 查看全部消息
  const handleViewAll = useCallback(() => {
    setOpen(false);
    history.push('/message');
  }, []);

  // 消息类型映射
  const messageTypeMap: Record<string, { color: string; text: string }> = {
    system: { color: '#1890ff', text: '系统' },
    appointment: { color: '#52c41a', text: '预约' },
    notification: { color: '#faad14', text: '通知' },
    reminder: { color: '#eb2f96', text: '提醒' },
  };

  const content = (
    <div className={styles.notificationPanel}>
      <div className={styles.panelHeader}>
        <span className={styles.panelTitle}>消息通知</span>
        {unreadCount > 0 && (
          <Button 
            type="link" 
            size="small" 
            icon={<CheckOutlined />}
            onClick={handleMarkAllAsRead}
          >
            全部已读
          </Button>
        )}
      </div>
      <Spin spinning={loading}>
        {messages.length > 0 ? (
          <List
            className={styles.messageList}
            dataSource={messages}
            renderItem={(item) => (
              <List.Item
                className={`${styles.messageItem} ${item.is_read ? '' : styles.unread}`}
                onClick={() => {
                  if (!item.is_read) {
                    handleMarkAsRead(item.id);
                  }
                }}
              >
                <div className={styles.messageContent}>
                  <div className={styles.messageHeader}>
                    <Badge 
                      color={messageTypeMap[item.message_type]?.color || '#999'} 
                      text={
                        <Text strong={!item.is_read} ellipsis className={styles.messageTitle}>
                          {item.title}
                        </Text>
                      }
                    />
                    {!item.is_read && <span className={styles.unreadDot} />}
                  </div>
                  {item.content && (
                    <Text type="secondary" ellipsis className={styles.messageDesc}>
                      {item.content}
                    </Text>
                  )}
                  <Text type="secondary" className={styles.messageTime}>
                    {dayjs(item.created_at).fromNow()}
                  </Text>
                </div>
              </List.Item>
            )}
          />
        ) : (
          <Empty 
            image={Empty.PRESENTED_IMAGE_SIMPLE} 
            description="暂无消息"
            className={styles.emptyState}
          />
        )}
      </Spin>
      <div className={styles.panelFooter}>
        <Button type="link" block onClick={handleViewAll}>
          查看全部消息
        </Button>
      </div>
    </div>
  );

  return (
    <Popover
      content={content}
      trigger="click"
      open={open}
      onOpenChange={setOpen}
      placement="bottomRight"
      overlayClassName={styles.notificationPopover}
      arrow={{ pointAtCenter: true }}
    >
      <Tooltip title="消息通知" open={open ? false : undefined}>
        <div className={styles.actionItem}>
          <Badge count={unreadCount} size="small" offset={[2, -2]}>
            <BellOutlined className={styles.bellIcon} />
          </Badge>
        </div>
      </Tooltip>
    </Popover>
  );
};

// 间距模式切换按钮
export const SpacingButton: React.FC = () => {
  const [currentMode, setCurrentMode] = useState<SpacingMode>(() => getSpacingMode());

  // 初始化时应用 CSS 变量
  useEffect(() => {
    applySpacingCSSVariables(currentMode);
  }, []);

  const handleModeChange = useCallback((mode: SpacingMode) => {
    setSpacingMode(mode);
    setCurrentMode(mode);
    applySpacingCSSVariables(mode);
    // 刷新页面以应用 Ant Design 主题变化
    window.location.reload();
  }, []);

  const menuItems: MenuProps['items'] = [
    {
      key: 'compact',
      label: (
        <div className={styles.spacingMenuItem}>
          <span>紧凑</span>
          {currentMode === 'compact' && <CheckOutlined />}
        </div>
      ),
      onClick: () => handleModeChange('compact'),
    },
    {
      key: 'standard',
      label: (
        <div className={styles.spacingMenuItem}>
          <span>标准</span>
          {currentMode === 'standard' && <CheckOutlined />}
        </div>
      ),
      onClick: () => handleModeChange('standard'),
    },
    {
      key: 'comfortable',
      label: (
        <div className={styles.spacingMenuItem}>
          <span>宽松</span>
          {currentMode === 'comfortable' && <CheckOutlined />}
        </div>
      ),
      onClick: () => handleModeChange('comfortable'),
    },
  ];

  return (
    <Dropdown menu={{ items: menuItems }} trigger={['click']} placement="bottomRight">
      <Tooltip title={`间距模式：${SPACING_LABELS[currentMode]}`}>
        <div className={styles.actionItem}>
          <ColumnWidthOutlined />
        </div>
      </Tooltip>
    </Dropdown>
  );
};

// 导出所有 Action 组件
export const HeaderActions: React.FC = () => {
  return (
    <Space className={styles.headerActions} size={4}>
      <StoreSwitcher />
      <SpacingButton />
      <RefreshButton />
      <NotificationButton />
      <FullscreenButton />
    </Space>
  );
};

export default HeaderActions;

