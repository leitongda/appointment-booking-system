import { PageContainer, ProForm, ProFormSelect, ProFormText, ProFormDateRangePicker, FooterToolbar } from '@ant-design/pro-components';
import { Card, App, Alert, Button, Space } from 'antd';
import { useEffect, useState } from 'react';
import { history } from '@umijs/max';
import { restDayApi, storeApi, doctorApi } from '@hospital/api';

const RestDayFormPage: React.FC = () => {
  const { message } = App.useApp();
  const [stores, setStores] = useState<any[]>([]);
  const [doctors, setDoctors] = useState<any[]>([]);
  const [selectedStore, setSelectedStore] = useState<string>();

  useEffect(() => {
    loadStores();
  }, []);

  useEffect(() => {
    if (selectedStore) {
      loadDoctorsByStore(selectedStore);
    }
  }, [selectedStore]);

  const loadStores = async () => {
    try {
      const res = await storeApi.getList({ pageSize: 100, status: 1 });
      setStores(res.data ?? []);
    } catch (error) {
      console.error('加载门店失败', error);
    }
  };

  const loadDoctorsByStore = async (storeId: string) => {
    try {
      const res = await doctorApi.getList({ storeId, pageSize: 100, status: 1 });
      setDoctors(res.data ?? []);
    } catch (error) {
      console.error('加载医生失败', error);
    }
  };

  const handleSubmit = async (values: any) => {
    try {
      await restDayApi.create({
        storeId: values.storeId,
        doctorIds: values.doctorIds,
        reason: values.reason,
        startDate: values.dateRange[0].format('YYYY-MM-DD'),
        endDate: values.dateRange[1].format('YYYY-MM-DD'),
      });
      message.success('添加成功');
      history.push('/schedule/rest-day');
    } catch (error: any) {
      message.error(error.message || '添加失败');
    }
  };

  return (
    <PageContainer title="添加休息日">
      <Alert
        message="排班权重说明"
        description="停诊 > 自定义排班 > 休息日设置 > 普通排班"
        type="info"
        showIcon
        style={{ marginBottom: 16 }}
      />

      <ProForm
        onFinish={handleSubmit}
        submitter={{
          render: (props, dom) => (
            <FooterToolbar>
              <Space>
                <Button onClick={() => history.back()}>取消</Button>
                <Button type="primary" onClick={() => props.form?.submit()}>
                  创建
                </Button>
              </Space>
            </FooterToolbar>
          ),
        }}
      >
        <Card title="休息日设置">
          <ProFormSelect
            name="storeId"
            label="选择门店"
            width="md"
            options={stores.map(s => ({ label: s.name, value: s.id }))}
            rules={[{ required: true, message: '请选择门店' }]}
            fieldProps={{
              onChange: (val) => setSelectedStore(val),
            }}
          />
          <ProFormSelect
            name="doctorIds"
            label="选择医生"
            width="lg"
            mode="multiple"
            options={doctors.map(d => ({ label: d.name, value: d.id }))}
            placeholder="不选则该门店所有医生都休息"
            extra="注：选择对应的医生则选择的医生休息，不选则该门店所有医生都休息"
          />
          <ProFormText
            name="reason"
            label="休息原因"
            width="lg"
            placeholder="请输入休息原因"
          />
          <ProFormDateRangePicker
            name="dateRange"
            label="休息日期"
            rules={[{ required: true, message: '请选择休息日期' }]}
          />
        </Card>
      </ProForm>
    </PageContainer>
  );
};

export default RestDayFormPage;

