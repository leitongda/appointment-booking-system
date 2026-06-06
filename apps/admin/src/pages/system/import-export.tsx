import { useState } from 'react';
import { PageContainer } from '@ant-design/pro-components';
import { Card, Tabs, Table, Button, Upload, Space, Typography } from 'antd';
import {
  DownloadOutlined,
  UploadOutlined,
  ExportOutlined,
} from '@ant-design/icons';
import { dataApi, request } from '@hospital/api';
import { useListPage } from '@/hooks/useListPage';

const { Text } = Typography;

/** 下载 blob 文件 */
const downloadBlob = (blob: Blob, filename: string) => {
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.click();
  window.URL.revokeObjectURL(url);
};

/** 数据类型配置 */
const DATA_TYPES = [
  {
    key: 'doctors',
    label: '医生',
    canExport: true,
    canImport: true,
    hasTemplate: true,
    exportUrl: dataApi.getExportDoctorsUrl,
    importUrl: dataApi.getImportDoctorsUrl,
    templateUrl: dataApi.getDoctorTemplateUrl,
  },
  {
    key: 'patients',
    label: '患者',
    canExport: true,
    canImport: true,
    hasTemplate: true,
    exportUrl: dataApi.getExportPatientsUrl,
    importUrl: dataApi.getImportPatientsUrl,
    templateUrl: dataApi.getPatientTemplateUrl,
  },
  {
    key: 'departments',
    label: '科室',
    canExport: true,
    canImport: true,
    hasTemplate: true,
    exportUrl: dataApi.getExportDepartmentsUrl,
    importUrl: dataApi.getImportDepartmentsUrl,
    templateUrl: dataApi.getDepartmentTemplateUrl,
  },
  {
    key: 'stores',
    label: '门店',
    canExport: true,
    canImport: true,
    hasTemplate: true,
    exportUrl: dataApi.getExportStoresUrl,
    importUrl: dataApi.getImportStoresUrl,
    templateUrl: dataApi.getStoreTemplateUrl,
  },
  {
    key: 'schedule-templates',
    label: '排班模板',
    canExport: true,
    canImport: false,
    hasTemplate: false,
    exportUrl: dataApi.getExportScheduleTemplatesUrl,
  },
  {
    key: 'users',
    label: '系统用户',
    canExport: true,
    canImport: false,
    hasTemplate: false,
    exportUrl: dataApi.getExportUsersUrl,
  },
  {
    key: 'logs',
    label: '操作日志',
    canExport: true,
    canImport: false,
    hasTemplate: false,
    exportUrl: dataApi.getExportLogsUrl,
  },
  {
    key: 'feedbacks',
    label: '用户反馈',
    canExport: true,
    canImport: false,
    hasTemplate: false,
    exportUrl: dataApi.getExportFeedbacksUrl,
  },
  {
    key: 'rule-sets',
    label: '排班规则组',
    canExport: true,
    canImport: true,
    hasTemplate: true,
    exportUrl: dataApi.getExportRuleSetsUrl,
    importUrl: dataApi.getImportRuleSetsUrl,
    templateUrl: dataApi.getRuleSetTemplateUrl,
  },
];

const ImportExportPage: React.FC = () => {
  const { message } = useListPage();
  const [activeTab, setActiveTab] = useState('export');
  const [importing, setImporting] = useState<string | null>(null);

  // 导出：通过 request 下载 blob
  const handleExport = async (item: typeof DATA_TYPES[0]) => {
    const url = item.exportUrl();
    if (!url) return;
    try {
      const blob = (await request.get(url, { responseType: 'blob' })) as any;
      downloadBlob(blob, `${item.label}-${new Date().toISOString().slice(0, 10)}.xlsx`);
    } catch (e: any) {
      message.error(e?.message || '导出失败');
    }
  };

  // 下载模板
  const handleDownloadTemplate = async (item: typeof DATA_TYPES[0]) => {
    if (!item.templateUrl) return;
    const url = item.templateUrl();
    try {
      const blob = (await request.get(url, { responseType: 'blob' })) as any;
      downloadBlob(blob, `${item.label}-导入模板.xlsx`);
    } catch (e: any) {
      message.error(e?.message || '模板下载失败');
    }
  };

  // 导入
  const handleImport = async (item: typeof DATA_TYPES[0], file: File) => {
    if (!item.importUrl) return;
    setImporting(item.key);
    try {
      const url = item.importUrl();
      const formData = new FormData();
      formData.append('file', file);
      await request.post(url, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      message.success(`${item.label}导入成功`);
    } catch (e: any) {
      message.error(e?.message || '导入失败');
    } finally {
      setImporting(null);
    }
  };

  // 导出 Tab 列
  const exportColumns = [
    { title: '数据类型', dataIndex: 'label', key: 'label' },
    {
      title: '操作',
      key: 'action',
      render: (_: any, record: typeof DATA_TYPES[0]) => (
        <Space>
          <Button
            type="primary"
            icon={<ExportOutlined />}
            size="small"
            onClick={() => handleExport(record)}
          >
            导出
          </Button>
          {record.hasTemplate && (
            <Button
              icon={<DownloadOutlined />}
              size="small"
              onClick={() => handleDownloadTemplate(record)}
            >
              下载模板
            </Button>
          )}
        </Space>
      ),
    },
  ];

  // 导入 Tab 列
  const importColumns = [
    { title: '数据类型', dataIndex: 'label', key: 'label' },
    {
      title: '操作',
      key: 'action',
      render: (_: any, record: typeof DATA_TYPES[0]) => {
        if (!record.canImport) {
          return <Text type="secondary">不支持导入</Text>;
        }
        return (
          <Space>
            <Upload
              accept=".xlsx,.xls,.csv"
              showUploadList={false}
              beforeUpload={(file) => {
                handleImport(record, file);
                return false;
              }}
              disabled={importing !== null}
            >
              <Button
                icon={<UploadOutlined />}
                loading={importing === record.key}
                size="small"
              >
                上传导入
              </Button>
            </Upload>
            {record.hasTemplate && (
              <Button
                icon={<DownloadOutlined />}
                size="small"
                onClick={() => handleDownloadTemplate(record)}
              >
                下载模板
              </Button>
            )}
          </Space>
        );
      },
    },
  ];

  const items = [
    {
      key: 'export',
      label: (
        <span>
          <ExportOutlined /> 数据导出
        </span>
      ),
      children: (
        <Table
          columns={exportColumns}
          dataSource={DATA_TYPES.filter((d) => d.canExport)}
          rowKey="key"
          pagination={false}
        />
      ),
    },
    {
      key: 'import',
      label: (
        <span>
          <UploadOutlined /> 数据导入
        </span>
      ),
      children: (
        <Table
          columns={importColumns}
          dataSource={DATA_TYPES}
          rowKey="key"
          pagination={false}
        />
      ),
    },
  ];

  return (
    <PageContainer
      title="数据导入导出"
      content="统一管理所有业务数据的导入、导出和模板下载。"
    >
      <Card>
        <Tabs activeKey={activeTab} onChange={setActiveTab} items={items} />
      </Card>
    </PageContainer>
  );
};

export default ImportExportPage;
