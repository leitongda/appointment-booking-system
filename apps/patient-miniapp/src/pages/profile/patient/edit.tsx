import { View } from '@tarojs/components';
import Taro, { useRouter } from '@tarojs/taro';
import { Form, Input, Radio, Button, Switch } from '@nutui/nutui-react-taro';
import { useState, useEffect } from 'react';
import { userApi } from '@hospital/api';
import type { PatientForm } from '@hospital/shared';
import './edit.less';

const PatientEditPage = () => {
  const router = useRouter();
  const { id } = router.params;
  const isEdit = !!id;

  const [loading, setLoading] = useState(false);
  const [formValues, setFormValues] = useState<Partial<PatientForm>>({
    gender: 1,
    isDefault: false,
  });

  useEffect(() => {
    if (isEdit) {
      loadPatient();
    }
  }, [id]);

  const loadPatient = async () => {
    try {
      const data = await userApi.getPatientDetail(id!);
      setFormValues(data);
    } catch (error) {
      console.error('加载就诊人信息失败', error);
    }
  };

  const handleSubmit = async (values: any) => {
    const formData: PatientForm = {
      ...formValues,
      ...values,
    };

    if (!formData.name || !formData.idCard || !formData.phone) {
      Taro.showToast({ title: '请填写完整信息', icon: 'none' });
      return;
    }

    setLoading(true);
    try {
      if (isEdit) {
        await userApi.updatePatient(id!, formData);
      } else {
        await userApi.createPatient(formData);
      }
      Taro.showToast({ title: '保存成功', icon: 'success' });
      Taro.navigateBack();
    } catch (error: any) {
      Taro.showToast({ title: error.message || '保存失败', icon: 'none' });
    } finally {
      setLoading(false);
    }
  };

  return (
    <View className="patient-edit-page">
      <Form
        initialValues={formValues}
        onFinish={handleSubmit}
      >
        <View className="form-section">
          <Form.Item label="姓名" name="name" required>
            <Input placeholder="请输入真实姓名" />
          </Form.Item>

          <Form.Item label="性别" name="gender" required>
            <Radio.Group
              value={formValues.gender}
              onChange={(value) => setFormValues({ ...formValues, gender: value as number })}
            >
              <Radio value={1}>男</Radio>
              <Radio value={2}>女</Radio>
            </Radio.Group>
          </Form.Item>

          <Form.Item label="身份证号" name="idCard" required>
            <Input placeholder="请输入身份证号" maxLength={18} />
          </Form.Item>

          <Form.Item label="手机号" name="phone" required>
            <Input placeholder="请输入手机号" type="tel" maxLength={11} />
          </Form.Item>

          <Form.Item label="与本人关系" name="relationship">
            <Input placeholder="如：本人、父亲、母亲等" />
          </Form.Item>
        </View>

        <View className="form-section">
          <Form.Item label="设为默认" name="isDefault">
            <Switch
              checked={formValues.isDefault}
              onChange={(value) => setFormValues({ ...formValues, isDefault: value })}
            />
          </Form.Item>
        </View>

        <View className="submit-wrap">
          <Button type="primary" block formType="submit" loading={loading}>
            保存
          </Button>
        </View>
      </Form>
    </View>
  );
};

export default PatientEditPage;

