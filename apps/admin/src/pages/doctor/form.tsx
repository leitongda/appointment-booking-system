import { PageContainer, ProForm, ProFormText, ProFormSelect, ProFormTextArea, ProFormDigit } from '@ant-design/pro-components';
import { Card, message } from 'antd';
import { history, useParams } from 'umi';
import { DOCTOR_TITLES } from '@hospital/shared';

const DoctorFormPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const isEdit = !!id;

  const handleSubmit = async (values: any) => {
    console.log('提交数据:', values);
    message.success(isEdit ? '更新成功' : '创建成功');
    history.push('/doctor/list');
  };

  return (
    <PageContainer title={isEdit ? '编辑医生' : '新增医生'}>
      <Card>
        <ProForm
          onFinish={handleSubmit}
          submitter={{
            searchConfig: { submitText: isEdit ? '保存' : '创建' },
            resetButtonProps: { style: { display: 'none' } },
          }}
        >
          <ProForm.Group>
            <ProFormText
              name="name"
              label="医生姓名"
              width="md"
              rules={[{ required: true, message: '请输入医生姓名' }]}
            />
            <ProFormText
              name="employeeNo"
              label="工号"
              width="md"
            />
          </ProForm.Group>

          <ProForm.Group>
            <ProFormSelect
              name="departmentId"
              label="所属科室"
              width="md"
              rules={[{ required: true, message: '请选择科室' }]}
              request={async () => {
                // TODO: 获取科室列表
                return [];
              }}
            />
            <ProFormSelect
              name="title"
              label="职称"
              width="md"
              options={DOCTOR_TITLES.map((t) => ({ label: t, value: t }))}
            />
          </ProForm.Group>

          <ProFormTextArea
            name="specialty"
            label="擅长领域"
            width="xl"
            fieldProps={{ rows: 3 }}
          />

          <ProFormTextArea
            name="introduction"
            label="医生简介"
            width="xl"
            fieldProps={{ rows: 5 }}
          />

          <ProFormDigit
            name="consultationFee"
            label="挂号费"
            width="sm"
            min={0}
            fieldProps={{ precision: 2, prefix: '¥' }}
          />
        </ProForm>
      </Card>
    </PageContainer>
  );
};

export default DoctorFormPage;

