import { PageContainer, ProCard } from '@ant-design/pro-components';
import { Calendar, Badge, Tag, Button, Modal, message, Spin, Input, Switch } from 'antd';
import type { Dayjs } from 'dayjs';
import dayjs from 'dayjs';
import { useState, useEffect } from 'react';
import { scheduleApi } from '@hospital/api';
import { TIME_SLOT_MAP } from '@hospital/shared';
import type { Schedule } from '@hospital/shared';

const SchedulePage: React.FC = () => {
  const [loading, setLoading] = useState(true);
  const [schedules, setSchedules] = useState<Schedule[]>([]);
  const [currentMonth, setCurrentMonth] = useState(dayjs());
  const [suspendModalVisible, setSuspendModalVisible] = useState(false);
  const [currentSchedule, setCurrentSchedule] = useState<Schedule | null>(null);
  const [suspendReason, setSuspendReason] = useState('');
  const [notifyPatients, setNotifyPatients] = useState(true);
  const [suspendLoading, setSuspendLoading] = useState(false);

  useEffect(() => {
    loadSchedules();
  }, [currentMonth]);

  const loadSchedules = async () => {
    setLoading(true);
    try {
      const startDate = currentMonth.startOf('month').format('YYYY-MM-DD');
      const endDate = currentMonth.endOf('month').format('YYYY-MM-DD');
      
      const result = await scheduleApi.getMyList({
        startDate,
        endDate,
      });
      setSchedules(result || []);
    } catch (error) {
      console.error('加载排班失败', error);
    } finally {
      setLoading(false);
    }
  };

  const getSchedulesByDate = (date: Dayjs): Schedule[] => {
    const dateStr = date.format('YYYY-MM-DD');
    return schedules.filter(s => s.scheduleDate === dateStr);
  };

  const dateCellRender = (date: Dayjs) => {
    const daySchedules = getSchedulesByDate(date);
    if (daySchedules.length === 0) return null;

    // 检查该日期是否有休息日的排班
    const hasRestDay = daySchedules.some(s => s.isRestDay);

    return (
      <ul style={{ listStyle: 'none', padding: 0, margin: 0 }}>
        {hasRestDay && (
          <li style={{ marginBottom: 4 }}>
            <Tag color="orange" style={{ fontSize: 10 }}>休息日</Tag>
          </li>
        )}
        {daySchedules.map((s) => {
          const available = s.totalSlots - s.bookedSlots;
          const isSuspended = s.status === 0;
          const isRestDay = s.isRestDay;
          
          return (
            <li 
              key={s.id} 
              style={{ cursor: 'pointer', marginBottom: 2 }}
              onClick={(e) => {
                e.stopPropagation();
                if (!isSuspended) {
                  openSuspendModal(s);
                }
              }}
            >
              <Badge 
                status={isSuspended ? 'error' : isRestDay ? 'warning' : (available > 0 ? 'success' : 'default')} 
                text={
                  <span style={{ fontSize: 12, opacity: isRestDay ? 0.7 : 1 }}>
                    {s.timeSlot ? TIME_SLOT_MAP[s.timeSlot] : ''}
                    {isSuspended ? (
                      <Tag color="red" style={{ marginLeft: 4, fontSize: 10 }}>停诊</Tag>
                    ) : (
                      <span style={{ marginLeft: 4 }}>{s.bookedSlots}/{s.totalSlots}</span>
                    )}
                  </span>
                } 
              />
            </li>
          );
        })}
      </ul>
    );
  };

  const openSuspendModal = (schedule: Schedule) => {
    setCurrentSchedule(schedule);
    setSuspendReason('');
    setNotifyPatients(true);
    setSuspendModalVisible(true);
  };

  const handleSuspend = async () => {
    if (!currentSchedule) return;

    setSuspendLoading(true);
    try {
      await scheduleApi.suspendSchedule(currentSchedule, suspendReason);
      message.success('停诊申请已提交');

      setSuspendModalVisible(false);
      loadSchedules();
    } catch (error: any) {
      message.error(error.message || '操作失败');
    } finally {
      setSuspendLoading(false);
    }
  };

  const handlePanelChange = (date: Dayjs) => {
    setCurrentMonth(date);
  };

  // 统计当月数据
  const monthStats = {
    total: schedules.length,
    suspended: schedules.filter(s => s.status === 0).length,
    totalSlots: schedules.reduce((sum, s) => sum + s.totalSlots, 0),
    bookedSlots: schedules.reduce((sum, s) => sum + s.bookedSlots, 0),
  };

  return (
    <PageContainer>
      <Spin spinning={loading}>
        {/* 统计卡片 */}
        <div style={{ display: 'flex', gap: 16, marginBottom: 16 }}>
          <ProCard style={{ flex: 1 }}>
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: 24, fontWeight: 500, color: '#1677ff' }}>{monthStats.total}</div>
              <div style={{ color: '#666' }}>本月排班</div>
            </div>
          </ProCard>
          <ProCard style={{ flex: 1 }}>
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: 24, fontWeight: 500, color: '#52c41a' }}>{monthStats.bookedSlots}</div>
              <div style={{ color: '#666' }}>已预约</div>
            </div>
          </ProCard>
          <ProCard style={{ flex: 1 }}>
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: 24, fontWeight: 500, color: '#faad14' }}>{monthStats.totalSlots - monthStats.bookedSlots}</div>
              <div style={{ color: '#666' }}>剩余号源</div>
            </div>
          </ProCard>
          <ProCard style={{ flex: 1 }}>
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: 24, fontWeight: 500, color: '#ff4d4f' }}>{monthStats.suspended}</div>
              <div style={{ color: '#666' }}>停诊</div>
            </div>
          </ProCard>
        </div>

        {/* 日历 */}
        <ProCard>
          <Calendar 
            cellRender={(date) => dateCellRender(date)} 
            onPanelChange={handlePanelChange}
          />
        </ProCard>

        {/* 图例 */}
        <div style={{ marginTop: 16, display: 'flex', gap: 24 }}>
          <span><Badge status="success" /> 有剩余号源</span>
          <span><Badge status="default" /> 已约满</span>
          <span><Badge status="warning" /> 休息日</span>
          <span><Badge status="error" /> 停诊</span>
          <span style={{ color: '#999', marginLeft: 'auto' }}>点击排班可申请停诊（休息日排班小程序端不可预约）</span>
        </div>
      </Spin>

      {/* 停诊确认弹窗 */}
      <Modal
        title="申请停诊"
        open={suspendModalVisible}
        onCancel={() => setSuspendModalVisible(false)}
        onOk={handleSuspend}
        confirmLoading={suspendLoading}
        okText="确认停诊"
        okButtonProps={{ danger: true }}
      >
        <div style={{ marginBottom: 16 }}>
          <p>
            确定要停诊 <strong>{currentSchedule?.scheduleDate}</strong> 
            <strong> {TIME_SLOT_MAP[currentSchedule?.timeSlot || 'morning']} </strong>的排班吗？
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

export default SchedulePage;
