import { scheduleApi } from '@hospital/api';
import {
  Button,
  Modal,
  Select,
  Space,
  Table,
  Tag,
  Typography,
  Upload,
  message,
} from 'antd';
import {
  DownloadOutlined,
  InboxOutlined,
  UploadOutlined,
} from '@ant-design/icons';
import React, { useState } from 'react';

const { Dragger } = Upload;
const { Text, Link } = Typography;

interface ImportModalProps {
  open: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

interface ImportError {
  row: number;
  errors: string[];
}

interface ImportResult {
  totalCount: number;
  successCount: number;
  skippedCount: number;
  conflictCount: number;
  errors: ImportError[];
}

type ConflictStrategy = 'skip' | 'overwrite' | 'report';

const ImportModal: React.FC<ImportModalProps> = ({
  open,
  onClose,
  onSuccess,
}) => {
  const [file, setFile] = useState<File | null>(null);
  const [conflictStrategy, setConflictStrategy] =
    useState<ConflictStrategy>('skip');
  const [importing, setImporting] = useState(false);
  const [result, setResult] = useState<ImportResult | null>(null);

  const handleUpload = async () => {
    if (!file) {
      message.warning('请先选择要导入的 Excel 文件');
      return;
    }

    setImporting(true);
    setResult(null);
    try {
      const res = await scheduleApi.importSchedules(file, conflictStrategy);
      setResult(res);
      if (res.successCount > 0) {
        message.success(`成功导入 ${res.successCount} 条排班`);
        onSuccess();
      } else {
        message.warning('导入完成，但未成功创建任何排班');
      }
    } catch (err: any) {
      message.error(err?.response?.data?.message || '导入失败，请检查文件格式');
    } finally {
      setImporting(false);
    }
  };

  const handleDownloadTemplate = async () => {
    try {
      await scheduleApi.downloadImportTemplate();
    } catch {
      message.error('模板下载失败');
    }
  };

  const handleClose = () => {
    setFile(null);
    setResult(null);
    setConflictStrategy('skip');
    onClose();
  };

  const errorColumns = [
    {
      title: '行号',
      dataIndex: 'row',
      key: 'row',
      width: 80,
    },
    {
      title: '错误信息',
      dataIndex: 'errors',
      key: 'errors',
      render: (errors: string[]) => errors.join('; '),
    },
  ];

  return (
    <Modal
      title="导入排班数据"
      open={open}
      onCancel={handleClose}
      width={640}
      footer={
        result
          ? [
              <Button key="close" onClick={handleClose}>
                关闭
              </Button>,
            ]
          : [
              <Button key="cancel" onClick={handleClose}>
                取消
              </Button>,
              <Button
                key="submit"
                type="primary"
                loading={importing}
                disabled={!file}
                onClick={handleUpload}
                icon={<UploadOutlined />}
              >
                开始导入
              </Button>,
            ]
      }
    >
      {!result ? (
        <Space direction="vertical" style={{ width: '100%' }} size="large">
          <div>
            <Text>冲突策略：</Text>
            <Select
              value={conflictStrategy}
              onChange={setConflictStrategy}
              style={{ width: 200, marginLeft: 8 }}
              options={[
                { label: '跳过冲突项', value: 'skip' },
                { label: '覆盖已有排班', value: 'overwrite' },
                { label: '仅报告冲突', value: 'report' },
              ]}
            />
          </div>

          <Dragger
            accept=".xlsx,.xls"
            maxCount={1}
            beforeUpload={(f) => {
              setFile(f);
              return false;
            }}
            fileList={file ? [{ uid: '-1', name: file.name, status: 'done' }] : []}
            onRemove={() => setFile(null)}
          >
            <p className="ant-upload-drag-icon">
              <InboxOutlined />
            </p>
            <p className="ant-upload-text">点击或拖拽 Excel 文件到此区域上传</p>
            <p className="ant-upload-hint">支持 .xlsx 和 .xls 格式</p>
          </Dragger>

          <div>
            <Link onClick={handleDownloadTemplate}>
              <DownloadOutlined /> 下载导入模板
            </Link>
          </div>
        </Space>
      ) : (
        <Space direction="vertical" style={{ width: '100%' }} size="middle">
          <div>
            <Text>导入结果：</Text>
            <Tag color="blue">总行数：{result.totalCount}</Tag>
            <Tag color="green">成功：{result.successCount}</Tag>
            {result.skippedCount > 0 && (
              <Tag color="orange">跳过：{result.skippedCount}</Tag>
            )}
            {result.conflictCount > 0 && (
              <Tag color="red">冲突：{result.conflictCount}</Tag>
            )}
          </div>

          {result.errors.length > 0 && (
            <Table
              columns={errorColumns}
              dataSource={result.errors.map((e, i) => ({ ...e, key: i }))}
              size="small"
              pagination={false}
              scroll={{ y: 300 }}
              title={() => <Text strong>错误详情</Text>}
            />
          )}
        </Space>
      )}
    </Modal>
  );
};

export default ImportModal;
