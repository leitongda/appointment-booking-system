import { PlusOutlined } from '@ant-design/icons';
import type { ActionType, ProColumns } from '@ant-design/pro-components';
import {
  PageContainer,
  ProTable,
  ModalForm,
  ProFormSelect,
  ProFormDigit,
  ProFormTimePicker,
} from '@ant-design/pro-components';
import { Button, App, Popconfirm, Space, Tag } from 'antd';
import { useRef, useState, useEffect } from 'react';
import { doctorBookingSettingApi, storeApi, doctorApi } from '@hospital/api';
import { toProTableResult } from '@/utils/proTable';
import type { DoctorBookingSetting, Store, Doctor } from '@hospital/shared';
import dayjs from 'dayjs';

const DoctorBookingSettingPage: React.FC = () => {
  const { message } = App.useApp();
  const actionRef = useRef<ActionType>();
  const [modalOpen, setModalOpen] = useState(false);
  const [editingRecord, setEditingRecord] = useState<DoctorBookingSetting | null>(null);
  const [stores, setStores] = useState<Store[]>([]);
  const [doctors, setDoctors] = useState<Doctor[]>([]);
  const [existingDoctorIds, setExistingDoctorIds] = useState<string[]>([]);
  const [selectedStoreId, setSelectedStoreId] = useState<string>();

  useEffect(() => {
    loadStores();
  }, []);

  // 当选择门店变化时，加载该门店的医生和已配置的医生ID
  useEffect(() => {
    if (selectedStoreId) {
      loadDoctorsByStore(selectedStoreId);
      loadExistingDoctorIds(selectedStoreId);
    } else {
      setDoctors([]);
      setExistingDoctorIds([]);
    }
  }, [selectedStoreId]);

  const loadStores = async () => {
    try {
      const data = await storeApi.getAll();
      setStores(data ?? []);
    } catch (error) {
      console.error('加载门店失败', error);
    }
  };

  const loadDoctorsByStore = async (storeId: string) => {
    try {
      const data = await doctorApi.getByStore(storeId);
      setDoctors(data ?? []);
    } catch (error) {
      console.error('加载医生失败', error);
    }
  };

  const loadExistingDoctorIds = async (storeId: string) => {
    try {
      const ids = await doctorBookingSettingApi.getExistingDoctorIds(storeId);
      setExistingDoctorIds(ids ?? []);
    } catch (error) {
      console.error('加载已配置医生失败', error);
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await doctorBookingSettingApi.delete(id);
      message.success('删除成功');
      actionRef.current?.reload();
    } catch (error: any) {
      message.error(error.message || '删除失败');
    }
  };

  const handleSubmit = async (values: any) => {
    try {
      // 格式化时间
      const releaseTime = values.releaseTime
        ? dayjs(values.releaseTime).format('HH:mm')
        : '00:00';

      const data = {
        ...values,
        releaseTime,
        status: 1,
      };

      if (editingRecord) {
        await doctorBookingSettingApi.update(editingRecord.id, {
          bookingStartOffset: data.bookingStartOffset,
          bookingRangeDays: data.bookingRangeDays,
          releaseTime: data.releaseTime,
        });
        message.success('更新成功');
      } else {
        await doctorBookingSettingApi.create(data);
        message.success('创建成功');
      }
      setModalOpen(false);
      setEditingRecord(null);
      setSelectedStoreId(undefined);
      actionRef.current?.reload();
      return true;
    } catch (error: any) {
      message.error(error.message || '操作失败');
      return false;
    }
  };

  const handleOpenModal = (record?: DoctorBookingSetting) => {
    if (record) {
      setEditingRecord(record);
      setSelectedStoreId(record.storeId);
    } else {
      setEditingRecord(null);
      setSelectedStoreId(undefined);
    }
    setModalOpen(true);
  };

  const columns: ProColumns<DoctorBookingSetting>[] = [
    {
      title: '门店',
      dataIndex: 'storeName',
      width: 150,
      ellipsis: true,
    },
    {
      title: '医生',
      dataIndex: 'doctorName',
      width: 120,
    },
    {
      title: '预约开始日期',
      dataIndex: 'bookingStartOffset',
      width: 120,
      search: false,
      render: (_, record) => {
        const offset = record.bookingStartOffset;
        if (offset === 0) return '当天';
        if (offset === 1) return '第2天';
        return `第${offset + 1}天`;
      },
    },
    {
      title: '预约范围',
      dataIndex: 'bookingRangeDays',
      width: 100,
      search: false,
      render: (val) => `${val}天`,
    },
    {
      title: '放号时间',
      dataIndex: 'releaseTime',
      width: 100,
      search: false,
    },
    {
      title: '状态',
      dataIndex: 'status',
      width: 80,
      valueEnum: {
        1: { text: '启用', status: 'Success' },
        0: { text: '禁用', status: 'Default' },
      },
    },
    {
      title: '创建时间',
      dataIndex: 'createdAt',
      width: 160,
      valueType: 'dateTime',
      search: false,
    },
    {
      title: '操作',
      valueType: 'option',
      width: 120,
      render: (_, record) => (
        <Space>
          <a onClick={() => handleOpenModal(record)}>编辑</a>
          <Popconfirm
            title="确定删除该设置吗？"
            onConfirm={() => handleDelete(record.id)}
          >
            <a style={{ color: '#ff4d4f' }}>删除</a>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <PageContainer>
      <ProTable<DoctorBookingSetting>
        headerTitle="医生预约设置"
        actionRef={actionRef}
        rowKey="id"
        columns={columns}
        request={async (params) => {
          const { current, pageSize, ...rest } = params;
          return toProTableResult(
            await doctorBookingSettingApi.getList({
              ...rest,
              page: current,
              pageSize,
            })
          );
        }}
        toolBarRender={() => [
          <Button
            key="add"
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => handleOpenModal()}
          >
            添加医生预约管理
          </Button>,
        ]}
        pagination={{ defaultPageSize: 10 }}
      />

      <ModalForm
        title={editingRecord ? '编辑医生预约设置' : '添加医生预约管理'}
        open={modalOpen}
        onOpenChange={(open) => {
          setModalOpen(open);
          if (!open) {
            setEditingRecord(null);
            setSelectedStoreId(undefined);
          }
        }}
        onFinish={handleSubmit}
        initialValues={
          editingRecord
            ? {
                storeId: editingRecord.storeId,
                doctorId: editingRecord.doctorId,
                bookingStartOffset: editingRecord.bookingStartOffset,
                bookingRangeDays: editingRecord.bookingRangeDays,
                releaseTime: editingRecord.releaseTime
                  ? dayjs(editingRecord.releaseTime, 'HH:mm')
                  : dayjs('00:00', 'HH:mm'),
              }
            : {
                bookingStartOffset: 0,
                bookingRangeDays: 14,
                releaseTime: dayjs('00:00', 'HH:mm'),
              }
        }
        modalProps={{ destroyOnHidden: true }}
        width={500}
      >
        <ProFormSelect
          name="storeId"
          label="选择门店"
          placeholder="请选择门店"
          options={(stores ?? []).map((s) => ({ label: s.name, value: s.id }))}
          rules={[{ required: true, message: '请选择门店' }]}
          disabled={!!editingRecord}
          fieldProps={{
            onChange: (val) => setSelectedStoreId(val as string),
          }}
        />

        <ProFormSelect
          name="doctorId"
          label="医生"
          placeholder="请先选择门店"
          options={(doctors ?? []).map((d) => ({
            label: d.name + (d.title ? ` - ${d.title}` : ''),
            value: d.id,
            disabled: !editingRecord && existingDoctorIds.includes(d.id),
          }))}
          rules={[{ required: true, message: '请选择医生' }]}
          disabled={!!editingRecord || !selectedStoreId}
          tooltip="已禁用表示已存在于当前预约列表的医生，无需再重复添加"
        />

        <ProFormDigit
          name="bookingStartOffset"
          label="预约开始日期"
          placeholder="请输入"
          min={0}
          max={30}
          rules={[{ required: true, message: '请输入预约开始日期' }]}
          tooltip="0表示从当天开始预约，1表示从第二天开始预约，2表示从第三天开始预约，n表示从n+1天开始预约"
          fieldProps={{ precision: 0 }}
        />

        <ProFormDigit
          name="bookingRangeDays"
          label="预约范围/天"
          placeholder="请输入预约范围，数字型"
          min={1}
          max={90}
          rules={[
            { required: true, message: '请输入预约范围' },
            {
              type: 'number',
              min: 1,
              max: 90,
              message: '请输入1-90以内的数字',
            },
          ]}
          tooltip="开放的预约天数，请输入1-90以内的数字"
          fieldProps={{ precision: 0 }}
        />

        <ProFormTimePicker
          name="releaseTime"
          label="放号时间"
          placeholder="请选择放号时间"
          rules={[{ required: true, message: '请选择放号时间' }]}
          fieldProps={{
            format: 'HH:mm',
            minuteStep: 5,
          }}
        />
      </ModalForm>
    </PageContainer>
  );
};

export default DoctorBookingSettingPage;
