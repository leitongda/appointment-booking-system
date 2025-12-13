import { PageContainer, ProTable, ModalForm, ProFormDatePicker, ProFormSelect, ProFormTextArea } from '@ant-design/pro-components';
import type { ProColumns, ActionType } from '@ant-design/pro-components';
import { Button, Tag, Space, message, Popconfirm, Alert } from 'antd';
import { PlusOutlined } from '@ant-design/icons';
import { useRef, useState } from 'react';
import { leaveRequestApi } from '@hospital/api';
import type { LeaveRequest } from '@hospital/shared';

const LeaveRequestPage: React.FC = () => {
  const actionRef = useRef<ActionType>();
  const [stopModalVisible, setStopModalVisible] = useState(false);
  const [changeModalVisible, setChangeModalVisible] = useState(false);
  
  // 模拟医生ID
  const doctorId = localStorage.getItem('doctorId') || '';

  const handleStopClinic = async (values: any) => {
    try {
      await leaveRequestApi.createStopClinic({
        doctorId,
        stopDate: values.stopDate,
        stopPeriod: values.stopPeriod,
        reason: values.reason,
      });
      message.success('停诊申请已提交');
      setStopModalVisible(false);
      actionRef.current?.reload();
      return true;
    } catch (error: any) {
      message.error(error.message || '提交失败');
      return false;
    }
  };

  const handleScheduleChange = async (values: any) => {
    try {
      await leaveRequestApi.createScheduleChange({
        doctorId,
        originalDate: values.originalDate,
        originalPeriod: values.originalPeriod,
        targetDate: values.targetDate,
        targetPeriod: values.targetPeriod,
        reason: values.reason,
      });
      message.success('调班申请已提交');
      setChangeModalVisible(false);
      actionRef.current?.reload();
      return true;
    } catch (error: any) {
      message.error(error.message || '提交失败');
      return false;
    }
  };

  const handleCancel = async (id: string) => {
    try {
      await leaveRequestApi.cancel(id, doctorId);
      message.success('已取消');
      actionRef.current?.reload();
    } catch (error: any) {
      message.error(error.message || '取消失败');
    }
  };

  const getStatusTag = (status: string) => {
    const statusMap: Record<string, { color: string; text: string }> = {
      pending: { color: 'processing', text: '待审核' },
      approved: { color: 'success', text: '已通过' },
      rejected: { color: 'error', text: '已拒绝' },
      cancelled: { color: 'default', text: '已取消' },
    };
    const config = statusMap[status] || { color: 'default', text: status };
    return <Tag color={config.color}>{config.text}</Tag>;
  };

  const getTypeTag = (type: string) => {
    return type === 'stop_clinic' 
      ? <Tag color="orange">停诊</Tag> 
      : <Tag color="blue">调班</Tag>;
  };

  const getPeriodText = (period: string) => {
    const map: Record<string, string> = {
      morning: '上午',
      afternoon: '下午',
      evening: '晚上',
      all: '全天',
    };
    return map[period] || period;
  };

  const columns: ProColumns<LeaveRequest>[] = [
    { 
      title: '类型', 
      dataIndex: 'requestType', 
      width: 80,
      render: (_, r) => getTypeTag(r.requestType),
      valueEnum: {
        stop_clinic: '停诊',
        schedule_change: '调班',
      }
    },
    { 
      title: '日期/时段', 
      width: 180,
      search: false,
      render: (_, r) => {
        if (r.requestType === 'stop_clinic') {
          return `${r.stopDate} ${getPeriodText(r.stopPeriod || '')}`;
        }
        return (
          <div>
            <div>原：{r.originalDate} {getPeriodText(r.originalPeriod || '')}</div>
            <div>调：{r.targetDate} {getPeriodText(r.targetPeriod || '')}</div>
          </div>
        );
      }
    },
    { title: '原因', dataIndex: 'reason', width: 200, ellipsis: true, search: false },
    { 
      title: '受影响预约', 
      dataIndex: 'affectedAppointments', 
      width: 100,
      search: false,
      render: (val) => val ? <Tag color="red">{val}人</Tag> : '-'
    },
    { 
      title: '状态', 
      dataIndex: 'status', 
      width: 100,
      render: (_, r) => getStatusTag(r.status),
      valueEnum: {
        pending: '待审核',
        approved: '已通过',
        rejected: '已拒绝',
        cancelled: '已取消',
      }
    },
    { title: '审核意见', dataIndex: 'reviewComment', width: 150, ellipsis: true, search: false },
    { title: '申请时间', dataIndex: 'createdAt', width: 160, valueType: 'dateTime', search: false },
    { 
      title: '操作', 
      valueType: 'option',
      width: 100,
      render: (_, record) => (
        record.status === 'pending' ? (
          <Popconfirm title="确定取消该申请吗？" onConfirm={() => handleCancel(record.id)}>
            <a style={{ color: 'red' }}>取消</a>
          </Popconfirm>
        ) : '-'
      )
    },
  ];

  const periodOptions = [
    { label: '上午', value: 'morning' },
    { label: '下午', value: 'afternoon' },
    { label: '晚上', value: 'evening' },
    { label: '全天', value: 'all' },
  ];

  return (
    <PageContainer>
      <Alert 
        message="温馨提示" 
        description="停诊或调班申请提交后需等待管理员审核，审核通过后系统将自动通知受影响的患者。" 
        type="info" 
        showIcon 
        style={{ marginBottom: 16 }}
      />
      
      <ProTable<LeaveRequest>
        actionRef={actionRef}
        rowKey="id"
        columns={columns}
        search={{ labelWidth: 'auto' }}
        toolBarRender={() => [
          <Button key="stop" type="primary" danger icon={<PlusOutlined />} onClick={() => setStopModalVisible(true)}>
            申请停诊
          </Button>,
          <Button key="change" type="primary" icon={<PlusOutlined />} onClick={() => setChangeModalVisible(true)}>
            申请调班
          </Button>
        ]}
        request={async (params) => {
          const { current, pageSize, requestType, status } = params;
          const result = await leaveRequestApi.getMyList(doctorId, status);
          // 前端过滤类型
          let data = result;
          if (requestType) {
            data = result.filter((r: LeaveRequest) => r.requestType === requestType);
          }
          return { 
            data: data.slice((current! - 1) * pageSize!, current! * pageSize!), 
            success: true, 
            total: data.length 
          };
        }}
      />

      {/* 停诊申请弹窗 */}
      <ModalForm
        title="申请停诊"
        open={stopModalVisible}
        onOpenChange={setStopModalVisible}
        onFinish={handleStopClinic}
        modalProps={{ destroyOnHidden: true }}
      >
        <ProFormDatePicker 
          name="stopDate" 
          label="停诊日期" 
          rules={[{ required: true, message: '请选择停诊日期' }]}
          fieldProps={{ 
            disabledDate: (current: any) => current && current.valueOf() < Date.now() - 86400000 
          }}
        />
        <ProFormSelect 
          name="stopPeriod" 
          label="停诊时段" 
          options={periodOptions}
          rules={[{ required: true, message: '请选择停诊时段' }]}
        />
        <ProFormTextArea 
          name="reason" 
          label="停诊原因" 
          rules={[{ required: true, message: '请填写停诊原因' }]}
          fieldProps={{ rows: 3, maxLength: 500, showCount: true }}
        />
      </ModalForm>

      {/* 调班申请弹窗 */}
      <ModalForm
        title="申请调班"
        open={changeModalVisible}
        onOpenChange={setChangeModalVisible}
        onFinish={handleScheduleChange}
        modalProps={{ destroyOnHidden: true }}
      >
        <ProFormDatePicker 
          name="originalDate" 
          label="原出诊日期" 
          rules={[{ required: true }]}
        />
        <ProFormSelect 
          name="originalPeriod" 
          label="原出诊时段" 
          options={periodOptions.filter(o => o.value !== 'all')}
          rules={[{ required: true }]}
        />
        <ProFormDatePicker 
          name="targetDate" 
          label="调整至日期" 
          rules={[{ required: true }]}
        />
        <ProFormSelect 
          name="targetPeriod" 
          label="调整至时段" 
          options={periodOptions.filter(o => o.value !== 'all')}
          rules={[{ required: true }]}
        />
        <ProFormTextArea 
          name="reason" 
          label="调班原因" 
          rules={[{ required: true }]}
          fieldProps={{ rows: 3, maxLength: 500, showCount: true }}
        />
      </ModalForm>
    </PageContainer>
  );
};

export default LeaveRequestPage;
