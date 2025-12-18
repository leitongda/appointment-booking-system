import { PageContainer, ProForm, ProFormSelect, ProFormDigit, ProFormTimePicker } from '@ant-design/pro-components';
import { Card, App, Row, Col } from 'antd';
import { useEffect, useState } from 'react';
import { history, useParams } from '@umijs/max';
import { doctorBookingSettingApi, storeApi, doctorApi } from '@hospital/api';
import type { DoctorBookingSetting, Store, Doctor } from '@hospital/shared';
import dayjs from 'dayjs';

const DoctorBookingSettingFormPage: React.FC = () => {
  const { message } = App.useApp();
  const { id } = useParams<{ id: string }>();
  const isEdit = !!id;
  const [loading, setLoading] = useState(false);
  const [setting, setSetting] = useState<DoctorBookingSetting | null>(null);
  const [stores, setStores] = useState<Store[]>([]);
  const [doctors, setDoctors] = useState<Doctor[]>([]);
  const [existingDoctorIds, setExistingDoctorIds] = useState<string[]>([]);
  const [selectedStoreId, setSelectedStoreId] = useState<string>();

  useEffect(() => {
    loadStores();
    if (isEdit) {
      loadSetting();
    }
  }, [id]);

  useEffect(() => {
    if (selectedStoreId) {
      loadDoctorsByStore(selectedStoreId);
      if (!isEdit) {
        loadExistingDoctorIds(selectedStoreId);
      }
    } else {
      setDoctors([]);
      setExistingDoctorIds([]);
    }
  }, [selectedStoreId]);

  const loadStores = async () => {
    try {
      const data = await storeApi.getAll();
      setStores(data ?? []);
    } catch (error) {
      console.error('加载门店失败', error);
    }
  };

  const loadDoctorsByStore = async (storeId: string) => {
    try {
      const data = await doctorApi.getByStore(storeId);
      setDoctors(data ?? []);
    } catch (error) {
      console.error('加载医生失败', error);
    }
  };

  const loadExistingDoctorIds = async (storeId: string) => {
    try {
      const ids = await doctorBookingSettingApi.getExistingDoctorIds(storeId);
      setExistingDoctorIds(ids ?? []);
    } catch (error) {
      console.error('加载已配置医生失败', error);
    }
  };

  const loadSetting = async () => {
    if (!id) return;
    setLoading(true);
    try {
      const data = await doctorBookingSettingApi.getDetail(id);
      setSetting(data);
      if (data.storeId) {
        setSelectedStoreId(data.storeId);
      }
    } catch (error: any) {
      message.error('加载预约设置失败');
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (values: any) => {
    try {
      const releaseTime = values.releaseTime
        ? dayjs(values.releaseTime).format('HH:mm')
        : '00:00';

      const data = {
        ...values,
        releaseTime,
        status: 1,
      };

      if (isEdit && id) {
        await doctorBookingSettingApi.update(id, {
          bookingStartOffset: data.bookingStartOffset,
          bookingRangeDays: data.bookingRangeDays,
          releaseTime: data.releaseTime,
        });
        message.success('更新成功');
      } else {
        await doctorBookingSettingApi.create(data);
        message.success('创建成功');
      }
      history.push('/doctor/booking-setting');
    } catch (error: any) {
      message.error(error.message || '操作失败');
    }
  };

  const initialValues = setting ? {
    storeId: setting.storeId,
    doctorId: setting.doctorId,
    bookingStartOffset: setting.bookingStartOffset,
    bookingRangeDays: setting.bookingRangeDays,
    releaseTime: setting.releaseTime
      ? dayjs(setting.releaseTime, 'HH:mm')
      : dayjs('00:00', 'HH:mm'),
  } : {
    bookingStartOffset: 0,
    bookingRangeDays: 14,
    releaseTime: dayjs('00:00', 'HH:mm'),
  };

  return (
    <PageContainer title={isEdit ? '编辑医生预约设置' : '添加医生预约管理'}>
      <ProForm
        onFinish={handleSubmit}
        initialValues={initialValues}
        submitter={{
          searchConfig: { submitText: isEdit ? '保存' : '创建' },
          resetButtonProps: { style: { display: 'none' } },
          render: (_, dom) => (
            <Row>
              <Col span={24} style={{ textAlign: 'center' }}>
                {dom}
              </Col>
            </Row>
          ),
        }}
      >
        <Card title="预约设置" loading={loading}>
          <ProForm.Group>
            <ProFormSelect
              name="storeId"
              label="选择门店"
              width="md"
              placeholder="请选择门店"
              options={(stores ?? []).map((s) => ({ label: s.name, value: s.id }))}
              rules={[{ required: true, message: '请选择门店' }]}
              disabled={isEdit}
              fieldProps={{
                onChange: (val) => setSelectedStoreId(val as string),
              }}
            />
            <ProFormSelect
              name="doctorId"
              label="医生"
              width="md"
              placeholder="请先选择门店"
              options={(doctors ?? []).map((d) => ({
                label: d.name + (d.title ? ` - ${d.title}` : ''),
                value: d.id,
                disabled: !isEdit && existingDoctorIds.includes(d.id),
              }))}
              rules={[{ required: true, message: '请选择医生' }]}
              disabled={isEdit || !selectedStoreId}
              tooltip="已禁用表示已存在于当前预约列表的医生，无需再重复添加"
            />
          </ProForm.Group>

          <ProForm.Group>
            <ProFormDigit
              name="bookingStartOffset"
              label="预约开始日期"
              width="md"
              placeholder="请输入"
              min={0}
              max={30}
              rules={[{ required: true, message: '请输入预约开始日期' }]}
              tooltip="0表示从当天开始预约，1表示从第二天开始预约，2表示从第三天开始预约，n表示从n+1天开始预约"
              fieldProps={{ precision: 0 }}
            />
            <ProFormDigit
              name="bookingRangeDays"
              label="预约范围/天"
              width="md"
              placeholder="请输入预约范围，数字型"
              min={1}
              max={90}
              rules={[
                { required: true, message: '请输入预约范围' },
                {
                  type: 'number',
                  min: 1,
                  max: 90,
                  message: '请输入1-90以内的数字',
                },
              ]}
              tooltip="开放的预约天数，请输入1-90以内的数字"
              fieldProps={{ precision: 0 }}
            />
          </ProForm.Group>

          <ProFormTimePicker
            name="releaseTime"
            label="放号时间"
            width="md"
            placeholder="请选择放号时间"
            rules={[{ required: true, message: '请选择放号时间' }]}
            fieldProps={{
              format: 'HH:mm',
              minuteStep: 5,
            }}
          />
        </Card>
      </ProForm>
    </PageContainer>
  );
};

export default DoctorBookingSettingFormPage;

