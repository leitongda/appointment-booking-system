import { PageContainer, ProTable, ModalForm, ProFormSelect, ProFormDatePicker, ProFormDigit, ProFormDateRangePicker, ProFormCheckbox, ProFormText, ProFormSwitch } from '@ant-design/pro-components';
import type { ProColumns, ActionType } from '@ant-design/pro-components';
import { Button, Tag, Space, message, Modal, Input, Switch, Popconfirm, Dropdown } from 'antd';
import { PlusOutlined, DownloadOutlined, StopOutlined, PlayCircleOutlined, MoreOutlined } from '@ant-design/icons';
import { useRef, useState } from 'react';
import { scheduleApi, doctorApi, exportApi } from '@hospital/api';
import { TIME_SLOT_MAP } from '@hospital/shared';
import type { Schedule } from '@hospital/shared';

const ScheduleListPage: React.FC = () => {
  const actionRef = useRef<ActionType>();
  const [singleModalVisible, setSingleModalVisible] = useState(false);
  const [batchModalVisible, setBatchModalVisible] = useState(false);
  const [suspendModalVisible, setSuspendModalVisible] = useState(false);
  const [currentSchedule, setCurrentSchedule] = useState<Schedule | null>(null);
  const [suspendReason, setSuspendReason] = useState('');
  const [notifyPatients, setNotifyPatients] = useState(true);
  const [suspendLoading, setSuspendLoading] = useState(false);

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
      const result = await scheduleApi.batchCreate({
        doctorId: values.doctorId,
        startDate,
        endDate,
        timeSlots: values.timeSlots,
        totalSlots: values.totalSlots,
        weekdays: values.weekdays,
      });
      message.success(result.message || '批量创建成功');
      setBatchModalVisible(false);
      actionRef.current?.reload();
      return true;
    } catch (error: any) {
      message.error(error.message || '创建失败');
      return false;
    }
  };

  const openSuspendModal = (record: Schedule) => {
    setCurrentSchedule(record);
    setSuspendReason('');
    setNotifyPatients(true);
    setSuspendModalVisible(true);
  };

  const handleSuspend = async () => {
    if (!currentSchedule) return;
    
    setSuspendLoading(true);
    try {
      const result = await scheduleApi.suspend(currentSchedule.id, suspendReason, notifyPatients);
      
      if (result.notification) {
        message.success(`停诊成功，已通知 ${result.notification.notifiedCount} 位患者`);
      } else {
        message.success('停诊成功');
      }
      
      setSuspendModalVisible(false);
      actionRef.current?.reload();
    } catch (error: any) {
      message.error(error.message || '操作失败');
    } finally {
      setSuspendLoading(false);
    }
  };

  const handleResume = async (id: string) => {
    try {
      await scheduleApi.resume(id);
      message.success('恢复成功');
      actionRef.current?.reload();
    } catch (error: any) {
      message.error(error.message || '操作失败');
    }
  };

  const handleExport = () => {
    exportApi.exportSchedules();
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
      width: 150,
      render: (_, record) => (
        <Space>
          {record.status === 1 ? (
            <a onClick={() => openSuspendModal(record)} style={{ color: '#ff4d4f' }}>
              <StopOutlined /> 停诊
            </a>
          ) : (
            <Popconfirm 
              title="确定恢复排班吗？"
              onConfirm={() => handleResume(record.id)}
            >
              <a style={{ color: '#52c41a' }}>
                <PlayCircleOutlined /> 恢复
              </a>
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
          <Button key="export" icon={<DownloadOutlined />} onClick={handleExport}>
            导出
          </Button>,
          <Button key="single" icon={<PlusOutlined />} onClick={() => setSingleModalVisible(true)}>
            单次排班
          </Button>,
          <Button key="batch" type="primary" icon={<PlusOutlined />} onClick={() => setBatchModalVisible(true)}>
            批量排班
          </Button>,
        ]}
        request={async (params) => {
          try {
            const { current, pageSize, doctorId, scheduleDate, timeSlot, status } = params;
            const result = await scheduleApi.getList({
              doctorId,
              startDate: scheduleDate,
              status,
              page: current,
              pageSize,
            });
            return { data: result.data, success: true, total: result.total };
          } catch (error: any) {
            message.error(error.message || '获取数据失败');
            return { data: [], success: false, total: 0 };
          }
        }}
      />

      {/* 单次排班 */}
      <ModalForm
        title="新增排班"
        open={singleModalVisible}
        onOpenChange={setSingleModalVisible}
        onFinish={handleSingleSubmit}
        initialValues={{ totalSlots: 10, status: 1 }}
        modalProps={{ destroyOnClose: true }}
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
        modalProps={{ destroyOnClose: true }}
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

      {/* 停诊确认 */}
      <Modal
        title="停诊确认"
        open={suspendModalVisible}
        onCancel={() => setSuspendModalVisible(false)}
        onOk={handleSuspend}
        confirmLoading={suspendLoading}
        okText="确认停诊"
        okButtonProps={{ danger: true }}
      >
        <div style={{ marginBottom: 16 }}>
          <p>
            确定要停诊 <strong>{currentSchedule?.doctorName}</strong> 在 
            <strong> {currentSchedule?.scheduleDate} {TIME_SLOT_MAP[currentSchedule?.timeSlot || 'AM']} </strong>
            的排班吗？
          </p>
          {currentSchedule && currentSchedule.bookedSlots > 0 && (
            <Tag color="warning">该时段已有 {currentSchedule.bookedSlots} 人预约</Tag>
          )}
        </div>
        
        <div style={{ marginBottom: 16 }}>
          <label style={{ display: 'block', marginBottom: 8 }}>停诊原因（可选）：</label>
          <Input.TextArea
            value={suspendReason}
            onChange={(e) => setSuspendReason(e.target.value)}
            placeholder="请输入停诊原因，将发送给已预约的患者"
            rows={3}
            maxLength={200}
          />
        </div>
        
        <div>
          <label style={{ marginRight: 8 }}>通知已预约患者：</label>
          <Switch checked={notifyPatients} onChange={setNotifyPatients} />
          <span style={{ marginLeft: 8, color: '#999' }}>
            {notifyPatients ? '将发送短信通知' : '不发送通知'}
          </span>
        </div>
      </Modal>
    </PageContainer>
  );
};

export default ScheduleListPage;
