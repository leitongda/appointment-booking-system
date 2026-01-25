import {
  PageContainer,
  ProForm,
  ProFormText,
  ProFormDigit,
  ProFormSwitch,
  ProFormTextArea,
  ProFormDateTimePicker,
  ProFormSelect,
  ProFormList,
  ModalForm,
} from '@ant-design/pro-components';
import { Card, App, Tabs, Spin, Table, Switch, Button, Input, Space, Popconfirm, Tag, Select, Form, Typography, Slider, Row, Col } from 'antd';
import { PlusOutlined, SearchOutlined, DeleteOutlined, CalendarOutlined, CloseCircleOutlined, CheckCircleOutlined, StopOutlined, NumberOutlined } from '@ant-design/icons';
import { useState, useEffect, useRef } from 'react';
import { useAccess, useModel } from '@umijs/max';
import { settingsApi, blacklistApi, storeApi } from '@hospital/api';
import { fetchAllData } from '@/utils/fetchAllData';
import type { BookingSettings, HospitalInfo, BookingFieldConfig, PatientCardConfig, BlacklistItem, EmailConfig, ImageConfig, ThumbnailSize, WechatConfig } from '@hospital/api';
import type { StoreWechatConfig, Store } from '@hospital/shared';

const { Text } = Typography;

// 预约设置默认值（与后端 DEFAULT_SETTINGS 保持一致）
const DEFAULT_BOOKING_SETTINGS: BookingSettings = {
  advanceDays: 10,
  sameDayBooking: true,
  cancelHours: 2,
  perDayLimit: 3,
  perDoctorLimit: 1,
  noShowLimit: 3,
  blacklistDays: 30,
  // 提前预约截止配置
  advanceBookingMinutes: 0,
  advanceBookingDirection: 'before',
  advanceBookingReference: 'end',
  // 签到时间配置
  signInAdvanceMinutes: 30,
  signInLateMinutes: 30,
};

// 就诊卡配置默认值
const DEFAULT_PATIENT_CARD_CONFIG: PatientCardConfig = {
  cardName: '就诊卡',
  cardDescription: '',
  maxCardsPerUser: 5,
  showOnHomepage: false,
};

// 邮件配置默认值
const DEFAULT_EMAIL_CONFIG: EmailConfig = {
  smtpHost: '',
  smtpPort: 465,
  smtpUser: '',
  smtpPassword: '',
  smtpSsl: true,
  senderName: '',
  senderEmail: '',
};

// 图片配置默认值
const DEFAULT_IMAGE_CONFIG: ImageConfig = {
  thumbnailSizes: [
    { name: 'small', width: 200, height: 200 },
    { name: 'medium', width: 800, height: 800 },
  ],
  compressQuality: 85,
};

const SettingsPage: React.FC = () => {
  const { message } = App.useApp();
  const access = useAccess();
  const { initialState } = useModel('@@initialState');
  const { currentUser } = initialState ?? {};
  const isSuperAdmin = access.canSuperAdmin;
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
  const [wechatConfig, setWechatConfig] = useState<WechatConfig | null>(null);
  const [selectedStoreId, setSelectedStoreId] = useState<string>('');
  const [storeWechatConfig, setStoreWechatConfig] = useState<StoreWechatConfig | null>(null);
  const [wechatLoading, setWechatLoading] = useState(false);
  // 预约设置门店选择
  const [selectedBookingStoreId, setSelectedBookingStoreId] = useState<string>('');
  const canEdit = access.hasPermission('system:settings');
  const canEditWechat = isSuperAdmin || access.hasPermission('settings:wechat') || access.hasPermission('settings:edit');

  useEffect(() => {
    loadSettings();
    loadStores();
  }, []);

  const loadSettings = async () => {
    setLoading(true);
    try {
      const [booking, hospital, fields, cardConfig, email, image, wechat] = await Promise.allSettled([
        settingsApi.getBookingSettings(),
        settingsApi.getHospitalInfo(),
        settingsApi.getBookingFields(),
        settingsApi.getPatientCardConfig(),
        settingsApi.getEmailConfig(),
        settingsApi.getImageConfig(),
        settingsApi.getWechatConfig(),
      ]);
      if (booking.status === 'fulfilled') setBookingSettings(booking.value);
      if (hospital.status === 'fulfilled') setHospitalInfo(hospital.value);
      if (fields.status === 'fulfilled') setBookingFields(fields.value);
      if (cardConfig.status === 'fulfilled') setPatientCardConfig(cardConfig.value);
      if (email.status === 'fulfilled') setEmailConfig(email.value);
      if (image.status === 'fulfilled') setImageConfig(image.value);
      if (wechat.status === 'fulfilled') setWechatConfig(wechat.value);
    } catch (error) {
      console.error('加载配置失败', error);
    } finally {
      setLoading(false);
    }
    loadBlacklist();
  };

  const loadStores = async () => {
    try {
      // 获取所有启用的门店
      const allStores = await fetchAllData((page, pageSize) =>
        storeApi.getList({ page, pageSize, status: 1 })
      );
      let storeList = allStores;
      // 非超管只显示其关联的门店
      if (!isSuperAdmin && currentUser?.storeIds?.length) {
        storeList = storeList.filter((s) => currentUser.storeIds?.includes(s.id));
      }
      setStores(storeList);
    } catch (error) {
      console.error('加载门店失败', error);
    }
  };

  const loadBlacklist = async (page = 1, keyword = '') => {
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
  };

  const handleBookingSubmit = async (values: any) => {
    try {
      await settingsApi.updateBookingSettings(values, selectedBookingStoreId || undefined);
      message.success('保存成功');
      // 重新加载配置
      if (selectedBookingStoreId) {
        await loadStoreBookingSettings(selectedBookingStoreId);
      } else {
        const settings = await settingsApi.getBookingSettings();
        setBookingSettings(settings);
      }
    } catch (error: any) {
      message.error(error.message || '保存失败');
    }
  };

  // 加载门店预约设置
  const loadStoreBookingSettings = async (storeId: string) => {
    if (!storeId) {
      // 加载全局配置
      const settings = await settingsApi.getBookingSettings();
      setBookingSettings(settings);
      return;
    }
    try {
      // 调用API时传递storeId参数
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
      });
    } catch (error: any) {
      console.error('加载门店预约设置失败', error);
    }
  };

  // 门店选择变化时加载配置
  const handleBookingStoreChange = (storeId: string) => {
    setSelectedBookingStoreId(storeId);
    loadStoreBookingSettings(storeId);
  };

  const handleHospitalSubmit = async (values: any) => {
    try {
      await settingsApi.updateHospitalInfo(values);
      message.success('保存成功');
    } catch (error: any) {
      message.error(error.message || '保存失败');
    }
  };

  const handleFieldChange = async (field: string, key: 'enabled' | 'required', value: boolean) => {
    const newFields = bookingFields.map((f) => {
      if (f.field === field) {
        return { ...f, [key]: value };
      }
      return f;
    });
    setBookingFields(newFields);
    
    try {
      await settingsApi.updateBookingFields(newFields);
      message.success('保存成功');
    } catch (error: any) {
      message.error(error.message || '保存失败');
    }
  };

  const handlePatientCardSubmit = async (values: any) => {
    try {
      await settingsApi.updatePatientCardConfig(values);
      message.success('保存成功');
    } catch (error: any) {
      message.error(error.message || '保存失败');
    }
  };

  const handleEmailConfigSubmit = async (values: any) => {
    try {
      await settingsApi.updateEmailConfig(values);
      message.success('保存成功');
    } catch (error: any) {
      message.error(error.message || '保存失败');
    }
  };

  const handleImageConfigSubmit = async (values: any) => {
    try {
      await settingsApi.updateImageConfig({
        thumbnailSizes: values.thumbnailSizes,
        compressQuality: values.compressQuality,
      });
      message.success('保存成功');
    } catch (error: any) {
      message.error(error.message || '保存失败');
    }
  };

  const handleWechatConfigSubmit = async (values: any) => {
    try {
      await settingsApi.updateWechatConfig(values);
      message.success('保存成功');
    } catch (error: any) {
      message.error(error.message || '保存失败');
    }
  };

  // 加载门店微信配置
  const loadStoreWechatConfig = async (storeId: string) => {
    if (!storeId) {
      setStoreWechatConfig(null);
      return;
    }
    setWechatLoading(true);
    try {
      const config = await storeApi.getWechatConfig(storeId);
      setStoreWechatConfig(config);
    } catch (error: any) {
      console.error('加载门店微信配置失败', error);
      setStoreWechatConfig(null);
    } finally {
      setWechatLoading(false);
    }
  };

  // 门店选择变化时加载配置
  const handleStoreChange = (storeId: string) => {
    setSelectedStoreId(storeId);
    loadStoreWechatConfig(storeId);
  };

  // 保存门店微信配置
  const handleStoreWechatConfigSubmit = async (values: any) => {
    if (!selectedStoreId) {
      message.warning('请先选择门店');
      return;
    }
    try {
      await storeApi.updateWechatConfig(selectedStoreId, values);
      message.success('保存成功');
    } catch (error: any) {
      message.error(error.message || '保存失败');
    }
  };

  const handleAddBlacklist = async (values: any) => {
    try {
      await blacklistApi.add({
        storeId: values.storeId === 'all' ? undefined : values.storeId,
        keyword: values.keyword,
        reason: values.reason,
        expireAt: values.expireAt,
      });
      message.success('添加成功');
      setAddModalVisible(false);
      loadBlacklist(1, blacklistKeyword);
      return true;
    } catch (error: any) {
      message.error(error.message || '添加失败');
      return false;
    }
  };

  const handleRemoveBlacklist = async (id: string) => {
    try {
      await blacklistApi.remove(id);
      message.success('解禁成功');
      loadBlacklist(blacklistPage, blacklistKeyword);
    } catch (error: any) {
      message.error(error.message || '操作失败');
    }
  };

  // 预约选项配置表格列
  const fieldColumns = [
    { title: '预约选项名称', dataIndex: 'name', width: 150 },
    {
      title: '状态',
      dataIndex: 'enabled',
      width: 120,
      render: (_: any, record: BookingFieldConfig) => (
        <Switch
          checked={record.enabled}
          checkedChildren="启用"
          unCheckedChildren="禁用"
          onChange={(checked) => handleFieldChange(record.field, 'enabled', checked)}
        />
      ),
    },
    {
      title: '必填/非必填',
      dataIndex: 'required',
      width: 120,
      render: (_: any, record: BookingFieldConfig) => (
        <Switch
          checked={record.required}
          checkedChildren="必填"
          unCheckedChildren="非必填"
          disabled={!record.enabled}
          onChange={(checked) => handleFieldChange(record.field, 'required', checked)}
        />
      ),
    },
    { title: '操作', width: 80, render: () => '-' },
  ];

  // 黑名单表格列
  const blacklistColumns = [
    {
      title: '禁用门店',
      dataIndex: 'storeName',
      width: 120,
      render: (val: string) => val || '全部',
    },
    {
      title: '用户',
      dataIndex: 'userName',
      width: 120,
      render: (val: string, record: BlacklistItem) => val || record.userPhone || '-',
    },
    { title: '关键词', dataIndex: 'keyword', width: 150 },
    { title: '创建时间', dataIndex: 'createdAt', width: 160 },
    { title: '解禁时间', dataIndex: 'expireAt', width: 160, render: (val: string) => val || '永久' },
    { title: '备注', dataIndex: 'reason', width: 150, ellipsis: true },
    {
      title: '来源',
      dataIndex: 'source',
      width: 80,
      render: (val: number) => (
        <Tag color={val === 2 ? 'orange' : 'blue'}>{val === 2 ? '自动' : '手动'}</Tag>
      ),
    },
    {
      title: '状态',
      dataIndex: 'status',
      width: 80,
      render: (val: number) => (
        <Tag color={val === 1 ? 'red' : 'default'}>{val === 1 ? '生效中' : '已解禁'}</Tag>
      ),
    },
    {
      title: '操作',
      width: 80,
      render: (_: any, record: BlacklistItem) =>
        canEdit && record.status === 1 ? (
          <Popconfirm title="确定解禁该用户吗？" onConfirm={() => handleRemoveBlacklist(record.id)}>
            <a>解禁</a>
          </Popconfirm>
        ) : (
          '-'
        ),
    },
  ];

  const items = [
    {
      key: 'booking',
      label: '规则配置',
      children: (
        <div>
          {/* 门店选择器 */}
          <div style={{ marginBottom: 24 }}>
            <span style={{ marginRight: 8 }}>选择门店：</span>
            <Select
              style={{ width: 300 }}
              placeholder="全局配置（不选择门店）"
              value={selectedBookingStoreId || undefined}
              onChange={handleBookingStoreChange}
              options={[
                { label: '全局配置（默认）', value: '' },
                ...stores.map((s) => ({ label: s.name, value: s.id }))
              ]}
              allowClear
            />
          </div>

          <ProForm
            key={selectedBookingStoreId || 'global'}
            onFinish={handleBookingSubmit}
            initialValues={{ ...DEFAULT_BOOKING_SETTINGS, ...bookingSettings }}
            submitter={{ searchConfig: { submitText: '保存设置' }, resetButtonProps: { style: { display: 'none' } } }}
          >
            <Space direction="vertical" style={{ width: '100%' }} size="large">
              {/* 预约时间限制 */}
              <Card title={<><CalendarOutlined /><span style={{ marginLeft: 8 }}>预约时间限制</span></>} size="small">
                <Row gutter={16}>
                  <Col span={8}>
                    <ProFormDigit
                      name="advanceDays"
                      label="提前预约天数"
                      min={1}
                      max={30}
                      fieldProps={{ addonAfter: '天' }}
                      tooltip="用户最多可以提前几天进行预约"
                    />
                  </Col>
                  <Col span={8}>
                    <ProFormSwitch
                      name="sameDayBooking"
                      label="允许当天预约"
                      tooltip="是否允许预约当天的号源"
                    />
                  </Col>
                  <Col span={8}>
                    <ProFormDigit
                      name="advanceBookingMinutes"
                      label="预约截止时间"
                      min={0}
                      max={1440}
                      fieldProps={{ addonAfter: '分钟' }}
                      tooltip="预约当天号源的截止时间，0表示不限制"
                    />
                  </Col>
                </Row>
                <Row gutter={16}>
                  <Col span={12}>
                    <ProFormSelect
                      name="advanceBookingDirection"
                      label="时间方向"
                      options={[
                        { label: '往前（提前）', value: 'before' },
                        { label: '往后（延后）', value: 'after' },
                      ]}
                      tooltip="'往前'表示从基准时间往前推算，'往后'表示从基准时间往后推算"
                    />
                  </Col>
                  <Col span={12}>
                    <ProFormSelect
                      name="advanceBookingReference"
                      label="基准时间"
                      options={[
                        { label: '开始时间', value: 'start' },
                        { label: '结束时间', value: 'end' },
                      ]}
                      tooltip="以班次的开始时间还是结束时间作为基准"
                    />
                  </Col>
                </Row>
              </Card>

              {/* 取消规则 */}
              <Card title={<><CloseCircleOutlined /><span style={{ marginLeft: 8 }}>取消规则</span></>} size="small">
                <ProFormDigit
                  name="cancelHours"
                  label="最晚取消时间"
                  min={0}
                  max={168}
                  fieldProps={{ addonAfter: '小时' }}
                  tooltip="用户最晚可以在就诊前几小时取消预约，0表示不限制"
                />
              </Card>

              {/* 签到规则 */}
              <Card title={<><CheckCircleOutlined /><span style={{ marginLeft: 8 }}>签到规则</span></>} size="small">
                <Row gutter={16}>
                  <Col span={12}>
                    <ProFormDigit
                      name="signInAdvanceMinutes"
                      label="提前签到时间"
                      min={0}
                      max={1440}
                      fieldProps={{ addonAfter: '分钟' }}
                      tooltip="用户最早可以在班次开始前几分钟签到"
                    />
                  </Col>
                  <Col span={12}>
                    <ProFormDigit
                      name="signInLateMinutes"
                      label="迟到签到时间"
                      min={0}
                      max={1440}
                      fieldProps={{ addonAfter: '分钟' }}
                      tooltip="用户最晚可以在班次开始后几分钟签到"
                    />
                  </Col>
                </Row>
              </Card>

              {/* 频次限制 */}
              <Card title={<><NumberOutlined /><span style={{ marginLeft: 8 }}>频次限制</span></>} size="small">
                <Row gutter={16}>
                  <Col span={8}>
                    <ProFormDigit
                      name="perDayLimit"
                      label="每人每天最大预约数"
                      min={1}
                      max={10}
                      tooltip="每个用户每天最多可以预约多少次"
                    />
                  </Col>
                  <Col span={8}>
                    <ProFormDigit
                      name="perDoctorLimit"
                      label="每人每医生最大预约数"
                      min={1}
                      max={5}
                      tooltip="每个用户对同一个医生最多可以预约多少次"
                    />
                  </Col>
                  <Col span={8}>
                    <ProFormDigit
                      name="noShowLimit"
                      label="爽约次数限制"
                      min={1}
                      max={10}
                      tooltip="用户爽约多少次后会被限制预约"
                    />
                  </Col>
                </Row>
              </Card>

              {/* 黑名单规则 */}
              <Card title={<><StopOutlined /><span style={{ marginLeft: 8 }}>黑名单规则</span></>} size="small">
                <ProFormDigit
                  name="blacklistDays"
                  label="黑名单限制天数"
                  min={1}
                  max={365}
                  fieldProps={{ addonAfter: '天' }}
                  tooltip="用户被加入黑名单后，多少天内无法预约"
                />
              </Card>
            </Space>
          </ProForm>
        </div>
      ),
    },
    {
      key: 'hospital',
      label: '医院信息',
      children: (
        <ProForm
          key={loading ? 'hospital-loading' : 'hospital-loaded'}
          onFinish={handleHospitalSubmit}
          initialValues={hospitalInfo || {}}
          submitter={{ searchConfig: { submitText: '保存设置' }, resetButtonProps: { style: { display: 'none' } } }}
        >
          <ProFormText name="hospitalName" label="医院名称" />
          <ProFormText name="hospitalLevel" label="医院等级" placeholder="如：三级甲等" />
          <ProFormText name="address" label="医院地址" />
          <ProFormText name="phone" label="联系电话" />
          <ProFormText name="workTime" label="工作时间" placeholder="如：08:00-17:30" />
          <ProFormText name="logo" label="Logo URL" />
          <ProFormTextArea name="introduction" label="医院简介" fieldProps={{ rows: 4 }} />
        </ProForm>
      ),
    },
    {
      key: 'bookingFields',
      label: '预约选项配置',
      children: (
        <Table
          columns={fieldColumns}
          dataSource={bookingFields}
          rowKey="field"
          pagination={false}
          size="middle"
        />
      ),
    },
    {
      key: 'patientCard',
      label: '建卡名称配置',
      children: (
        <ProForm
          key={loading ? 'patientCard-loading' : 'patientCard-loaded'}
          onFinish={handlePatientCardSubmit}
          initialValues={{ ...DEFAULT_PATIENT_CARD_CONFIG, ...patientCardConfig }}
          submitter={{ searchConfig: { submitText: '保存设置' }, resetButtonProps: { style: { display: 'none' } } }}
        >
          <ProFormText
            name="cardName"
            label="名称修改"
            placeholder="如：xxx就诊卡"
            extra='修改前端"就诊卡"字样；所有涉及到"就诊卡"的地方都会修改'
          />
          <ProFormText
            name="cardDescription"
            label="描述文字"
            placeholder="如：医道至朴.德泽万方"
            fieldProps={{ maxLength: 16, showCount: true }}
            extra='修改前端添加"就诊卡"时；下方的详细描述文字；限16字以内'
          />
          <ProFormDigit
            name="maxCardsPerUser"
            label="可建就诊卡数量"
            min={1}
            max={20}
            fieldProps={{ precision: 0 }}
          />
          <ProFormSwitch name="showOnHomepage" label="首页是否展示" />
        </ProForm>
      ),
    },
    {
      key: 'blacklist',
      label: '爽约黑名单',
      children: (
        <div>
          <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between' }}>
            <Space>
              <span>用户：</span>
              <Input.Search
                placeholder="搜索(用户昵称/电话/身份证)"
                style={{ width: 280 }}
                onSearch={(val) => {
                  setBlacklistKeyword(val);
                  loadBlacklist(1, val);
                }}
                allowClear
              />
            </Space>
            {canEdit && (
              <Button type="primary" icon={<PlusOutlined />} onClick={() => setAddModalVisible(true)}>
                添加黑名单
              </Button>
            )}
          </div>
          <Text type="secondary" style={{ display: 'block', marginBottom: 16 }}>
            注：黑名单规则，如果只填关键词则判断就诊卡的手机号或者身份证，如果选择的是用户则该用户无法预约，选择门店只针对该门店不选择则针对所有门店
          </Text>
          <Table
            columns={blacklistColumns}
            dataSource={blacklist}
            rowKey="id"
            loading={blacklistLoading}
            pagination={{
              current: blacklistPage,
              total: blacklistTotal,
              pageSize: 20,
              showSizeChanger: false,
              onChange: (page) => loadBlacklist(page, blacklistKeyword),
            }}
            scroll={{ x: 1200 }}
            size="middle"
          />
        </div>
      ),
    },
    {
      key: 'email',
      label: '邮件配置',
      children: (
        <ProForm
          key={loading ? 'email-loading' : 'email-loaded'}
          onFinish={handleEmailConfigSubmit}
          initialValues={{ ...DEFAULT_EMAIL_CONFIG, ...emailConfig }}
          submitter={{ searchConfig: { submitText: '保存设置' }, resetButtonProps: { style: { display: 'none' } } }}
        >
          <Text type="secondary" style={{ display: 'block', marginBottom: 16 }}>
            配置SMTP服务器信息，用于发送邮件通知（如预约确认、就诊提醒等）。常见邮箱SMTP设置：QQ邮箱(smtp.qq.com:465)、163邮箱(smtp.163.com:465)、Gmail(smtp.gmail.com:587)
          </Text>
          <ProFormText
            name="smtpHost"
            label="SMTP服务器"
            placeholder="如：smtp.qq.com"
            rules={[{ required: true, message: '请输入SMTP服务器地址' }]}
          />
          <ProFormDigit
            name="smtpPort"
            label="SMTP端口"
            placeholder="如：465 或 587"
            min={1}
            max={65535}
            fieldProps={{ precision: 0 }}
            rules={[{ required: true, message: '请输入SMTP端口' }]}
          />
          <ProFormText
            name="smtpUser"
            label="SMTP用户名"
            placeholder="通常为邮箱地址"
            rules={[{ required: true, message: '请输入SMTP用户名' }]}
          />
          <ProFormText.Password
            name="smtpPassword"
            label="SMTP密码"
            placeholder="邮箱密码或授权码"
            rules={[{ required: true, message: '请输入SMTP密码' }]}
            extra="部分邮箱需要使用授权码而非登录密码"
            fieldProps={{ autoComplete: 'new-password' }}
          />
          <ProFormSwitch
            name="smtpSsl"
            label="使用SSL"
            extra="大多数邮箱服务器需要启用SSL"
          />
          <ProFormText
            name="senderName"
            label="发件人名称"
            placeholder="如：XX医院"
            rules={[{ required: true, message: '请输入发件人名称' }]}
          />
          <ProFormText
            name="senderEmail"
            label="发件人邮箱"
            placeholder="如：noreply@hospital.com"
            rules={[
              { required: true, message: '请输入发件人邮箱' },
              { type: 'email', message: '请输入正确的邮箱格式' },
            ]}
          />
        </ProForm>
      ),
    },
    {
      key: 'wechat',
      label: '微信配置',
      children: (
        <div>
          <Text type="secondary" style={{ display: 'block', marginBottom: 16 }}>
            每个门店可以配置独立的微信小程序。请先选择门店，然后配置对应的 AppID 和 Secret。在{' '}
            <a href="https://mp.weixin.qq.com" target="_blank" rel="noopener noreferrer">
              微信公众平台
            </a>{' '}
            → 开发管理 → 开发设置 中获取。
          </Text>
          
          <div style={{ marginBottom: 24 }}>
            <span style={{ marginRight: 8 }}>选择门店：</span>
            <Select
              style={{ width: 300 }}
              placeholder="请选择门店"
              value={selectedStoreId || undefined}
              onChange={handleStoreChange}
              options={stores.map((s) => ({ label: s.name, value: s.id }))}
              allowClear
            />
          </div>

          {selectedStoreId ? (
            <Spin spinning={wechatLoading}>
              <ProForm
                key={selectedStoreId}
                onFinish={handleStoreWechatConfigSubmit}
                initialValues={storeWechatConfig || {}}
                submitter={{ 
                  searchConfig: { submitText: '保存设置' }, 
                  resetButtonProps: { style: { display: 'none' } },
                  submitButtonProps: { disabled: !canEditWechat }
                }}
              >
                <ProFormText
                  name="appId"
                  label="小程序 AppID"
                  placeholder="请输入小程序 AppID"
                  rules={[{ required: true, message: '请输入小程序 AppID' }]}
                  extra="在微信公众平台 → 开发管理 → 开发设置 中获取"
                  disabled={!canEditWechat}
                />
                <ProFormText.Password
                  name="appSecret"
                  label="小程序 Secret"
                  placeholder="请输入小程序 Secret"
                  rules={[{ required: true, message: '请输入小程序 Secret' }]}
                  extra="Secret 是敏感信息，请妥善保管（已保存的密钥显示为 ******）"
                  fieldProps={{ autoComplete: 'new-password' }}
                  disabled={!canEditWechat}
                />
                <ProFormText
                  name="mchId"
                  label="商户号 (选填)"
                  placeholder="请输入微信支付商户号"
                  extra="如需使用微信支付功能，请填写商户号"
                  disabled={!canEditWechat}
                />
                <ProFormText.Password
                  name="apiKey"
                  label="API 密钥 (选填)"
                  placeholder="请输入微信支付 API 密钥"
                  extra="如需使用微信支付功能，请填写 API 密钥"
                  fieldProps={{ autoComplete: 'new-password' }}
                  disabled={!canEditWechat}
                />
                <ProFormText
                  name="notifyUrl"
                  label="支付回调地址 (选填)"
                  placeholder="如：https://your-domain.com/api/v1/wechat/pay/notify"
                  extra="微信支付结果通知的回调地址"
                  disabled={!canEditWechat}
                />
                {!canEditWechat && (
                  <Text type="warning" style={{ display: 'block', marginTop: 16 }}>
                    您没有修改微信配置的权限，仅可查看
                  </Text>
                )}
              </ProForm>
            </Spin>
          ) : (
            <div style={{ textAlign: 'center', padding: '40px 0', color: '#999' }}>
              请先选择门店以查看或编辑微信配置
            </div>
          )}
        </div>
      ),
    },
    {
      key: 'image',
      label: '图片处理配置',
      children: (
        <ProForm
          key={loading ? 'image-loading' : 'image-loaded'}
          onFinish={handleImageConfigSubmit}
          initialValues={{ ...DEFAULT_IMAGE_CONFIG, ...imageConfig }}
          submitter={{ searchConfig: { submitText: '保存设置' }, resetButtonProps: { style: { display: 'none' } } }}
        >
          <Text type="secondary" style={{ display: 'block', marginBottom: 16 }}>
            配置图片上传时的缩略图生成规则和压缩质量。上传时可选择是否生成缩略图。
          </Text>
          <ProFormDigit
            name="compressQuality"
            label="压缩质量"
            min={1}
            max={100}
            fieldProps={{ 
              precision: 0,
              addonAfter: '%',
            }}
            extra="图片压缩质量，1-100，值越高质量越好但文件越大，推荐 75-90"
          />
          <ProFormList
            name="thumbnailSizes"
            label="缩略图尺寸配置"
            creatorButtonProps={{
              creatorButtonText: '添加尺寸',
              icon: <PlusOutlined />,
            }}
            copyIconProps={false}
            deleteIconProps={{
              Icon: DeleteOutlined,
              tooltipText: '删除',
            }}
            itemRender={({ listDom, action }) => (
              <div style={{ display: 'flex', alignItems: 'flex-start', gap: 8 }}>
                {listDom}
                {action}
              </div>
            )}
          >
            <Space align="baseline">
              <ProFormText
                name="name"
                placeholder="名称，如 small"
                rules={[{ required: true, message: '请输入名称' }]}
                width="sm"
              />
              <ProFormDigit
                name="width"
                placeholder="宽度"
                min={1}
                max={4096}
                fieldProps={{ precision: 0, addonAfter: 'px' }}
                rules={[{ required: true, message: '请输入宽度' }]}
                width="sm"
              />
              <ProFormDigit
                name="height"
                placeholder="高度"
                min={1}
                max={4096}
                fieldProps={{ precision: 0, addonAfter: 'px' }}
                rules={[{ required: true, message: '请输入高度' }]}
                width="sm"
              />
            </Space>
          </ProFormList>
          <Text type="secondary">
            提示：缩略图会等比例缩放，保持原图宽高比，不会拉伸变形。宽度和高度表示缩略图的最大尺寸。
          </Text>
        </ProForm>
      ),
    },
  ];

  return (
    <PageContainer>
      <Spin spinning={loading}>
        <Card>
          <Tabs items={items} />
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
