/**
 * Settings 配置中心 — 薄编排层。
 *
 * 职责：状态管理 + 权限控制 + tab 路由。
 * 每个 tab 的 UI 抽取到 ./settings/ 子目录的独立组件中。
 *
 * 重构前：1474 行（7 个默认值 + 30+ 状态 + 15 个 handler + 11 个内联 tab JSX）
 * 重构后：~250 行（状态 + handler + 薄 JSX 装配）
 */
import { PageContainer, ModalForm, ProFormSelect, ProFormText, ProFormDateTimePicker, ProFormTextArea } from '@ant-design/pro-components';
import { Card, App, Tabs, Spin, Typography } from 'antd';
import { useState, useEffect } from 'react';
import { history, useAccess, useLocation, useModel } from '@umijs/max';
import { settingsApi, blacklistApi, storeApi } from '@hospital/api';
import { fetchAllData } from '@/utils/fetchAllData';
import type {
  BookingSettings, HospitalInfo, BookingFieldConfig, PatientCardConfig,
  BlacklistItem, EmailConfig, ImageConfig, WechatConfig, SmsConfig,
  SecurityConfig, SourceReleaseConfig,
} from '@hospital/api';
import type { StoreWechatConfig } from '@hospital/shared';

import {
  BookingTab, HospitalTab, BookingFieldsTab, PatientCardTab,
  BlacklistTab, EmailTab, WechatTab, ImageTab, SmsTab,
  SecurityTab, SourceReleaseTab,
} from './settings/index';

const { Text } = Typography;

// ===================== 路由映射（保留，属于编排逻辑） =====================

const TAB_PATH_TO_KEY: Record<string, string> = {
  '/operations/system/settings/booking': 'booking',
  '/operations/system/settings/blacklist': 'blacklist',
  '/operations/system/settings/wechat': 'wechat',
  '/operations/system/settings/base': 'hospital',
  '/configuration/booking-rules': 'booking',
  '/configuration/blacklist': 'blacklist',
  '/configuration/wechat': 'wechat',
  '/configuration/booking-fields': 'bookingFields',
  '/configuration/patient-card': 'patientCard',
  '/configuration/hospital-info': 'hospital',
  '/configuration/email-config': 'email',
  '/configuration/image-config': 'image',
  '/organization/medical-config/booking-rules': 'booking',
  '/organization/medical-config/booking-fields': 'bookingFields',
  '/organization/medical-config/patient-card': 'patientCard',
  '/system/config/hospital-info': 'hospital',
  '/system/config/wechat': 'wechat',
  '/system/config/email-config': 'email',
  '/system/config/image-config': 'image',
  '/system/config/sms': 'sms',
  '/system/config/security': 'security',
  '/system/config/source-release': 'sourceRelease',
  '/system/blacklist': 'blacklist',
};

const TAB_KEY_TO_PATH: Record<string, string> = {
  booking: '/organization/medical-config/booking-rules',
  blacklist: '/system/blacklist',
  wechat: '/system/config/wechat',
  hospital: '/system/config/hospital-info',
  bookingFields: '/organization/medical-config/booking-fields',
  patientCard: '/organization/medical-config/patient-card',
  email: '/system/config/email-config',
  image: '/system/config/image-config',
  sms: '/system/config/sms',
  security: '/system/config/security',
  sourceRelease: '/system/config/source-release',
};

const TAB_KEY_TO_TITLE: Record<string, string> = {
  booking: '预约规则',
  blacklist: '黑名单管理',
  wechat: '微信配置',
  hospital: '医院信息',
  bookingFields: '预约字段',
  patientCard: '就诊卡配置',
  email: '邮件配置',
  image: '图片配置',
  sms: '短信通知',
  security: '安全策略',
  sourceRelease: '号源释放',
};

// ===================== 编排层组件 =====================

const SettingsPage: React.FC = () => {
  const { message } = App.useApp();
  const location = useLocation();
  const access = useAccess();
  const { initialState } = useModel('@@initialState');
  const { currentUser } = initialState ?? {};
  const isSuperAdmin = access.canSuperAdmin;

  // ---- 状态 ----
  const [loading, setLoading] = useState(false);
  const [bookingSettings, setBookingSettings] = useState<BookingSettings | null>(null);
  const [hospitalInfo, setHospitalInfo] = useState<HospitalInfo | null>(null);
  const [bookingFields, setBookingFields] = useState<BookingFieldConfig[]>([]);
  const [patientCardConfig, setPatientCardConfig] = useState<PatientCardConfig | null>(null);
  const [blacklist, setBlacklist] = useState<BlacklistItem[]>([]);
  const [blacklistTotal, setBlacklistTotal] = useState(0);
  const [blacklistPage, setBlacklistPage] = useState(1);
  const [blacklistKeyword, setBlacklistKeyword] = useState('');
  const [blacklistLoading, setBlacklistLoading] = useState(false);
  const [addModalVisible, setAddModalVisible] = useState(false);
  const [stores, setStores] = useState<any[]>([]);
  const [emailConfig, setEmailConfig] = useState<EmailConfig | null>(null);
  const [imageConfig, setImageConfig] = useState<ImageConfig | null>(null);
  const [_wechatConfig, setWechatConfig] = useState<WechatConfig | null>(null);
  const [selectedStoreId, setSelectedStoreId] = useState<string>('');
  const [storeWechatConfig, setStoreWechatConfig] = useState<StoreWechatConfig | null>(null);
  const [wechatLoading, setWechatLoading] = useState(false);
  const [smsConfig, setSmsConfig] = useState<SmsConfig | null>(null);
  const [securityConfig, setSecurityConfig] = useState<SecurityConfig | null>(null);
  const [sourceReleaseConfig, setSourceReleaseConfig] = useState<SourceReleaseConfig | null>(null);
  const [selectedBookingStoreId, setSelectedBookingStoreId] = useState<string>('');
  const [activeTab, setActiveTab] = useState<string>(TAB_PATH_TO_KEY[location.pathname] || 'booking');

  // ---- 权限 ----
  const canEditSettings = access.hasPermission('system:settings') || access.hasPermission('settings:edit');
  const canViewBooking = canEditSettings;
  const canViewHospital = canEditSettings;
  const canViewBookingFields = canEditSettings;
  const canViewPatientCard = canEditSettings;
  const canViewEmail = access.hasPermission('settings:email') || access.hasPermission('settings:edit');
  const canEditEmail = canViewEmail;
  const canViewImage = access.hasPermission('settings:edit');
  const canEditImage = canViewImage;
  const canViewWechat = isSuperAdmin || access.hasPermission('settings:wechat') || access.hasPermission('settings:edit');
  const canEditWechat = canViewWechat;
  const canViewSms = access.hasPermission('settings:sms') || access.hasPermission('settings:edit');
  const canEditSms = canViewSms;
  const canViewSecurity = access.hasPermission('settings:edit');
  const canEditSecurity = canViewSecurity;
  const canViewSourceRelease = access.hasPermission('settings:edit');
  const canEditSourceRelease = canViewSourceRelease;
  const canViewBlacklist =
    access.hasPermission('blacklist:list') ||
    access.hasPermission('blacklist:create') ||
    access.hasPermission('blacklist:delete');
  const canAddBlacklist = access.hasPermission('blacklist:create');
  const canDeleteBlacklist = access.hasPermission('blacklist:delete');
  const isLegacySettingsRoute = location.pathname.startsWith('/operations/system/settings');

  // ---- 数据加载 ----

  async function loadBlacklist(page = 1, keyword = '') {
    setBlacklistLoading(true);
    try {
      const res = await blacklistApi.getList({ page, pageSize: 20, keyword: keyword || undefined });
      setBlacklist(res.data ?? []);
      setBlacklistTotal(res.total ?? 0);
      setBlacklistPage(page);
    } catch (error) {
      console.error('加载黑名单失败', error);
    } finally {
      setBlacklistLoading(false);
    }
  }

  async function loadSettings() {
    setLoading(true);
    try {
      const loaders: Promise<void>[] = [];
      if (canViewBooking) loaders.push(settingsApi.getBookingSettings().then(setBookingSettings));
      if (canViewHospital) loaders.push(settingsApi.getHospitalInfo().then(setHospitalInfo));
      if (canViewBookingFields) loaders.push(settingsApi.getBookingFields().then(setBookingFields));
      if (canViewPatientCard) loaders.push(settingsApi.getPatientCardConfig().then(setPatientCardConfig));
      if (canViewEmail) loaders.push(settingsApi.getEmailConfig().then(setEmailConfig));
      if (canViewImage) loaders.push(settingsApi.getImageConfig().then(setImageConfig));
      if (canViewWechat) loaders.push(settingsApi.getWechatConfig().then(setWechatConfig));
      if (canViewSms) loaders.push(settingsApi.getSmsConfig().then(setSmsConfig));
      if (canViewSecurity) loaders.push(settingsApi.getSecurityConfig().then(setSecurityConfig));
      if (canViewSourceRelease) loaders.push(settingsApi.getSourceReleaseConfig().then(setSourceReleaseConfig));
      await Promise.allSettled(loaders);
    } catch (error) {
      console.error('加载配置失败', error);
    } finally {
      setLoading(false);
    }
    if (canViewBlacklist) loadBlacklist();
  }

  async function loadStores() {
    try {
      const allStores = await fetchAllData((page, pageSize) =>
        storeApi.getList({ page, pageSize, status: 1 })
      );
      let storeList = allStores;
      if (!isSuperAdmin && currentUser?.storeIds?.length) {
        storeList = storeList.filter((s) => currentUser.storeIds?.includes(s.id));
      }
      setStores(storeList);
    } catch (error) {
      console.error('加载门店失败', error);
    }
  }

  useEffect(() => {
    loadSettings();
    if (canViewBooking || canViewWechat || canViewBlacklist) loadStores();
  }, []);

  useEffect(() => {
    setActiveTab(TAB_PATH_TO_KEY[location.pathname] || 'booking');
  }, [location.pathname]);

  useEffect(() => {
    if (stores.length > 0 && !selectedStoreId && activeTab === 'wechat') {
      const firstStore = stores[0];
      setSelectedStoreId(firstStore.id);
      loadStoreWechatConfig(firstStore.id);
    }
  }, [stores, activeTab]);

  // ---- Handlers ----

  async function loadStoreBookingSettings(storeId: string) {
    if (!storeId) {
      setBookingSettings(await settingsApi.getBookingSettings());
      return;
    }
    try {
      const rules = await settingsApi.getBookingRules(storeId);
      setBookingSettings({
        advanceDays: rules.advanceDays,
        sameDayBooking: rules.sameDayBooking,
        cancelHours: rules.cancelHours,
        perDayLimit: rules.perDayLimit,
        perDoctorLimit: 1,
        noShowLimit: 3,
        blacklistDays: 30,
        advanceBookingMinutes: rules.advanceBookingMinutes,
        advanceBookingDirection: rules.advanceBookingDirection,
        advanceBookingReference: rules.advanceBookingReference,
        signInAdvanceMinutes: rules.signInAdvanceMinutes,
        signInLateMinutes: rules.signInLateMinutes,
        appointmentReminderHours: rules.appointmentReminderHours,
      });
    } catch (error: any) {
      console.error('加载门店预约设置失败', error);
    }
  }

  const handleBookingSubmit = async (values: any) => {
    try {
      await settingsApi.updateBookingSettings(values, selectedBookingStoreId || undefined);
      message.success('保存成功');
      if (selectedBookingStoreId) {
        await loadStoreBookingSettings(selectedBookingStoreId);
      } else {
        setBookingSettings(await settingsApi.getBookingSettings());
      }
    } catch (error: any) {
      message.error(error.message || '保存失败');
    }
  };

  const handleBookingStoreChange = async (storeId: string) => {
    await loadStoreBookingSettings(storeId);
    setSelectedBookingStoreId(storeId);
  };

  const handleHospitalSubmit = async (values: any) => {
    try { await settingsApi.updateHospitalInfo(values); message.success('保存成功'); } catch (error: any) { message.error(error.message || '保存失败'); }
  };

  const handleFieldChange = async (field: string, key: 'enabled' | 'required', value: boolean) => {
    const newFields = bookingFields.map((f) => f.field === field ? { ...f, [key]: value } : f);
    setBookingFields(newFields);
    try { await settingsApi.updateBookingFields(newFields); message.success('保存成功'); } catch (error: any) { message.error(error.message || '保存失败'); }
  };

  const handlePatientCardSubmit = async (values: any) => {
    try { await settingsApi.updatePatientCardConfig(values); message.success('保存成功'); } catch (error: any) { message.error(error.message || '保存失败'); }
  };

  const handleEmailConfigSubmit = async (values: any) => {
    try { await settingsApi.updateEmailConfig(values); message.success('保存成功'); } catch (error: any) { message.error(error.message || '保存失败'); }
  };

  const handleImageConfigSubmit = async (values: any) => {
    try { await settingsApi.updateImageConfig({ thumbnailSizes: values.thumbnailSizes, compressQuality: values.compressQuality }); message.success('保存成功'); } catch (error: any) { message.error(error.message || '保存失败'); }
  };

  const handleSmsPolicySubmit = async (values: any) => {
    try { await settingsApi.updateSmsConfig({ codeExpireSeconds: values.codeExpireSeconds, sendIntervalSeconds: values.sendIntervalSeconds }); message.success('保存成功'); setSmsConfig(await settingsApi.getSmsConfig()); } catch (error: any) { message.error(error.message || '保存失败'); }
  };

  const handleSecuritySubmit = async (values: any) => {
    try { await settingsApi.updateSecurityConfig({ accessTokenExpireMinutes: values.accessTokenExpireMinutes, refreshTokenExpireDays: values.refreshTokenExpireDays, defaultPassword: values.defaultPassword, rateLimitPerMinute: values.rateLimitPerMinute, rateLimitPerSecond: values.rateLimitPerSecond, loginFailureLockCount: values.loginFailureLockCount, sessionTimeoutMinutes: values.sessionTimeoutMinutes }); message.success('保存成功'); setSecurityConfig(await settingsApi.getSecurityConfig()); } catch (error: any) { message.error(error.message || '保存失败'); }
  };

  const handleSourceReleaseSubmit = async (values: any) => {
    try { await settingsApi.updateSourceReleaseConfig({ lockTimeoutMinutes: values.lockTimeoutMinutes, batchReleaseEnabled: values.batchReleaseEnabled, batchReleaseDays: values.batchReleaseDays, batchReleaseTime: values.batchReleaseTime, autoCancelUnpaidMinutes: values.autoCancelUnpaidMinutes, noShowAutoMarkHours: values.noShowAutoMarkHours, allowOverbooking: values.allowOverbooking, overbookingLimit: values.overbookingLimit }); message.success('保存成功'); setSourceReleaseConfig(await settingsApi.getSourceReleaseConfig()); } catch (error: any) { message.error(error.message || '保存失败'); }
  };

  const loadStoreWechatConfig = async (storeId: string) => {
    if (!storeId) { setStoreWechatConfig(null); return; }
    setWechatLoading(true);
    try { setStoreWechatConfig(await storeApi.getWechatConfig(storeId)); } catch { setStoreWechatConfig(null); } finally { setWechatLoading(false); }
  };

  const handleStoreChange = (storeId: string) => { setSelectedStoreId(storeId); loadStoreWechatConfig(storeId); };

  const handleStoreWechatConfigSubmit = async (values: any) => {
    if (!selectedStoreId) { message.warning('请先选择门店'); return; }
    try { await storeApi.updateWechatConfig(selectedStoreId, values); message.success('保存成功'); } catch (error: any) { message.error(error.message || '保存失败'); }
  };

  const handleAddBlacklist = async (values: any) => {
    try {
      await blacklistApi.add({ storeId: values.storeId === 'all' ? undefined : values.storeId, keyword: values.keyword, reason: values.reason, expireAt: values.expireAt });
      message.success('添加成功');
      setAddModalVisible(false);
      loadBlacklist(1, blacklistKeyword);
      return true;
    } catch (error: any) { message.error(error.message || '添加失败'); return false; }
  };

  const handleRemoveBlacklist = async (id: string) => {
    try { await blacklistApi.remove(id); message.success('解禁成功'); loadBlacklist(blacklistPage, blacklistKeyword); } catch (error: any) { message.error(error.message || '操作失败'); }
  };

  // ---- Tab 路由 ----

  const handleTabChange = (key: string) => {
    setActiveTab(key);
    const targetPath = TAB_KEY_TO_PATH[key] || '/system/config/hospital-info';
    if (targetPath !== location.pathname) history.replace(targetPath);
  };

  // ---- Tab 组件装配 ----

  const items = [
    {
      key: 'booking', label: '预约规则',
      children: <BookingTab bookingSettings={bookingSettings} selectedBookingStoreId={selectedBookingStoreId} stores={stores} onStoreChange={handleBookingStoreChange} onSubmit={handleBookingSubmit} canEdit={canEditSettings} />,
    },
    {
      key: 'hospital', label: '医院信息',
      children: <HospitalTab hospitalInfo={hospitalInfo} onSubmit={handleHospitalSubmit} canEdit={canEditSettings} loading={loading} />,
    },
    {
      key: 'bookingFields', label: '预约字段',
      children: <BookingFieldsTab bookingFields={bookingFields} onFieldChange={handleFieldChange} canEdit={canEditSettings} />,
    },
    {
      key: 'patientCard', label: '就诊卡配置',
      children: <PatientCardTab patientCardConfig={patientCardConfig} onSubmit={handlePatientCardSubmit} canEdit={canEditSettings} loading={loading} />,
    },
    {
      key: 'blacklist', label: '黑名单管理',
      children: <BlacklistTab blacklist={blacklist} blacklistTotal={blacklistTotal} blacklistPage={blacklistPage} blacklistKeyword={blacklistKeyword} blacklistLoading={blacklistLoading} onLoadBlacklist={loadBlacklist} onAddBlacklist={handleAddBlacklist} onRemoveBlacklist={handleRemoveBlacklist} canAdd={canAddBlacklist} canDelete={canDeleteBlacklist} stores={stores} addModalVisible={addModalVisible} onAddModalChange={setAddModalVisible} />,
    },
    {
      key: 'email', label: '邮件配置',
      children: <EmailTab emailConfig={emailConfig} onSubmit={handleEmailConfigSubmit} canEdit={canEditEmail} loading={loading} />,
    },
    {
      key: 'wechat', label: '微信配置',
      children: <WechatTab selectedStoreId={selectedStoreId} stores={stores} storeWechatConfig={storeWechatConfig} wechatLoading={wechatLoading} onStoreChange={handleStoreChange} onSubmit={handleStoreWechatConfigSubmit} canEdit={canEditWechat} />,
    },
    {
      key: 'image', label: '图片配置',
      children: <ImageTab imageConfig={imageConfig} onSubmit={handleImageConfigSubmit} canEdit={canEditImage} loading={loading} />,
    },
    {
      key: 'sms', label: '短信通知',
      children: <SmsTab smsConfig={smsConfig} onSubmit={handleSmsPolicySubmit} canEdit={canEditSms} loading={loading} />,
    },
    {
      key: 'security', label: '安全策略',
      children: <SecurityTab securityConfig={securityConfig} onSubmit={handleSecuritySubmit} canEdit={canEditSecurity} loading={loading} />,
    },
    {
      key: 'sourceRelease', label: '号源释放',
      children: <SourceReleaseTab sourceReleaseConfig={sourceReleaseConfig} onSubmit={handleSourceReleaseSubmit} canEdit={canEditSourceRelease} loading={loading} />,
    },
  ];

  const visibleItems = items.filter((item) => {
    if (item.key === 'booking') return canViewBooking;
    if (item.key === 'hospital') return canViewHospital;
    if (item.key === 'bookingFields') return canViewBookingFields;
    if (item.key === 'patientCard') return canViewPatientCard;
    if (item.key === 'blacklist') return canViewBlacklist;
    if (item.key === 'email') return canViewEmail;
    if (item.key === 'wechat') return canViewWechat;
    if (item.key === 'image') return canViewImage;
    if (item.key === 'sms') return canViewSms;
    if (item.key === 'security') return canViewSecurity;
    if (item.key === 'sourceRelease') return canViewSourceRelease;
    return true;
  });

  const activeItem = visibleItems.find((item) => item.key === activeTab) ?? visibleItems[0];

  useEffect(() => {
    if (!visibleItems.length) return;
    if (!visibleItems.some((item) => item.key === activeTab)) handleTabChange(visibleItems[0].key);
  }, [activeTab, visibleItems]);

  return (
    <PageContainer
      title={isLegacySettingsRoute ? undefined : TAB_KEY_TO_TITLE[activeTab] || '配置中心'}
      subTitle={isLegacySettingsRoute ? undefined : '配置中心按职责拆分为独立菜单入口，旧版聚合设置页仅保留兼容跳转。'}
    >
      <Spin spinning={loading}>
        <Card>
          {isLegacySettingsRoute ? (
            <Tabs activeKey={activeTab} items={visibleItems} onChange={handleTabChange} />
          ) : (
            activeItem?.children
          )}
        </Card>
      </Spin>

      <ModalForm
        title="添加黑名单"
        open={addModalVisible}
        onOpenChange={setAddModalVisible}
        onFinish={handleAddBlacklist}
        width={500}
      >
        <ProFormSelect
          name="storeId"
          label="选择门店"
          initialValue="all"
          options={[{ label: '全部', value: 'all' }, ...stores.map((s) => ({ label: s.name, value: s.id }))]}
        />
        <ProFormText
          name="keyword"
          label="关键词"
          placeholder="请填写用户手机号 或者 身份证"
          rules={[{ required: true, message: '请填写手机号或身份证' }]}
          extra="用户手机号 或者 身份证"
        />
        <ProFormDateTimePicker name="expireAt" label="解禁时间" placeholder="选择日期（不填则永久）" />
        <ProFormTextArea name="reason" label="备注" placeholder="请输入备注" fieldProps={{ rows: 2 }} />
        <Text type="secondary">
          黑名单规则: 关键词会匹配就诊卡的手机号或者身份证，选择门店只针对该门店，不选择则针对所有门店
        </Text>
      </ModalForm>
    </PageContainer>
  );
};

export default SettingsPage;
