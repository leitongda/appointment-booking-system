import { ProForm, ProFormText, ProFormDigit, ProFormSwitch } from '@ant-design/pro-components';
import type { PatientCardTabProps } from './types';
import { DEFAULT_PATIENT_CARD_CONFIG } from './defaults';

const PatientCardTab: React.FC<PatientCardTabProps> = ({
  patientCardConfig,
  onSubmit,
  canEdit,
  loading,
}) => (
  <ProForm
    key={loading ? 'patientCard-loading' : 'patientCard-loaded'}
    onFinish={onSubmit}
    initialValues={{ ...DEFAULT_PATIENT_CARD_CONFIG, ...patientCardConfig }}
    submitter={{ searchConfig: { submitText: '保存设置' }, resetButtonProps: { style: { display: 'none' } } }}
    disabled={!canEdit}
  >
    <ProFormText
      name="cardName"
      label="名称修改"
      placeholder="如：xxx就诊卡"
      extra='修改前端"就诊卡"字样；所有涉及到"就诊卡"的地方都会修改'
    />
    <ProFormText
      name="cardDescription"
      label="描述文字"
      placeholder="如：医道至朴.德泽万方"
      fieldProps={{ maxLength: 16, showCount: true }}
      extra='修改前端添加"就诊卡"时；下方的详细描述文字；限16字以内'
    />
    <ProFormDigit
      name="maxCardsPerUser"
      label="可建就诊卡数量"
      min={1}
      max={20}
      fieldProps={{ precision: 0 }}
    />
    <ProFormSwitch name="showOnHomepage" label="首页是否展示" />
  </ProForm>
);

export default PatientCardTab;
