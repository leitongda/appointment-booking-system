import { NavBar, Form, Input, Button, Picker, Switch, Toast } from 'antd-mobile';
import { history, useSearchParams } from 'umi';
import { useState } from 'react';
import { GENDER_MAP, PATIENT_RELATIONSHIPS } from '@hospital/shared';
import styles from './edit.less';

const genderOptions = [[{ label: '男', value: 1 }, { label: '女', value: 2 }]];
const relationshipOptions = [PATIENT_RELATIONSHIPS.map((r) => ({ label: r, value: r }))];

const PatientEditPage: React.FC = () => {
  const [searchParams] = useSearchParams();
  const id = searchParams.get('id');
  const isEdit = !!id;

  const [genderVisible, setGenderVisible] = useState(false);
  const [relationVisible, setRelationVisible] = useState(false);

  const onFinish = (values: any) => {
    console.log(values);
    Toast.show(isEdit ? '保存成功' : '添加成功');
    history.back();
  };

  return (
    <div className={styles.container}>
      <NavBar onBack={() => history.back()}>{isEdit ? '编辑就诊人' : '添加就诊人'}</NavBar>
      <Form layout="horizontal" onFinish={onFinish} footer={<Button block type="submit" color="primary">{isEdit ? '保存' : '添加'}</Button>}>
        <Form.Item name="name" label="姓名" rules={[{ required: true }]}>
          <Input placeholder="请输入真实姓名" />
        </Form.Item>
        <Form.Item name="phone" label="手机号" rules={[{ required: true }]}>
          <Input placeholder="请输入手机号" type="tel" />
        </Form.Item>
        <Form.Item name="idCard" label="身份证号" rules={[{ required: true }]}>
          <Input placeholder="请输入身份证号" />
        </Form.Item>
        <Form.Item name="gender" label="性别" trigger="onConfirm" onClick={() => setGenderVisible(true)}>
          <Picker columns={genderOptions} visible={genderVisible} onClose={() => setGenderVisible(false)}>
            {(value) => value?.[0]?.label || '请选择'}
          </Picker>
        </Form.Item>
        <Form.Item name="relationship" label="与本人关系" trigger="onConfirm" onClick={() => setRelationVisible(true)}>
          <Picker columns={relationshipOptions} visible={relationVisible} onClose={() => setRelationVisible(false)}>
            {(value) => value?.[0]?.label || '请选择'}
          </Picker>
        </Form.Item>
        <Form.Item name="isDefault" label="设为默认" valuePropName="checked">
          <Switch />
        </Form.Item>
      </Form>
    </div>
  );
};

export default PatientEditPage;

