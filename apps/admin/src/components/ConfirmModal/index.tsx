import { Modal, Input, Alert, Space, Typography, Divider, Grid } from 'antd';
import { useCallback } from 'react';
import {
  ExclamationCircleOutlined,
  WarningOutlined,
  DeleteOutlined,
  StopOutlined,
} from '@ant-design/icons';

const { useBreakpoint: _useBreakpoint } = Grid;
const { Text } = Typography;

const CONFIRM_TEXT = 'CONFIRM';

/**
 * 删除影响范围类型
 */
export interface DeleteImpactScope {
  /** 影响的记录数量 */
  affectedCount?: number;
  /** 影响的关联实体描述 */
  relatedEntities?: string[];
  /** 自定义影响描述 */
  customDescription?: string;
}

/**
 * 确认删除选项
 */
export interface ConfirmDeleteOptions {
  /** 标题 */
  title?: string;
  /** 内容描述 */
  content?: React.ReactNode;
  /** 警告消息 */
  alertMessage?: string;
  /** 影响范围 */
  impactScope?: DeleteImpactScope;
  /** 实体名称（如：科室、医生、用户） */
  entityName?: string;
  /** 实体标识（如：科室名称） */
  entityIdentifier?: string;
  /** 是否显示强制确认输入框（默认 true） */
  requireTyping?: boolean;
  /** 确认回调 */
  onOk: () => void | Promise<void>;
}

/**
 * 生成影响范围描述
 */
const generateImpactDescription = (impactScope: DeleteImpactScope, _entityName?: string): React.ReactNode => {
  const items: React.ReactNode[] = [];

  if (impactScope.customDescription) {
    items.push(
      <Alert
        key="custom"
        message={impactScope.customDescription}
        type="warning"
        showIcon
        icon={<WarningOutlined />}
        style={{ marginTop: 8 }}
      />
    );
  }

  if (impactScope.affectedCount !== undefined && impactScope.affectedCount > 0) {
    items.push(
      <div key="count" style={{ marginTop: 8 }}>
        <Text type="warning">
          <ExclamationCircleOutlined style={{ marginRight: 8 }} />
          此操作将影响 <Text strong>{impactScope.affectedCount}</Text> 条关联数据
        </Text>
      </div>
    );
  }

  if (impactScope.relatedEntities && impactScope.relatedEntities.length > 0) {
    items.push(
      <div key="entities" style={{ marginTop: 8 }}>
        <Text type="secondary">关联影响范围：</Text>
        <ul style={{ margin: '4px 0 0 20px', padding: 0 }}>
          {impactScope.relatedEntities.map((entity, index) => (
            <li key={index}>
              <Text type="warning">{entity}</Text>
            </li>
          ))}
        </ul>
      </div>
    );
  }

  return items.length > 0 ? items : null;
};

/**
 * 强制确认删除的 Modal
 * 用户需要输入 "CONFIRM" 才能启用删除按钮
 *
 * @example
 * // 基础用法
 * confirmDelete({
 *   entityName: '科室',
 *   entityIdentifier: '心内科',
 *   onOk: async () => await deleteDepartment(id),
 * });
 *
 * @example
 * // 带影响范围
 * confirmDelete({
 *   entityName: '医生',
 *   entityIdentifier: '张医生',
 *   impactScope: {
 *     affectedCount: 15,
 *     relatedEntities: ['关联的排班记录', '关联的预约记录'],
 *   },
 *   onOk: async () => await deleteDoctor(id),
 * });
 *
 * @example
 * // 不需要输入确认（简单确认）
 * confirmDelete({
 *   title: '确认删除',
 *   content: '删除后数据将无法恢复',
 *   requireTyping: false,
 *   onOk: handleDelete,
 * });
 */
export const confirmDelete = (options: ConfirmDeleteOptions) => {
  const {
    title = '确认删除',
    content,
    alertMessage,
    impactScope,
    entityName = '记录',
    entityIdentifier,
    requireTyping = true,
    onOk,
  } = options;

  let inputValue = '';
  let modalInstance: ReturnType<typeof Modal.confirm>;

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    inputValue = e.target.value;
    // 通过更新按钮状态来反映输入变化
    modalInstance.update({
      okButtonProps: {
        disabled: requireTyping && inputValue !== CONFIRM_TEXT,
      },
    });
  };

  // 构建删除对象描述
  const entityDescription = entityIdentifier
    ? `「${entityIdentifier}」`
    : `此${entityName}`;

  // 构建影响范围内容
  const impactContent = impactScope
    ? generateImpactDescription(impactScope, entityName)
    : null;

  // 基础警告信息
  const defaultWarning = (
    <Alert
      title={
        <Space size={0}>
          <Text strong>删除后果说明：</Text>
          <Text>1. {entityDescription}将被永久删除，无法恢复</Text>
          <Text>2. 相关的历史数据和统计报表可能受到影响</Text>
          {entityIdentifier && (
            <Text>3. 如需重新使用，需要重新创建{entityName}信息</Text>
          )}
        </Space>
      }
      type="error"
      showIcon
      icon={<StopOutlined />}
      style={{ marginTop: 12 }}
    />
  );

  // 自定义警告（如果有 alertMessage）
  const customAlert = alertMessage ? (
    <Alert
      title={alertMessage}
      type="warning"
      showIcon
      style={{ marginTop: 12 }}
    />
  ) : null;

  // 确认输入框
  const confirmInput = requireTyping ? (
    <Space style={{ width: '100%', marginTop: 16 }}>
      <div>
        请输入 <Text keyboard strong style={{ color: '#ff4d4f' }}>{CONFIRM_TEXT}</Text> 以确认删除操作：
      </div>
      <Input
        placeholder={`请输入 ${CONFIRM_TEXT}`}
        onChange={handleInputChange}
        onPressEnter={() => {
          if (!requireTyping || inputValue === CONFIRM_TEXT) {
            modalInstance.destroy();
            onOk();
          }
        }}
        autoFocus
        prefix={<DeleteOutlined style={{ color: '#bfbfbf' }} />}
        status={inputValue && inputValue !== CONFIRM_TEXT ? 'error' : undefined}
      />
      {inputValue && inputValue !== CONFIRM_TEXT && (
        <Text type="danger" style={{ fontSize: 12 }}>
          输入内容不正确，请输入 {CONFIRM_TEXT}
        </Text>
      )}
    </Space>
  ) : null;

  modalInstance = Modal.confirm({
    title: (
      <Space>
        <DeleteOutlined style={{ color: '#ff4d4f' }} />
        {title}
      </Space>
    ),
    width: 520,
    icon: null,
    content: (
      <div style={{ marginTop: 16 }}>
        {/* 主要描述 */}
        {content && <div>{content}</div>}

        {/* 删除对象确认 */}
        {entityIdentifier && !content && (
          <Text>
            您即将删除{entityName}：<Text strong>{entityIdentifier}</Text>
          </Text>
        )}

        {/* 自定义警告 */}
        {customAlert}

        {/* 影响范围 */}
        {impactContent}

        <Divider style={{ margin: '16px 0' }} />

        {/* 操作后果说明 */}
        {defaultWarning}

        {/* 确认输入 */}
        {confirmInput}
      </div>
    ),
    okText: requireTyping ? '确认删除' : '删除',
    okType: 'danger',
    okButtonProps: {
      disabled: requireTyping,
    },
    cancelText: '取消',
    centered: true,
    onOk: async () => {
      if (!requireTyping || inputValue === CONFIRM_TEXT) {
        await onOk();
      }
    },
  });

  return modalInstance;
};

/**
 * 简化的确认删除函数（适用于列表页快速删除）
 *
 * @example
 * confirmSimpleDelete('科室', '心内科', async () => await deleteDepartment(id));
 */
export const confirmSimpleDelete = (
  entityName: string,
  entityIdentifier: string,
  onOk: () => void | Promise<void>,
  options?: Partial<ConfirmDeleteOptions>
) => {
  return confirmDelete({
    entityName,
    entityIdentifier,
    onOk,
    ...options,
  });
};

/**
 * 带影响范围的确认删除（适用于有关联数据的删除）
 *
 * @example
 * confirmDeleteWithImpact('医生', '张医生', {
 *   affectedCount: 15,
 *   relatedEntities: ['3个排班记录', '12个预约记录'],
 * }, async () => await deleteDoctor(id));
 */
export const confirmDeleteWithImpact = (
  entityName: string,
  entityIdentifier: string,
  impactScope: DeleteImpactScope,
  onOk: () => void | Promise<void>,
  options?: Partial<ConfirmDeleteOptions>
) => {
  return confirmDelete({
    entityName,
    entityIdentifier,
    impactScope,
    onOk,
    ...options,
  });
};

/**
 * useConfirmDelete hook
 * 提供一个可复用的删除确认方法
 *
 * @example
 * const confirmDelete = useConfirmDelete();
 *
 * // 基础用法
 * confirmDelete({
 *   entityName: '科室',
 *   entityIdentifier: record.name,
 *   onOk: async () => await deleteDepartment(record.id),
 * });
 *
 * // 带影响范围
 * confirmDelete({
 *   entityName: '医生',
 *   entityIdentifier: record.name,
 *   impactScope: {
 *     affectedCount: record.appointmentCount,
 *     relatedEntities: ['排班记录', '预约记录'],
 *   },
 *   onOk: async () => await deleteDoctor(record.id),
 * });
 */
export const useConfirmDelete = () => {
  return useCallback((options: ConfirmDeleteOptions) => {
    return confirmDelete(options);
  }, []);
};

/**
 * useConfirmSimpleDelete hook
 * 提供简化的删除确认方法
 */
export const useConfirmSimpleDelete = () => {
  return useCallback((
    entityName: string,
    entityIdentifier: string,
    onOk: () => void | Promise<void>,
    options?: Partial<ConfirmDeleteOptions>
  ) => {
    return confirmSimpleDelete(entityName, entityIdentifier, onOk, options);
  }, []);
};

export default confirmDelete;
