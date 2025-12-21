import { PlusOutlined } from '@ant-design/icons';
import type { ActionType, ProColumns } from '@ant-design/pro-components';
import { PageContainer, ProTable } from '@ant-design/pro-components';
import { Button, App, Popconfirm, Space, Tag, Avatar } from 'antd';
import { useRef, useState, useEffect, useMemo } from 'react';
import { history, useAccess, useModel } from '@umijs/max';
import { doctorApi, departmentApi, storeApi } from '@hospital/api';
import { toProTableResult } from '@/utils/proTable';
import type { Doctor, Department, Store } from '@hospital/shared';
import DoctorConsultationFeeModal from './consultation-fee-modal';

const DoctorListPage: React.FC = () => {
  const { message } = App.useApp();
  const access = useAccess();
  const { initialState } = useModel('@@initialState');
  const actionRef = useRef<ActionType>();
  const [departments, setDepartments] = useState<Department[]>([]);
  const [stores, setStores] = useState<Store[]>([]);
  const [feeModalOpen, setFeeModalOpen] = useState(false);
  const [selectedDoctor, setSelectedDoctor] = useState<{ id: string; name: string } | null>(null);

  // 用户门店相关信息
  const currentUser = initialState?.currentUser;
  const currentStore = initialState?.currentStore;
  const userStores = initialState?.userStores || [];
  const canViewAllStores = access.canViewAllStores;
  const isSingleStore = !canViewAllStores && userStores.length <= 1;

  useEffect(() => {
    loadDepartments();
    // 只有超管或多门店用户才需要加载门店列表
    if (canViewAllStores || userStores.length > 1) {
      loadStores();
    }
  }, []);

  const loadDepartments = async () => {
    try {
      const res = await departmentApi.getList({ pageSize: 100 });
      setDepartments(res.data ?? []);
    } catch (error) {
      console.error('加载科室失败', error);
    }
  };

  const loadStores = async () => {
    try {
      const res = await storeApi.getList({ pageSize: 100 });
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
      await doctorApi.delete(id);
      message.success('删除成功');
      actionRef.current?.reload();
    } catch (error: any) {
      message.error(error.message || '删除失败');
    }
  };

  const columns: ProColumns<Doctor>[] = [
    {
      title: '头像',
      dataIndex: 'avatar',
      width: 60,
      search: false,
      render: (_, record) => (
        <Avatar src={record.avatar} size={40}>
          {record.name?.charAt(0)}
        </Avatar>
      ),
    },
    {
      title: '医生姓名',
      dataIndex: 'name',
      width: 100,
    },
    {
      title: '性别',
      dataIndex: 'gender',
      width: 60,
      search: false,
      render: (_, record) => record.gender === 1 ? '男' : '女',
    },
    {
      title: '所属门店',
      dataIndex: 'storeId',
      width: 120,
      valueType: 'select',
      // 单门店用户隐藏门店筛选
      hideInSearch: isSingleStore,
      hideInTable: isSingleStore,
      fieldProps: {
        options: storeFilterOptions,
        placeholder: canViewAllStores ? '全部门店' : '请选择门店',
      },
      render: (_, record) => record.storeName || '-',
    },
    {
      title: '所属科室',
      dataIndex: 'departmentId',
      width: 120,
      valueType: 'select',
      fieldProps: {
        options: (departments ?? []).map((d) => ({ label: d.name, value: d.id })),
      },
      render: (_, record) => record.departmentName || '-',
    },
    {
      title: '职称',
      dataIndex: 'title',
      width: 120,
      search: false,
    },
    {
      title: '标签',
      dataIndex: 'tags',
      width: 150,
      search: false,
      ellipsis: true,
      render: (_, record) => {
        if (!record.tags) return '-';
        const tagList = record.tags.split(',').filter(Boolean);
        return (
          <Space size={[0, 4]} wrap>
            {tagList.slice(0, 3).map((tag) => (
              <Tag key={tag} color="blue">{tag}</Tag>
            ))}
            {tagList.length > 3 && <span>+{tagList.length - 3}</span>}
          </Space>
        );
      },
    },
    {
      title: '挂号费',
      dataIndex: 'registrationFee',
      width: 80,
      search: false,
      render: (val) => `¥${val || 0}`,
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
      title: '状态',
      dataIndex: 'status',
      width: 80,
      valueType: 'select',
      valueEnum: {
        1: { text: '在职', status: 'Success' },
        0: { text: '离职', status: 'Default' },
      },
    },
    {
      title: '操作',
      valueType: 'option',
      width: 200,
      fixed: 'right',
      render: (_, record) => (
        <Space>
          {access.hasPermission('doctor:detail') && (
            <a onClick={() => history.push(`/doctor/${record.id}`)}>详情</a>
          )}
          {access.hasPermission('doctor:update') && (
            <a onClick={() => history.push(`/doctor/${record.id}/edit`)}>编辑</a>
          )}
          {access.hasPermission('doctor:update') && (
            <a
              onClick={() => {
                setSelectedDoctor({ id: record.id, name: record.name });
                setFeeModalOpen(true);
              }}
            >
              诊费
            </a>
          )}
          {access.hasPermission('doctor:delete') && (
            <Popconfirm
              title="确定删除该医生吗？"
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
      <ProTable<Doctor>
        headerTitle="医生列表"
        actionRef={actionRef}
        rowKey="id"
        columns={columns}
        scroll={{ x: 1200 }}
        request={async (params) => {
          const { current, pageSize, ...rest } = params;
          return toProTableResult(await doctorApi.getList({
            ...rest,
            page: current,
            pageSize,
          }));
        }}
        toolBarRender={() => [
          access.hasPermission('doctor:create') && (
            <Button
              key="add"
              type="primary"
              icon={<PlusOutlined />}
              onClick={() => history.push('/doctor/create')}
            >
              新增医生
            </Button>
          ),
        ]}
        pagination={{ defaultPageSize: 10 }}
      />
      
      {selectedDoctor && (
        <DoctorConsultationFeeModal
          open={feeModalOpen}
          doctorId={selectedDoctor.id}
          doctorName={selectedDoctor.name}
          onClose={() => {
            setFeeModalOpen(false);
            setSelectedDoctor(null);
          }}
        />
      )}
    </PageContainer>
  );
};

export default DoctorListPage;
