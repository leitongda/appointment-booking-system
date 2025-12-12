import { PageContainer, ProForm, ProFormText, ProFormDigit, ProFormSwitch, ProFormTextArea } from '@ant-design/pro-components';
import { Card, App, Tabs, Spin } from 'antd';
import { useState, useEffect } from 'react';
import { settingsApi } from '@hospital/api';
import type { BookingSettings, HospitalInfo } from '@hospital/api';

const SettingsPage: React.FC = () => {
  const { message } = App.useApp();
  const [loading, setLoading] = useState(false);
  const [bookingSettings, setBookingSettings] = useState<BookingSettings | null>(null);
  const [hospitalInfo, setHospitalInfo] = useState<HospitalInfo | null>(null);

  useEffect(() => {
    loadSettings();
  }, []);

  const loadSettings = async () => {
    setLoading(true);
    try {
      const [booking, hospital] = await Promise.allSettled([
        settingsApi.getBookingSettings(),
        settingsApi.getHospitalInfo(),
      ]);
      if (booking.status === 'fulfilled') setBookingSettings(booking.value);
      if (hospital.status === 'fulfilled') setHospitalInfo(hospital.value);
    } catch (error) {
      console.error('加载配置失败', error);
    } finally {
      setLoading(false);
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
  ];

  return (
    <PageContainer>
      <Spin spinning={loading}>
        <Card>
          <Tabs items={items} />
        </Card>
      </Spin>
    </PageContainer>
  );
};

export default SettingsPage;
