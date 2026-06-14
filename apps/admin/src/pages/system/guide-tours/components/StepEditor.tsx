/**
 * StepEditor - 指引步骤编辑器
 *
 * 支持：
 * - 添加/删除步骤
 * - 拖拽排序（简化版：上下移动）
 * - 每步编辑：target, placement, route, title, description
 */
import { PlusOutlined, DeleteOutlined, ArrowUpOutlined, ArrowDownOutlined } from '@ant-design/icons';
import { Button, Card, Input, Select, Space, Typography } from 'antd';
import type { TourStep } from '@hospital/api';

interface StepEditorProps {
  value?: TourStep[];
  onChange?: (steps: TourStep[]) => void;
}

const PLACEMENT_OPTIONS = [
  { label: '上方 (top)', value: 'top' },
  { label: '下方 (bottom)', value: 'bottom' },
  { label: '左侧 (left)', value: 'left' },
  { label: '右侧 (right)', value: 'right' },
  { label: '左上 (topLeft)', value: 'topLeft' },
  { label: '右上 (topRight)', value: 'topRight' },
  { label: '左下 (bottomLeft)', value: 'bottomLeft' },
  { label: '右下 (bottomRight)', value: 'bottomRight' },
];

const DEFAULT_STEP: TourStep = {
  target: '',
  placement: 'bottom',
  route: '',
  title: { zh: '', en: '' },
  description: { zh: '', en: '' },
  highlightPadding: 4,
};

export default function StepEditor({ value = [], onChange }: StepEditorProps) {
  const steps = value;

  const updateStep = (index: number, field: string, val: any) => {
    const newSteps = [...steps];
    const step = { ...newSteps[index] };

    if (field.startsWith('title.')) {
      const lang = field.split('.')[1];
      step.title = { ...step.title, [lang]: val };
    } else if (field.startsWith('description.')) {
      const lang = field.split('.')[1];
      step.description = { ...step.description, [lang]: val };
    } else {
      (step as any)[field] = val;
    }

    newSteps[index] = step;
    onChange?.(newSteps);
  };

  const addStep = () => {
    onChange?.([...steps, { ...DEFAULT_STEP, title: { zh: '', en: '' }, description: { zh: '', en: '' } }]);
  };

  const removeStep = (index: number) => {
    const newSteps = steps.filter((_, i) => i !== index);
    onChange?.(newSteps);
  };

  const moveStep = (index: number, direction: 'up' | 'down') => {
    const newIndex = direction === 'up' ? index - 1 : index + 1;
    if (newIndex < 0 || newIndex >= steps.length) return;
    const newSteps = [...steps];
    [newSteps[index], newSteps[newIndex]] = [newSteps[newIndex], newSteps[index]];
    onChange?.(newSteps);
  };

  return (
    <div>
      {steps.map((step, index) => (
        <Card
          key={index}
          size="small"
          title={
            <Space>
              <Typography.Text strong>步骤 {index + 1}</Typography.Text>
              <Button size="small" icon={<ArrowUpOutlined />} disabled={index === 0} onClick={() => moveStep(index, 'up')} />
              <Button size="small" icon={<ArrowDownOutlined />} disabled={index === steps.length - 1} onClick={() => moveStep(index, 'down')} />
            </Space>
          }
          extra={
            <Button size="small" danger icon={<DeleteOutlined />} onClick={() => removeStep(index)}>
              删除
            </Button>
          }
          style={{ marginBottom: 12 }}
        >
          <Space direction="vertical" style={{ width: '100%' }} size="middle">
            {/* 基本配置 */}
            <Space style={{ width: '100%' }} wrap>
              <div style={{ flex: 1, minWidth: 200 }}>
                <Typography.Text type="secondary" style={{ fontSize: 12 }}>目标元素 (CSS 选择器)</Typography.Text>
                <Input
                  placeholder=".ant-layout-sider .ant-menu-item:first-child"
                  value={step.target}
                  onChange={(e) => updateStep(index, 'target', e.target.value)}
                />
              </div>
              <div style={{ minWidth: 150 }}>
                <Typography.Text type="secondary" style={{ fontSize: 12 }}>所在路由</Typography.Text>
                <Input
                  placeholder="/dashboard"
                  value={step.route}
                  onChange={(e) => updateStep(index, 'route', e.target.value)}
                />
              </div>
              <div style={{ minWidth: 120 }}>
                <Typography.Text type="secondary" style={{ fontSize: 12 }}>气泡位置</Typography.Text>
                <Select
                  style={{ width: '100%' }}
                  options={PLACEMENT_OPTIONS}
                  value={step.placement}
                  onChange={(val) => updateStep(index, 'placement', val)}
                />
              </div>
            </Space>

            {/* 中文内容 */}
            <Space style={{ width: '100%' }} wrap>
              <div style={{ flex: 1, minWidth: 200 }}>
                <Typography.Text type="secondary" style={{ fontSize: 12 }}>标题 (中文)</Typography.Text>
                <Input
                  placeholder="步骤标题"
                  value={step.title.zh}
                  onChange={(e) => updateStep(index, 'title.zh', e.target.value)}
                />
              </div>
              <div style={{ flex: 2, minWidth: 300 }}>
                <Typography.Text type="secondary" style={{ fontSize: 12 }}>描述 (中文)</Typography.Text>
                <Input.TextArea
                  placeholder="步骤详细说明"
                  value={step.description.zh}
                  onChange={(e) => updateStep(index, 'description.zh', e.target.value)}
                  rows={2}
                />
              </div>
            </Space>

            {/* 英文内容 */}
            <Space style={{ width: '100%' }} wrap>
              <div style={{ flex: 1, minWidth: 200 }}>
                <Typography.Text type="secondary" style={{ fontSize: 12 }}>Title (English)</Typography.Text>
                <Input
                  placeholder="Step title"
                  value={step.title.en}
                  onChange={(e) => updateStep(index, 'title.en', e.target.value)}
                />
              </div>
              <div style={{ flex: 2, minWidth: 300 }}>
                <Typography.Text type="secondary" style={{ fontSize: 12 }}>Description (English)</Typography.Text>
                <Input.TextArea
                  placeholder="Step description"
                  value={step.description.en}
                  onChange={(e) => updateStep(index, 'description.en', e.target.value)}
                  rows={2}
                />
              </div>
            </Space>
          </Space>
        </Card>
      ))}

      <Button type="dashed" block icon={<PlusOutlined />} onClick={addStep} style={{ marginTop: 8 }}>
        添加步骤
      </Button>
    </div>
  );
}
