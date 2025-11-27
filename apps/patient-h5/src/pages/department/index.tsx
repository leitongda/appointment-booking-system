import { NavBar, SideBar, List, SearchBar } from 'antd-mobile';
import { history } from 'umi';
import { useState } from 'react';
import styles from './index.less';

const mockDepts = [
  { id: '1', name: '内科', children: [{ id: '1-1', name: '心内科' }, { id: '1-2', name: '消化内科' }, { id: '1-3', name: '呼吸内科' }] },
  { id: '2', name: '外科', children: [{ id: '2-1', name: '普外科' }, { id: '2-2', name: '骨外科' }, { id: '2-3', name: '神经外科' }] },
  { id: '3', name: '儿科', children: [{ id: '3-1', name: '小儿内科' }, { id: '3-2', name: '小儿外科' }] },
  { id: '4', name: '妇产科', children: [{ id: '4-1', name: '妇科' }, { id: '4-2', name: '产科' }] },
];

const DepartmentPage: React.FC = () => {
  const [activeKey, setActiveKey] = useState('1');
  const currentDept = mockDepts.find((d) => d.id === activeKey);

  return (
    <div className={styles.container}>
      <NavBar onBack={() => history.back()}>选择科室</NavBar>
      <SearchBar placeholder="搜索科室" className={styles.search} />
      <div className={styles.content}>
        <SideBar activeKey={activeKey} onChange={setActiveKey} className={styles.sidebar}>
          {mockDepts.map((dept) => (
            <SideBar.Item key={dept.id} title={dept.name} />
          ))}
        </SideBar>
        <div className={styles.list}>
          <List>
            {currentDept?.children.map((child) => (
              <List.Item
                key={child.id}
                onClick={() => history.push(`/doctor?departmentId=${child.id}`)}
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

