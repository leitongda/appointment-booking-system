import { PageContainer, ProForm, ProFormText, ProFormTextArea, ProFormDigit, ProFormSwitch } from '@ant-design/pro-components';
import { Card, App, Row, Col } from 'antd';
import { useEffect, useState } from 'react';
import { history, useParams } from '@umijs/max';
import { consultationFeeTypeApi } from '@hospital/api';
import type { ConsultationFeeType } from '@hospital/shared';

const ConsultationFeeTypeFormPage: React.FC = () => {
  const { message } = App.useApp();
  const { id } = useParams<{ id: string }>();
  const isEdit = !!id;
  const [loading, setLoading] = useState(false);
  const [feeType, setFeeType] = useState<ConsultationFeeType | null>(null);

  useEffect(() => {
    if (isEdit) {
      loadFeeType();
    }
  }, [id]);

  const loadFeeType = async () => {
    if (!id) return;
    setLoading(true);
    try {
      const data = await consultationFeeTypeApi.getDetail(id);
      setFeeType(data);
    } catch (error: any) {
      message.error('加载诊费类型信息失败');
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (values: any) => {
    try {
      const data = {
        ...values,
        status: values.status ? 1 : 0,
      };
      if (isEdit && id) {
        await consultationFeeTypeApi.update(id, data);
        message.success('更新成功');
      } else {
        await consultationFeeTypeApi.create(data);
        message.success('创建成功');
      }
      history.push('/system/consultation-fee-types');
    } catch (error: any) {
      message.error(error.message || '操作失败');
    }
  };

  const initialValues = feeType ? {
    ...feeType,
    status: feeType.status === 1,
  } : {
    sortOrder: 0,
    status: true,
  };

  return (
    <PageContainer title={isEdit ? '编辑诊费类型' : '新增诊费类型'}>
      <ProForm
        onFinish={handleSubmit}
        initialValues={initialValues}
        submitter={{
          searchConfig: { submitText: isEdit ? '保存' : '创建' },
          resetButtonProps: { style: { display: 'none' } },
          render: (_, dom) => (
            <Row>
              <Col span={24} style={{ textAlign: 'center' }}>
                {dom}
              </Col>
            </Row>
          ),
        }}
      >
        <Card title="诊费类型信息" loading={loading}>
          <ProFormText
            name="name"
            label="类型名称"
            width="md"
            placeholder="请输入诊费类型名称，如：专家、普通、加急"
            rules={[{ required: true, message: '请输入类型名称' }]}
          />
          <ProFormText
            name="code"
            label="类型编码"
            width="md"
            placeholder="请输入类型编码，如：expert、normal、urgent"
            tooltip="用于系统识别，建议使用英文"
          />
          <ProFormTextArea
            name="description"
            label="描述"
            placeholder="请输入诊费类型描述"
          />
          <ProForm.Group>
            <ProFormDigit
              name="sortOrder"
              label="排序"
              width="sm"
              placeholder="数字越小越靠前"
              min={0}
              max={999}
            />
            <ProFormSwitch name="status" label="启用状态" />
          </ProForm.Group>
        </Card>
      </ProForm>
    </PageContainer>
  );
};

export default ConsultationFeeTypeFormPage;

