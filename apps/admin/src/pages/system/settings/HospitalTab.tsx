import { ProForm, ProFormText, ProFormTextArea } from '@ant-design/pro-components';
import type { HospitalTabProps } from './types';

const HospitalTab: React.FC<HospitalTabProps> = ({
  hospitalInfo,
  onSubmit,
  canEdit,
  loading,
}) => (
  <ProForm
    key={loading ? 'hospital-loading' : 'hospital-loaded'}
    onFinish={onSubmit}
    initialValues={hospitalInfo || {}}
    submitter={{ searchConfig: { submitText: '保存设置' }, resetButtonProps: { style: { display: 'none' } } }}
    disabled={!canEdit}
  >
    <ProFormText name="hospitalName" label="医院名称" />
    <ProFormText name="hospitalLevel" label="医院等级" placeholder="如：三级甲等" />
    <ProFormText name="address" label="医院地址" />
    <ProFormText name="phone" label="联系电话" />
    <ProFormText name="workTime" label="工作时间" placeholder="如：08:00-17:30" />
    <ProFormText name="logo" label="Logo URL" />
    <ProFormTextArea name="introduction" label="医院简介" fieldProps={{ rows: 4 }} />
  </ProForm>
);

export default HospitalTab;
