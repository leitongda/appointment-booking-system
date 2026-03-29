import { 
  ModalForm, 
  ProFormSelect, 
  ProFormDigit,
  ProFormTimePicker,
} from '@ant-design/pro-components';
import { App, Space, Tag, Popconfirm, Empty, List, Button } from 'antd';
import { PlusOutlined } from '@ant-design/icons';
import { useState } from 'react';
import type { Dayjs } from 'dayjs';
import dayjs from 'dayjs';
import { scheduleApi } from '@hospital/api';
import type { Schedule } from '@hospital/shared';

interface ScheduleEditModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  doctorId: string;
  date: Dayjs | null;
  schedules: Schedule[];
  onSuccess: () => void;
}

const TIME_SLOTS = [
  { label: '上午', value: 'morning' },
  { label: '下午', value: 'afternoon' },
  { label: '晚上', value: 'evening' },
];

const TIME_SLOT_LABELS: Record<string, string> = {
  morning: '上午',
  afternoon: '下午',
  evening: '晚上',
};

const DEFAULT_TIMES: Record<string, { start: string; end: string }> = {
  morning: { start: '08:00', end: '12:00' },
  afternoon: { start: '14:00', end: '17:30' },
  evening: { start: '18:00', end: '21:00' },
};

const ScheduleEditModal: React.FC<ScheduleEditModalProps> = ({
  open,
  onOpenChange,
  doctorId,
  date,
  schedules,
  onSuccess,
}) => {
  const { message } = App.useApp();
  const [addFormOpen, setAddFormOpen] = useState(false);
  const [loading, setLoading] = useState(false);

  const handleSuspend = async (schedule: Schedule) => {
    try {
      setLoading(true);
      await scheduleApi.suspendSchedule(schedule, '管理员停诊');
      message.success('停诊成功');
      onSuccess();
    } catch (error: any) {
      message.error(error.message || '操作失败');
    } finally {
      setLoading(false);
    }
  };

  const handleResume = async (schedule: Schedule) => {
    try {
      setLoading(true);
      await scheduleApi.resumeSchedule(schedule);
      message.success('恢复成功');
      onSuccess();
    } catch (error: any) {
      message.error(error.message || '操作失败');
    } finally {
      setLoading(false);
    }
  };

  const handleAddSchedule = async (values: any) => {
    if (!date) return false;
    
    try {
      const timeSlot = values.timeSlot;
      const defaultTime = DEFAULT_TIMES[timeSlot] || DEFAULT_TIMES.morning;
      
      // 格式化时间，确保有效性
      let startTime = defaultTime.start;
      if (values.startTime) {
        const formatted = dayjs(values.startTime);
        if (formatted.isValid()) {
          startTime = formatted.format('HH:mm');
        }
      }
      
      let endTime = defaultTime.end;
      if (values.endTime) {
        const formatted = dayjs(values.endTime);
        if (formatted.isValid()) {
          endTime = formatted.format('HH:mm');
        }
      }
      
      await scheduleApi.create({
        doctorId,
        scheduleDate: date.format('YYYY-MM-DD'),
        timeSlot: values.timeSlot,
        startTime,
        endTime,
        totalSlots: values.totalSlots,
        status: 1,
      });
      message.success('添加排班成功');
      setAddFormOpen(false);
      onSuccess();
      return true;
    } catch (error: any) {
      message.error(error.message || '添加失败');
      return false;
    }
  };

  // 获取已存在的时段
  const existingTimeSlots = schedules.map((s) => s.timeSlot);
  const availableTimeSlots = TIME_SLOTS.filter(
    (slot) => !existingTimeSlots.includes(slot.value)
  );

  const getStatusTag = (schedule: Schedule) => {
    if (schedule.status === 0) {
      return <Tag color="default">停诊</Tag>;
    }
    const available = schedule.totalSlots - schedule.bookedSlots;
    if (available <= 0) {
      return <Tag color="error">已满</Tag>;
    }
    if (available <= schedule.totalSlots * 0.2) {
      return <Tag color="warning">即将满</Tag>;
    }
    return <Tag color="success">正常</Tag>;
  };

  // 按时段排序
  const sortOrder = { morning: 0, afternoon: 1, evening: 2 };
  const sortedSchedules = [...schedules].sort(
    (a, b) => (sortOrder[a.timeSlot as keyof typeof sortOrder] ?? 3) - (sortOrder[b.timeSlot as keyof typeof sortOrder] ?? 3)
  );

  return (
    <>
      <ModalForm
        title={date ? `${date.format('YYYY年MM月DD日')} 排班管理` : '排班管理'}
        open={open}
        onOpenChange={onOpenChange}
        submitter={false}
        width={560}
        modalProps={{ destroyOnHidden: true }}
      >
        <div style={{ marginBottom: 16 }}>
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => setAddFormOpen(true)}
            disabled={availableTimeSlots.length === 0}
          >
            添加排班
          </Button>
          {availableTimeSlots.length === 0 && (
            <span style={{ marginLeft: 8, color: '#999', fontSize: 12 }}>
              所有时段已排班
            </span>
          )}
        </div>

        {sortedSchedules.length === 0 ? (
          <Empty description="当日暂无排班" />
        ) : (
          <List
            loading={loading}
            dataSource={sortedSchedules}
            renderItem={(schedule) => (
              <List.Item
                actions={[
                  schedule.status === 1 ? (
                    <Popconfirm
                      key="suspend"
                      title="确定停诊吗？已预约的患者将收到通知。"
                      onConfirm={() => handleSuspend(schedule)}
                    >
                      <a style={{ color: '#ff4d4f' }}>停诊</a>
                    </Popconfirm>
                  ) : (
                    <a key="resume" onClick={() => handleResume(schedule)}>
                      恢复
                    </a>
                  ),
                ]}
              >
                <List.Item.Meta
                  title={
                    <Space>
                      <span>{TIME_SLOT_LABELS[schedule.timeSlot] || schedule.timeSlot}</span>
                      {getStatusTag(schedule)}
                    </Space>
                  }
                  description={
                    <Space split="·">
                      <span>
                        时间: {schedule.startTime || '-'} - {schedule.endTime || '-'}
                      </span>
                      <span>
                        号源: {schedule.bookedSlots}/{schedule.totalSlots}
                      </span>
                      <span>
                        剩余: {schedule.totalSlots - schedule.bookedSlots}
                      </span>
                    </Space>
                  }
                />
              </List.Item>
            )}
          />
        )}
      </ModalForm>

      {/* 添加排班弹窗 */}
      <ModalForm
        title="添加排班"
        open={addFormOpen}
        onOpenChange={setAddFormOpen}
        onFinish={handleAddSchedule}
        width={400}
        modalProps={{ destroyOnHidden: true }}
        initialValues={{ totalSlots: 20 }}
      >
        <ProFormSelect
          name="timeSlot"
          label="时段"
          options={availableTimeSlots}
          rules={[{ required: true, message: '请选择时段' }]}
        />
        <ProFormTimePicker
          name="startTime"
          label="开始时间"
          fieldProps={{ format: 'HH:mm' }}
          placeholder="留空使用默认时间"
        />
        <ProFormTimePicker
          name="endTime"
          label="结束时间"
          fieldProps={{ format: 'HH:mm' }}
          placeholder="留空使用默认时间"
        />
        <ProFormDigit
          name="totalSlots"
          label="号源数量"
          min={1}
          max={100}
          rules={[{ required: true, message: '请输入号源数量' }]}
        />
      </ModalForm>
    </>
  );
};

export default ScheduleEditModal;

