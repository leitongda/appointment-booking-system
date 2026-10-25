import type { ActionType, ProColumns } from '@ant-design/pro-components';
import {PageContainer, ProTable} from '@ant-design/pro-components';
import {useRef} from 'react';
import {auditLogApi} from '@hospital/api';
import {createListRequest} from '@/utils/proTable';

const CheckinAuditLogsPage: React.FC = () => {
  const actionRef = useRef<ActionType>();

  const columns: ProColumns[] = [
    {
      title: '患者姓名',
      dataIndex: 'patientName',
      width: 100,
      search: false,
    },
    {
      title: '患者电话',
      dataIndex: 'patientPhone',
      width: 120,
      search: false,
    },
    {
      title: '医生姓名',
      dataIndex: 'doctorName',
      width: 100,
      search: false,
    },
    {
      title: '科室',
      dataIndex: 'departmentName',
      width: 100,
      search: false,
    },
    {
      title: '签到时间',
      dataIndex: 'checkinTime',
      valueType: 'dateTime',
      width: 160,
      search: { transform: (value: any) => value },
    },
    {
      title: '签到方式',
      dataIndex: 'checkinMethod',
      width: 100,
      valueType: 'select',
      valueEnum: {
        QR_CODE: { text: '扫码签到', status: 'Processing' },
        MANUAL: { text: '后台签到', status: 'Default' },
        PHONE: { text: '手机端签到', status: 'Success' },
      },
    },
    {
      title: '状态',
      dataIndex: 'status',
      width: 80,
      valueType: 'select',
      valueEnum: {
        SUCCESS: { text: '成功', status: 'Success' },
        FAILED: { text: '失败', status: 'Error' },
        CANCELLED: { text: '已取消', status: 'Default' },
      },
    },
    {
      title: '设备信息',
      dataIndex: 'deviceInfo',
      width: 150,
      search: false,
      ellipsis: true,
    },
    {
      title: '位置信息',
      dataIndex: 'locationInfo',
      width: 150,
      search: false,
      ellipsis: true,
    },
    {
      title: '操作人类型',
      dataIndex: 'operatorType',
      width: 100,
      valueType: 'select',
      valueEnum: {
        USER: { text: '患者' },
        ADMIN: { text: '管理员' },
        DOCTOR: { text: '医生' },
      },
    },
    {
      title: '失败原因',
      dataIndex: 'failReason',
      width: 200,
      search: false,
      ellipsis: true,
    },
  ];

  return (
    <PageContainer title="签到审计日志">
      <ProTable
        headerTitle="签到审计日志"
        actionRef={actionRef}
        rowKey="id"
        columns={columns}
        search={{
          labelWidth: 'auto',
        }}
        request={createListRequest(auditLogApi.getCheckinLogs, ({ checkinTime, ...params }) => ({
          ...params,
          startTime: checkinTime?.[0],
          endTime: checkinTime?.[1],
        }))}
        pagination={{
          defaultPageSize: 20,
          showSizeChanger: true,
        }}
        columnsState={{
          defaultValue: {
            // 隐藏一些默认不显示的列
            departmentName: { show: false },
            deviceInfo: { show: false },
            locationInfo: { show: false },
            operatorType: { show: false },
          } as any,
        }}
      />
    </PageContainer>
  );
};

export default CheckinAuditLogsPage;
