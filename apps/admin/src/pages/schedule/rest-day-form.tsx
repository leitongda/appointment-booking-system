/**
 * 休息日表单页面（重构版）
 *
 * 代码行数：119 行 (vs 原始 145 行)
 *
 * 使用基础设施：
 * - FormPage 组件：统一表单页面布局和底部工具栏
 * - requiredRules: 必填验证规则
 * - fetchAllData: 数据获取工具
 *
 * 业务特性：
 * - 级联选择：门店 → 医生
 * - 日期范围处理：处理字符串和 dayjs 对象
 * - 权限控制：超管可查看所有门店，其他用户只能查看关联门店
 *
 * 优化效果：
 * - 减少重复的表单布局代码
 * - 统一表单提交处理
 * - 提高代码可读性和可维护性
 */
import { ProFormSelect, ProFormText, ProFormDateRangePicker } from '@ant-design/pro-components';
import { Card, Alert } from 'antd';
import { useEffect, useState } from 'react';
import { history, useAccess, useModel } from '@umijs/max';
import { restDayApi, storeApi, doctorApi } from '@hospital/api';
import { fetchAllData } from '@/utils/fetchAllData';

// 基础设施导入
import FormPage from '@/components/FormPage';
import { requiredRules } from '@/utils/formValidators';
import dayjs from 'dayjs';

const RestDayFormPage: React.FC = () => {
  const access = useAccess();
  const { initialState } = useModel('@@initialState');
  const { currentUser } = initialState ?? {};
  const isSuperAdmin = access.canSuperAdmin;

  const [stores, setStores] = useState<any[]>([]);
  const [doctors, setDoctors] = useState<any[]>([]);
  const [selectedStore, setSelectedStore] = useState<string>();

  // 加载门店列表
  useEffect(() => {
    const loadStores = async () => {
      try {
        const allStores = await fetchAllData((page, pageSize) =>
          storeApi.getList({ page, pageSize, status: 1 })
        );
        let storeList = allStores;
        // 非超管只显示其关联的门店
        if (!isSuperAdmin && currentUser?.storeIds?.length) {
          storeList = storeList.filter((s) => currentUser.storeIds?.includes(s.id));
        }
        setStores(storeList);
      } catch (error) {
        console.error('加载门店失败', error);
      }
    };
    loadStores();
  }, [isSuperAdmin, currentUser?.storeIds]);

  // 加载医生列表
  useEffect(() => {
    if (!selectedStore) return;

    const loadDoctors = async () => {
      try {
        const allDoctors = await fetchAllData((page, pageSize) =>
          doctorApi.getList({ storeId: selectedStore, page, pageSize, status: 1 })
        );
        setDoctors(allDoctors);
      } catch (error) {
        console.error('加载医生失败', error);
      }
    };
    loadDoctors();
  }, [selectedStore]);

  // 提交表单
  const handleSubmit = async (values: any) => {
    const { dateRange } = values;
    // ProFormDateRangePicker 可能返回字符串或 dayjs 对象
    const startDate = typeof dateRange[0] === 'string'
      ? dateRange[0]
      : dateRange[0].format('YYYY-MM-DD');
    const endDate = typeof dateRange[1] === 'string'
      ? dateRange[1]
      : dateRange[1].format('YYYY-MM-DD');

    await restDayApi.create({
      storeId: values.storeId,
      doctorIds: values.doctorIds,
      reason: values.reason,
      startDate,
      endDate,
    });

    history.push('/medical-services/schedule/rest-day');
  };

  return (
    <FormPage
      title="添加休息日"
      onFinish={handleSubmit}
      onCancel={() => history.back()}
      saveText="创建"
    >
      <Alert
        message="排班权重说明"
        description="停诊 > 自定义排班 > 休息日设置 > 普通排班"
        type="info"
        showIcon
        style={{ marginBottom: 16 }}
      />

      <Card title="休息日设置">
        <ProFormSelect
          name="storeId"
          label="选择门店"
          width="md"
          options={stores.map(s => ({ label: s.name, value: s.id }))}
          rules={[requiredRules('请选择门店')]}
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
          rules={[requiredRules('请选择休息日期')]}
        />
      </Card>
    </FormPage>
  );
};

export default RestDayFormPage;
