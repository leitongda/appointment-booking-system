import type { ActionType, ProColumns } from '@ant-design/pro-components';
import {
  PageContainer,
  ProTable,
  ModalForm,
  ProFormText,
  ProFormSelect,
  ProFormDatePicker,
  ProFormTextArea,
  ProForm,
} from '@ant-design/pro-components';
import { App, Popconfirm, Space, Tag, Button } from 'antd';
import { PlusOutlined } from '@ant-design/icons';
import { useRef, useState } from 'react';
import { history, useAccess } from '@umijs/max';
import { patientApi, dataApi } from '@hospital/api';
import { toProTableResult } from '@/utils/proTable';
import type { PatientListItem } from '@hospital/api';
import type { PatientCreateData } from '@hospital/api/src/modules/patient';
import ImportExport from '@/components/ImportExport';

const SOURCE_MAP: Record<number, string> = {
  1: '用户添加',
  2: '管理员添加',
};

const GENDER_OPTIONS = [
  { label: '男', value: 1 },
  { label: '女', value: 2 },
];

const RELATIONSHIP_OPTIONS = [
  { label: '本人', value: '本人' },
  { label: '父亲', value: '父亲' },
  { label: '母亲', value: '母亲' },
  { label: '配偶', value: '配偶' },
  { label: '子女', value: '子女' },
  { label: '其他', value: '其他' },
];

const ID_CARD_TYPE_OPTIONS = [
  { label: '居民身份证', value: 1 },
  { label: '户口簿', value: 2 },
  { label: '护照', value: 3 },
];

const PatientPage: React.FC = () => {
  const { message } = App.useApp();
  const access = useAccess();
  const actionRef = useRef<ActionType>();
  const [createModalVisible, setCreateModalVisible] = useState(false);

  const handleBlacklist = async (id: string, add: boolean) => {
    try {
      if (add) {
        await patientApi.addToBlacklist(id, '多次爽约');
        message.success('已加入黑名单');
      } else {
        await patientApi.removeFromBlacklist(id);
        message.success('已移出黑名单');
      }
      actionRef.current?.reload();
    } catch (error: any) {
      message.error(error.message || '操作失败');
    }
  };

  const handleCreate = async (values: PatientCreateData) => {
    try {
      await patientApi.create(values);
      message.success('创建成功');
      setCreateModalVisible(false);
      actionRef.current?.reload();
      return true;
    } catch (error: any) {
      message.error(error.message || '创建失败');
      return false;
    }
  };

  const columns: ProColumns<PatientListItem>[] = [
    { title: '就诊卡编号', dataIndex: 'cardNo', width: 140, ellipsis: true },
    { title: '姓名', dataIndex: 'name', width: 80 },
    { title: '手机号', dataIndex: 'phone', width: 120 },
    { title: '身份证号', dataIndex: 'idCard', width: 180, search: false, ellipsis: true },
    {
      title: '性别',
      dataIndex: 'gender',
      width: 60,
      search: false,
      render: (val) => (val === 1 ? '男' : val === 2 ? '女' : '-'),
    },
    { title: '与本人关系', dataIndex: 'relationship', width: 100, search: false },
    {
      title: '来源',
      dataIndex: 'source',
      width: 100,
      search: false,
      render: (_, record) => SOURCE_MAP[record.source || 1] || '-',
    },
    { title: '预约次数', dataIndex: 'appointmentCount', width: 90, search: false },
    { title: '爽约次数', dataIndex: 'noShowCount', width: 90, search: false },
    {
      title: '黑名单',
      dataIndex: 'isBlacklist',
      width: 80,
      valueEnum: { true: { text: '是', status: 'Error' }, false: { text: '否', status: 'Default' } },
      render: (_, record) => record.isBlacklist ? <Tag color="red">黑名单</Tag> : '-',
    },
    { title: '创建时间', dataIndex: 'createdAt', valueType: 'dateTime', width: 160, search: false },
    {
      title: '操作',
      valueType: 'option',
      width: 140,
      fixed: 'right',
      render: (_, record) => (
        <Space>
          {access.hasPermission('patient:detail') && (
            <a onClick={() => history.push(`/patient/${record.id}`)}>详情</a>
          )}
          {access.hasPermission('patient:update') && (
            record.isBlacklist ? (
              <Popconfirm title="确定移出黑名单吗？" onConfirm={() => handleBlacklist(record.id, false)}>
                <a>移出黑名单</a>
              </Popconfirm>
            ) : (
              <Popconfirm title="确定加入黑名单吗？" onConfirm={() => handleBlacklist(record.id, true)}>
                <a style={{ color: '#ff4d4f' }}>加黑名单</a>
              </Popconfirm>
            )
          )}
        </Space>
      ),
    },
  ];

  return (
    <PageContainer>
      <ProTable<PatientListItem>
        headerTitle="患者列表"
        actionRef={actionRef}
        rowKey="id"
        columns={columns}
        scroll={{ x: 1300 }}
        request={async (params) => {
          const { current, pageSize, name, phone, cardNo, ...rest } = params;
          const keyword = name || phone || cardNo;
          return toProTableResult(await patientApi.getList({ ...rest, keyword, page: current, pageSize }));
        }}
        pagination={{ defaultPageSize: 10 }}
        search={{ labelWidth: 'auto' }}
        toolBarRender={() => [
          <ImportExport
            key="import-export"
            moduleName="患者"
            exportUrl={dataApi.getExportPatientsUrl()}
            importUrl={dataApi.getImportPatientsUrl()}
            templateUrl={dataApi.getPatientTemplateUrl()}
            onImportSuccess={() => actionRef.current?.reload()}
          />,
          access.hasPermission('patient:create') && (
            <Button
              key="add"
              type="primary"
              icon={<PlusOutlined />}
              onClick={() => setCreateModalVisible(true)}
            >
              新增患者
            </Button>
          ),
        ]}
      />

      {/* 新增患者弹窗 */}
      <ModalForm
        title="新增患者"
        open={createModalVisible}
        onOpenChange={setCreateModalVisible}
        onFinish={handleCreate}
        width={600}
        modalProps={{ destroyOnHidden: true }}
      >
        <ProForm.Group>
          <ProFormText
            name="name"
            label="姓名"
            width="sm"
            rules={[{ required: true, message: '请输入姓名' }]}
            placeholder="请输入姓名"
          />
          <ProFormText
            name="phone"
            label="手机号"
            width="sm"
            rules={[
              { required: true, message: '请输入手机号' },
              { pattern: /^1\d{10}$/, message: '手机号格式不正确' },
            ]}
            placeholder="请输入手机号"
          />
        </ProForm.Group>
        <ProForm.Group>
          <ProFormSelect
            name="gender"
            label="性别"
            width="sm"
            options={GENDER_OPTIONS}
            placeholder="请选择性别"
          />
          <ProFormDatePicker
            name="birthday"
            label="出生日期"
            width="sm"
            placeholder="请选择出生日期"
          />
        </ProForm.Group>
        <ProForm.Group>
          <ProFormText
            name="idCard"
            label="身份证号"
            width="sm"
            rules={[
              { pattern: /^[1-9]\d{5}(18|19|20)\d{2}(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])\d{3}[\dXx]$/, message: '身份证号格式不正确' },
            ]}
            placeholder="请输入身份证号"
          />
          <ProFormSelect
            name="idCardType"
            label="证件类型"
            width="sm"
            options={ID_CARD_TYPE_OPTIONS}
            initialValue={1}
          />
        </ProForm.Group>
        <ProForm.Group>
          <ProFormSelect
            name="relationship"
            label="与本人关系"
            width="sm"
            options={RELATIONSHIP_OPTIONS}
            initialValue="本人"
          />
          <ProFormText
            name="ethnicity"
            label="民族"
            width="sm"
            initialValue="汉族"
            placeholder="请输入民族"
          />
        </ProForm.Group>
        <ProForm.Group>
          <ProFormText name="province" label="省" width="sm" placeholder="请输入省份" />
          <ProFormText name="city" label="市" width="sm" placeholder="请输入城市" />
        </ProForm.Group>
        <ProForm.Group>
          <ProFormText name="district" label="区" width="sm" placeholder="请输入区县" />
          <ProFormText name="street" label="街道/社区" width="sm" placeholder="请输入街道/社区" />
        </ProForm.Group>
        <ProFormTextArea
          name="address"
          label="详细地址"
          placeholder="请输入详细地址"
        />
      </ModalForm>
    </PageContainer>
  );
};

export default PatientPage;
