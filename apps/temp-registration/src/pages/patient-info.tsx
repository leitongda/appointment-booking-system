/**
 * 患者信息填写页面
 * 临时挂号第四步：填写患者基本信息
 */
import React, { useState, useEffect } from 'react';
import { Form, Input, Button, Toast, Radio, Space } from 'antd-mobile';
import { history } from 'umi';
import { motion } from 'framer-motion';
import { Card, StepIndicator, PageHeader, fadeInUp } from '@/components/ui';
import { saveRegistrationData, getRegistrationData } from '@/utils/storage';

// 挂号流程步骤
const steps = [
  { key: 'department', title: '选科室' },
  { key: 'doctor', title: '选医生' },
  { key: 'time', title: '选时段' },
  { key: 'patient', title: '填信息' },
  { key: 'confirm', title: '确认' },
];

interface PatientForm {
  name: string;
  phone: string;
  idCard: string;
  gender: 'male' | 'female';
  age: string;
}

const PatientInfoPage: React.FC = () => {
  const [form] = Form.useForm<PatientForm>();
  const [submitting, setSubmitting] = useState(false);
  const registrationData = getRegistrationData();

  useEffect(() => {
    // 验证是否已完成前面的步骤
    if (!registrationData.scheduleId) {
      Toast.show({
        icon: 'fail',
        content: '请先选择就诊时段',
      });
      history.replace('/');
      return;
    }

    // 如果之前填过，预填充数据
    if (registrationData.patientName) {
      form.setFieldsValue({
        name: registrationData.patientName,
        phone: registrationData.patientPhone,
        idCard: registrationData.patientIdCard,
        gender: registrationData.patientGender,
        age: registrationData.patientAge?.toString(),
      });
    }
  }, []);

  const validateIdCard = (idCard: string) => {
    // 简单的身份证格式验证
    const reg = /(^\d{15}$)|(^\d{18}$)|(^\d{17}(\d|X|x)$)/;
    return reg.test(idCard);
  };

  const validatePhone = (phone: string) => {
    const reg = /^1[3-9]\d{9}$/;
    return reg.test(phone);
  };

  const handleSubmit = async (values: PatientForm) => {
    // 验证手机号
    if (!validatePhone(values.phone)) {
      Toast.show({
        icon: 'fail',
        content: '请输入正确的手机号',
      });
      return;
    }

    // 验证身份证
    if (!validateIdCard(values.idCard)) {
      Toast.show({
        icon: 'fail',
        content: '请输入正确的身份证号',
      });
      return;
    }

    setSubmitting(true);
    try {
      saveRegistrationData({
        patientName: values.name,
        patientPhone: values.phone,
        patientIdCard: values.idCard,
        patientGender: values.gender,
        patientAge: parseInt(values.age, 10),
      });
      
      history.push('/confirm');
    } catch (error) {
      Toast.show({
        icon: 'fail',
        content: '保存失败，请重试',
      });
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-background pb-24">
      {/* 步骤指示器 */}
      <StepIndicator steps={steps} currentStep={3} />

      {/* 页面头部 */}
      <PageHeader 
        title="患者信息" 
        subtitle="请填写就诊人信息"
      />

      {/* 表单区域 */}
      <motion.div 
        className="px-4 py-4"
        variants={fadeInUp}
        initial="hidden"
        animate="visible"
      >
        <Card variant="default" padding="md">
          <Form
            form={form}
            layout="vertical"
            onFinish={handleSubmit}
            footer={null}
            style={{
              '--border-inner': 'none',
              '--border-top': 'none',
              '--border-bottom': 'none',
            } as React.CSSProperties}
          >
            <Form.Item
              name="name"
              label="姓名"
              rules={[
                { required: true, message: '请输入姓名' },
                { min: 2, message: '姓名至少2个字符' },
              ]}
            >
              <Input 
                placeholder="请输入真实姓名" 
                className="!h-12 !text-base !rounded-xl !bg-muted !border-0"
              />
            </Form.Item>

            <Form.Item
              name="phone"
              label="手机号"
              rules={[{ required: true, message: '请输入手机号' }]}
            >
              <Input 
                placeholder="请输入手机号码" 
                type="tel"
                maxLength={11}
                className="!h-12 !text-base !rounded-xl !bg-muted !border-0"
              />
            </Form.Item>

            <Form.Item
              name="idCard"
              label="身份证号"
              rules={[{ required: true, message: '请输入身份证号' }]}
            >
              <Input 
                placeholder="请输入18位身份证号" 
                maxLength={18}
                className="!h-12 !text-base !rounded-xl !bg-muted !border-0"
              />
            </Form.Item>

            <Form.Item
              name="gender"
              label="性别"
              rules={[{ required: true, message: '请选择性别' }]}
            >
              <Radio.Group>
                <Space direction="horizontal" style={{ '--gap': '24px' } as React.CSSProperties}>
                  <Radio 
                    value="male"
                    style={{
                      '--icon-size': '22px',
                      '--font-size': '16px',
                    } as React.CSSProperties}
                  >
                    <span className="ml-1">男</span>
                  </Radio>
                  <Radio 
                    value="female"
                    style={{
                      '--icon-size': '22px',
                      '--font-size': '16px',
                    } as React.CSSProperties}
                  >
                    <span className="ml-1">女</span>
                  </Radio>
                </Space>
              </Radio.Group>
            </Form.Item>

            <Form.Item
              name="age"
              label="年龄"
              rules={[
                { required: true, message: '请输入年龄' },
                { pattern: /^\d+$/, message: '请输入有效年龄' },
              ]}
            >
              <Input 
                placeholder="请输入年龄" 
                type="number"
                maxLength={3}
                className="!h-12 !text-base !rounded-xl !bg-muted !border-0"
              />
            </Form.Item>
          </Form>
        </Card>

        {/* 隐私提示 */}
        <motion.div 
          className="mt-4 px-2"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.3 }}
        >
          <div className="flex items-start gap-2 text-sm text-muted-foreground">
            <svg className="w-4 h-4 mt-0.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} 
                    d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
            </svg>
            <p>您的个人信息将受到严格保护，仅用于本次挂号服务</p>
          </div>
        </motion.div>
      </motion.div>

      {/* 底部按钮 */}
      <div className="fixed bottom-0 left-0 right-0 p-4 bg-card border-t border-border safe-area-bottom">
        <Button
          block
          color="primary"
          size="large"
          loading={submitting}
          onClick={() => form.submit()}
          className="!h-12 !rounded-xl !text-base !font-medium"
          style={{
            background: 'linear-gradient(135deg, #00A3A3 0%, #00C4B4 100%)',
          }}
        >
          下一步
        </Button>
      </div>
    </div>
  );
};

export default PatientInfoPage;

