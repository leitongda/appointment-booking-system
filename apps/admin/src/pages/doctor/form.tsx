import { PageContainer, ProForm, ProFormText, ProFormTextArea, ProFormDigit, ProFormSelect, ProFormSwitch, ProFormMoney } from '@ant-design/pro-components';
import { Card, message, Button, Space } from 'antd';
import { history, useParams, useRequest } from 'umi';
import { doctorApi, departmentApi } from '@hospital/api';
import { DOCTOR_TITLE_MAP } from '@hospital/shared';
import { useEffect, useState } from 'react';

const DoctorFormPage: React.FC = () => {
  const params = useParams<{ id?: string }>();
  const isEdit = !!params.id;
  const [loading, setLoading] = useState(false);
  const [initialValues, setInitialValues] = useState<any>(null);

  useEffect(() => {
    if (isEdit && params.id) {
      setLoading(true);
      doctorApi.getDetail(params.id).then((data) => {
        setInitialValues({
          ...data,
          isRecommended: data.isRecommended === 1,
          status: data.status === 1,
        });
      }).finally(() => setLoading(false));
    }
  }, [isEdit, params.id]);

  const handleSubmit = async (values: any) => {
    try {
      const submitData = {
        ...values,
        isRecommended: values.isRecommended ? 1 : 0,
        status: values.status ? 1 : 0,
      };

      if (isEdit && params.id) {
        await doctorApi.update(params.id, submitData);
        message.success('更新成功');
      } else {
        await doctorApi.create(submitData);
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
        {(!isEdit || initialValues) && (
          <ProForm
            initialValues={initialValues || { sortOrder: 0, isRecommended: false, status: true, registrationFee: 0 }}
            onFinish={handleSubmit}
            submitter={{
              render: (props, doms) => (
                <Space>
                  <Button onClick={() => history.back()}>取消</Button>
                  <Button type="primary" onClick={() => props.form?.submit()}>提交</Button>
                </Space>
              ),
            }}
          >
            <ProForm.Group>
              <ProFormText name="name" label="医生姓名" rules={[{ required: true }]} width="md" />
              <ProFormText name="phone" label="手机号" rules={[{ pattern: /^1\d{10}$/, message: '请输入正确的手机号' }]} width="md" />
            </ProForm.Group>

            <ProForm.Group>
              <ProFormSelect
                name="departmentId"
                label="所属科室"
                rules={[{ required: true }]}
                width="md"
                request={async () => {
                  const tree = await departmentApi.getTree();
                  const flatten = (nodes: any[]): any[] => {
                    return nodes.flatMap((n) => [{ label: n.name, value: n.id }, ...flatten(n.children || [])]);
                  };
                  return flatten(tree);
                }}
              />
              <ProFormSelect
                name="title"
                label="职称"
                width="md"
                valueEnum={DOCTOR_TITLE_MAP}
              />
            </ProForm.Group>

            <ProForm.Group>
              <ProFormMoney name="registrationFee" label="挂号费" min={0} width="md" locale="zh-CN" />
              <ProFormDigit name="sortOrder" label="排序" min={0} max={999} width="md" />
            </ProForm.Group>

            <ProFormTextArea name="specialty" label="擅长" fieldProps={{ rows: 3 }} />
            <ProFormTextArea name="introduction" label="简介" fieldProps={{ rows: 4 }} />

            {!isEdit && (
              <ProFormText.Password name="password" label="登录密码" tooltip="医生端登录密码" width="md" />
            )}

            <ProForm.Group>
              <ProFormSwitch name="isRecommended" label="推荐医生" checkedChildren="是" unCheckedChildren="否" />
              <ProFormSwitch name="status" label="状态" checkedChildren="启用" unCheckedChildren="禁用" />
            </ProForm.Group>
          </ProForm>
        )}
      </Card>
    </PageContainer>
  );
};

export default DoctorFormPage;
