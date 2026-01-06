import React, { useState } from 'react';
import { Button, Dropdown, Modal, Upload, message, Space, Alert, Table, Progress, Typography } from 'antd';
import { DownloadOutlined, UploadOutlined, FileExcelOutlined, MoreOutlined } from '@ant-design/icons';
import type { UploadProps, MenuProps } from 'antd';
import type { RcFile } from 'antd/es/upload';
import { request } from '@umijs/max';
import { getToken } from '@hospital/shared';

const { Text } = Typography;

export interface ImportExportProps {
  /** 模块名称，用于显示 */
  moduleName: string;
  /** 导出接口路径 */
  exportUrl?: string;
  /** 导入接口路径 */
  importUrl?: string;
  /** 模板下载路径 */
  templateUrl?: string;
  /** 导出时的查询参数 */
  exportParams?: Record<string, any>;
  /** 导入成功后的回调 */
  onImportSuccess?: () => void;
  /** 是否显示导出按钮 */
  showExport?: boolean;
  /** 是否显示导入按钮 */
  showImport?: boolean;
}

interface ImportResult {
  success_count: number;
  fail_count: number;
  total: number;
  errors: Array<{
    row: number;
    data: Record<string, any>;
    errors: string[];
  }>;
}

const ImportExport: React.FC<ImportExportProps> = ({
  moduleName,
  exportUrl,
  importUrl,
  templateUrl,
  exportParams = {},
  onImportSuccess,
  showExport = true,
  showImport = true,
}) => {
  const [importModalVisible, setImportModalVisible] = useState(false);
  const [importing, setImporting] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [importResult, setImportResult] = useState<ImportResult | null>(null);
  const [selectedFile, setSelectedFile] = useState<RcFile | null>(null);

  // 导出数据
  const handleExport = async () => {
    if (!exportUrl) return;
    
    setExporting(true);
    try {
      const params = new URLSearchParams();
      Object.entries(exportParams).forEach(([key, value]) => {
        if (value !== undefined && value !== null && value !== '') {
          params.append(key, String(value));
        }
      });
      
      const queryString = params.toString();
      const url = queryString ? `${exportUrl}?${queryString}` : exportUrl;
      
      const response = await fetch(url, {
        headers: {
          Authorization: `Bearer ${getToken()}`,
        },
      });
      
      if (!response.ok) {
        throw new Error('导出失败');
      }
      
      const blob = await response.blob();
      const contentDisposition = response.headers.get('Content-Disposition');
      let filename = `${moduleName}_${new Date().toISOString().slice(0, 10)}.xlsx`;
      
      if (contentDisposition) {
        const match = contentDisposition.match(/filename=(.+)/);
        if (match) {
          filename = match[1];
        }
      }
      
      const downloadUrl = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = downloadUrl;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(downloadUrl);
      
      message.success('导出成功');
    } catch (error: any) {
      message.error(error.message || '导出失败');
    } finally {
      setExporting(false);
    }
  };

  // 下载模板
  const handleDownloadTemplate = async () => {
    if (!templateUrl) return;
    
    try {
      const response = await fetch(templateUrl, {
        headers: {
          Authorization: `Bearer ${getToken()}`,
        },
      });
      
      if (!response.ok) {
        throw new Error('下载模板失败');
      }
      
      const blob = await response.blob();
      const downloadUrl = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = downloadUrl;
      link.download = `${moduleName}_导入模板.xlsx`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(downloadUrl);
      
      message.success('模板下载成功');
    } catch (error: any) {
      message.error(error.message || '下载模板失败');
    }
  };

  // 上传配置
  const uploadProps: UploadProps = {
    accept: '.xlsx,.xls',
    maxCount: 1,
    beforeUpload: (file) => {
      setSelectedFile(file);
      return false;
    },
    onRemove: () => {
      setSelectedFile(null);
    },
  };

  // 执行导入
  const handleImport = async () => {
    if (!selectedFile || !importUrl) return;
    
    setImporting(true);
    setImportResult(null);
    
    try {
      const formData = new FormData();
      formData.append('file', selectedFile);
      
      const result = await request<ImportResult>(importUrl, {
        method: 'POST',
        data: formData,
        requestType: 'form',
      });
      
      setImportResult(result);
      
      if (result.fail_count === 0) {
        message.success(`导入成功！共导入 ${result.success_count} 条数据`);
        setImportModalVisible(false);
        setSelectedFile(null);
        onImportSuccess?.();
      } else {
        message.warning(`导入完成：成功 ${result.success_count} 条，失败 ${result.fail_count} 条`);
      }
    } catch (error: any) {
      message.error(error.message || '导入失败');
    } finally {
      setImporting(false);
    }
  };

  // 关闭弹窗
  const handleCloseModal = () => {
    setImportModalVisible(false);
    setSelectedFile(null);
    setImportResult(null);
  };

  // 下拉菜单项
  const menuItems: MenuProps['items'] = [];
  
  if (showExport && exportUrl) {
    menuItems.push({
      key: 'export',
      icon: <DownloadOutlined />,
      label: '导出数据',
      onClick: handleExport,
    });
  }
  
  if (showImport && importUrl) {
    menuItems.push({
      key: 'import',
      icon: <UploadOutlined />,
      label: '导入数据',
      onClick: () => setImportModalVisible(true),
    });
  }
  
  if (templateUrl) {
    menuItems.push({
      key: 'template',
      icon: <FileExcelOutlined />,
      label: '下载导入模板',
      onClick: handleDownloadTemplate,
    });
  }

  // 错误表格列
  const errorColumns = [
    { title: '行号', dataIndex: 'row', width: 80 },
    { 
      title: '错误信息', 
      dataIndex: 'errors', 
      render: (errors: string[]) => errors.join('; '),
    },
  ];

  if (menuItems.length === 0) {
    return null;
  }

  // 如果只有一个按钮，直接显示
  if (menuItems.length === 1) {
    const item = menuItems[0];
    return (
      <>
        <Button
          icon={item?.icon}
          loading={item?.key === 'export' && exporting}
          onClick={item?.onClick as any}
        >
          {item?.label}
        </Button>
        
        {/* 导入弹窗 */}
        <Modal
          title={`导入${moduleName}`}
          open={importModalVisible}
          onCancel={handleCloseModal}
          onOk={handleImport}
          confirmLoading={importing}
          okText="开始导入"
          cancelText="取消"
          width={600}
          destroyOnHidden
        >
          <Space direction="vertical" style={{ width: '100%' }} size="middle">
            <Alert
              message="导入说明"
              description={
                <ul style={{ margin: 0, paddingLeft: 20 }}>
                  <li>请先下载导入模板，按模板格式填写数据</li>
                  <li>支持 .xlsx 和 .xls 格式的 Excel 文件</li>
                  <li>红色表头为必填字段</li>
                </ul>
              }
              type="info"
              showIcon
            />
            
            {templateUrl && (
              <Button icon={<FileExcelOutlined />} onClick={handleDownloadTemplate}>
                下载导入模板
              </Button>
            )}
            
            <Upload.Dragger {...uploadProps}>
              <p className="ant-upload-drag-icon">
                <UploadOutlined style={{ fontSize: 48, color: '#1890ff' }} />
              </p>
              <p className="ant-upload-text">点击或拖拽文件到此区域上传</p>
              <p className="ant-upload-hint">仅支持 .xlsx 和 .xls 格式</p>
            </Upload.Dragger>
            
            {importResult && importResult.fail_count > 0 && (
              <>
                <Alert
                  message={`导入结果：成功 ${importResult.success_count} 条，失败 ${importResult.fail_count} 条`}
                  type="warning"
                  showIcon
                />
                <Table
                  size="small"
                  columns={errorColumns}
                  dataSource={importResult.errors}
                  rowKey="row"
                  pagination={{ pageSize: 5 }}
                  scroll={{ y: 200 }}
                />
              </>
            )}
          </Space>
        </Modal>
      </>
    );
  }

  return (
    <>
      <Dropdown menu={{ items: menuItems }} placement="bottomRight">
        <Button loading={exporting}>
          导入导出 <MoreOutlined />
        </Button>
      </Dropdown>
      
      {/* 导入弹窗 */}
      <Modal
        title={`导入${moduleName}`}
        open={importModalVisible}
        onCancel={handleCloseModal}
        onOk={handleImport}
        confirmLoading={importing}
        okText="开始导入"
        cancelText="取消"
        okButtonProps={{ disabled: !selectedFile }}
        width={600}
        destroyOnHidden
      >
        <Space direction="vertical" style={{ width: '100%' }} size="middle">
          <Alert
            message="导入说明"
            description={
              <ul style={{ margin: 0, paddingLeft: 20 }}>
                <li>请先下载导入模板，按模板格式填写数据</li>
                <li>支持 .xlsx 和 .xls 格式的 Excel 文件</li>
                <li>红色表头为必填字段</li>
              </ul>
            }
            type="info"
            showIcon
          />
          
          {templateUrl && (
            <Button icon={<FileExcelOutlined />} onClick={handleDownloadTemplate}>
              下载导入模板
            </Button>
          )}
          
          <Upload.Dragger {...uploadProps}>
            <p className="ant-upload-drag-icon">
              <UploadOutlined style={{ fontSize: 48, color: '#1890ff' }} />
            </p>
            <p className="ant-upload-text">点击或拖拽文件到此区域上传</p>
            <p className="ant-upload-hint">仅支持 .xlsx 和 .xls 格式</p>
          </Upload.Dragger>
          
          {importResult && importResult.fail_count > 0 && (
            <>
              <Alert
                message={`导入结果：成功 ${importResult.success_count} 条，失败 ${importResult.fail_count} 条`}
                type="warning"
                showIcon
              />
              <Table
                size="small"
                columns={errorColumns}
                dataSource={importResult.errors}
                rowKey="row"
                pagination={{ pageSize: 5 }}
                scroll={{ y: 200 }}
              />
            </>
          )}
        </Space>
      </Modal>
    </>
  );
};

export default ImportExport;
