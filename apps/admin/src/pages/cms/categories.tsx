/**
 * 栏目管理 - 列表页（树形）
 *
 * 栏目按站点组织，列表以树形展示。顶部提供站点筛选。
 */
import { useEffect, useMemo, useState } from 'react';
import { PageContainer } from '@ant-design/pro-components';
import { App, Button, Card, Space, Tree } from 'antd';
import type { DataNode } from 'antd/es/tree';
import { PlusOutlined, EditOutlined, DeleteOutlined } from '@ant-design/icons';
import { history, useAccess } from '@umijs/max';
import { categoryApi, siteApi } from '@hospital/api';
import type { CmsCategory, CmsCategoryTreeNode, CmsSite } from '@hospital/api';

const CategoryListPage: React.FC = () => {
  const { message, modal } = App.useApp();
  const access = useAccess();
  const [sites, setSites] = useState<CmsSite[]>([]);
  const [siteId, setSiteId] = useState<string | undefined>();
  const [tree, setTree] = useState<CmsCategoryTreeNode[]>([]);
  const [loading, setLoading] = useState(false);
  const [expandedKeys, setExpandedKeys] = useState<React.Key[]>([]);

  // 加载站点列表（用于切换）
  const loadSites = async () => {
    try {
      const all: CmsSite[] = [];
      let page = 1;
      // 拉取全部站点（一般数量不多）
      // eslint-disable-next-line no-constant-condition
      while (true) {
        const res = await siteApi.getList({ page, pageSize: 100 });
        all.push(...(res.data || []));
        if (all.length >= (res.total || 0)) break;
        page += 1;
      }
      setSites(all);
      if (!siteId && all.length > 0) setSiteId(all[0].id);
    } catch (e: any) {
      message.error(e.message || '加载站点失败');
    }
  };

  const loadTree = async (sid?: string) => {
    if (!sid) {
      setTree([]);
      return;
    }
    setLoading(true);
    try {
      const data = await categoryApi.getTree({ siteId: sid });
      setTree(data);
      // 默认展开全部
      setExpandedKeys(collectKeys(data));
    } catch (e: any) {
      message.error(e.message || '加载栏目失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadSites();
  }, []);

  useEffect(() => {
    loadTree(siteId);
  }, [siteId]);

  const handleDelete = (record: CmsCategory) => {
    modal.confirm({
      title: '删除栏目',
      content: `确定删除栏目「${record.name}」吗？`,
      onOk: async () => {
        try {
          await categoryApi.delete(record.id);
          message.success('删除成功');
          loadTree(siteId);
        } catch (e: any) {
          message.error(e.message || '删除失败');
        }
      },
    });
  };

  // 把栏目树转为 antd Tree 数据节点
  const treeData: DataNode[] = useMemo(
    () =>
      tree.map((node) => ({
        key: node.id,
        title: (
          <Space>
            <span>{node.name}</span>
            <span style={{ color: '#999', fontSize: 12 }}>/ {node.slug}</span>
            {access.hasPermission('cms:category:update') && (
              <Button
                type="link"
                size="small"
                icon={<EditOutlined />}
                onClick={(e) => {
                  e.stopPropagation();
                  history.push(`/cms/categories/${node.id}/edit`);
                }}
              />
            )}
            {access.hasPermission('cms:category:delete') && (
              <Button
                type="link"
                size="small"
                danger
                icon={<DeleteOutlined />}
                onClick={(e) => {
                  e.stopPropagation();
                  handleDelete(node);
                }}
              />
            )}
          </Space>
        ),
        children: node.children?.length ? toDataNodes(node.children, access, handleDelete) : undefined,
      })) as DataNode[],
    [tree, access],
  );

  return (
    <PageContainer>
      <Card
        title="栏目管理"
        extra={[
          <Space key="actions">
            <select
              value={siteId || ''}
              onChange={(e) => setSiteId(e.target.value)}
              style={{ height: 32, borderRadius: 6, borderColor: '#d9d9d9', padding: '0 8px' }}
            >
              {sites.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name}
                </option>
              ))}
            </select>
            {access.hasPermission('cms:category:create') && siteId && (
              <Button
                type="primary"
                icon={<PlusOutlined />}
                onClick={() => history.push(`/cms/categories/create?siteId=${siteId}`)}
              >
                新增栏目
              </Button>
            )}
          </Space>,
        ]}
      >
        {sites.length === 0 ? (
          <div style={{ color: '#999', padding: 24, textAlign: 'center' }}>
            暂无站点，请先在「站点管理」中创建站点。
          </div>
        ) : (
          <Tree
            treeData={treeData}
            expandedKeys={expandedKeys}
            onExpand={(keys) => setExpandedKeys(keys)}
            showLine
            blockNode
          />
        )}
      </Card>
    </PageContainer>
  );
};

/** 递归收集树的所有 key（用于默认展开） */
function collectKeys(nodes: CmsCategoryTreeNode[]): React.Key[] {
  const keys: React.Key[] = [];
  const walk = (list: CmsCategoryTreeNode[]) => {
    list.forEach((n) => {
      keys.push(n.id);
      if (n.children?.length) walk(n.children);
    });
  };
  walk(nodes);
  return keys;
}

/** 递归把栏目子节点转为 DataNode */
function toDataNodes(
  nodes: CmsCategoryTreeNode[],
  access: ReturnType<typeof useAccess>,
  handleDelete: (r: CmsCategory) => void,
): DataNode[] {
  return nodes.map((node) => ({
    key: node.id,
    title: (
      <Space>
        <span>{node.name}</span>
        <span style={{ color: '#999', fontSize: 12 }}>/ {node.slug}</span>
        {access.hasPermission('cms:category:update') && (
          <Button
            type="link"
            size="small"
            icon={<EditOutlined />}
            onClick={(e) => {
              e.stopPropagation();
              history.push(`/cms/categories/${node.id}/edit`);
            }}
          />
        )}
        {access.hasPermission('cms:category:delete') && (
          <Button
            type="link"
            size="small"
            danger
            icon={<DeleteOutlined />}
            onClick={(e) => {
              e.stopPropagation();
              handleDelete(node);
            }}
          />
        )}
      </Space>
    ),
    children: node.children?.length ? toDataNodes(node.children, access, handleDelete) : undefined,
  })) as DataNode[];
}

export default CategoryListPage;
