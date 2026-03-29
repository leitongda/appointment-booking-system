import { NavBar, Form, Input, Picker, Switch, Toast, Dialog, TextArea, DatePicker } from 'antd-mobile';
import { history, useSearchParams } from 'umi';
import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { userApi } from '@hospital/api';
import { GENDER_MAP, PATIENT_RELATIONSHIPS } from '@hospital/shared';
import type { Patient } from '@hospital/shared';
import { Button, Card } from '@/components/ui';
import { fadeInUp, stagger } from '@/components/ui/animations';

const genderOptions = [[
  { label: '男', value: 1 },
  { label: '女', value: 2 },
]];

const relationshipOptions = [PATIENT_RELATIONSHIPS.map((r) => ({ label: r, value: r }))];

const idCardTypeOptions = [[
  { label: '居民身份证', value: 1 },
  { label: '户口簿', value: 2 },
  { label: '护照', value: 3 },
]];

const PatientEditPage: React.FC = () => {
  const [searchParams] = useSearchParams();
  const id = searchParams.get('id');
  const isEdit = !!id;

  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [patient, setPatient] = useState<Patient | null>(null);
  const [form] = Form.useForm();

  const [genderVisible, setGenderVisible] = useState(false);
  const [relationVisible, setRelationVisible] = useState(false);
  const [idCardTypeVisible, setIdCardTypeVisible] = useState(false);
  const [birthdayVisible, setBirthdayVisible] = useState(false);

  useEffect(() => {
    if (isEdit) {
      loadPatient();
    }
  }, [id]);

  const loadPatient = async () => {
    setLoading(true);
    try {
      const patients = await userApi.getPatients();
      const current = patients.find((p) => p.id === id);
      if (current) {
        setPatient(current);
        form.setFieldsValue({
          name: current.name,
          phone: current.phone,
          idCard: current.idCard,
          gender: current.gender ? [current.gender] : undefined,
          relationship: current.relationship ? [current.relationship] : undefined,
          isDefault: current.isDefault,
          birthday: current.birthday,
          idCardType: current.idCardType ? [current.idCardType] : undefined,
          ethnicity: current.ethnicity,
          province: current.province,
          city: current.city,
          district: current.district,
          address: current.address,
        });
      }
    } catch (error) {
      Toast.show({ content: '加载失败', icon: 'fail' });
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async () => {
    try {
      await form.validateFields();
    } catch {
      return;
    }

    const values = form.getFieldsValue();
    const submitData = {
      name: values.name,
      phone: values.phone,
      idCard: values.idCard,
      gender: values.gender?.[0],
      relationship: values.relationship?.[0],
      isDefault: values.isDefault || false,
      birthday: values.birthday || undefined,
      idCardType: values.idCardType?.[0],
      ethnicity: values.ethnicity || undefined,
      province: values.province || undefined,
      city: values.city || undefined,
      district: values.district || undefined,
      address: values.address || undefined,
    };

    setSubmitting(true);
    try {
      if (isEdit && id) {
        await userApi.updatePatient(id, submitData);
        Toast.show({ content: '保存成功', icon: 'success' });
      } else {
        await userApi.addPatient(submitData);
        Toast.show({ content: '添加成功', icon: 'success' });
      }
      history.back();
    } catch (error: any) {
      Toast.show({ content: error.message || '操作失败', icon: 'fail' });
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async () => {
    if (!id) return;

    const result = await Dialog.confirm({
      content: '确定要删除该就诊人吗？',
    });

    if (!result) return;

    try {
      await userApi.deletePatient(id);
      Toast.show({ content: '删除成功', icon: 'success' });
      history.back();
    } catch (error: any) {
      Toast.show({ content: error.message || '删除失败', icon: 'fail' });
    }
  };

  return (
    <div className="min-h-screen bg-background pb-6">
      <NavBar 
        onBack={() => history.back()}
        className="!bg-card border-b border-border"
      >
        {isEdit ? '编辑就诊人' : '添加就诊人'}
      </NavBar>

      <motion.div
        className="p-4"
        variants={stagger}
        initial="hidden"
        animate="visible"
      >
        <motion.div variants={fadeInUp}>
          <Card variant="default" padding="none" className="overflow-hidden">
            <Form
              form={form}
              layout="horizontal"
              className="[&_.adm-list-item]:min-h-[52px]"
            >
              <Form.Item
                name="name"
                label="姓名"
                rules={[{ required: true, message: '请输入姓名' }]}
              >
                <Input placeholder="请输入真实姓名" className="text-right" />
              </Form.Item>

              <Form.Item
                name="phone"
                label="手机号"
                rules={[
                  { required: true, message: '请输入手机号' },
                  { pattern: /^1\d{10}$/, message: '请输入正确的手机号' },
                ]}
              >
                <Input placeholder="请输入手机号" type="tel" maxLength={11} className="text-right" />
              </Form.Item>

              <Form.Item
                name="idCard"
                label="身份证号"
                rules={[
                  { pattern: /(^\d{15}$)|(^\d{18}$)|(^\d{17}(\d|X|x)$)/, message: '请输入正确的身份证号' },
                ]}
              >
                <Input placeholder="请输入身份证号" maxLength={18} className="text-right font-mono" />
              </Form.Item>

              <Form.Item
                name="gender"
                label="性别"
                trigger="onConfirm"
                onClick={() => setGenderVisible(true)}
              >
                <Picker
                  columns={genderOptions}
                  visible={genderVisible}
                  onClose={() => setGenderVisible(false)}
                >
                  {(value) => (
                    <span className={value?.[0]?.label ? 'text-foreground' : 'text-muted-foreground'}>
                      {value?.[0]?.label || '请选择'}
                    </span>
                  )}
                </Picker>
              </Form.Item>

              <Form.Item
                name="relationship"
                label="与本人关系"
                trigger="onConfirm"
                onClick={() => setRelationVisible(true)}
              >
                <Picker
                  columns={relationshipOptions}
                  visible={relationVisible}
                  onClose={() => setRelationVisible(false)}
                >
                  {(value) => (
                    <span className={value?.[0]?.label ? 'text-foreground' : 'text-muted-foreground'}>
                      {value?.[0]?.label || '请选择'}
                    </span>
                  )}
                </Picker>
              </Form.Item>

              <Form.Item
                name="birthday"
                label="出生日期"
                trigger="onConfirm"
                onClick={() => setBirthdayVisible(true)}
              >
                <DatePicker
                  visible={birthdayVisible}
                  onClose={() => setBirthdayVisible(false)}
                  onConfirm={(val) => {
                    const date = new Date(val);
                    const formatted = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`;
                    form.setFieldValue('birthday', formatted);
                  }}
                >
                  {(value) => (
                    <span className={value ? 'text-foreground' : 'text-muted-foreground'}>
                      {value || '请选择'}
                    </span>
                  )}
                </DatePicker>
              </Form.Item>

              <Form.Item
                name="idCardType"
                label="证件类型"
                trigger="onConfirm"
                onClick={() => setIdCardTypeVisible(true)}
              >
                <Picker
                  columns={idCardTypeOptions}
                  visible={idCardTypeVisible}
                  onClose={() => setIdCardTypeVisible(false)}
                >
                  {(value) => (
                    <span className={value?.[0]?.label ? 'text-foreground' : 'text-muted-foreground'}>
                      {value?.[0]?.label || '请选择'}
                    </span>
                  )}
                </Picker>
              </Form.Item>

              <Form.Item
                name="ethnicity"
                label="民族"
              >
                <Input placeholder="请输入民族" className="text-right" />
              </Form.Item>

              <Form.Item
                name="province"
                label="省"
              >
                <Input placeholder="请输入省份" className="text-right" />
              </Form.Item>

              <Form.Item
                name="city"
                label="市"
              >
                <Input placeholder="请输入城市" className="text-right" />
              </Form.Item>

              <Form.Item
                name="district"
                label="区"
              >
                <Input placeholder="请输入区县" className="text-right" />
              </Form.Item>

              <Form.Item
                name="address"
                label="详细地址"
              >
                <TextArea placeholder="请输入详细地址" rows={2} maxLength={255} showCount />
              </Form.Item>

              <Form.Item name="isDefault" label="设为默认" childElementPosition="right">
                <Switch />
              </Form.Item>
            </Form>
          </Card>
        </motion.div>

        <motion.div variants={fadeInUp} className="mt-6 space-y-3">
          {isEdit && (
            <Button 
              variant="ghost"
              className="w-full !text-red-500 !border-red-200 hover:!bg-red-50"
              onClick={handleDelete}
            >
              删除就诊人
            </Button>
          )}
          <Button 
            variant="primary"
            className="w-full"
            disabled={submitting}
            onClick={handleSubmit}
          >
            {submitting ? '提交中...' : (isEdit ? '保存' : '添加')}
          </Button>
        </motion.div>
      </motion.div>
    </div>
  );
};

export default PatientEditPage;
