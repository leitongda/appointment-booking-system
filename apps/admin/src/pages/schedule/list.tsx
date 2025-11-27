import { PageContainer, ProTable, ModalForm, ProFormSelect, ProFormDatePicker, ProFormDigit, ProFormDateRangePicker, ProFormCheckbox } from '@ant-design/pro-components';
import type { ProColumns, ActionType } from '@ant-design/pro-components';
import { Button, Tag, Space, message, Popconfirm, Tabs } from 'antd';
import { PlusOutlined } from '@ant-design/icons';
import { useRef, useState } from 'react';
import { scheduleApi, doctorApi } from '@hospital/api';
import { TIME_SLOT_MAP, WEEKDAY_MAP } from '@hospital/shared';
import type { Schedule } from '@hospital/shared';

const ScheduleListPage: React.FC = () => {
  const actionRef = useRef<ActionType>();
  const [singleModalVisible, setSingleModalVisible] = useState(false);
  const [batchModalVisible, setBatchModalVisible] = useState(false);

  const handleSingleSubmit = async (values: any) => {
    try {
      await scheduleApi.create(values);
      message.success('创建成功');
      setSingleModalVisible(false);
      actionRef.current?.reload();
      return true;
    } catch (error: any) {
      message.error(error.message || '创建失败');
      return false;
    }
  };

  const handleBatchSubmit = async (values: any) => {
    try {
      const [startDate, endDate] = values.dateRange;
      await scheduleApi.batchCreate({
        doctorId: values.doctorId,
        startDate,
        endDate,
        timeSlots: values.timeSlots,
        totalSlots: values.totalSlots,
        weekdays: values.weekdays,
      });
      message.success('批量创建成功');
      setBatchModalVisible(false);
      actionRef.current?.reload();
      return true;
    } catch (error: any) {
      message.error(error.message || '创建失败');
      return false;
    }
  };

  const handleSuspend = async (id: string) => {
    try {
      await scheduleApi.suspend(id);
      message.success('停诊成功');
      actionRef.current?.reload();
    } catch (error: any) {
      message.error(error.message || '操作失败');
    }
  };

  const columns: ProColumns<Schedule>[] = [
    { title: '医生', dataIndex: 'doctorName', width: 120 },
    { title: '科室', dataIndex: 'departmentName', width: 120, search: false },
    { title: '日期', dataIndex: 'scheduleDate', width: 120, valueType: 'date' },
    { title: '时段', dataIndex: 'timeSlot', width: 80, render: (_, r) => TIME_SLOT_MAP[r.timeSlot], valueEnum: TIME_SLOT_MAP },
    { title: '总号源', dataIndex: 'totalSlots', width: 80, search: false },
    { title: '已预约', dataIndex: 'bookedSlots', width: 80, search: false },
    { 
      title: '剩余', 
      width: 80, 
      search: false,
      render: (_, r) => {
        const remain = r.totalSlots - r.bookedSlots;
        return <Tag color={remain > 0 ? 'green' : 'red'}>{remain}</Tag>;
      }
    },
    { 
      title: '状态', 
      dataIndex: 'status', 
      width: 80,
      valueEnum: { 0: { text: '停诊', status: 'Error' }, 1: { text: '正常', status: 'Success' } }
    },
    { 
      title: '操作', 
      valueType: 'option',
      width: 120,
      render: (_, record) => (
        <Space>
          {record.status === 1 && (
            <Popconfirm title="确定停诊吗？已预约的患者将收到通知" onConfirm={() => handleSuspend(record.id)}>
              <a style={{ color: 'red' }}>停诊</a>
            </Popconfirm>
          )}
        </Space>
      )
    },
  ];

  const doctorSelectProps = {
    request: async () => {
      const result = await doctorApi.getList({ status: 1, pageSize: 100 });
      return result.data.map((d: any) => ({ label: `${d.name} - ${d.departmentName}`, value: d.id }));
    },
    showSearch: true,
    placeholder: '选择医生',
  };

  return (
    <PageContainer>
      <ProTable<Schedule>
        actionRef={actionRef}
        rowKey="id"
        columns={columns}
        search={{ labelWidth: 'auto' }}
        toolBarRender={() => [
          <Button key="single" icon={<PlusOutlined />} onClick={() => setSingleModalVisible(true)}>
            单次排班
          </Button>,
          <Button key="batch" type="primary" icon={<PlusOutlined />} onClick={() => setBatchModalVisible(true)}>
            批量排班
          </Button>,
        ]}
        request={async (params) => {
          const { current, pageSize, doctorId, scheduleDate, timeSlot, status } = params;
          const result = await scheduleApi.getList({
            doctorId,
            startDate: scheduleDate,
            status,
            page: current,
            pageSize,
          });
          return { data: result.data, success: true, total: result.total };
        }}
      />

      {/* 单次排班 */}
      <ModalForm
        title="新增排班"
        open={singleModalVisible}
        onOpenChange={setSingleModalVisible}
        onFinish={handleSingleSubmit}
        initialValues={{ totalSlots: 10, status: 1 }}
      >
        <ProFormSelect name="doctorId" label="医生" rules={[{ required: true }]} {...doctorSelectProps} />
        <ProFormDatePicker name="scheduleDate" label="日期" rules={[{ required: true }]} width="md" />
        <ProFormSelect name="timeSlot" label="时段" rules={[{ required: true }]} valueEnum={TIME_SLOT_MAP} width="sm" />
        <ProFormDigit name="totalSlots" label="号源数" rules={[{ required: true }]} min={1} max={100} width="sm" />
      </ModalForm>

      {/* 批量排班 */}
      <ModalForm
        title="批量排班"
        open={batchModalVisible}
        onOpenChange={setBatchModalVisible}
        onFinish={handleBatchSubmit}
        initialValues={{ totalSlots: 10, weekdays: [1, 2, 3, 4, 5], timeSlots: ['AM', 'PM'] }}
        width={600}
      >
        <ProFormSelect name="doctorId" label="医生" rules={[{ required: true }]} {...doctorSelectProps} />
        <ProFormDateRangePicker name="dateRange" label="日期范围" rules={[{ required: true }]} width="md" />
        <ProFormCheckbox.Group
          name="weekdays"
          label="星期"
          rules={[{ required: true }]}
          options={[
            { label: '周一', value: 1 },
            { label: '周二', value: 2 },
            { label: '周三', value: 3 },
            { label: '周四', value: 4 },
            { label: '周五', value: 5 },
            { label: '周六', value: 6 },
            { label: '周日', value: 7 },
          ]}
        />
        <ProFormCheckbox.Group
          name="timeSlots"
          label="时段"
          rules={[{ required: true }]}
          options={[
            { label: '上午', value: 'AM' },
            { label: '下午', value: 'PM' },
          ]}
        />
        <ProFormDigit name="totalSlots" label="每时段号源数" rules={[{ required: true }]} min={1} max={100} width="sm" />
      </ModalForm>
    </PageContainer>
  );
};

export default ScheduleListPage;
