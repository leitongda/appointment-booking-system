import { useState, useCallback } from 'react';
import { Card, Button, Space, App, Alert } from 'antd';
import { ThunderboltOutlined, ReloadOutlined } from '@ant-design/icons';
import { 
  ModalForm, 
  ProFormDateRangePicker,
  ProFormSelect,
} from '@ant-design/pro-components';
import type { Dayjs } from 'dayjs';
import { useAccess } from '@umijs/max';
import { scheduleTemplateApi } from '@hospital/api';
import type { Schedule, ScheduleTemplate } from '@hospital/shared';
import ScheduleCalendar from './ScheduleCalendar';
import ScheduleEditModal from './ScheduleEditModal';

interface DoctorScheduleTabProps {
  doctorId: string;
  doctorName?: string;
}

const DoctorScheduleTab: React.FC<DoctorScheduleTabProps> = ({ doctorId, doctorName }) => {
  const { message } = App.useApp();
  const access = useAccess();
  
  const [selectedDate, setSelectedDate] = useState<Dayjs | null>(null);
  const [selectedSchedules, setSelectedSchedules] = useState<Schedule[]>([]);
  const [editModalOpen, setEditModalOpen] = useState(false);
  const [generateModalOpen, setGenerateModalOpen] = useState(false);
  const [templates, setTemplates] = useState<ScheduleTemplate[]>([]);
  const [refreshKey, setRefreshKey] = useState(0);

  const handleDateClick = (date: Dayjs, schedules: Schedule[]) => {
    setSelectedDate(date);
    setSelectedSchedules(schedules);
    setEditModalOpen(true);
  };

  const handleRefresh = useCallback(() => {
    setRefreshKey((prev) => prev + 1);
  }, []);

  const handleScheduleSuccess = () => {
    // 关闭弹窗并刷新日历数据
    setEditModalOpen(false);
    handleRefresh();
  };

  const loadTemplates = async () => {
    try {
      const result = await scheduleTemplateApi.getList({
        doctorId,
        pageSize: 100,
        status: 1,
      });
      setTemplates(result.data ?? []);
    } catch (error) {
      console.error('加载模板失败', error);
    }
  };

  const handleOpenGenerateModal = async () => {
    await loadTemplates();
    setGenerateModalOpen(true);
  };

  const handleGenerateSubmit = async (values: any) => {
    const { dateRange, templateIds } = values;
    if (!dateRange || dateRange.length !== 2) {
      message.error('请选择日期范围');
      return false;
    }

    if (!templateIds || templateIds.length === 0) {
      message.error('请选择排班模板');
      return false;
    }

    try {
      const result = await scheduleTemplateApi.generate({
        templateIds,
        startDate: dateRange[0],
        endDate: dateRange[1],
      });
      message.success(result.message || '生成成功');
      setGenerateModalOpen(false);
      handleRefresh();
      return true;
    } catch (error: any) {
      message.error(error.message || '生成排班失败');
      return false;
    }
  };

  return (
    <Card
      title={doctorName ? `${doctorName} 的排班` : '排班管理'}
      extra={
        <Space>
          <Button icon={<ReloadOutlined />} onClick={handleRefresh}>
            刷新
          </Button>
          {access.hasPermission?.('schedule:template') && (
            <Button
              type="primary"
              icon={<ThunderboltOutlined />}
              onClick={handleOpenGenerateModal}
            >
              从模板生成
            </Button>
          )}
        </Space>
      }
    >
      <Alert
        title="点击日历中的日期可以查看和编辑当天的排班"
        type="info"
        showIcon
        style={{ marginBottom: 16 }}
      />
      
      <ScheduleCalendar
        key={refreshKey}
        doctorId={doctorId}
        onDateClick={handleDateClick}
      />

      <ScheduleEditModal
        open={editModalOpen}
        onOpenChange={setEditModalOpen}
        doctorId={doctorId}
        date={selectedDate}
        schedules={selectedSchedules}
        onSuccess={handleScheduleSuccess}
      />

      {/* 从模板生成排班弹窗 */}
      <ModalForm
        title="从模板生成排班"
        open={generateModalOpen}
        onOpenChange={setGenerateModalOpen}
        onFinish={handleGenerateSubmit}
        width={500}
        modalProps={{ destroyOnHidden: true }}
      >
        {templates.length === 0 ? (
          <Alert
            title="该医生暂无排班模板"
            description="请先在「排班管理 - 排班模板」中为该医生创建排班模板"
            type="warning"
            showIcon
            style={{ marginBottom: 16 }}
          />
        ) : (
          <>
            <Alert
              title={`找到 ${templates.length} 个可用模板`}
              type="info"
              showIcon
              style={{ marginBottom: 16 }}
            />
            <ProFormSelect
              name="templateIds"
              label="选择模板"
              mode="multiple"
              options={templates.map((t) => ({
                label: `${t.name} (周${['日', '一', '二', '三', '四', '五', '六'][(t as any).weekday ?? 0]} ${t.startTime}-${t.endTime})`,
                value: t.id,
              }))}
              rules={[{ required: true, message: '请选择至少一个模板' }]}
            />
          </>
        )}
        <ProFormDateRangePicker
          name="dateRange"
          label="生成日期范围"
          rules={[{ required: true, message: '请选择日期范围' }]}
          fieldProps={{
            style: { width: '100%' },
          }}
          extra="系统将根据模板配置的星期和排班方式，在日期范围内生成对应的排班"
        />
      </ModalForm>
    </Card>
  );
};

export default DoctorScheduleTab;

