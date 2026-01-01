import { PlusOutlined, StarOutlined, HolderOutlined } from '@ant-design/icons';
import type { ActionType, ProColumns } from '@ant-design/pro-components';
import { PageContainer, ProTable } from '@ant-design/pro-components';
import { Button, App, Popconfirm, Space, Tag, Avatar, Switch, Modal, Empty, Spin } from 'antd';
import { useRef, useState, useEffect, useMemo, useCallback } from 'react';
import { history, useAccess, useModel } from '@umijs/max';
import { doctorApi, departmentApi, storeApi, dataApi } from '@hospital/api';
import { toProTableResult } from '@/utils/proTable';
import type { Doctor, Department, Store } from '@hospital/shared';
import DoctorConsultationFeeModal from './consultation-fee-modal';
import ImportExport from '@/components/ImportExport';
import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  DragEndEvent,
} from '@dnd-kit/core';
import {
  arrayMove,
  SortableContext,
  sortableKeyboardCoordinates,
  useSortable,
  verticalListSortingStrategy,
} from '@dnd-kit/sortable';
import { restrictToVerticalAxis } from '@dnd-kit/modifiers';
import { CSS } from '@dnd-kit/utilities';
import React from 'react';

// ========== 推荐医生排序弹窗组件 ==========
interface SortableItemProps {
  id: string;
  doctor: Doctor;
  index: number;
}

const SortableItem: React.FC<SortableItemProps> = ({ id, doctor, index }) => {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id });

  const style: React.CSSProperties = {
    transform: CSS.Transform.toString(transform && { ...transform, scaleY: 1 }),
    // 拖拽中的元素不需要transition，其他元素需要transition来平滑移动
    transition: isDragging ? 'none' : (transition || 'transform 200ms ease'),
    zIndex: isDragging ? 9999 : 'auto',
    position: 'relative',
  };

  return (
    <div ref={setNodeRef} style={style} {...attributes} {...listeners}>
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          padding: '10px 16px',
          marginBottom: 8,
          background: isDragging ? '#fff' : '#fafafa',
          borderRadius: 8,
          border: isDragging ? '2px solid #1890ff' : '1px solid #f0f0f0',
          cursor: isDragging ? 'grabbing' : 'grab',
          transition: isDragging ? 'none' : 'all 0.2s ease',
          boxShadow: isDragging ? '0 8px 24px rgba(24, 144, 255, 0.25)' : 'none',
        }}
      >
        {/* 序号 */}
        <div
          style={{
            width: 22,
            height: 22,
            borderRadius: '50%',
            background: index < 3 ? 'linear-gradient(135deg, #1890ff 0%, #096dd9 100%)' : '#d9d9d9',
            color: '#fff',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: 12,
            fontWeight: 600,
            marginRight: 10,
            flexShrink: 0,
          }}
        >
          {index + 1}
        </div>

        {/* 拖拽手柄 */}
        <HolderOutlined
          style={{
            color: '#bfbfbf',
            fontSize: 14,
            marginRight: 10,
            flexShrink: 0,
          }}
        />

        {/* 头像 */}
        <Avatar
          src={doctor.avatar}
          size={36}
          style={{
            marginRight: 12,
            flexShrink: 0,
            border: '1px solid #fff',
            boxShadow: '0 1px 4px rgba(0,0,0,0.08)',
          }}
        >
          {doctor.name?.charAt(0)}
        </Avatar>

        {/* 医生信息 - 单行紧凑布局 */}
        <div style={{ flex: 1, minWidth: 0, display: 'flex', alignItems: 'center', gap: 12 }}>
          <span style={{ fontWeight: 600, fontSize: 14, color: '#262626', flexShrink: 0 }}>
            {doctor.name}
          </span>
          {doctor.title && (
            <Tag style={{ margin: 0, borderRadius: 4, fontSize: 11, padding: '0 6px', lineHeight: '18px' }} color="processing">
              {doctor.title}
            </Tag>
          )}
          <span style={{ color: '#d9d9d9' }}>|</span>
          <span style={{ fontSize: 13, color: '#8c8c8c' }}>{doctor.departmentName || '-'}</span>
          {doctor.storeName && (
            <>
              <span style={{ color: '#d9d9d9' }}>|</span>
              <span style={{ fontSize: 13, color: '#8c8c8c' }}>{doctor.storeName}</span>
            </>
          )}
        </div>
      </div>
    </div>
  );
};

interface RecommendedSortModalProps {
  open: boolean;
  onClose: () => void;
  onSuccess?: () => void;
}

const RecommendedSortModal: React.FC<RecommendedSortModalProps> = ({ open, onClose, onSuccess }) => {
  const { message } = App.useApp();
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [doctors, setDoctors] = useState<Doctor[]>([]);

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 5 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates })
  );

  // 加载推荐医生
  const loadRecommendedDoctors = useCallback(async () => {
    setLoading(true);
    try {
      const data = await doctorApi.getRecommended(100);
      setDoctors(data || []);
    } catch (error) {
      console.error('加载推荐医生失败', error);
      message.error('加载推荐医生失败');
    } finally {
      setLoading(false);
    }
  }, [message]);

  useEffect(() => {
    if (open) {
      loadRecommendedDoctors();
    }
  }, [open, loadRecommendedDoctors]);

  // 拖拽结束处理
  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    if (!over || active.id === over.id) return;

    const oldIndex = doctors.findIndex((d) => d.id === active.id);
    const newIndex = doctors.findIndex((d) => d.id === over.id);
    if (oldIndex === -1 || newIndex === -1) return;

    setDoctors(arrayMove(doctors, oldIndex, newIndex));
  };

  // 保存排序
  const handleSave = async () => {
    const sortItems = doctors.map((doctor, index) => ({
      id: doctor.id,
      sortOrder: doctors.length - index, // 排序值越大越靠前
    }));

    setSaving(true);
    try {
      await doctorApi.batchUpdateSort(sortItems);
      message.success('推荐排序已保存');
      onSuccess?.();
      onClose();
    } catch (error: any) {
      message.error(error.message || '保存失败');
    } finally {
      setSaving(false);
    }
  };

  return (
    <Modal
      title={
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <StarOutlined style={{ color: '#faad14' }} />
          <span>推荐医生排序</span>
        </div>
      }
      open={open}
      onCancel={onClose}
      onOk={handleSave}
      confirmLoading={saving}
      okText="保存排序"
      cancelText="取消"
      width={680}
      destroyOnClose
      styles={{
        body: { padding: '16px 24px 24px' },
      }}
    >
      {loading ? (
        <div style={{ textAlign: 'center', padding: '60px 0' }}>
          <Spin size="large" />
          <div style={{ marginTop: 16, color: '#8c8c8c' }}>加载中...</div>
        </div>
      ) : doctors.length === 0 ? (
        <Empty
          description="暂无推荐医生"
          style={{ padding: '40px 0' }}
        >
          <div style={{ color: '#8c8c8c', fontSize: 13 }}>
            请先在医生列表中设置推荐
          </div>
        </Empty>
      ) : (
        <>
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              marginBottom: 16,
              padding: '10px 14px',
              background: 'linear-gradient(135deg, #e6f4ff 0%, #f0f5ff 100%)',
              borderRadius: 8,
              border: '1px solid #bae0ff',
            }}
          >
            <span style={{ fontSize: 13, color: '#1677ff' }}>
              拖拽调整顺序，排在前面的优先展示
            </span>
            <Tag color="blue" style={{ margin: 0 }}>
              共 {doctors.length} 位
            </Tag>
          </div>
          <div
            style={{
              maxHeight: 420,
              overflow: 'auto',
              paddingRight: 4,
            }}
          >
            <DndContext
              sensors={sensors}
              collisionDetection={closestCenter}
              modifiers={[restrictToVerticalAxis]}
              onDragEnd={handleDragEnd}
            >
              <SortableContext items={doctors.map((d) => d.id)} strategy={verticalListSortingStrategy}>
                {doctors.map((doctor, index) => (
                  <SortableItem key={doctor.id} id={doctor.id} doctor={doctor} index={index} />
                ))}
              </SortableContext>
            </DndContext>
          </div>
        </>
      )}
    </Modal>
  );
};

// ========== 主页面组件 ==========
const DoctorListPage: React.FC = () => {
  const { message } = App.useApp();
  const access = useAccess();
  const { initialState } = useModel('@@initialState');
  const actionRef = useRef<ActionType>();
  const [departments, setDepartments] = useState<Department[]>([]);
  const [stores, setStores] = useState<Store[]>([]);
  const [feeModalOpen, setFeeModalOpen] = useState(false);
  const [selectedDoctor, setSelectedDoctor] = useState<{ id: string; name: string } | null>(null);
  const [recommendSortModalOpen, setRecommendSortModalOpen] = useState(false);

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

  // 切换推荐状态
  const handleRecommendChange = useCallback(async (id: string, checked: boolean) => {
    try {
      await doctorApi.update(id, { isRecommended: checked ? 1 : 0 });
      message.success(checked ? '已设为推荐' : '已取消推荐');
      actionRef.current?.reload();
    } catch (error: any) {
      message.error(error.message || '操作失败');
    }
  }, [message]);

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
      title: '号源状态',
      dataIndex: 'hasAvailableSlots',
      width: 90,
      search: false,
      render: (_, record) => (
        <Tag color={record.hasAvailableSlots ? 'success' : 'default'}>
          {record.hasAvailableSlots ? '有号' : '无号'}
        </Tag>
      ),
    },
    {
      title: '推荐',
      dataIndex: 'isRecommended',
      width: 80,
      search: false,
      render: (_, record) => (
        <Switch
          checked={record.isRecommended === 1}
          onChange={(checked) => handleRecommendChange(record.id, checked)}
          disabled={!access.hasPermission('doctor:update')}
          size="small"
        />
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
          <ImportExport
            key="import-export"
            moduleName="医生"
            exportUrl={dataApi.getExportDoctorsUrl()}
            importUrl={dataApi.getImportDoctorsUrl()}
            templateUrl={dataApi.getDoctorTemplateUrl()}
            onImportSuccess={() => actionRef.current?.reload()}
          />,
          access.hasPermission('doctor:update') && (
            <Button
              key="recommend-sort"
              icon={<StarOutlined />}
              onClick={() => setRecommendSortModalOpen(true)}
            >
              推荐排序
            </Button>
          ),
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

      <RecommendedSortModal
        open={recommendSortModalOpen}
        onClose={() => setRecommendSortModalOpen(false)}
        onSuccess={() => actionRef.current?.reload()}
      />
    </PageContainer>
  );
};

export default DoctorListPage;
