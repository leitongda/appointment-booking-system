import {
  PageContainer,
  ProForm,
  ProFormText,
  ProFormDigit,
  ProFormSwitch,
  ProFormTextArea,
  ProFormDateTimePicker,
  ProFormSelect,
  ModalForm,
} from '@ant-design/pro-components';
import { Card, App, Tabs, Spin, Table, Switch, Button, Input, Space, Popconfirm, Tag, Select, Form, Typography } from 'antd';
import { PlusOutlined, SearchOutlined } from '@ant-design/icons';
import { useState, useEffect, useRef } from 'react';
import { useAccess } from '@umijs/max';
import { settingsApi, blacklistApi, storeApi } from '@hospital/api';
import type { BookingSettings, HospitalInfo, BookingFieldConfig, PatientCardConfig, BlacklistItem, EmailConfig } from '@hospital/api';

const { Text } = Typography;

const SettingsPage: React.FC = () => {
  const { message } = App.useApp();
  const access = useAccess();
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
  const canEdit = access.hasPermission('system:settings');

  useEffect(() => {
    loadSettings();
    loadStores();
  }, []);

  const loadSettings = async () => {
    setLoading(true);
    try {
      const [booking, hospital, fields, cardConfig, email] = await Promise.allSettled([
        settingsApi.getBookingSettings(),
        settingsApi.getHospitalInfo(),
        settingsApi.getBookingFields(),
        settingsApi.getPatientCardConfig(),
        settingsApi.getEmailConfig(),
      ]);
      if (booking.status === 'fulfilled') setBookingSettings(booking.value);
      if (hospital.status === 'fulfilled') setHospitalInfo(hospital.value);
      if (fields.status === 'fulfilled') setBookingFields(fields.value);
      if (cardConfig.status === 'fulfilled') setPatientCardConfig(cardConfig.value);
      if (email.status === 'fulfilled') setEmailConfig(email.value);
    } catch (error) {
      console.error('加载配置失败', error);
    } finally {
      setLoading(false);
    }
    loadBlacklist();
  };

  const loadStores = async () => {
    try {
      const res = await storeApi.getList({ pageSize: 100, status: 1 });
      setStores(res.data ?? []);
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
      await settingsApi.updateBookingSettings(values);
      message.success('保存成功');
    } catch (error: any) {
      message.error(error.message || '保存失败');
    }
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
      label: '预约设置',
      children: (
        <ProForm
          onFinish={handleBookingSubmit}
          initialValues={bookingSettings || {}}
          submitter={{ searchConfig: { submitText: '保存设置' }, resetButtonProps: { style: { display: 'none' } } }}
        >
          <ProFormDigit name="advanceDays" label="提前预约天数" min={1} max={30} fieldProps={{ addonAfter: '天' }} />
          <ProFormDigit name="cancelHours" label="取消提前小时数" min={1} max={48} fieldProps={{ addonAfter: '小时' }} />
          <ProFormDigit name="perDayLimit" label="每人每天最大预约数" min={1} max={10} />
          <ProFormDigit name="perDoctorLimit" label="每人每医生最大预约数" min={1} max={5} />
          <ProFormDigit name="noShowLimit" label="爽约次数限制" min={1} max={10} />
          <ProFormDigit name="blacklistDays" label="黑名单限制天数" min={1} max={365} fieldProps={{ addonAfter: '天' }} />
          <ProFormSwitch name="sameDayBooking" label="允许当天预约" />
        </ProForm>
      ),
    },
    {
      key: 'hospital',
      label: '医院信息',
      children: (
        <ProForm
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
          onFinish={handlePatientCardSubmit}
          initialValues={patientCardConfig || {}}
          submitter={{ searchConfig: { submitText: '保存设置' }, resetButtonProps: { style: { display: 'none' } } }}
        >
          <ProFormText
            name="cardName"
            label="名称修改"
            placeholder="如：朴泽堂就诊卡"
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
          onFinish={handleEmailConfigSubmit}
          initialValues={emailConfig || {}}
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
