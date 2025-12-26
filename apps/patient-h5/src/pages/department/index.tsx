import { NavBar, SideBar, SearchBar, Skeleton } from 'antd-mobile';
import { history } from 'umi';
import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { departmentApi } from '@hospital/api';
import type { DepartmentTreeNode } from '@hospital/shared';
import { fadeInUp, stagger } from '@/components/ui/animations';

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
      <div className="min-h-screen bg-background">
        <NavBar 
          onBack={() => history.back()}
          className="!bg-card border-b border-border"
        >
          选择科室
        </NavBar>
        <div className="p-4">
          <Skeleton.Paragraph lineCount={10} animated />
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background flex flex-col">
      <NavBar 
        onBack={() => history.back()}
        className="!bg-card border-b border-border flex-shrink-0"
      >
        选择科室
      </NavBar>
      
      {/* Search Bar */}
      <div className="px-4 py-3 bg-card border-b border-border">
        <SearchBar 
          placeholder="搜索科室" 
          value={searchValue}
          onChange={setSearchValue}
          style={{
            '--background': '#F1F5F9',
            '--border-radius': '12px',
            '--height': '44px',
          } as React.CSSProperties}
        />
      </div>

      {/* Content */}
      <div className="flex-1 flex overflow-hidden">
        {/* Sidebar */}
        <SideBar 
          activeKey={activeKey} 
          onChange={setActiveKey}
          className="!bg-muted flex-shrink-0 w-28"
          style={{
            '--background-color': '#F1F5F9',
            '--item-border-radius': '0',
          } as React.CSSProperties}
        >
          {departments.map((dept) => (
            <SideBar.Item 
              key={dept.id} 
              title={dept.name}
            />
          ))}
        </SideBar>

        {/* List */}
        <div className="flex-1 overflow-y-auto bg-card">
          <motion.div
            variants={stagger}
            initial="hidden"
            animate="visible"
            className="p-2"
          >
            {currentDept?.children
              .filter((child) => !searchValue || child.name.includes(searchValue))
              .map((child) => (
                <motion.div
                  key={child.id}
                  variants={fadeInUp}
                  className="
                    flex items-center justify-between 
                    px-4 py-4 
                    rounded-xl 
                    mb-2
                    bg-muted hover:bg-accent/5 
                    cursor-pointer 
                    active:bg-accent/10 
                    transition-colors
                  "
                  onClick={() => handleSelectDept(child.id, child.name)}
                >
                  <span className="text-foreground font-medium">{child.name}</span>
                  <svg 
                    className="w-5 h-5 text-muted-foreground" 
                    fill="none" 
                    stroke="currentColor" 
                    viewBox="0 0 24 24"
                  >
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                  </svg>
                </motion.div>
              ))}
          </motion.div>
        </div>
      </div>
    </div>
  );
};

export default DepartmentPage;
