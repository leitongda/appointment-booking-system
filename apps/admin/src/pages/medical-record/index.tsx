import { EyeOutlined } from '@ant-design/icons';
import type { ActionType, ProColumns } from '@ant-design/pro-components';
import { PageContainer, ProTable } from '@ant-design/pro-components';
import { App, Button, Descriptions, Drawer, Space, Spin, Tag } from 'antd';
import { useRef, useState } from 'react';
import { departmentApi, doctorApi, medicalRecordApi } from '@hospital/api';
import type { MedicalRecord, MedicalRecordListItem } from '@hospital/api';
import { fetchAllData } from '@/utils/fetchAllData';
import dayjs from 'dayjs';

const STATUS_MAP: Record<number, { text: string; color: string }> = {
  0: { text: '草稿', color: 'default' },
  1: { text: '已完成', color: 'success' },
  2: { text: '已归档', color: 'processing' },
};

const MedicalRecordPage: React.FC = () => {
  const { message } = App.useApp();
  const actionRef = useRef<ActionType>();
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [detailLoading, setDetailLoading] = useState(false);
  const [currentRecord, setCurrentRecord] = useState<MedicalRecord | null>(null);

  const handleView = async (id: string) => {
    setDetailLoading(true);
    setDrawerOpen(true);
    try {
      const result = await medicalRecordApi.getDetail(id);
      setCurrentRecord(result);
    } catch (error: any) {
      message.error(error.message || '加载病历详情失败');
      setDrawerOpen(false);
    } finally {
      setDetailLoading(false);
    }
  };

  const columns: ProColumns<MedicalRecordListItem>[] = [
    {
      title: '关键字',
      dataIndex: 'keyword',
      hideInTable: true,
      fieldProps: {
        placeholder: '病历号/患者姓名/诊断',
      },
    },
    {
      title: '医生',
      dataIndex: 'doctorId',
      hideInTable: true,
      valueType: 'select',
      fieldProps: {
        showSearch: true,
        optionFilterProp: 'label',
        placeholder: '请选择医生',
      },
      request: async () => {
        try {
          const doctors = await fetchAllData((page, pageSize) => doctorApi.getList({ page, pageSize }));
          return [
            { label: '全部医生', value: '' },
            ...doctors.map((doctor: any) => ({ label: doctor.name, value: doctor.id })),
          ];
        } catch {
          return [];
        }
      },
    },
    {
      title: '科室',
      dataIndex: 'departmentId',
      hideInTable: true,
      valueType: 'select',
      fieldProps: {
        showSearch: true,
        optionFilterProp: 'label',
        placeholder: '请选择科室',
      },
      request: async () => {
        try {
          const departments = await fetchAllData((page, pageSize) => departmentApi.getList({ page, pageSize }));
          return [
            { label: '全部科室', value: '' },
            ...departments.map((department: any) => ({ label: department.name, value: department.id })),
          ];
        } catch {
          return [];
        }
      },
    },
    {
      title: '就诊日期',
      dataIndex: 'visitDateRange',
      hideInTable: true,
      valueType: 'dateRange',
      search: {
        transform: (value) => {
          if (!value) return {};
          return {
            startDate: value[0],
            endDate: value[1],
          };
        },
      },
    },
    {
      title: '状态',
      dataIndex: 'status',
      hideInTable: true,
      valueType: 'select',
      valueEnum: Object.fromEntries(
        Object.entries(STATUS_MAP).map(([key, value]) => [key, { text: value.text }]),
      ),
    },
    {
      title: '病历号',
      dataIndex: 'recordNo',
      width: 160,
      copyable: true,
      search: false,
    },
    {
      title: '患者',
      dataIndex: 'patientName',
      width: 100,
      search: false,
    },
    {
      title: '医生',
      dataIndex: 'doctorName',
      width: 100,
      search: false,
    },
    {
      title: '科室',
      dataIndex: 'departmentName',
      width: 110,
      search: false,
    },
    {
      title: '诊断',
      dataIndex: 'diagnosis',
      ellipsis: true,
      search: false,
    },
    {
      title: '就诊日期',
      dataIndex: 'visitDate',
      width: 120,
      valueType: 'date',
      search: false,
    },
    {
      title: '状态',
      dataIndex: 'status',
      width: 100,
      search: false,
      render: (_, record) => {
        const status = STATUS_MAP[record.status] || { text: '未知', color: 'default' };
        return <Tag color={status.color}>{status.text}</Tag>;
      },
    },
    {
      title: '创建时间',
      dataIndex: 'createdAt',
      width: 180,
      valueType: 'dateTime',
      search: false,
    },
    {
      title: '操作',
      key: 'option',
      valueType: 'option',
      width: 100,
      render: (_, record) => (
        <Space>
          <Button type="link" size="small" icon={<EyeOutlined />} onClick={() => handleView(record.id)}>
            查看
          </Button>
        </Space>
      ),
    },
  ];

  return (
    <PageContainer>
      <ProTable<MedicalRecordListItem>
        headerTitle="病历管理"
        actionRef={actionRef}
        rowKey="id"
        columns={columns}
        request={async (params) => {
          const {
            current,
            pageSize,
            keyword,
            doctorId,
            departmentId,
            startDate,
            endDate,
            status,
          } = params;

          const result = await medicalRecordApi.getList({
            keyword: keyword || undefined,
            doctorId: doctorId || undefined,
            departmentId: departmentId || undefined,
            startDate: startDate || undefined,
            endDate: endDate || undefined,
            status: status !== undefined && status !== '' ? Number(status) : undefined,
            page: current,
            pageSize,
          });

          return {
            data: result.data || [],
            total: result.total || 0,
            success: true,
          };
        }}
        pagination={{ defaultPageSize: 10 }}
        search={{ labelWidth: 'auto' }}
      />

      <Drawer
        title={currentRecord?.recordNo ? `病历详情 · ${currentRecord.recordNo}` : '病历详情'}
        open={drawerOpen}
        onClose={() => {
          setDrawerOpen(false);
          setCurrentRecord(null);
        }}
        width={720}
      >
        <Spin spinning={detailLoading}>
          {currentRecord ? (
            <Descriptions column={2} bordered size="small" items={[
              { key: '0', label: '病历号', children: currentRecord.recordNo },
              { key: '1', label: '状态', children: (
                <Tag color={STATUS_MAP[currentRecord.status]?.color || 'default'}>
                  {STATUS_MAP[currentRecord.status]?.text || '未知'}
                </Tag>
              ) },
              { key: '2', label: '患者', children: currentRecord.patientName || '-' },
              { key: '3', label: '手机号', children: currentRecord.patientPhone || '-' },
              { key: '4', label: '医生', children: currentRecord.doctorName || '-' },
              { key: '5', label: '科室', children: currentRecord.departmentName || '-' },
              { key: '6', label: '就诊日期', children: currentRecord.visitDate ? dayjs(currentRecord.visitDate).format('YYYY-MM-DD HH:mm') : '-' },
              { key: '7', label: '总费用', children: typeof currentRecord.totalFee === 'number' ? `¥${currentRecord.totalFee}` : '-' },
              { key: '8', label: '主诉', span: 2, children: currentRecord.chiefComplaint || '-' },
              { key: '9', label: '现病史', span: 2, children: currentRecord.presentIllness || '-' },
              { key: '10', label: '既往史', span: 2, children: currentRecord.pastHistory || '-' },
              { key: '11', label: '过敏史', span: 2, children: currentRecord.allergyHistory || '-' },
              { key: '12', label: '体格检查', span: 2, children: currentRecord.physicalExam || '-' },
              { key: '13', label: '辅助检查', span: 2, children: currentRecord.auxiliaryExam || '-' },
              { key: '14', label: '诊断', span: 2, children: currentRecord.diagnosis || '-' },
              { key: '15', label: '治疗方案', span: 2, children: currentRecord.treatment || '-' },
              { key: '16', label: '处方', span: 2, children: currentRecord.prescription || '-' },
              { key: '17', label: '医嘱', span: 2, children: currentRecord.advice || '-' },
              { key: '18', label: '创建时间', children: currentRecord.createdAt ? dayjs(currentRecord.createdAt).format('YYYY-MM-DD HH:mm:ss') : '-' },
              { key: '19', label: '更新时间', children: currentRecord.updatedAt ? dayjs(currentRecord.updatedAt).format('YYYY-MM-DD HH:mm:ss') : '-' },
            ]} />
          ) : null}
        </Spin>
      </Drawer>
    </PageContainer>
  );
};

export default MedicalRecordPage;
