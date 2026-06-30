import { ProForm, ProFormText, ProFormDigit, ProFormList } from '@ant-design/pro-components';
import { Typography, Space } from 'antd';
import { PlusOutlined, DeleteOutlined } from '@ant-design/icons';
import type { ImageTabProps } from './types';
import { DEFAULT_IMAGE_CONFIG } from './defaults';

const { Text } = Typography;

const ImageTab: React.FC<ImageTabProps> = ({
  imageConfig,
  onSubmit,
  canEdit,
  loading,
}) => (
  <ProForm
    key={loading ? 'image-loading' : 'image-loaded'}
    onFinish={onSubmit}
    initialValues={{ ...DEFAULT_IMAGE_CONFIG, ...imageConfig }}
    submitter={{ searchConfig: { submitText: '保存设置' }, resetButtonProps: { style: { display: 'none' } } }}
    disabled={!canEdit}
  >
    <Text type="secondary" style={{ display: 'block', marginBottom: 16 }}>
      配置图片上传时的缩略图生成规则和压缩质量。上传时可选择是否生成缩略图。
    </Text>
    <ProFormDigit
      name="compressQuality"
      label="压缩质量"
      min={1}
      max={100}
      fieldProps={{ precision: 0, addonAfter: '%' }}
      extra="图片压缩质量，1-100，值越高质量越好但文件越大，推荐 75-90"
    />
    <ProFormList
      name="thumbnailSizes"
      label="缩略图尺寸配置"
      creatorButtonProps={{ creatorButtonText: '添加尺寸', icon: <PlusOutlined /> }}
      copyIconProps={false}
      deleteIconProps={{ Icon: DeleteOutlined, tooltipText: '删除' }}
      itemRender={({ listDom, action }) => (
        <div style={{ display: 'flex', alignItems: 'flex-start', gap: 8 }}>
          {listDom}
          {action}
        </div>
      )}
    >
      <Space align="baseline">
        <ProFormText name="name" placeholder="名称，如 small" rules={[{ required: true, message: '请输入名称' }]} width="sm" />
        <ProFormDigit name="width" placeholder="宽度" min={1} max={4096} fieldProps={{ precision: 0, addonAfter: 'px' }} rules={[{ required: true, message: '请输入宽度' }]} width="sm" />
        <ProFormDigit name="height" placeholder="高度" min={1} max={4096} fieldProps={{ precision: 0, addonAfter: 'px' }} rules={[{ required: true, message: '请输入高度' }]} width="sm" />
      </Space>
    </ProFormList>
    <Text type="secondary">
      提示：缩略图会等比例缩放，保持原图宽高比，不会拉伸变形。宽度和高度表示缩略图的最大尺寸。
    </Text>
  </ProForm>
);

export default ImageTab;
