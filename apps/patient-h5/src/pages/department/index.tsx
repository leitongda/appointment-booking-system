import { NavBar, SideBar, List, SearchBar, Skeleton } from 'antd-mobile';
import { history } from 'umi';
import { useState, useEffect } from 'react';
import { departmentApi } from '@hospital/api';
import type { DepartmentTreeNode } from '@hospital/shared';
import styles from './index.less';

const DepartmentPage: React.FC = () => {
  const [loading, setLoading] = useState(true);
  const [departments, setDepartments] = useState<DepartmentTreeNode[]>([]);
  const [activeKey, setActiveKey] = useState<string>('');
  const [searchValue, setSearchValue] = useState('');

  useEffect(() => {
    loadDepartments();
  }, []);

  const loadDepartments = async () => {
    try {
      const data = await departmentApi.getTree();
      setDepartments(data);
      if (data.length > 0) {
        setActiveKey(data[0].id);
      }
    } catch (error) {
      console.error('加载科室失败', error);
    } finally {
      setLoading(false);
    }
  };

  const currentDept = departments.find((d) => d.id === activeKey);

  const handleSelectDept = (deptId: string, deptName: string) => {
    history.push(`/doctor?departmentId=${deptId}&departmentName=${encodeURIComponent(deptName)}`);
  };

  if (loading) {
    return (
      <div className={styles.container}>
        <NavBar onBack={() => history.back()}>选择科室</NavBar>
        <Skeleton.Paragraph lineCount={10} animated />
      </div>
    );
  }

  return (
    <div className={styles.container}>
      <NavBar onBack={() => history.back()}>选择科室</NavBar>
      <SearchBar 
        placeholder="搜索科室" 
        className={styles.search}
        value={searchValue}
        onChange={setSearchValue}
      />
      <div className={styles.content}>
        <SideBar activeKey={activeKey} onChange={setActiveKey} className={styles.sidebar}>
          {departments.map((dept) => (
            <SideBar.Item key={dept.id} title={dept.name} />
          ))}
        </SideBar>
        <div className={styles.list}>
          <List>
            {currentDept?.children
              .filter((child) => !searchValue || child.name.includes(searchValue))
              .map((child) => (
                <List.Item
                  key={child.id}
                  onClick={() => handleSelectDept(child.id, child.name)}
                  arrow
                >
                  {child.name}
                </List.Item>
              ))}
          </List>
        </div>
      </div>
    </div>
  );
};

export default DepartmentPage;
