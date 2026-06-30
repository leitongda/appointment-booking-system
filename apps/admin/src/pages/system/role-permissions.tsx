import { FooterToolbar, ModalForm, PageContainer, ProFormDigit, ProFormSelect, ProFormText } from '@ant-design/pro-components';
import {
  ApartmentOutlined,
  ApiOutlined,
  AppstoreOutlined,
  BarChartOutlined,
  BellOutlined,
  CalendarOutlined,
  CommentOutlined,
  DashboardOutlined,
  DeleteOutlined,
  ExceptionOutlined,
  FileTextOutlined,
  FilterOutlined,
  LayoutOutlined,
  PlusOutlined,
  SearchOutlined,
  SettingOutlined,
  ShopOutlined,
  SolutionOutlined,
  TeamOutlined,
  ThunderboltOutlined,
  UserOutlined,
} from '@ant-design/icons';
import {
  Alert,
  App,
  Button,
  Card,
  Col,
  Empty,
  Input,
  Popconfirm,
  Row,
  Space,
  Spin,
  Statistic,
  Switch,
  Tag,
  Tree,
  Typography,
} from 'antd';
import './role-permissions.less';
import type { TreeDataNode, TreeProps } from 'antd';
import { useEffect, useState, type ReactNode } from 'react';
import { history, useParams } from '@umijs/max';
import { adminApi } from '@hospital/api';
import type { Role } from '@hospital/api';
import {
  collectPermissionCodes,
  CONTROL_TYPE_LABELS,
  CONTROL_TYPE_ORDER,
  countCoveredModules,
  countSelectedByControlType,
  countVisibleByControlType,
  filterPermissionsTree,
  getAllKeys,
  isHighRiskPermission,
  normalizePermissionsTree,
  type PermissionControlType,
  type PermissionViewNode,
} from './role-permissions.utils';

const { Paragraph, Text } = Typography;

const CONTROL_TYPE_ICONS: Record<PermissionControlType, ReactNode> = {
  page: <LayoutOutlined style={{ color: 'var(--color-primary)' }} />,
  tab: <AppstoreOutlined style={{ color: '#7a5af8' }} />,
  action: <ThunderboltOutlined style={{ color: 'var(--color-evening)' }} />,
  api: <ApiOutlined style={{ color: '#13a8a8' }} />,
};

const MODULE_ICON_MAP: Record<string, ReactNode> = {
  dashboard: <DashboardOutlined />,
  shop: <ShopOutlined />,
  apartment: <ApartmentOutlined />,
  user: <UserOutlined />,
  calendar: <CalendarOutlined />,
  schedule: <SolutionOutlined />,
  team: <TeamOutlined />,
  exception: <ExceptionOutlined />,
  comment: <CommentOutlined />,
  bell: <BellOutlined />,
  fileText: <FileTextOutlined />,
  barChart: <BarChartOutlined />,
  setting: <SettingOutlined />,
  appstore: <AppstoreOutlined />,
};

const MODULE_ICON_STYLE_MAP: Record<string, { color: string; background: string; borderColor: string }> = {
  dashboard: { color: '#1d4ed8', background: 'var(--color-primary-bg)', borderColor: '#bfdbfe' },
  shop: { color: '#c2410c', background: 'var(--color-white)7ed', borderColor: '#fed7aa' },
  apartment: { color: '#5b21b6', background: '#f5f3ff', borderColor: '#ddd6fe' },
  user: { color: '#2563eb', background: 'var(--color-primary-bg)', borderColor: '#bfdbfe' },
  calendar: { color: '#0f766e', background: '#ecfeff', borderColor: '#a5f3fc' },
  schedule: { color: '#0f766e', background: '#ecfeff', borderColor: '#a5f3fc' },
  team: { color: '#1d4ed8', background: 'var(--color-primary-bg)', borderColor: '#bfdbfe' },
  exception: { color: '#b91c1c', background: '#fef2f2', borderColor: '#fecaca' },
  comment: { color: '#7c3aed', background: '#f5f3ff', borderColor: '#ddd6fe' },
  bell: { color: '#b45309', background: 'var(--color-white)beb', borderColor: '#fde68a' },
  fileText: { color: '#0369a1', background: '#f0f9ff', borderColor: '#bae6fd' },
  barChart: { color: '#166534', background: '#f0fdf4', borderColor: '#bbf7d0' },
  setting: { color: '#475467', background: '#f8fafc', borderColor: '#d0d5dd' },
  appstore: { color: '#7c3aed', background: '#f5f3ff', borderColor: '#ddd6fe' },
};

const MODULE_ICON_FALLBACK_BY_CODE: Record<string, string> = {
  dashboard: 'dashboard',
  store: 'shop',
  department: 'apartment',
  doctor: 'user',
  schedule: 'calendar',
  appointment: 'schedule',
  patient: 'team',
  'leave-request': 'exception',
  feedback: 'comment',
  message: 'bell',
  content: 'fileText',
  statistics: 'barChart',
  system: 'setting',
};

const CONTROL_TYPE_CLASS_NAMES: Record<PermissionControlType, string> = {
  page: 'type-icon-page',
  tab: 'type-icon-tab',
  action: 'type-icon-action',
  api: 'type-icon-api',
};

const renderPermissionTitle = (
  permission: PermissionViewNode,
  onDelete?: (code: string) => void,
): ReactNode => {
  return (
    <div className={`permission-node node-type-${permission.controlType}`}>
      <div className="node-left">
        <span
          className={`type-icon-badge ${CONTROL_TYPE_CLASS_NAMES[permission.controlType]}`}
          title={CONTROL_TYPE_LABELS[permission.controlType]}
          aria-label={CONTROL_TYPE_LABELS[permission.controlType]}
        >
          {CONTROL_TYPE_ICONS[permission.controlType]}
        </span>
        <span className="node-title">{permission.name}</span>
        {isHighRiskPermission(permission) && <Tag color="error">高风险</Tag>}
      </div>
      <div className="node-right">
        <span>{permission.code}</span>
        {onDelete && (
          <Popconfirm
            title="确定删除该权限？"
            description="删除后不可恢复，已分配该权限的角色将失去此权限。"
            onConfirm={(e) => { e?.stopPropagation(); onDelete(permission.code); }}
            onCancel={(e) => e?.stopPropagation()}
          >
            <Button
              type="text"
              size="small"
              danger
              icon={<DeleteOutlined />}
              onClick={(e) => e.stopPropagation()}
            />
          </Popconfirm>
        )}
      </div>
    </div>
  );
};

const convertToTreeData = (
  permissions: PermissionViewNode[],
  onDelete?: (code: string) => void,
): TreeDataNode[] => {
  return permissions.map((permission) => ({
    key: permission.code,
    title: renderPermissionTitle(permission, onDelete),
    children: permission.children?.length ? convertToTreeData(permission.children, onDelete) : undefined,
  }));
};

const resolveModuleIconKey = (module: PermissionViewNode): string => {
  return module.icon || MODULE_ICON_FALLBACK_BY_CODE[module.code] || 'appstore';
};

const renderModuleIcon = (module: PermissionViewNode): ReactNode => {
  const iconKey = resolveModuleIconKey(module);
  const iconStyle = MODULE_ICON_STYLE_MAP[iconKey] || MODULE_ICON_STYLE_MAP.appstore;

  return (
    <span
      className="module-card-icon"
      style={{
        color: iconStyle.color,
        background: iconStyle.background,
        borderColor: iconStyle.borderColor,
      }}
      aria-hidden="true"
    >
      {MODULE_ICON_MAP[iconKey] || MODULE_ICON_MAP.appstore}
    </span>
  );
};

const flattenPermissionMap = (permissions: PermissionViewNode[]): Map<string, PermissionViewNode> => {
  const permissionMap = new Map<string, PermissionViewNode>();

  const traverse = (nodes: PermissionViewNode[]) => {
    nodes.forEach((node) => {
      permissionMap.set(node.code, node);
      if (node.children?.length) {
        traverse(node.children);
      }
    });
  };

  traverse(permissions);
  return permissionMap;
};

const summarizeCodesByControlType = (
  codes: string[],
  permissionMap: Map<string, PermissionViewNode>,
): Record<PermissionControlType, number> => {
  const summary = {
    page: 0,
    tab: 0,
    action: 0,
    api: 0,
  };

  codes.forEach((code) => {
    const permission = permissionMap.get(code);
    if (permission) {
      summary[permission.controlType] += 1;
    }
  });

  return summary;
};

const renderFooterTypeSummary = (summary: Record<PermissionControlType, number>): ReactNode => {
  return (
    <div className="permission-footer-type-summary">
      {CONTROL_TYPE_ORDER.map((controlType) => (
        <span
          key={controlType}
          className="permission-footer-type-item"
          title={`${CONTROL_TYPE_LABELS[controlType]} ${summary[controlType]}`}
          aria-label={`${CONTROL_TYPE_LABELS[controlType]} ${summary[controlType]}`}
        >
          <span className={`permission-footer-type-dot permission-footer-type-dot-${controlType}`} />
          <span className="permission-footer-type-value">{summary[controlType]}</span>
        </span>
      ))}
    </div>
  );
};

const RolePermissionsPage: React.FC = () => {
  const { message, modal } = App.useApp();
  const { id } = useParams();
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [role, setRole] = useState<Role | null>(null);
  const [permissionsTree, setPermissionsTree] = useState<PermissionViewNode[]>([]);
  const [checkedKeys, setCheckedKeys] = useState<string[]>([]);
  const [initialCheckedKeys, setInitialCheckedKeys] = useState<string[]>([]);
  const [expandedKeys, setExpandedKeys] = useState<string[]>([]);
  const [searchKeyword, setSearchKeyword] = useState('');
  const [activeControlTypes, setActiveControlTypes] = useState<PermissionControlType[]>(CONTROL_TYPE_ORDER);
  const [onlySelected, setOnlySelected] = useState(false);
  const [createModalVisible, setCreateModalVisible] = useState(false);

  async function loadRole() {
    if (!id) return;
    setLoading(true);
    try {
      const data = await adminApi.getRole(id);
      setRole(data);
      setCheckedKeys(data.permissions || []);
      setInitialCheckedKeys(data.permissions || []);
    } catch (error: any) {
      message.error('加载角色信息失败');
    } finally {
      setLoading(false);
    }
  }

  async function loadPermissionsTree() {
    try {
      const tree = await adminApi.getPermissionsTree();
      const normalizedTree = normalizePermissionsTree(tree);
      setPermissionsTree(normalizedTree);
      setExpandedKeys(getAllKeys(normalizedTree));
    } catch (error: any) {
      message.error(error.message || '加载权限列表失败');
    }
  }

  const handleCreatePermission = async (values: any) => {
    try {
      await adminApi.createPermission({
        code: values.code,
        name: values.name,
        type: values.type,
        controlType: values.controlType,
        parentCode: values.parentCode || undefined,
        icon: values.icon || undefined,
        sort: values.sort ?? 0,
      });
      message.success('权限创建成功');
      setCreateModalVisible(false);
      loadPermissionsTree();
      return true;
    } catch (error: any) {
      message.error(error.message || '创建权限失败');
      return false;
    }
  };

  const handleDeletePermission = async (code: string) => {
    try {
      await adminApi.deletePermission(code);
      message.success('权限已删除');
      // 从 checkedKeys 中移除已删除的权限
      setCheckedKeys(checkedKeys.filter((k) => k !== code));
      loadPermissionsTree();
    } catch (error: any) {
      message.error(error.message || '删除权限失败');
    }
  };

  useEffect(() => {
    if (id) {
      loadRole();
      loadPermissionsTree();
    }
  }, [id]);

  useEffect(() => {
    if (!permissionsTree.length) return;
    const nextTree = filterPermissionsTree(permissionsTree, {
      keyword: searchKeyword,
      controlTypes: activeControlTypes,
      checkedKeys: new Set(checkedKeys),
      onlySelected,
    });
    setExpandedKeys(getAllKeys(nextTree));
  }, [permissionsTree, searchKeyword, activeControlTypes, onlySelected]);

  useEffect(() => {
    if (!permissionsTree.length || !onlySelected) return;
    const nextTree = filterPermissionsTree(permissionsTree, {
      keyword: searchKeyword,
      controlTypes: activeControlTypes,
      checkedKeys: new Set(checkedKeys),
      onlySelected,
    });
    setExpandedKeys(getAllKeys(nextTree));
  }, [permissionsTree, checkedKeys, searchKeyword, activeControlTypes, onlySelected]);

  const checkedKeySet = new Set(checkedKeys);
  const filteredPermissionsTree = filterPermissionsTree(permissionsTree, {
    keyword: searchKeyword,
    controlTypes: activeControlTypes,
    checkedKeys: checkedKeySet,
    onlySelected,
  });
  const visiblePermissionCodes = collectPermissionCodes(filteredPermissionsTree);
  const selectedTypeSummary = countSelectedByControlType(permissionsTree, checkedKeySet);
  const visibleTypeSummary = countVisibleByControlType(filteredPermissionsTree);
  const coveredModules = countCoveredModules(permissionsTree, checkedKeySet);
  const permissionMap = flattenPermissionMap(permissionsTree);
  const initialCheckedSet = new Set(initialCheckedKeys);
  const addedCodes = checkedKeys.filter((code) => !initialCheckedSet.has(code));
  const removedCodes = initialCheckedKeys.filter((code) => !checkedKeySet.has(code));
  const hasChanges = addedCodes.length > 0 || removedCodes.length > 0;
  const addedTypeSummary = summarizeCodesByControlType(addedCodes, permissionMap);
  const removedTypeSummary = summarizeCodesByControlType(removedCodes, permissionMap);

  const handlePersist = async () => {
    if (!id) return;
    setSaving(true);
    try {
      await adminApi.updateRolePermissions(id, checkedKeys);
      setInitialCheckedKeys(checkedKeys);
      message.success('权限保存成功');
      history.push('/system/role');
    } catch (error: any) {
      message.error(error.message || '保存失败');
    } finally {
      setSaving(false);
    }
  };

  const handleSave = async () => {
    if (!id) return;
    if (!hasChanges) {
      message.info('当前没有需要保存的变更');
      return;
    }

    modal.confirm({
      title: '确认保存权限变更',
      width: 760,
      okText: '确认保存',
      cancelText: '返回检查',
      content: (
        <div className="permission-diff-dialog">
          <Alert
            type="warning"
            showIcon
            message={`角色“${role?.name || '未命名角色'}”将新增 ${addedCodes.length} 项、移除 ${removedCodes.length} 项权限`}
            description="请确认这次调整符合预期，尤其是高风险操作型权限。保存后将立即影响该角色的页面可见性和操作范围。"
          />
          <div className="permission-diff-grid">
            <Card size="small" className="permission-diff-card permission-diff-card-added">
              <Text strong>新增权限</Text>
              <Text type="secondary">
                页面 {addedTypeSummary.page} · 视图 {addedTypeSummary.tab} · 操作 {addedTypeSummary.action} · 接口 {addedTypeSummary.api}
              </Text>
              {addedCodes.length > 0 ? (
                <div className="permission-diff-tags">
                  {addedCodes.slice(0, 10).map((code) => {
                    const permission = permissionMap.get(code);
                    return (
                      <Tag key={code} color="success">
                        {permission?.name || code}
                      </Tag>
                    );
                  })}
                  {addedCodes.length > 10 && <Tag>+{addedCodes.length - 10} 项</Tag>}
                </div>
              ) : (
                <Text type="secondary">无新增权限</Text>
              )}
            </Card>
            <Card size="small" className="permission-diff-card permission-diff-card-removed">
              <Text strong>移除权限</Text>
              <Text type="secondary">
                页面 {removedTypeSummary.page} · 视图 {removedTypeSummary.tab} · 操作 {removedTypeSummary.action} · 接口 {removedTypeSummary.api}
              </Text>
              {removedCodes.length > 0 ? (
                <div className="permission-diff-tags">
                  {removedCodes.slice(0, 10).map((code) => {
                    const permission = permissionMap.get(code);
                    return (
                      <Tag key={code} color="error">
                        {permission?.name || code}
                      </Tag>
                    );
                  })}
                  {removedCodes.length > 10 && <Tag>+{removedCodes.length - 10} 项</Tag>}
                </div>
              ) : (
                <Text type="secondary">无移除权限</Text>
              )}
            </Card>
          </div>
        </div>
      ),
      onOk: handlePersist,
    });
  };

  const handleCancel = () => {
    if (!hasChanges) {
      history.push('/system/role');
      return;
    }

    modal.confirm({
      title: '放弃未保存的权限调整？',
      content: `当前还有 ${addedCodes.length + removedCodes.length} 项未保存变更，离开后这些调整会丢失。`,
      okText: '放弃并离开',
      cancelText: '继续编辑',
      okButtonProps: { danger: true },
      onOk: () => history.push('/system/role'),
    });
  };

  const onCheck: TreeProps['onCheck'] = (checked) => {
    const checkedKeysValue = Array.isArray(checked) ? checked : checked.checked;
    setCheckedKeys(checkedKeysValue as string[]);
  };

  const toggleControlType = (controlType: PermissionControlType, checked: boolean) => {
    if (checked) {
      const nextTypes = [...activeControlTypes, controlType].filter((value, index, list) => list.indexOf(value) === index);
      setActiveControlTypes(nextTypes);
      return;
    }

    if (activeControlTypes.length === 1) {
      return;
    }

    setActiveControlTypes(activeControlTypes.filter((item) => item !== controlType));
  };

  const handleCheckVisible = (shouldSelect: boolean, codes: string[]) => {
    const visibleCodeSet = new Set(codes);
    if (shouldSelect) {
      const nextKeys = Array.from(new Set([...checkedKeys, ...codes]));
      setCheckedKeys(nextKeys);
      return;
    }

    setCheckedKeys(checkedKeys.filter((key) => !visibleCodeSet.has(key)));
  };

  return (
    <PageContainer
      title={`分配权限 - ${role?.name || ''}`}
      subTitle="按模块理解权限，再按页面、视图、操作和接口能力精确授权"
    >
      <div className="permission-page">
        <Card loading={loading} variant="borderless" className="permission-intro-card">
          <Alert
            type={hasChanges ? 'warning' : 'info'}
            showIcon
            message={hasChanges ? `当前有未保存变更：新增 ${addedCodes.length} 项，移除 ${removedCodes.length} 项` : `当前角色：${role?.name || '未命名角色'}`}
            description={
              <div className="permission-intro-copy">
                <Paragraph>
                  页面权限决定是否能进入某个功能域，Tab / 视图权限决定页内工作台是否可见，按钮 / 操作权限控制创建、编辑、删除等变更行为，
                  接口 / 数据权限则覆盖列表、详情、导出、统计等访问能力。
                </Paragraph>
                {hasChanges && (
                  <Text type="secondary">
                    保存前会展示变更摘要，帮助你确认本次调整影响的权限类型和范围。
                  </Text>
                )}
                {role?.description && <Text type="secondary">{role.description}</Text>}
              </div>
            }
          />
        </Card>

        {permissionsTree.length === 0 ? (
          <div className="permission-empty-loading">
            <Spin tip="加载权限列表中...">
              <span />
            </Spin>
          </div>
        ) : (
          <>
            <Row gutter={[16, 16]} className="permission-overview-row">
              <Col xs={24} sm={12} xl={8}>
                <Card className="summary-card summary-card-selected" variant="borderless">
                  <Statistic title="已选权限" value={checkedKeys.length} suffix={`/ ${collectPermissionCodes(permissionsTree).length}`} />
                  <Text type="secondary">覆盖 {coveredModules} 个业务模块</Text>
                </Card>
              </Col>
              {CONTROL_TYPE_ORDER.map((controlType) => (
                <Col xs={24} sm={12} xl={4} key={controlType}>
                  <Card className={`summary-card summary-card-${controlType}`} variant="borderless">
                    <div className="summary-card-header">
                      <span className="summary-card-icon">{CONTROL_TYPE_ICONS[controlType]}</span>
                      <Text>{CONTROL_TYPE_LABELS[controlType]}</Text>
                    </div>
                    <Statistic value={selectedTypeSummary[controlType]} />
                    <Text type="secondary">当前结果 {visibleTypeSummary[controlType]} 项</Text>
                  </Card>
                </Col>
              ))}
            </Row>

            <Card variant="borderless" className="permission-toolbar-card">
              <div className="permission-toolbar">
                <Input
                  allowClear
                  prefix={<SearchOutlined />}
                  placeholder="搜索权限名称或权限码"
                  value={searchKeyword}
                  onChange={(event) => setSearchKeyword(event.target.value)}
                />
                <div className="permission-toolbar-switch">
                  <span>仅看已选</span>
                  <Switch checked={onlySelected} onChange={setOnlySelected} />
                </div>
                <Space wrap>
                  <Button icon={<PlusOutlined />} type="primary" onClick={() => setCreateModalVisible(true)}>
                    创建权限
                  </Button>
                  <Button icon={<FilterOutlined />} onClick={() => setExpandedKeys(getAllKeys(filteredPermissionsTree))}>
                    展开当前结果
                  </Button>
                  <Button onClick={() => setExpandedKeys([])}>收起全部</Button>
                  <Button type="primary" ghost onClick={() => handleCheckVisible(true, visiblePermissionCodes)}>
                    全选当前结果
                  </Button>
                  <Button danger ghost onClick={() => handleCheckVisible(false, visiblePermissionCodes)}>
                    清空当前结果
                  </Button>
                </Space>
              </div>
              <div className="permission-filter-tags">
                {CONTROL_TYPE_ORDER.map((controlType) => (
                  <Tag.CheckableTag
                    key={controlType}
                    checked={activeControlTypes.includes(controlType)}
                    onChange={(checked) => toggleControlType(controlType, checked)}
                  >
                    <Space size={4}>
                      {CONTROL_TYPE_ICONS[controlType]}
                      {CONTROL_TYPE_LABELS[controlType]}
                    </Space>
                  </Tag.CheckableTag>
                ))}
              </div>
            </Card>

            {filteredPermissionsTree.length === 0 ? (
              <Card variant="borderless" className="permission-result-card">
                <Empty
                  description="当前筛选条件下没有可分配的权限"
                  image={Empty.PRESENTED_IMAGE_SIMPLE}
                />
              </Card>
            ) : (
              <div className="permission-modules-grid">
                {filteredPermissionsTree.map((module) => {
                  const selectedCount = module.descendantCodes.filter((code) => checkedKeySet.has(code)).length;
                  const visibleCount = module.descendantCodes.length;
                  const moduleTypeSummary = countVisibleByControlType([module]);

                  return (
                    <Card
                      key={module.code}
                      variant="borderless"
                      className="permission-module-card"
                      title={
                        <div className="module-card-title">
                          <div className="module-card-title-main">
                            {renderModuleIcon(module)}
                            <div className="module-card-title-copy">
                              <Text strong>
                                {module.name}
                                <Text type="secondary" className="module-card-code">
                                  （{module.code}）
                                </Text>
                              </Text>
                              <div className="module-card-type-summary">
                                {CONTROL_TYPE_ORDER.map((controlType) => (
                                  <span
                                    key={controlType}
                                    className={`module-card-type-pill module-card-type-pill-${controlType}`}
                                  >
                                    {CONTROL_TYPE_LABELS[controlType]} {moduleTypeSummary[controlType]}
                                  </span>
                                ))}
                              </div>
                            </div>
                          </div>
                          <span className="module-card-count">
                            {selectedCount} / {visibleCount}
                          </span>
                        </div>
                      }
                    >
                      <div className="permission-tree-container">
                        <Tree
                          checkable
                          showLine={{ showLeafIcon: false }}
                          blockNode
                          checkedKeys={checkedKeys}
                          expandedKeys={expandedKeys}
                          onExpand={(keys) => setExpandedKeys(keys as string[])}
                          onCheck={onCheck}
                          treeData={convertToTreeData([module], handleDeletePermission)}
                        />
                      </div>
                    </Card>
                  );
                })}
              </div>
            )}

            <ModalForm
              title="创建权限"
              open={createModalVisible}
              onOpenChange={setCreateModalVisible}
              onFinish={handleCreatePermission}
              width={520}
              modalProps={{ destroyOnClose: true }}
            >
              <ProFormText
                name="code"
                label="权限码"
                placeholder="例如：store:create"
                rules={[{ required: true, message: '请输入权限码' }]}
                extra="建议格式：模块:操作，如 doctor:update"
              />
              <ProFormText
                name="name"
                label="权限名称"
                placeholder="例如：创建门店"
                rules={[{ required: true, message: '请输入权限名称' }]}
              />
              <ProFormSelect
                name="type"
                label="权限类型"
                options={[
                  { label: '菜单', value: 'menu' },
                  { label: '按钮', value: 'button' },
                ]}
                rules={[{ required: true, message: '请选择权限类型' }]}
              />
              <ProFormSelect
                name="controlType"
                label="控制类型"
                options={[
                  { label: '页面', value: 'page' },
                  { label: '视图/Tab', value: 'tab' },
                  { label: '操作/按钮', value: 'action' },
                  { label: '接口/数据', value: 'api' },
                ]}
                extra="决定权限在树形结构中的图标和分类"
              />
              <ProFormText
                name="parentCode"
                label="父权限码"
                placeholder="留空则为顶级权限"
                extra="输入已有权限码以创建子权限"
              />
              <ProFormText
                name="icon"
                label="图标"
                placeholder="例如：ShopOutlined"
              />
              <ProFormDigit
                name="sort"
                label="排序"
                min={0}
                initialValue={0}
                extra="数值越小越靠前"
              />
            </ModalForm>

            <FooterToolbar>
              <div className="permission-footer-toolbar">
                {hasChanges ? (
                  <div className="permission-footer-summary">
                    <Text strong>{`待保存变更 ${addedCodes.length + removedCodes.length} 项`}</Text>
                    <Text type="secondary">{`新增 ${addedCodes.length} 项 · 移除 ${removedCodes.length} 项`}</Text>
                  </div>
                ) : (
                  <div className="permission-footer-summary permission-footer-summary-inline">
                    {renderFooterTypeSummary(selectedTypeSummary)}
                    <Text strong>{`当前已选择 ${checkedKeys.length} 个权限点`}</Text>
                  </div>
                )}
                <Space>
                  <Button onClick={handleCancel}>取消</Button>
                  <Button type="primary" loading={saving} onClick={handleSave} disabled={!hasChanges}>
                    保存权限
                  </Button>
                </Space>
              </div>
            </FooterToolbar>
          </>
        )}
      </div>
    </PageContainer>
  );
};

export default RolePermissionsPage;
