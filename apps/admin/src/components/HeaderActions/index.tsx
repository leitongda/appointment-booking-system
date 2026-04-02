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
  QrcodeOutlined,
  MoneyCollectOutlined,
  ClockCircleOutlined,
  EditOutlined,
  DeleteOutlined,
  EyeOutlined,
} from '@ant-design/icons';
import { history, useModel, useAccess } from '@umijs/max';
import { Badge, Tooltip, Popover, List, Empty, Spin, Button, Typography, Space, App, Avatar, Tag, Dropdown, Modal, QRCode, Tabs, Divider, Card } from 'antd';
import type { MenuProps } from 'antd';

import React, { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { messageApi, adminApi, storeApi } from '@hospital/api';
import type { StoreInfo } from '@hospital/api';
import TenantSwitcher from '@/components/TenantSwitcher';
import dayjs from 'dayjs';
import relativeTime from 'dayjs/plugin/relativeTime';
import 'dayjs/locale/zh-cn';
import { setStorage, STORAGE_KEYS } from '@hospital/shared';
import styles from './index.less';

dayjs.extend(relativeTime);
dayjs.locale('zh-cn');

const { Text } = Typography;

// 门店列表缓存 TTL（5 分钟）
const STORE_CACHE_TTL = 5 * 60 * 1000;

// 门店切换器组件
export const StoreSwitcher: React.FC = () => {
  const { message, modal } = App.useApp();
  const { initialState } = useModel('@@initialState');
  const access = useAccess();
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [stores, setStores] = useState<StoreInfo[]>([]);
  const [canSwitchStores, setCanSwitchStores] = useState(false);
  const [switching, setSwitching] = useState(false);
  const [switchingStoreName, setSwitchingStoreName] = useState('');
  
  // 签到二维码弹窗状态
  const [qrcodeModalVisible, setQrcodeModalVisible] = useState(false);
  const [qrcodeContent, setQrcodeContent] = useState('');
  const [qrcodeLoading, setQrcodeLoading] = useState(false);
  
  // 门店列表缓存
  const storesCacheRef = useRef<{ stores: StoreInfo[]; canSwitchStores: boolean; timestamp: number } | null>(null);
  
  const currentUser = initialState?.currentUser;
  const currentStore = initialState?.currentStore;
  const userStores = initialState?.userStores || [];
  const isSuperAdmin = currentUser?.isSuperAdmin || currentUser?.roleCode === 'SUPER_ADMIN';
  
  // 判断是否可以切换门店：非超级管理员 且 绑定多个门店
  const hasMultipleStores = userStores.length > 1 && !isSuperAdmin;

  // 加载门店列表（带缓存）
  const loadStores = useCallback(async () => {
    if (!currentUser?.id) return;
    
    // 使用缓存（5 分钟内有效）
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

  // 打开时加载门店列表
  useEffect(() => {
    if (open) {
      loadStores();
    }
  }, [open, loadStores]);

  // 检测当前是否在表单编辑页面
  const isOnFormPage = useCallback(() => {
    const { pathname } = history.location;
    return /\/(create|edit)($|\/)/.test(pathname);
  }, []);

  // 执行门店切换
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
      // 清除缓存，确保下次加载最新数据
      storesCacheRef.current = null;

      // 保存当前路径以便 reload 后恢复（排除表单编辑页）
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

  // 执行切换到"全部门店"
  const doSelectAllStores = useCallback(() => {
    setSwitching(true);
    setSwitchingStoreName('全部门店');
    setOpen(false);
    localStorage.removeItem('hospital_current_store');
    storesCacheRef.current = null;

    // 保存当前路径以便 reload 后恢复
    const { pathname, search, hash } = history.location;
    if (!/\/(create|edit)($|\/)/.test(pathname)) {
      setStorage(STORAGE_KEYS.SWITCH_REDIRECT_PATH, pathname + (search || '') + (hash || ''));
    } else {
      const listPath = pathname.replace(/\/(create|edit)($|\/.*)/, '');
      setStorage(STORAGE_KEYS.SWITCH_REDIRECT_PATH, listPath || '/dashboard');
    }

    window.location.reload();
  }, []);

  // 切换到"全部门店"模式（仅超级管理员，含表单页保护）
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

  // 切换门店（含表单页保护提示）
  const handleSwitchStore = useCallback((storeId: string) => {
    // 点击已选中的门店，仅关闭面板，不触发切换
    if (storeId === currentStore?.id) {
      setOpen(false);
      return;
    }
    // 防止切换过程中重复点击
    if (switching) return;

    // 在表单编辑页面时，提示用户确认
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

  // 只有一个门店且非超级管理员：显示静态信息（不显示切换功能）
  const showStaticInfo = !hasMultipleStores;

  // 打开签到二维码弹窗
  const handleOpenQrcode = useCallback(async () => {
    if (!currentStore?.id) {
      message.warning('请先选择一个门店');
      return;
    }
    setQrcodeModalVisible(true);
    setQrcodeLoading(true);
    setOpen(false); // 关闭门店切换面板
    try {
      const result = await storeApi.getCheckinQrcode(currentStore.id);
      setQrcodeContent(result.qrcodeContent);
    } catch (error: any) {
      message.error(error.message || '获取二维码失败');
    } finally {
      setQrcodeLoading(false);
    }
  }, [currentStore?.id, message]);

  // 下载二维码
  const handleDownloadQrcode = useCallback(() => {
    const canvas = document.querySelector('#store-header-qrcode canvas') as HTMLCanvasElement;
    if (canvas) {
      const link = document.createElement('a');
      link.download = `签到二维码-${currentStore?.name || '门店'}.png`;
      link.href = canvas.toDataURL('image/png');
      link.click();
    }
  }, [currentStore?.name]);

  // 门店管理功能入口（根据权限过滤）
  const storeActions = useMemo(() => {
    const actions = [
      { 
        key: 'qrcode', 
        icon: <QrcodeOutlined />, 
        label: '签到二维码',
        permission: 'store:list',
        onClick: handleOpenQrcode 
      },
      { 
        key: 'fee', 
        icon: <MoneyCollectOutlined />, 
        label: '诊费设置',
        permission: 'store:update',
        onClick: () => {
          setOpen(false);
          history.push(`/organization/store/${currentStore?.id}/fee-templates`);
        }
      },
      { 
        key: 'visit', 
        icon: <ClockCircleOutlined />, 
        label: '复诊规则',
        permission: 'store:update',
        onClick: () => {
          setOpen(false);
          history.push(`/organization/store/${currentStore?.id}/visit-type-config`);
        }
      },
      { 
        key: 'edit', 
        icon: <EditOutlined />, 
        label: '编辑门店',
        permission: 'store:update',
        onClick: () => {
          setOpen(false);
          history.push(`/organization/store/${currentStore?.id}/edit`);
        }
      },
    ];
    return actions.filter(action => access.hasPermission(action.permission));
  }, [access, currentStore?.id, handleOpenQrcode]);

  // 渲染当前门店信息
  const renderCurrentStore = () => {
    if (!currentStore) {
      // 超级管理员无门店选中时显示"全部门店"；普通用户显示"请选择门店"
      const label = isSuperAdmin ? '全部门店' : '请选择门店';
      const color = isSuperAdmin ? '#1890ff' : 'rgba(0, 0, 0, 0.45)';
      const textColor = isSuperAdmin ? 'rgba(0, 0, 0, 0.85)' : 'rgba(0, 0, 0, 0.45)';
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
          <ShopOutlined style={{ marginRight: 8, fontSize: 16, color: '#1890ff' }} />
        )}
        <span className={styles.storeName}>{currentStore.name}</span>
        {(!showStaticInfo || hasStoreActions) && (
          <DownOutlined className={`${styles.storeDropdownIcon} ${open ? styles.storeDropdownIconOpen : ''}`} />
        )}
      </>
    );
  };

  // 静态显示（不可切换门店，但仍需要显示门店管理功能区）
  // 如果有门店管理功能权限，仍然需要显示 Popover（但超级管理员除外）
  const hasStoreActions = storeActions.length > 0 && currentStore;

  if (showStaticInfo && (!hasStoreActions || isSuperAdmin)) {
    return (
      <Tooltip title={currentStore?.name || '未选择门店'}>
        <div className={styles.storeInfo}>
          {renderCurrentStore()}
        </div>
      </Tooltip>
    );
  }

  // 门店切换面板
  const content = (
    <div className={styles.storeSwitcherPanel}>
      {/* 标题栏：根据是否可切换门店显示不同标题 */}
      <div className={styles.storeSwitcherHeader}>
        <span className={styles.headerTitle}>
          {showStaticInfo ? '门店管理' : '切换门店'}
        </span>
      </div>
      {/* 门店列表：仅在可切换门店时显示 */}
      {!showStaticInfo && (
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
      )}
      {/* 门店管理功能区 */}
      {currentStore && storeActions.length > 0 && (
        <div className={styles.storeActionsSection} style={showStaticInfo ? { borderTop: 'none' } : undefined}>
          {!showStaticInfo && <div className={styles.sectionTitle}>门店管理</div>}
          <div className={styles.storeActionGrid}>
            {storeActions.map(action => (
              <div 
                key={action.key} 
                className={styles.storeActionItem}
                onClick={action.onClick}
              >
                {action.icon}
                <span>{action.label}</span>
              </div>
            ))}
          </div>
        </div>
      )}
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
      
      {/* 签到二维码弹窗 */}
      <Modal
        title={`签到二维码 - ${currentStore?.name || ''}`}
        open={qrcodeModalVisible}
        onCancel={() => setQrcodeModalVisible(false)}
        footer={[
          <Button key="close" onClick={() => setQrcodeModalVisible(false)}>
            关闭
          </Button>,
          <Button key="download" type="primary" onClick={handleDownloadQrcode} disabled={!qrcodeContent}>
            下载二维码
          </Button>,
        ]}
        width={400}
        destroyOnHidden
      >
        <div style={{ textAlign: 'center', padding: '24px 0' }} id="store-header-qrcode">
          {qrcodeLoading ? (
            <Spin tip="加载中..." />
          ) : qrcodeContent ? (
            <>
              <QRCode
                value={qrcodeContent}
                size={256}
                style={{ margin: '0 auto' }}
              />
              <div style={{ marginTop: 16, color: '#666' }}>
                请使用微信扫描此二维码进行签到
              </div>
              <div style={{ marginTop: 8, fontSize: 12, color: '#999' }}>
                二维码内容: {qrcodeContent}
              </div>
            </>
          ) : (
            <Empty description="获取二维码失败" />
          )}
        </div>
      </Modal>

      {/* 门店切换全屏过渡遮罩 */}
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
  const [activeTab, setActiveTab] = useState('all');

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
        pageSize: 10,
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
  const handleMarkAsRead = useCallback(async (messageId: string, event?: React.MouseEvent) => {
    event?.stopPropagation();
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

  // 删除消息
  const handleDeleteMessage = useCallback(async (messageId: string, event?: React.MouseEvent) => {
    event?.stopPropagation();
    if (!currentUser?.id) return;
    try {
      await messageApi.delete(messageId, currentUser.id);
      fetchMessages();
      fetchUnreadCount();
      message.success('删除成功');
    } catch (error) {
      console.error('删除消息失败:', error);
    }
  }, [currentUser?.id, fetchMessages, fetchUnreadCount, message]);

  // 查看全部消息
  const handleViewAll = useCallback(() => {
    setOpen(false);
    history.push('/content-center/message');
  }, []);

  // 消息类型映射
  const messageTypeConfig: Record<string, { color: string; text: string; icon: React.ReactNode }> = {
    system: { color: 'blue', text: '系统', icon: <BellOutlined /> },
    appointment: { color: 'green', text: '预约', icon: <CheckOutlined /> },
    notification: { color: 'orange', text: '通知', icon: <EyeOutlined /> },
    reminder: { color: 'red', text: '提醒', icon: <ClockCircleOutlined /> },
  };

  // 过滤消息
  const filteredMessages = useMemo(() => {
    if (activeTab === 'all') return messages;
    if (activeTab === 'unread') return messages.filter(m => !m.is_read);
    return messages.filter(m => m.message_type === activeTab);
  }, [messages, activeTab]);

  // 统计各类型消息数量
  const messageCounts = useMemo(() => {
    const counts: Record<string, number> = {
      all: messages.length,
      unread: messages.filter(m => !m.is_read).length,
      system: 0,
      appointment: 0,
      notification: 0,
      reminder: 0,
    };
    messages.forEach(m => {
      if (counts[m.message_type] !== undefined) {
        counts[m.message_type]++;
      }
    });
    return counts;
  }, [messages]);

  // 渲染消息项操作菜单
  const renderMessageActions = (item: Message) => {
    const items: MenuProps['items'] = [
      !item.is_read && {
        key: 'read',
        icon: <EyeOutlined />,
        label: '标为已读',
        onClick: (e) => handleMarkAsRead(item.id, e.domEvent),
      },
      {
        key: 'delete',
        icon: <DeleteOutlined />,
        label: '删除',
        danger: true,
        onClick: (e) => handleDeleteMessage(item.id, e.domEvent),
      },
    ].filter(Boolean);

    if (items.length === 0) return null;

    return (
      <Dropdown menu={{ items }} trigger={['click']} placement="bottomRight">
        <Button
          type="text"
          size="small"
          icon={<DownOutlined />}
          onClick={(e) => e.stopPropagation()}
          className={styles.messageActionBtn}
        />
      </Dropdown>
    );
  };

  // Tab 配置
  const tabItems = [
    { key: 'all', label: '全部', count: messageCounts.all },
    { key: 'unread', label: '未读', count: messageCounts.unread },
    { key: 'system', label: '系统', count: messageCounts.system },
    { key: 'appointment', label: '预约', count: messageCounts.appointment },
  ].filter(tab => tab.count > 0 || tab.key === 'all' || tab.key === 'unread');

  const content = (
    <div className={styles.notificationPanel}>
      {/* 头部 */}
      <div className={styles.panelHeader}>
        <Space size={12}>
          <BellOutlined className={styles.headerIcon} />
          <span className={styles.panelTitle}>消息通知</span>
          {unreadCount > 0 && (
            <Badge count={unreadCount} size="small" />
          )}
        </Space>
        {unreadCount > 0 && (
          <Button
            type="text"
            size="small"
            icon={<CheckOutlined />}
            onClick={handleMarkAllAsRead}
            className={styles.headerActionBtn}
          >
            全部已读
          </Button>
        )}
      </div>

      <Divider className={styles.headerDivider} />

      {/* 标签页 */}
      <Tabs
        activeKey={activeTab}
        onChange={setActiveTab}
        className={styles.messageTabs}
        items={tabItems.map(tab => ({
          key: tab.key,
          label: (
            <Space size={4}>
              <span>{tab.label}</span>
              {tab.count > 0 && (
                <Badge count={tab.count} size="small" />
              )}
            </Space>
          ),
        }))}
      />

      {/* 消息列表 */}
      <Spin spinning={loading}>
        {filteredMessages.length > 0 ? (
          <List
            className={styles.messageList}
            dataSource={filteredMessages}
            renderItem={(item) => {
              const config = messageTypeConfig[item.message_type] || messageTypeConfig.system;
              return (
                <List.Item
                  className={`${styles.messageItem} ${!item.is_read ? styles.unread : ''}`}
                  onClick={() => {
                    if (!item.is_read) {
                      handleMarkAsRead(item.id);
                    }
                  }}
                >
                  <div className={styles.messageContent}>
                    <div className={styles.messageHeader}>
                      <Space size={8}>
                        <Tag color={config.color} icon={config.icon} className={styles.messageTypeTag}>
                          {config.text}
                        </Tag>
                        {!item.is_read && <Badge status="processing" />}
                      </Space>
                      {renderMessageActions(item)}
                    </div>
                    <div className={styles.messageTitleWrapper}>
                      <Text
                        strong={!item.is_read}
                        className={styles.messageTitle}
                        ellipsis={{ tooltip: item.title }}
                      >
                        {item.title}
                      </Text>
                    </div>
                    {item.content && (
                      <Text
                        type="secondary"
                        ellipsis={{ tooltip: item.content }}
                        className={styles.messageDesc}
                      >
                        {item.content}
                      </Text>
                    )}
                    <Text type="secondary" className={styles.messageTime}>
                      {dayjs(item.created_at).fromNow()}
                    </Text>
                  </div>
                </List.Item>
              );
            }}
          />
        ) : (
          <Empty
            image={Empty.PRESENTED_IMAGE_SIMPLE}
            description={
              activeTab === 'unread' ? '暂无未读消息' : '暂无消息'
            }
            className={styles.emptyState}
          />
        )}
      </Spin>

      <Divider className={styles.footerDivider} />

      {/* 底部 */}
      <div className={styles.panelFooter}>
        <Button type="link" icon={<AppstoreOutlined />} onClick={handleViewAll}>
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
      arrow={false}
      destroyOnHidden
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

// 导出所有 Action 组件
export const HeaderActions: React.FC = () => {
  return (
    <Space className={styles.headerActions} size={4}>
      <TenantSwitcher />
      <StoreSwitcher />
      <RefreshButton />
      <NotificationButton />
      <FullscreenButton />
    </Space>
  );
};

export default HeaderActions;

