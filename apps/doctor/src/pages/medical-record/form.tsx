import { PageContainer, ProForm, ProFormText, ProFormTextArea } from '@ant-design/pro-components';
import { Card, message } from 'antd';
import { history, useSearchParams } from 'umi';

const MedicalRecordFormPage: React.FC = () => {
  const [searchParams] = useSearchParams();
  const appointmentId = searchParams.get('appointmentId');

  const handleSubmit = async (values: any) => {
    console.log('提交病历:', values);
    message.success('病历保存成功');
    history.push('/medical-record/list');
  };

  return (
    <PageContainer title="填写病历">
      <Card>
        <ProForm onFinish={handleSubmit}>
          <ProFormTextArea name="chiefComplaint" label="主诉" rules={[{ required: true }]} fieldProps={{ rows: 2 }} />
          <ProFormTextArea name="presentIllness" label="现病史" fieldProps={{ rows: 3 }} />
          <ProFormTextArea name="pastHistory" label="既往史" fieldProps={{ rows: 2 }} />
          <ProFormTextArea name="physicalExam" label="体格检查" fieldProps={{ rows: 2 }} />
          <ProFormTextArea name="diagnosis" label="诊断" rules={[{ required: true }]} fieldProps={{ rows: 2 }} />
          <ProFormTextArea name="treatment" label="治疗方案" fieldProps={{ rows: 3 }} />
          <ProFormTextArea name="prescription" label="处方" fieldProps={{ rows: 3 }} />
          <ProFormTextArea name="advice" label="医嘱" fieldProps={{ rows: 2 }} />
        </ProForm>
      </Card>
    </PageContainer>
  );
};

export default MedicalRecordFormPage;

