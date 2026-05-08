import { PageContainer, ProTable } from '@ant-design/pro-components';
import type { ProColumns, ActionType } from '@ant-design/pro-components';
import { Tag, Button, message, Space } from 'antd';
import { EyeOutlined } from '@ant-design/icons';
import { useRef, useState } from 'react';
import { history } from 'umi';
import { appointmentApi } from '@hospital/api';
import { APPOINTMENT_STATUS_MAP, APPOINTMENT_STATUS_COLOR, TIME_SLOT_MAP } from '@hospital/shared';
import type { Appointment } from '@hospital/shared';

const HistoryAppointmentPage: React.FC = () => {
  const actionRef = useRef<ActionType>();

  const columns: ProColumns<Appointment>[] = [
    { title: '预约单号', dataIndex: 'appointmentNo', width: 150 },
    { title: '患者姓名', dataIndex: 'patientName', width: 100 },
    {
      title: '预约日期',
      dataIndex: 'scheduleDate',
      width: 120,
      valueType: 'date',
      search: {
        transform: (value) => ({ startDate: value }),
      },
    },
    {
      title: '时段',
      dataIndex: 'timeSlot',
      width: 80,
      search: false,
      render: (_, r) => TIME_SLOT_MAP[r.timeSlot || ''] || r.timeSlot,
    },
    {
      title: '状态',
      dataIndex: 'status',
      width: 100,
      valueEnum: {
        1: { text: '已预约', status: 'Processing' },
        2: { text: '已签到', status: 'Warning' },
        4: { text: '就诊中', status: 'Processing' },
        5: { text: '已完成', status: 'Success' },
        6: { text: '已取消', status: 'Default' },
        7: { text: '已过期', status: 'Default' },
        8: { text: '已爽约', status: 'Error' },
      },
      render: (_, r) => (
        <Tag color={APPOINTMENT_STATUS_COLOR[r.status]}>
          {APPOINTMENT_STATUS_MAP[r.status]}
        </Tag>
      ),
    },
    { title: '签到时间', dataIndex: 'signInTime', width: 160, valueType: 'dateTime', search: false },
    { title: '完成时间', dataIndex: 'completeTime', width: 160, valueType: 'dateTime', search: false },
    {
      title: '操作',
      valueType: 'option',
      width: 100,
      render: (_, record) => (
        <Space>
          {record.status === 5 && (
            <Button
              type="link"
              icon={<EyeOutlined />}
              onClick={() => history.push(`/medical-record/create?appointmentId=${record.id}`)}
            >
              病历
            </Button>
          )}
        </Space>
      ),
    },
  ];

  return (
    <PageContainer>
      <ProTable<Appointment>
        actionRef={actionRef}
        rowKey="id"
        columns={columns}
        search={{ labelWidth: 'auto' }}
        request={async (params) => {
          try {
            const { current, pageSize, startDate, ...rest } = params;
            const result = await appointmentApi.getMyAppointments({
              page: current || 1,
              pageSize: pageSize || 20,
              startDate: startDate as string,
              ...rest,
            });
            // doctor-portal 端点直接返回数组，非分页格式
            return {
              data: Array.isArray(result) ? result : (result as any).data || [],
              success: true,
              total: Array.isArray(result) ? result.length : (result as any).total || 0,
            };
          } catch (error: any) {
            message.error(error.message || '获取预约列表失败');
            return { data: [], success: false, total: 0 };
          }
        }}
      />
    </PageContainer>
  );
};

export default HistoryAppointmentPage;
