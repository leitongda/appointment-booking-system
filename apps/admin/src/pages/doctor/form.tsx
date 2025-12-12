import { PageContainer, ProForm, ProFormText, ProFormTextArea, ProFormDigit, ProFormSelect, ProFormSwitch } from '@ant-design/pro-components';
import { Card, App } from 'antd';
import { useEffect, useState } from 'react';
import { history, useParams } from '@umijs/max';
import { doctorApi, departmentApi } from '@hospital/api';
import type { Doctor, Department } from '@hospital/shared';

const DoctorFormPage: React.FC = () => {
  const { message } = App.useApp();
  const { id } = useParams<{ id: string }>();
  const isEdit = !!id;
  const [loading, setLoading] = useState(false);
  const [doctor, setDoctor] = useState<Doctor | null>(null);
  const [departments, setDepartments] = useState<Department[]>([]);

  useEffect(() => {
    loadDepartments();
    if (isEdit) {
      loadDoctor();
    }
  }, [id]);

  const loadDepartments = async () => {
    try {
      const res = await departmentApi.getList({ pageSize: 100, status: 1 });
      setDepartments(res.data);
    } catch (error) {
      console.error('加载科室失败', error);
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

  return (
    <PageContainer title={isEdit ? '编辑医生' : '新增医生'}>
      <Card loading={loading}>
        <ProForm
          onFinish={handleSubmit}
          initialValues={doctor ? {
            ...doctor,
            isRecommended: doctor.isRecommended === 1,
            status: doctor.status === 1,
          } : { sortOrder: 0, registrationFee: 0, isRecommended: false, status: true }}
          submitter={{
            searchConfig: { submitText: isEdit ? '保存' : '创建' },
            resetButtonProps: { style: { display: 'none' } },
          }}
        >
          <ProForm.Group>
            <ProFormSelect
              name="departmentId"
              label="所属科室"
              width="md"
              options={departments.map((d) => ({ label: d.name, value: d.id }))}
              rules={[{ required: true, message: '请选择科室' }]}
            />
            <ProFormText
              name="name"
              label="医生姓名"
              width="md"
              rules={[{ required: true, message: '请输入医生姓名' }]}
            />
          </ProForm.Group>
          <ProForm.Group>
            <ProFormText name="phone" label="手机号" width="md" />
            <ProFormText name="title" label="职称" width="md" placeholder="如：主任医师" />
          </ProForm.Group>
          <ProFormText name="avatar" label="头像URL" />
          <ProFormText name="specialty" label="专长" placeholder="医生专长领域" />
          <ProFormTextArea name="introduction" label="简介" placeholder="医生简介" />
          <ProForm.Group>
            <ProFormDigit name="registrationFee" label="挂号费" width="sm" min={0} addonAfter="元" />
            <ProFormDigit name="sortOrder" label="排序" width="sm" min={0} />
          </ProForm.Group>
          <ProForm.Group>
            <ProFormSwitch name="isRecommended" label="推荐医生" />
            <ProFormSwitch name="status" label="启用状态" />
          </ProForm.Group>
          {!isEdit && (
            <ProFormText.Password
              name="password"
              label="登录密码"
              width="md"
              placeholder="医生端登录密码"
              rules={[{ required: true, message: '请输入登录密码' }]}
            />
          )}
        </ProForm>
      </Card>
    </PageContainer>
  );
};

export default DoctorFormPage;
