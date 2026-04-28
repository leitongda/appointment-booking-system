/**
 * 租户切换器组件
 *
 * 用于多租户架构下，平台管理员或跨租户管理员在不同租户之间切换。
 * 选择租户后：
 * 1. 将 tenantId 保存到 localStorage，请求拦截器会自动将其添加到 X-Tenant-ID Header
 * 2. 清除门店缓存，确保下次加载正确的门店列表
 * 3. 刷新页面以应用新的租户上下文
 */
import { BankOutlined, DownOutlined, CheckOutlined, SearchOutlined } from '@ant-design/icons';
import { history, useModel } from '@umijs/max';
import { Tooltip, Popover, Spin, Empty, Avatar, Input, App } from 'antd';
import React, { useState, useEffect, useCallback, useRef } from 'react';
import { tenantApi, adminApi } from '@hospital/api';
import type { Tenant } from '@hospital/api';
import { setStorage, removeStorage, STORAGE_KEYS } from '@hospital/shared';
import styles from './index.less';

// 租户列表缓存 TTL（5 分钟）
const TENANT_CACHE_TTL = 5 * 60 * 1000;

const TenantSwitcher: React.FC = () => {
  const { modal, message } = App.useApp();
  const { initialState } = useModel('@@initialState');
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [tenants, setTenants] = useState<Tenant[]>([]);
  const [switching, setSwitching] = useState(false);
  const [switchingTenantName, setSwitchingTenantName] = useState('');
  const [searchText, setSearchText] = useState('');

  // 租户列表缓存
  const tenantsCacheRef = useRef<{ tenants: Tenant[]; timestamp: number } | null>(null);

  const currentUser = initialState?.currentUser;
  const currentTenantId = initialState?.currentTenantId;
  const isSuperAdmin = currentUser?.isSuperAdmin || currentUser?.roleCode === 'SUPER_ADMIN';
  const isPlatformAdmin = currentUser?.is_platform_admin || isSuperAdmin;

  // 当前选中的租户名称
  const currentTenantName = React.useMemo(() => {
    if (!currentTenantId) return undefined;
    const tenant = tenants.find(t => t.id === currentTenantId);
    return tenant?.name;
  }, [currentTenantId, tenants]);

  // 加载租户列表（带缓存）
  const loadTenants = useCallback(async () => {
    // 使用缓存（5 分钟内有效）
    const cache = tenantsCacheRef.current;
    if (cache && Date.now() - cache.timestamp < TENANT_CACHE_TTL) {
      setTenants(cache.tenants);
      return;
    }

    setLoading(true);
    try {
      const result = await tenantApi.getTenants({
        page: 1,
        pageSize: 100, // 后端限制最大 100
        status: 1, // 仅正常状态的租户
      });
      const fetchedTenants = result?.data || [];
      setTenants(fetchedTenants);
      tenantsCacheRef.current = {
        tenants: fetchedTenants,
        timestamp: Date.now(),
      };
    } catch (error) {
      console.error('加载租户列表失败:', error);
    } finally {
      setLoading(false);
    }
  }, []);

  // 挂载时加载租户列表（确保初始渲染有名称可显示）
  useEffect(() => {
    if (isPlatformAdmin) {
      loadTenants();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // 下拉打开时刷新（利用缓存，5 分钟内不会重复请求）
  useEffect(() => {
    if (open) {
      loadTenants();
      setSearchText('');
    }
  }, [open, loadTenants]);

  // 检测当前是否在表单编辑页面
  const isOnFormPage = useCallback(() => {
    const { pathname } = history.location;
    return /\/(create|edit)($|\/)/.test(pathname);
  }, []);

  // 搜索过滤后的租户列表
  const filteredTenants = React.useMemo(() => {
    if (!searchText.trim()) return tenants;
    const keyword = searchText.trim().toLowerCase();
    return tenants.filter(
      t => t.name?.toLowerCase().includes(keyword) || t.tenantCode?.toLowerCase().includes(keyword)
    );
  }, [tenants, searchText]);

  // 非平台管理员不显示租户切换器
  if (!isPlatformAdmin) {
    return null;
  }

  // 执行租户切换
  const doSwitchTenant = useCallback(async (tenantId: string) => {
    const targetTenant = tenants.find(t => t.id === tenantId);
    setSwitching(true);
    setSwitchingTenantName(targetTenant?.name || '');
    setOpen(false);

    try {
      // 先调 API 验证租户存在且状态正常
      await adminApi.switchTenant(tenantId);

      // API 成功后保存到 localStorage
      localStorage.setItem('hospital_current_tenant_id', tenantId);
      localStorage.removeItem('hospital_current_store');
      tenantsCacheRef.current = null;

      // 保存当前路径以便 reload 后恢复（排除表单编辑页）
      const { pathname, search, hash } = history.location;
      if (!/\/(create|edit)($|\/)/.test(pathname)) {
        setStorage(STORAGE_KEYS.SWITCH_REDIRECT_PATH, pathname + (search || '') + (hash || ''));
      } else {
        // 表单页回退到列表页（去掉最后一段路径）
        const listPath = pathname.replace(/\/(create|edit)($|\/.*)/, '');
        setStorage(STORAGE_KEYS.SWITCH_REDIRECT_PATH, listPath || '/dashboard');
      }

      window.location.reload();
    } catch (error: any) {
      setSwitching(false);
      setSwitchingTenantName('');
      message.error(error.message || '切换租户失败');
    }
  }, [tenants, message]);

  // 点击切换（含表单页保护提示）
  const handleSwitchTenant = useCallback((tenantId: string) => {
    // 点击已选中的租户，仅关闭面板
    if (tenantId === currentTenantId) {
      setOpen(false);
      return;
    }
    // 防止切换过程中重复点击
    if (switching) return;

    // 在表单编辑页面时，提示用户确认
    if (isOnFormPage()) {
      const targetTenant = tenants.find(t => t.id === tenantId);
      modal.confirm({
        title: '切换租户',
        content: `切换到「${targetTenant?.name || ''}」将导致当前页面未保存的更改丢失，是否继续？`,
        okText: '确定切换',
        cancelText: '取消',
        onOk: () => doSwitchTenant(tenantId),
      });
    } else {
      doSwitchTenant(tenantId);
    }
  }, [currentTenantId, switching, isOnFormPage, tenants, modal, doSwitchTenant]);

  // 渲染触发按钮
  const renderTrigger = () => {
    // 有选中的租户
    if (currentTenantId) {
      return (
        <>
          <BankOutlined style={{ marginRight: 8, fontSize: 16, color: '#1890ff' }} />
          <span className={styles.tenantName}>{currentTenantName || currentTenantId}</span>
          <DownOutlined className={`${styles.tenantDropdownIcon} ${open ? styles.tenantDropdownIconOpen : ''}`} />
        </>
      );
    }

    // 未选择租户（平台管理员）
    return (
      <>
        <BankOutlined style={{ marginRight: 8, fontSize: 16, color: 'rgba(0, 0, 0, 0.45)' }} />
        <span className={styles.tenantName} style={{ color: 'rgba(0, 0, 0, 0.45)' }}>选择租户</span>
        <DownOutlined className={`${styles.tenantDropdownIcon} ${open ? styles.tenantDropdownIconOpen : ''}`} />
      </>
    );
  };

  // 租户切换面板内容
  const content = (
    <div className={styles.tenantSwitcherPanel}>
      <div className={styles.tenantSwitcherHeader}>
        <span className={styles.headerTitle}>切换租户</span>
      </div>
      {tenants.length > 5 && (
        <div className={styles.tenantSearchWrapper}>
          <Input
            prefix={<SearchOutlined />}
            placeholder="搜索租户名称或编码"
            value={searchText}
            onChange={e => setSearchText(e.target.value)}
            allowClear
            size="small"
          />
        </div>
      )}
      <Spin spinning={loading}>
        <div className={styles.tenantList}>
          {filteredTenants.map((tenant) => (
            <div
              key={tenant.id}
              className={`${styles.tenantItem} ${currentTenantId === tenant.id ? styles.active : ''}`}
              onClick={() => handleSwitchTenant(tenant.id)}
            >
              <Avatar
                icon={<BankOutlined />}
                size={32}
                className={styles.tenantItemLogo}
                style={{ backgroundColor: currentTenantId === tenant.id ? '#1890ff' : '#87d068' }}
              />
              <div className={styles.tenantItemInfo}>
                <span className={styles.tenantItemName}>{tenant.name}</span>
                <span className={styles.tenantItemCode}>{tenant.tenantCode}</span>
              </div>
              {currentTenantId === tenant.id && <CheckOutlined className={styles.tenantItemCheck} />}
            </div>
          ))}
          {filteredTenants.length === 0 && !loading && (
            <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description={searchText ? '未找到匹配的租户' : '暂无可用租户'} />
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
        overlayClassName={styles.tenantSwitcherPopover}
        arrow={{ pointAtCenter: true }}
      >
        <Tooltip title={currentTenantName || '切换租户'} open={open ? false : undefined}>
          <div className={styles.tenantInfo}>
            {renderTrigger()}
          </div>
        </Tooltip>
      </Popover>

      {/* 租户切换全屏过渡遮罩 */}
      {switching && (
        <div className={styles.tenantSwitchingOverlay}>
          <Spin size="large" />
          <div className={styles.switchingText}>
            正在切换到 {switchingTenantName}...
          </div>
        </div>
      )}
    </>
  );
};

export default TenantSwitcher;
