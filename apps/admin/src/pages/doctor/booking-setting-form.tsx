import { PageContainer, ProForm, ProFormSelect, ProFormDigit, ProFormTimePicker, FooterToolbar } from '@ant-design/pro-components';
import type { ProFormInstance } from '@ant-design/pro-components';
import { Card, App, Button, Space, Alert, Descriptions, Typography, Tag } from 'antd';
import { ClockCircleOutlined, CalendarOutlined, InfoCircleOutlined } from '@ant-design/icons';
import { useEffect, useState, useRef, useMemo } from 'react';
import { history, useParams, useAccess, useModel } from '@umijs/max';
import { doctorBookingSettingApi, storeApi, doctorApi } from '@hospital/api';
import type { DoctorBookingSetting, Store, Doctor } from '@hospital/shared';
import dayjs from 'dayjs';
import type { Dayjs } from 'dayjs';

const { Text } = Typography;

const DoctorBookingSettingFormPage: React.FC = () => {
  const { message } = App.useApp();
  const { id } = useParams();
  const access = useAccess();
  const { initialState } = useModel('@@initialState');
  const { currentUser } = initialState ?? {};
  const isSuperAdmin = access.canSuperAdmin;
  const isEdit = !!id;
  const [loading, setLoading] = useState(false);
  const [setting, setSetting] = useState<DoctorBookingSetting | null>(null);
  const [stores, setStores] = useState<Store[]>([]);
  const [doctors, setDoctors] = useState<Doctor[]>([]);
  const [existingDoctorIds, setExistingDoctorIds] = useState<string[]>([]);
  const [selectedStoreId, setSelectedStoreId] = useState<string>();
  const formRef = useRef<ProFormInstance>();
  const [previewValues, setPreviewValues] = useState<{
    bookingStartOffset?: number;
    bookingRangeDays?: number;
    releaseTime?: Dayjs;
  }>({
    bookingStartOffset: 0,
    bookingRangeDays: 14,
    releaseTime: dayjs('00:00', 'HH:mm'),
  });

  async function loadStores() {
    try {
      const data = await storeApi.getAll();
      let storeList = data ?? [];
      // 非超管只显示其关联的门店
      if (!isSuperAdmin && currentUser?.storeIds?.length) {
        storeList = storeList.filter((s) => currentUser.storeIds?.includes(s.id));
      }
      setStores(storeList);
    } catch (error) {
      console.error('加载门店失败', error);
    }
  }

  async function loadDoctorsByStore(storeId: string) {
    try {
      const data = await doctorApi.getByStore(storeId);
      setDoctors(data ?? []);
    } catch (error) {
      console.error('加载医生失败', error);
    }
  }

  async function loadExistingDoctorIds(storeId: string) {
    try {
      const ids = await doctorBookingSettingApi.getExistingDoctorIds(storeId);
      setExistingDoctorIds(ids ?? []);
    } catch (error) {
      console.error('加载已配置医生失败', error);
    }
  }

  function getValidReleaseTime(timeStr?: string) {
    if (!timeStr) return dayjs('00:00', 'HH:mm');
    const parsed = dayjs(timeStr, 'HH:mm');
    return parsed.isValid() ? parsed : dayjs('00:00', 'HH:mm');
  }

  async function loadSetting() {
    if (!id) return;
    setLoading(true);
    try {
      const data = await doctorBookingSettingApi.getDetail(id);
      setSetting(data);
      if (data.storeId) {
        setSelectedStoreId(data.storeId);
      }
      // 异步加载完成后，使用 setFieldsValue 更新表单值
      const releaseTimeVal = getValidReleaseTime(data.releaseTime);
      formRef.current?.setFieldsValue({
        storeId: data.storeId,
        doctorId: data.doctorId,
        bookingStartOffset: data.bookingStartOffset,
        bookingRangeDays: data.bookingRangeDays,
        releaseTime: releaseTimeVal,
      });
      setPreviewValues({
        bookingStartOffset: data.bookingStartOffset,
        bookingRangeDays: data.bookingRangeDays,
        releaseTime: releaseTimeVal,
      });
    } catch (error: any) {
      message.error('加载预约设置失败');
    } finally {
      setLoading(false);
    }
  }

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

  const previewResult = useMemo(() => {
    const { bookingStartOffset = 0, bookingRangeDays = 14, releaseTime } = previewValues;
    const today = dayjs();
    const startDate = today.add(bookingStartOffset, 'day');
    const endDate = startDate.add(bookingRangeDays - 1, 'day');
    const offsetLabel = bookingStartOffset === 0
      ? '当天'
      : bookingStartOffset === 1
        ? '第2天'
        : `第${bookingStartOffset + 1}天`;
    const releaseTimeStr = releaseTime?.isValid()
      ? releaseTime.format('HH:mm')
      : '00:00';
    const isImmediate = releaseTimeStr === '00:00';

    return {
      startDate,
      endDate,
      offsetLabel,
      releaseTimeStr,
      isImmediate,
      today,
    };
  }, [previewValues]);

  const handleSubmit = async (values: any) => {
    try {
      const releaseTimeValue = dayjs(values.releaseTime);
      const releaseTime = releaseTimeValue.isValid()
        ? releaseTimeValue.format('HH:mm')
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
      history.push('/medical-services/doctor/booking-setting');
    } catch (error: any) {
      message.error(error.message || '操作失败');
    }
  };

  const initialValues = setting ? {
    storeId: setting.storeId,
    doctorId: setting.doctorId,
    bookingStartOffset: setting.bookingStartOffset,
    bookingRangeDays: setting.bookingRangeDays,
    releaseTime: getValidReleaseTime(setting.releaseTime),
  } : {
    bookingStartOffset: 0,
    bookingRangeDays: 14,
    releaseTime: dayjs('00:00', 'HH:mm'),
  };

  return (
    <PageContainer title={isEdit ? '编辑医生预约设置' : '添加医生预约管理'}>
      <ProForm
        formRef={formRef}
        onFinish={handleSubmit}
        initialValues={initialValues}
        onValuesChange={(changedValues, allValues) => {
          setPreviewValues((prev) => ({
            ...prev,
            bookingStartOffset: allValues.bookingStartOffset ?? prev.bookingStartOffset,
            bookingRangeDays: allValues.bookingRangeDays ?? prev.bookingRangeDays,
            releaseTime: allValues.releaseTime ?? prev.releaseTime,
          }));
        }}
        submitter={{
          render: (props, _dom) => (
            <FooterToolbar>
              <Space>
                <Button onClick={() => history.back()}>取消</Button>
                <Button type="primary" onClick={() => props.form?.submit()}>
                  {isEdit ? '保存' : '创建'}
                </Button>
              </Space>
            </FooterToolbar>
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

        <Card
          title={
            <Space>
              <InfoCircleOutlined />
              <span>配置预览</span>
            </Space>
          }
          size="small"
          style={{ marginTop: 16 }}
          styles={{ body: { padding: '16px 24px' } }}
        >
          <Alert
            type="info"
            showIcon
            icon={<CalendarOutlined />}
            style={{ marginBottom: 12 }}
            title={
              <Text>
                患者可预约{' '}
                <Text strong>
                  {previewResult.startDate.format('M月D日(dd)')}
                </Text>
                {' '}~{' '}
                <Text strong>
                  {previewResult.endDate.format('M月D日(dd)')}
                </Text>
                {' '}的排班
                <Text type="secondary" style={{ marginLeft: 8 }}>
                  (共 {previewValues.bookingRangeDays ?? 14} 天)
                </Text>
              </Text>
            }
          />
          <Descriptions size="small" column={{ xs: 1, sm: 2, md: 3 }}>
            <Descriptions.Item label="开始日期">
              <Tag color="blue">{previewResult.offsetLabel}</Tag>
              <Text type="secondary" style={{ marginLeft: 4 }}>
                ({previewResult.startDate.format('YYYY-MM-DD')})
              </Text>
            </Descriptions.Item>
            <Descriptions.Item label="截止日期">
              <Text strong>{previewResult.endDate.format('YYYY-MM-DD')}</Text>
            </Descriptions.Item>
            <Descriptions.Item label="放号规则">
              {previewResult.isImmediate ? (
                <Space size={4}>
                  <ClockCircleOutlined />
                  <Text>全天开放，不限制放号时间</Text>
                </Space>
              ) : (
                <Space size={4}>
                  <ClockCircleOutlined />
                  <Text>
                    每天 <Text strong>{previewResult.releaseTimeStr}</Text> 释放新号源
                  </Text>
                </Space>
              )}
            </Descriptions.Item>
          </Descriptions>
        </Card>
      </ProForm>
    </PageContainer>
  );
};

export default DoctorBookingSettingFormPage;

