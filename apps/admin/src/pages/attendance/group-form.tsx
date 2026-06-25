/**
 * 签到组表单页面
 *
 * 使用基础设施：
 * - FormPage 组件：统一表单页面布局
 * - useFormInitialValues hook：初始值处理
 * - useFormSubmit hook：提交处理
 */
import {
  ProFormText,
  ProFormTextArea,
  ProFormInputNumber,
  ProFormSwitch,
  ProFormSelect,
} from '@ant-design/pro-components';
import { Card, message } from 'antd';
import { useParams, history } from '@umijs/max';
import { useEffect, useState } from 'react';
import { attendanceApi } from '@hospital/api';
import type { AttendanceGroup } from '@hospital/api';

// 基础设施导入
import FormPage from '@/components/FormPage';
import { useFormInitialValues } from '@/hooks/useFormInitialValues';
import { useFormSubmit } from '@/hooks/useFormSubmit';
import { requiredRules } from '@/utils/formValidators';

/** 签到方式选项 */
const CHECK_METHOD_OPTIONS = [
  { label: 'GPS 定位', value: 'gps' },
  { label: 'WiFi 验证', value: 'wifi' },
  { label: '设备绑定', value: 'device' },
];

const GroupFormPage: React.FC = () => {
  const { id } = useParams();
  const isEdit = !!id;
  const [group, setGroup] = useState<AttendanceGroup | null>(null);
  const [loading, setLoading] = useState(false);

  // 加载签到组数据
  useEffect(() => {
    if (isEdit && id) {
      setLoading(true);
      attendanceApi.getGroupById(id)
        .then(setGroup)
        .catch(() => {
          message.error('加载签到组失败');
          history.back();
        })
        .finally(() => setLoading(false));
    }
  }, [id]);

  // 使用 useFormInitialValues hook
  const { initialValues } = useFormInitialValues<AttendanceGroup>(
    group,
    {
      switchFields: ['enabled'],
      defaults: { enabled: true, checkMethod: 'gps', locationRadius: 300 },
    }
  );

  // 使用 useFormSubmit hook
  const { handleSubmit, submitting } = useFormSubmit(
    async (values: any) => {
      if (isEdit && id) {
        return attendanceApi.updateGroup(id, values);
      } else {
        return attendanceApi.createGroup(values);
      }
    },
    {
      switchFields: ['enabled'],
      onSuccess: () => history.push('/attendance/groups'),
      successMessage: isEdit ? '更新成功' : '创建成功',
    }
  );

  return (
    <FormPage
      title={isEdit ? '编辑签到组' : '新增签到组'}
      loading={loading}
      submitting={submitting}
      initialValues={initialValues}
      onFinish={handleSubmit}
      onCancel={() => history.back()}
      saveText={isEdit ? '保存' : '创建'}
    >
      <Card title="基本信息">
        <ProFormText
          name="name"
          label="组名称"
          width="lg"
          placeholder="如：总部门诊签到组"
          rules={[requiredRules('请输入签到组名称')]}
          fieldProps={{
            showCount: true,
            maxLength: 100,
          }}
        />

        <ProFormTextArea
          name="description"
          label="描述"
          width="lg"
          fieldProps={{
            rows: 3,
            showCount: true,
            maxLength: 500,
          }}
          placeholder="请输入签到组的详细描述"
        />

        <ProFormSelect
          name="checkMethod"
          label="签到方式"
          width="md"
          options={CHECK_METHOD_OPTIONS}
          rules={[requiredRules('请选择签到方式')]}
          extra="GPS：基于地理位置签到；WiFi：连接指定WiFi签到；设备：绑定设备签到"
        />
      </Card>

      <Card title="位置设置" style={{ marginTop: 16 }}>
        <ProFormInputNumber
          name="locationLat"
          label="纬度"
          width="md"
          fieldProps={{
            precision: 6,
            step: 0.000001,
          }}
          extra="签到地点纬度（中国境内：3.8 ~ 53.5）"
        />

        <ProFormInputNumber
          name="locationLng"
          label="经度"
          width="md"
          fieldProps={{
            precision: 6,
            step: 0.000001,
          }}
          extra="签到地点经度（中国境内：73.5 ~ 135.5）"
        />

        <ProFormInputNumber
          name="locationRadius"
          label="签到半径（米）"
          width="md"
          min={50}
          max={5000}
          fieldProps={{
            precision: 0,
          }}
          extra="签到有效范围半径，默认300米"
        />
      </Card>

      <Card title="WiFi 设置" style={{ marginTop: 16 }}>
        <ProFormText
          name="wifiSsid"
          label="WiFi 名称 (SSID)"
          width="lg"
          placeholder="如：Office-WiFi"
          extra="签到方式为 WiFi 时必填，用于验证连接的WiFi是否匹配"
        />
      </Card>

      <Card title="状态" style={{ marginTop: 16 }}>
        <ProFormSwitch
          name="enabled"
          label="启用状态"
          extra="禁用后该签到组将无法使用"
        />
      </Card>
    </FormPage>
  );
};

export default GroupFormPage;
