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
import { App, Popconfirm, Space, Tag, Button, Divider, Dropdown, Modal } from 'antd';
import type { MenuProps } from 'antd';
import { PlusOutlined, EditOutlined, DeleteOutlined, MoreOutlined, EyeOutlined, StopOutlined } from '@ant-design/icons';
import { useRef, useState } from 'react';
import { history, useAccess } from '@umijs/max';
import { patientApi, dataApi } from '@hospital/api';
import { GENDER_MAP, GENDER_OPTIONS } from '@/constants';
import { toProTableResult } from '@/utils/proTable';
import type { PatientListItem, PatientUpdateData } from '@hospital/api';
import type { PatientCreateData } from '@hospital/api/src/modules/patient';
import ImportExport from '@/components/ImportExport';

const SOURCE_MAP: Record<number, string> = {
  1: '用户添加',
  2: '管理员添加',
};

const RELATIONSHIP_OPTIONS = [
  { label: '本人', value: '本人' },
  { label: '父母', value: '父母' },
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
  const [editModalVisible, setEditModalVisible] = useState(false);
  const [currentPatient, setCurrentPatient] = useState<PatientListItem | null>(null);

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

  const handleEdit = async (values: PatientUpdateData) => {
    if (!currentPatient) return false;
    try {
      await patientApi.update(currentPatient.id, values);
      message.success('保存成功');
      setEditModalVisible(false);
      setCurrentPatient(null);
      actionRef.current?.reload();
      return true;
    } catch (error: any) {
      message.error(error.message || '保存失败');
      return false;
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await patientApi.delete(id);
      message.success('删除成功');
      actionRef.current?.reload();
    } catch (error: any) {
      message.error(error.message || '删除失败');
    }
  };

  const columns: ProColumns<PatientListItem>[] = [
    { title: '卡号', dataIndex: 'cardNo', width: 150, ellipsis: true },
    { title: '姓名', dataIndex: 'name', width: 80 },
    {
      title: '性别',
      dataIndex: 'gender',
      width: 60,
      search: false,
      render: (val) => GENDER_MAP[val as number] || '-',
    },
    { title: '年龄', dataIndex: 'age', width: 60, search: false, render: (val) => val ?? '-' },
    { title: '手机号', dataIndex: 'phone', width: 120 },
    {
      title: '默认',
      dataIndex: 'isDefault',
      width: 60,
      search: false,
      render: (val) => val ? <Tag color="blue">默认</Tag> : '-',
    },
    {
      title: '所属患者',
      dataIndex: 'userNickname',
      width: 120,
      search: false,
      render: (_, record) => (
        <Space size={0}>
          <span>{record.userNickname || '微信用户'}</span>
          <span style={{ color: '#999', fontSize: 12 }}>{record.userPhone}</span>
        </Space>
      ),
    },
    {
      title: '来源',
      dataIndex: 'source',
      width: 100,
      valueEnum: {
        1: { text: '用户添加' },
        2: { text: '管理员添加' },
      },
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
      width: 220,
      fixed: 'right',
      render: (_, record) => {
        // 更多操作菜单项
        const moreMenuItems: MenuProps['items'] = [
          access.hasPermission('patient:update') && (
            record.isBlacklist ? {
              key: 'remove-blacklist',
              icon: <StopOutlined />,
              label: '移出黑名单',
              onClick: () => handleBlacklist(record.id, false),
            } : {
              key: 'add-blacklist',
              icon: <StopOutlined />,
              label: '加黑名单',
              onClick: () => {
                Modal.confirm({
                  title: '确定加入黑名单吗？',
                  onOk: () => handleBlacklist(record.id, true),
                });
              },
            }
          ),
        ].filter(Boolean);

        return (
          <Space size={4} separator={<Divider type="vertical" style={{ margin: 0 }} />}>
            {access.hasPermission('patient:detail') && (
              <a onClick={() => history.push(`/medical-services/patient/card/${record.id}`)} style={{ fontSize: 13 }}>
                <EyeOutlined /> 详情
              </a>
            )}
            {access.hasPermission('patient:update') && (
              <a onClick={() => { setCurrentPatient(record); setEditModalVisible(true); }} style={{ fontSize: 13 }}>
                <EditOutlined /> 编辑
              </a>
            )}
            {access.hasPermission('patient:delete') && (
              <Popconfirm
                title="确定删除该就诊卡吗？"
                description="删除后不可恢复"
                onConfirm={() => handleDelete(record.id)}
              >
                <a style={{ color: '#ff4d4f', fontSize: 13 }}>
                  <DeleteOutlined /> 删除
                </a>
              </Popconfirm>
            )}
            {moreMenuItems.length > 0 && (
              <Dropdown menu={{ items: moreMenuItems }} trigger={['click']}>
                <a style={{ color: '#666', fontSize: 13 }}>
                  <MoreOutlined /> 更多
                </a>
              </Dropdown>
            )}
          </Space>
        );
      },
    },
  ];

  return (
    <PageContainer>
      <ProTable<PatientListItem>
        headerTitle="就诊卡列表"
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
            moduleName="就诊卡"
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
              新增就诊卡
            </Button>
          ),
        ]}
      />

      {/* 新增就诊卡弹窗 */}
      <ModalForm
        title="新增就诊卡"
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

      {/* 编辑就诊卡弹窗 */}
      <ModalForm
        title="编辑就诊卡"
        open={editModalVisible}
        onOpenChange={(open) => {
          setEditModalVisible(open);
          if (!open) setCurrentPatient(null);
        }}
        onFinish={handleEdit}
        width={600}
        modalProps={{ destroyOnHidden: true }}
        initialValues={currentPatient ? {
          name: currentPatient.name,
          phone: currentPatient.phone,
          gender: currentPatient.gender,
          idCard: currentPatient.idCard,
          birthday: currentPatient.birthday,
          relationship: currentPatient.relationship,
          idCardType: currentPatient.idCardType,
          ethnicity: currentPatient.ethnicity,
          province: currentPatient.province,
          city: currentPatient.city,
          district: currentPatient.district,
          street: currentPatient.street,
          address: currentPatient.address,
        } : {}}
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
            placeholder="请输入身份证号"
          />
          <ProFormSelect
            name="idCardType"
            label="证件类型"
            width="sm"
            options={ID_CARD_TYPE_OPTIONS}
          />
        </ProForm.Group>
        <ProForm.Group>
          <ProFormSelect
            name="relationship"
            label="与本人关系"
            width="sm"
            options={RELATIONSHIP_OPTIONS}
          />
          <ProFormText
            name="ethnicity"
            label="民族"
            width="sm"
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
