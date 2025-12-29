import { PlusOutlined, UserOutlined } from '@ant-design/icons';
import type { ActionType, ProColumns } from '@ant-design/pro-components';
import { PageContainer, ProTable } from '@ant-design/pro-components';
import { Button, App, Popconfirm, Space, Tag, Modal, Spin, Empty, Checkbox, Avatar, List } from 'antd';
import { useRef, useState, useEffect, useMemo, useCallback } from 'react';
import { history, useAccess, useModel } from '@umijs/max';
import { departmentApi, storeApi, dataApi } from '@hospital/api';
import { toProTableResult } from '@/utils/proTable';
import type { Department, Store, DoctorListItem } from '@hospital/shared';
import ImportExport from '@/components/ImportExport';

const DepartmentPage: React.FC = () => {
  const { message } = App.useApp();
  const access = useAccess();
  const { initialState } = useModel('@@initialState');
  const actionRef = useRef<ActionType>();
  const [stores, setStores] = useState<Store[]>([]);

  // 医生绑定弹窗状态
  const [bindModalVisible, setBindModalVisible] = useState(false);
  const [bindingDepartment, setBindingDepartment] = useState<Department | null>(null);
  const [availableDoctors, setAvailableDoctors] = useState<DoctorListItem[]>([]);
  const [checkedDoctorIds, setCheckedDoctorIds] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  // 用户门店相关信息
  const userStores = initialState?.userStores || [];
  const canViewAllStores = access.canViewAllStores;
  const isSingleStore = !canViewAllStores && userStores.length <= 1;

  useEffect(() => {
    // 只有超管或多门店用户才需要加载门店列表
    if (canViewAllStores || userStores.length > 1) {
      loadStores();
    }
  }, []);

  const loadStores = async () => {
    try {
      const res = await storeApi.getList({ pageSize: 100, status: 1 });
      setStores(res.data ?? []);
    } catch (error) {
      console.error('加载门店失败', error);
    }
  };

  // 构建门店筛选选项
  const storeFilterOptions = useMemo(() => {
    if (isSingleStore) return [];
    
    const options: { label: string; value: string }[] = [];
    
    // 多门店用户或超管可以选择"全部"
    if (canViewAllStores) {
      options.push({ label: '全部门店', value: 'all' });
    }
    
    // 添加门店选项
    const storeList = access.canSuperAdmin ? stores : userStores;
    storeList.forEach((s: any) => {
      options.push({ label: s.name, value: s.id });
    });
    
    return options;
  }, [stores, userStores, canViewAllStores, isSingleStore, access.canSuperAdmin]);

  const handleDelete = async (id: string) => {
    try {
      await departmentApi.delete(id);
      message.success('删除成功');
      actionRef.current?.reload();
    } catch (error: any) {
      message.error(error.message || '删除失败');
    }
  };

  // 打开绑定医生弹窗
  const handleOpenBindModal = useCallback(async (department: Department) => {
    setBindingDepartment(department);
    setBindModalVisible(true);
    setLoading(true);
    
    try {
      // 并行获取可绑定的医生和已绑定的医生
      const [allDoctors, boundDoctors] = await Promise.all([
        departmentApi.getAvailableDoctors(department.id),
        departmentApi.getDoctors(department.id),
      ]);
      
      setAvailableDoctors(allDoctors || []);
      
      // 设置已绑定的医生为选中状态
      const boundIds = (boundDoctors || []).map((d) => d.id);
      setCheckedDoctorIds(boundIds);
    } catch (error: any) {
      message.error('加载医生数据失败');
      console.error(error);
    } finally {
      setLoading(false);
    }
  }, [message]);

  // 处理医生选中变化
  const handleDoctorCheck = (doctorId: string, checked: boolean) => {
    if (checked) {
      setCheckedDoctorIds((prev) => [...prev, doctorId]);
    } else {
      setCheckedDoctorIds((prev) => prev.filter((id) => id !== doctorId));
    }
  };

  // 提交绑定
  const handleBindSubmit = async () => {
    if (!bindingDepartment) return;
    
    setSubmitting(true);
    try {
      await departmentApi.batchBindDoctors(bindingDepartment.id, checkedDoctorIds);
      message.success('绑定成功');
      setBindModalVisible(false);
      actionRef.current?.reload();
    } catch (error: any) {
      message.error(error.message || '绑定失败');
    } finally {
      setSubmitting(false);
    }
  };

  // 关闭弹窗
  const handleCloseBindModal = () => {
    setBindModalVisible(false);
    setBindingDepartment(null);
    setAvailableDoctors([]);
    setCheckedDoctorIds([]);
  };

  const columns: ProColumns<Department>[] = [
    {
      title: '科室名称',
      dataIndex: 'name',
      ellipsis: true,
      width: 150,
    },
    {
      title: '所属门店',
      dataIndex: 'storeName',
      ellipsis: true,
      width: 120,
      search: false,
      // 单门店用户隐藏门店列
      hideInTable: isSingleStore,
      render: (_, record) => record.storeName || '-',
    },
    {
      title: '门店筛选',
      dataIndex: 'storeId',
      hideInTable: true,
      // 单门店用户隐藏门店筛选
      hideInSearch: isSingleStore,
      valueType: 'select',
      fieldProps: {
        options: storeFilterOptions,
        allowClear: true,
        placeholder: canViewAllStores ? '全部门店' : '请选择门店',
      },
    },
    {
      title: '科室标签',
      dataIndex: 'tag',
      ellipsis: true,
      width: 100,
      search: false,
      render: (_, record) => record.tag ? <Tag color="blue">{record.tag}</Tag> : '-',
    },
    {
      title: '排序',
      dataIndex: 'sortOrder',
      width: 70,
      search: false,
    },
    {
      title: '终极科室',
      dataIndex: 'isFinal',
      width: 90,
      search: false,
      render: (_, record) => (
        record.isFinal === 1 ? <Tag color="green">是</Tag> : <Tag>否</Tag>
      ),
    },
    {
      title: '推荐',
      dataIndex: 'isRecommended',
      width: 70,
      search: false,
      render: (_, record) => (
        record.isRecommended === 1 ? <Tag color="orange">推荐</Tag> : '-'
      ),
    },
    {
      title: '热门',
      dataIndex: 'isHot',
      width: 70,
      search: false,
      render: (_, record) => (
        record.isHot === 1 ? <Tag color="red">热门</Tag> : '-'
      ),
    },
    {
      title: '状态',
      dataIndex: 'status',
      width: 80,
      valueType: 'select',
      valueEnum: {
        1: { text: '启用', status: 'Success' },
        0: { text: '禁用', status: 'Default' },
      },
    },
    {
      title: '创建时间',
      dataIndex: 'createdAt',
      valueType: 'dateTime',
      width: 160,
      search: false,
    },
    {
      title: '操作',
      valueType: 'option',
      width: 180,
      fixed: 'right',
      render: (_, record) => (
        <Space>
          {access.hasPermission('department:update') && record.isFinal === 1 && (
            <a onClick={() => handleOpenBindModal(record)}>
              <UserOutlined /> 医生
            </a>
          )}
          {access.hasPermission('department:update') && (
            <a onClick={() => history.push(`/department/${record.id}/edit`)}>编辑</a>
          )}
          {access.hasPermission('department:delete') && (
            <Popconfirm
              title="确定删除该科室吗？"
              onConfirm={() => handleDelete(record.id)}
            >
              <a style={{ color: '#ff4d4f' }}>删除</a>
            </Popconfirm>
          )}
        </Space>
      ),
    },
  ];

  return (
    <PageContainer>
      <ProTable<Department>
        headerTitle="科室列表"
        actionRef={actionRef}
        rowKey="id"
        columns={columns}
        scroll={{ x: 1200 }}
        request={async (params) => {
          const { current, pageSize, ...rest } = params;
          return toProTableResult(await departmentApi.getList({
            ...rest,
            page: current,
            pageSize,
          }));
        }}
        toolBarRender={() => [
          <ImportExport
            key="import-export"
            moduleName="科室"
            exportUrl={dataApi.getExportDepartmentsUrl()}
            importUrl={dataApi.getImportDepartmentsUrl()}
            templateUrl={dataApi.getDepartmentTemplateUrl()}
            onImportSuccess={() => actionRef.current?.reload()}
          />,
          access.hasPermission('department:create') && (
            <Button
              key="add"
              type="primary"
              icon={<PlusOutlined />}
              onClick={() => history.push('/department/create')}
            >
              新增科室
            </Button>
          ),
        ]}
        pagination={{ defaultPageSize: 10 }}
      />

      {/* 医生绑定弹窗 */}
      <Modal
        title={`绑定医生 - ${bindingDepartment?.name || ''}`}
        open={bindModalVisible}
        onCancel={handleCloseBindModal}
        onOk={handleBindSubmit}
        confirmLoading={submitting}
        okText="确定"
        cancelText="取消"
        width={600}
        destroyOnClose
      >
        {loading ? (
          <div style={{ textAlign: 'center', padding: '40px 0' }}>
            <Spin tip="加载中..." />
          </div>
        ) : availableDoctors.length === 0 ? (
          <Empty description="暂无可绑定的医生" />
        ) : (
          <div style={{ maxHeight: 400, overflow: 'auto' }}>
            <List
              dataSource={availableDoctors}
              renderItem={(doctor) => (
                <List.Item
                  key={doctor.id}
                  style={{ padding: '12px 0' }}
                  actions={[
                    <Checkbox
                      key="check"
                      checked={checkedDoctorIds.includes(doctor.id)}
                      onChange={(e) => handleDoctorCheck(doctor.id, e.target.checked)}
                    />,
                  ]}
                >
                  <List.Item.Meta
                    avatar={
                      <Avatar
                        src={doctor.avatar}
                        icon={!doctor.avatar && <UserOutlined />}
                        size={48}
                      />
                    }
                    title={
                      <Space>
                        <span>{doctor.name}</span>
                        {doctor.title && <Tag color="blue">{doctor.title}</Tag>}
                      </Space>
                    }
                    description={
                      <Space direction="vertical" size={0}>
                        {doctor.departmentName && (
                          <span style={{ color: '#999' }}>
                            当前科室: {doctor.departmentName}
                          </span>
                        )}
                        {doctor.specialty && (
                          <span style={{ color: '#666', fontSize: 12 }}>
                            擅长: {doctor.specialty.length > 30 ? doctor.specialty.slice(0, 30) + '...' : doctor.specialty}
                          </span>
                        )}
                      </Space>
                    }
                  />
                </List.Item>
              )}
            />
          </div>
        )}
      </Modal>
    </PageContainer>
  );
};

export default DepartmentPage;
