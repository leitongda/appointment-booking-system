import { PageContainer, ProForm, ProFormText, ProFormTextArea, ProFormDigit, ProFormSelect, ProFormSwitch, ProFormRadio } from '@ant-design/pro-components';
import { Card, App, Row, Col } from 'antd';
import { useEffect, useState } from 'react';
import { history, useParams } from '@umijs/max';
import { doctorApi, departmentApi, storeApi } from '@hospital/api';
import type { Doctor, Department, Store } from '@hospital/shared';

const GENDER_OPTIONS = [
  { label: '男', value: 1 },
  { label: '女', value: 0 },
];

const PAGE_STYLE_OPTIONS = [
  { label: '风格1', value: 1 },
  { label: '风格2', value: 2 },
  { label: '风格3', value: 3 },
];

const EDUCATION_OPTIONS = [
  { label: '专科', value: '专科' },
  { label: '本科', value: '本科' },
  { label: '硕士', value: '硕士' },
  { label: '博士', value: '博士' },
  { label: '博士后', value: '博士后' },
];

const DoctorFormPage: React.FC = () => {
  const { message } = App.useApp();
  const { id } = useParams<{ id: string }>();
  const isEdit = !!id;
  const [loading, setLoading] = useState(false);
  const [doctor, setDoctor] = useState<Doctor | null>(null);
  const [departments, setDepartments] = useState<Department[]>([]);
  const [stores, setStores] = useState<Store[]>([]);

  useEffect(() => {
    loadDepartments();
    loadStores();
    if (isEdit) {
      loadDoctor();
    }
  }, [id]);

  const loadDepartments = async () => {
    try {
      const res = await departmentApi.getList({ pageSize: 100, status: 1 });
      setDepartments(res.data ?? []);
    } catch (error) {
      console.error('加载科室失败', error);
    }
  };

  const loadStores = async () => {
    try {
      const res = await storeApi.getList({ pageSize: 100, status: 1 });
      setStores(res.data ?? []);
    } catch (error) {
      console.error('加载门店失败', error);
    }
  };

  const loadDoctor = async () => {
    if (!id) return;
    setLoading(true);
    try {
      const data = await doctorApi.getDetail(id);
      setDoctor(data);
    } catch (error: any) {
      message.error('加载医生信息失败');
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (values: any) => {
    const data = {
      ...values,
      isRecommended: values.isRecommended ? 1 : 0,
      onlineConsultEnabled: values.onlineConsultEnabled ? 1 : 0,
      status: values.status ? 1 : 0,
    };

    try {
      if (isEdit && id) {
        await doctorApi.update(id, data);
        message.success('更新成功');
      } else {
        await doctorApi.create(data);
        message.success('创建成功');
      }
      history.push('/doctor/list');
    } catch (error: any) {
      message.error(error.message || '操作失败');
    }
  };

  const initialValues = doctor ? {
    ...doctor,
    isRecommended: doctor.isRecommended === 1,
    onlineConsultEnabled: doctor.onlineConsultEnabled === 1,
    status: doctor.status === 1,
  } : {
    gender: 1,
    yearsOfExperience: 0,
    maxDailyAppointments: 0,
    onlineConsultEnabled: false,
    onlineConsultFee: 0,
    registrationFee: 0,
    pageStyle: 1,
    sortOrder: 0,
    isRecommended: false,
    status: true,
  };

  return (
    <PageContainer title={isEdit ? '编辑医生' : '新增医生'}>
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
        {/* 基础信息 */}
        <Card title="基础信息" style={{ marginBottom: 16 }} loading={loading}>
          <ProForm.Group>
            <ProFormText
              name="name"
              label="医生姓名"
              width="md"
              rules={[{ required: true, message: '请输入医生姓名' }]}
            />
            <ProFormRadio.Group
              name="gender"
              label="性别"
              options={GENDER_OPTIONS}
            />
            <ProFormSelect
              name="storeId"
              label="所属门店"
              width="md"
              options={(stores ?? []).map((s) => ({ label: s.name, value: s.id }))}
              placeholder="请选择门店"
            />
          </ProForm.Group>
          <ProForm.Group>
            <ProFormText
              name="username"
              label="医生账号"
              width="md"
              placeholder="用于医生端登录"
              rules={[{ required: true, message: '请输入医生账号' }]}
            />
            {!isEdit && (
              <ProFormText.Password
                name="password"
                label="医生密码"
                width="md"
                placeholder="医生端登录密码"
                rules={[{ required: true, message: '请输入登录密码' }]}
              />
            )}
          </ProForm.Group>
          <ProForm.Group>
            <ProFormText
              name="avatar"
              label="医生头像"
              width="lg"
              placeholder="图片URL，推荐尺寸：160px × 160px，≤100KB"
              tooltip="1:1比例，推荐尺寸：160px × 160px"
            />
          </ProForm.Group>
          <ProForm.Group>
            <ProFormText
              name="banner"
              label="医生banner"
              width="lg"
              placeholder="图片URL，推荐尺寸：680px × 300px，≤300KB"
              tooltip="16:9比例，若选择医生风格3，请务必上传banner图"
            />
          </ProForm.Group>
          <ProForm.Group>
            <ProFormSelect
              name="departmentId"
              label="所属科室"
              width="md"
              options={(departments ?? []).map((d) => ({ label: d.name, value: d.id }))}
              rules={[{ required: true, message: '请选择科室' }]}
            />
            <ProFormText
              name="title"
              label="职称"
              width="md"
              placeholder="如：国家注册中医医师"
            />
            <ProFormDigit
              name="yearsOfExperience"
              label="医龄(年)"
              width="sm"
              min={0}
              fieldProps={{ precision: 0 }}
            />
          </ProForm.Group>
          <ProFormText name="phone" label="手机号" width="md" />
        </Card>

        {/* 资质信息 */}
        <Card title="资质信息" style={{ marginBottom: 16 }} loading={loading}>
          <ProForm.Group>
            <ProFormSelect
              name="education"
              label="学历"
              width="sm"
              options={EDUCATION_OPTIONS}
              placeholder="请选择"
            />
            <ProFormText
              name="graduateSchool"
              label="毕业院校"
              width="md"
              placeholder="如：重庆市中医大学"
            />
          </ProForm.Group>
          <ProForm.Group>
            <ProFormText
              name="licenseNumber"
              label="执业证书编号"
              width="md"
              placeholder="请输入执业证书编号"
            />
            <ProFormText
              name="licenseImage"
              label="执业证书图片"
              width="lg"
              placeholder="执业证书图片URL"
            />
          </ProForm.Group>
          <ProFormTextArea
            name="honors"
            label="所获荣誉"
            placeholder="如：国家认证的第三批老中医学术继承人"
            fieldProps={{ rows: 3 }}
          />
        </Card>

        {/* 坐诊设置 */}
        <Card title="坐诊设置" style={{ marginBottom: 16 }} loading={loading}>
          <ProFormText
            name="scheduleDesc"
            label="坐诊时间说明"
            width="lg"
            placeholder="如：每周一、三、五上午"
          />
          <ProForm.Group>
            <ProFormDigit
              name="maxDailyAppointments"
              label="每日最大接诊量"
              width="sm"
              min={0}
              fieldProps={{ precision: 0 }}
              tooltip="0表示不限制"
              addonAfter="人"
            />
            <ProFormDigit
              name="registrationFee"
              label="挂号费"
              width="sm"
              min={0}
              addonAfter="元"
            />
          </ProForm.Group>
          <ProForm.Group>
            <ProFormSwitch
              name="onlineConsultEnabled"
              label="支持在线问诊"
            />
            <ProFormDigit
              name="onlineConsultFee"
              label="在线问诊费用"
              width="sm"
              min={0}
              addonAfter="元"
            />
          </ProForm.Group>
        </Card>

        {/* 展示设置 */}
        <Card title="展示设置" style={{ marginBottom: 16 }} loading={loading}>
          <ProForm.Group>
            <ProFormRadio.Group
              name="pageStyle"
              label="页面风格"
              options={PAGE_STYLE_OPTIONS}
              tooltip="选择医生详情页的展示风格"
            />
          </ProForm.Group>
          <ProFormText
            name="promoVideo"
            label="宣传视频"
            width="lg"
            placeholder="视频URL"
          />
          <ProFormText
            name="tags"
            label="标签"
            width="lg"
            placeholder="多个标签用逗号分隔，如：减肥,多囊,失眠"
            tooltip="用于搜索和展示"
          />
          <ProFormTextArea
            name="specialty"
            label="擅长"
            placeholder="医生擅长领域"
            fieldProps={{ rows: 4 }}
          />
          <ProFormTextArea
            name="introduction"
            label="医生介绍"
            placeholder="医生详细介绍"
            fieldProps={{ rows: 6 }}
          />
        </Card>

        {/* 其他设置 */}
        <Card title="其他设置" loading={loading}>
          <ProForm.Group>
            <ProFormDigit
              name="sortOrder"
              label="排序"
              width="sm"
              min={0}
              fieldProps={{ precision: 0 }}
              tooltip="数字越大越靠前"
            />
            <ProFormSwitch name="isRecommended" label="是否推荐" />
            <ProFormSwitch name="status" label="启用状态" />
          </ProForm.Group>
        </Card>
      </ProForm>
    </PageContainer>
  );
};

export default DoctorFormPage;
