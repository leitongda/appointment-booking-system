import { PageContainer } from '@ant-design/pro-components';
import { ProForm, ProFormText, ProFormTextArea, ProFormSelect } from '@ant-design/pro-components';
import { Card, message, Form, Row, Col } from 'antd';
import { history, useParams } from '@umijs/max';
import { useEffect, useState } from 'react';
import { miniappPlatformApi } from '@hospital/api';
import type { CompanyCreateData, CompanyUpdateData } from '@hospital/api';

const CompanyFormPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const isEdit = !!id;
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [checkingCode, setCheckingCode] = useState(false);

  useEffect(() => {
    if (isEdit) {
      loadCompany();
    }
  }, [id]);

  const loadCompany = async () => {
    setLoading(true);
    try {
      const res = await miniappPlatformApi.getCompany(id);
      const company = res.data;
      form.setFieldsValue({
        name: company.name,
        code: company.code,
        unifiedSocialCreditCode: company.unifiedSocialCreditCode,
        contactName: company.contactName,
        contactPhone: company.contactPhone,
      });
    } catch (error) {
      message.error('加载公司信息失败');
      history.back();
    } finally {
      setLoading(false);
    }
  };

  const checkCompanyCode = async (_: any, value: string) => {
    if (!value) return Promise.resolve();

    // 编辑模式下，如果 code 没有变化，不需要检查
    if (isEdit) {
      const currentCode = form.getFieldValue('code');
      if (currentCode === value) return Promise.resolve();
    }

    setCheckingCode(true);
    try {
      const res = await miniappPlatformApi.checkCompanyCodeUnique(value, isEdit ? id : undefined);
      if (res.data?.exists) {
        return Promise.reject(new Error('该公司编码已存在'));
      }
      return Promise.resolve();
    } catch (error) {
      return Promise.resolve();
    } finally {
      setCheckingCode(false);
    }
  };

  const handleSubmit = async (values: any) => {
    try {
      if (isEdit) {
        await miniappPlatformApi.updateCompany(id, values as CompanyUpdateData);
        message.success('更新成功');
      } else {
        await miniappPlatformApi.createCompany(values as CompanyCreateData);
        message.success('创建成功');
      }
      history.push('/miniapp-platform/company');
    } catch (error: any) {
      message.error(error.message || '操作失败');
    }
  };

  return (
    <PageContainer title={isEdit ? '编辑公司' : '新增公司'}>
      <Card loading={loading}>
        <ProForm
          form={form}
          onFinish={handleSubmit}
          submitter={{
            searchConfig: { submitText: '保存' },
            resetText: '取消',
            onReset: () => history.back(),
          }}
        >
          <Row gutter={24}>
            <Col span={12}>
              <ProFormText
                name="name"
                label="公司名称"
                placeholder="请输入公司名称"
                rules={[{ required: true, message: '请输入公司名称' }]}
              />
            </Col>
            <Col span={12}>
              <ProFormText
                name="code"
                label="公司编码"
                placeholder="请输入公司编码"
                rules={[
                  { validator: checkCompanyCode },
                ]}
                disabled={isEdit}
                extra="租户内唯一，用于系统识别"
                validateDebounce={500}
              />
            </Col>
          </Row>

          <Row gutter={24}>
            <Col span={12}>
              <ProFormText
                name="unifiedSocialCreditCode"
                label="统一社会信用代码"
                placeholder="请输入统一社会信用代码"
              />
            </Col>
            <Col span={12}>
              <ProFormText
                name="contactName"
                label="联系人"
                placeholder="请输入联系人姓名"
              />
            </Col>
          </Row>

          <Row gutter={24}>
            <Col span={12}>
              <ProFormText
                name="contactPhone"
                label="联系电话"
                placeholder="请输入联系电话"
                rules={[
                  { pattern: /^1[3-9]\d{9}$/, message: '请输入有效的手机号' }
                ]}
              />
            </Col>
          </Row>
        </ProForm>
      </Card>
    </PageContainer>
  );
};

export default CompanyFormPage;
