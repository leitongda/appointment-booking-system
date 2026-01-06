import { PageContainer, ProForm, ProFormText, ProFormTextArea, ProFormSwitch } from '@ant-design/pro-components';
import { Card, message } from 'antd';
import { useEffect, useState, useRef } from 'react';
import { history, useParams } from '@umijs/max';
import { shiftTypeApi } from '@hospital/api';
import type { ShiftType } from '@hospital/shared';

/**
 * 班次类型表单页面
 */
const ShiftTypeFormPage: React.FC = () => {
  const { id } = useParams();
  const isEdit = !!id;
  const [loading, setLoading] = useState(false);
  const [initialData, setInitialData] = useState<ShiftType | null>(null);
  const formRef = useRef<any>();

  useEffect(() => {
    if (isEdit && id) {
      loadShiftType();
    }
  }, [id]);

  const loadShiftType = async () => {
    if (!id) return;
    setLoading(true);
    try {
      const data = await shiftTypeApi.getById(id);
      setInitialData(data);
      formRef.current?.setFieldsValue(data);
    } catch (error: any) {
      message.error('加载班次类型失败');
      history.back();
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (values: any) => {
    try {
      if (isEdit && id) {
        await shiftTypeApi.update(id, values);
        message.success('更新成功');
      } else {
        await shiftTypeApi.create(values);
        message.success('创建成功');
      }
      history.push('/system/shift-types');
    } catch (error: any) {
      message.error(error.message || '操作失败');
      throw error;
    }
  };

  return (
    <PageContainer
      title={isEdit ? '编辑班次类型' : '新增班次类型'}
      onBack={() => history.push('/system/shift-types')}
    >
      <ProForm
        formRef={formRef}
        loading={loading}
        onFinish={handleSubmit}
        submitter={{
          render: (props) => (
            <div style={{ textAlign: 'right' }}>
              <a
                onClick={() => history.back()}
                style={{ marginRight: 16 }}
              >
                取消
              </a>
              <a onClick={() => props.form?.submit?.()}>
                {isEdit ? '保存' : '创建'}
              </a>
            </div>
          ),
        }}
      >
        <Card title="基本信息" loading={loading && isEdit}>
          <ProFormText
            name="code"
            label="类型代码"
            width="lg"
            placeholder="如：OPD、CHECKUP、EXAM"
            rules={[
              { required: true, message: '请输入类型代码' },
              {
                pattern: /^[A-Z_]+$/,
                message: '代码只能包含大写字母和下划线'
              },
            ]}
            extra="用于系统内部标识，建议使用大写字母和下划线，如 OPD、CHECKUP 等"
            disabled={isEdit}
            fieldProps={{
              showCount: true,
              maxLength: 50,
            }}
          />

          <ProFormText
            name="name"
            label="类型名称"
            width="lg"
            placeholder="如：门诊、体检、检查"
            rules={[
              { required: true, message: '请输入类型名称' },
            ]}
            fieldProps={{
              showCount: true,
              maxLength: 100,
            }}
          />

          <ProFormTextArea
            name="description"
            label="描述"
            width="lg"
            fieldProps={{
              rows: 3,
              showCount: true,
              maxLength: 500,
            }}
            placeholder="请输入班次类型的详细描述"
            extra="可选，用于说明该班次类型的用途和适用场景"
          />

          <ProFormSwitch
            name="enabled"
            label="启用状态"
            initialValue={true}
            extra="禁用后，关联的班次将无法使用该类型"
          />
        </Card>

        <Card
          title="常见类型代码说明"
          style={{ marginTop: 16 }}
          type="inner"
        >
          <div style={{ lineHeight: 2 }}>
            <div><strong>OPD</strong> - 门诊（Outpatient Department）</div>
            <div><strong>CHECKUP</strong> - 体检/健康检查</div>
            <div><strong>EXAM</strong> - 检查/检验（如CT、MRI等）</div>
            <div><strong>NURSING</strong> - 护理/输液</div>
            <div><strong>SPECIAL</strong> - 特殊门诊/专家门诊</div>
            <div><strong>EMERGENCY</strong> - 急诊</div>
          </div>
        </Card>
      </ProForm>
    </PageContainer>
  );
};

export default ShiftTypeFormPage;
