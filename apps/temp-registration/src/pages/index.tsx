/**
 * 首页 - 科室选择
 * 临时挂号第一步：选择要挂号的科室
 */
import React, { useState, useEffect } from 'react';
import { Grid, SearchBar, Skeleton, Toast } from 'antd-mobile';
import { history } from 'umi';
import { motion } from 'framer-motion';
import { departmentApi } from '@hospital/api';
import type { Department } from '@hospital/shared';
import { Card, StepIndicator, fadeInUp, stagger, viewportOptions } from '@/components/ui';
import { saveRegistrationData, resetRegistration } from '@/utils/storage';

// 挂号流程步骤
const steps = [
  { key: 'department', title: '选科室' },
  { key: 'doctor', title: '选医生' },
  { key: 'time', title: '选时段' },
  { key: 'patient', title: '填信息' },
  { key: 'confirm', title: '确认' },
];

// 热门科室图标
const deptIcons: Record<string, React.ReactNode> = {
  '内科': (
    <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z" />
    </svg>
  ),
  '外科': (
    <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 14l9-5-9-5-9 5 9 5zm0 0l6.16-3.422a12.083 12.083 0 01.665 6.479A11.952 11.952 0 0012 20.055a11.952 11.952 0 00-6.824-2.998 12.078 12.078 0 01.665-6.479L12 14z" />
    </svg>
  ),
};

const HomePage: React.FC = () => {
  const [loading, setLoading] = useState(true);
  const [departments, setDepartments] = useState<Department[]>([]);
  const [searchValue, setSearchValue] = useState('');

  useEffect(() => {
    // 重置挂号流程
    resetRegistration();
    loadDepartments();
  }, []);

  const loadDepartments = async () => {
    try {
      const data = await departmentApi.getAll();
      setDepartments(data);
    } catch (error) {
      console.error('加载科室列表失败', error);
      Toast.show({
        icon: 'fail',
        content: '加载科室失败，请重试',
      });
    } finally {
      setLoading(false);
    }
  };

  const handleSelectDepartment = (dept: Department) => {
    saveRegistrationData({
      departmentId: dept.id,
      departmentName: dept.name,
    });
    history.push(`/doctor?departmentId=${dept.id}&departmentName=${encodeURIComponent(dept.name)}`);
  };

  // 过滤科室
  const filteredDepts = searchValue
    ? departments.filter(d => d.name.includes(searchValue))
    : departments;

  return (
    <div className="min-h-screen bg-background">
      {/* 步骤指示器 */}
      <StepIndicator steps={steps} currentStep={0} />

      {/* 头部渐变区域 */}
      <motion.div 
        className="bg-gradient-to-br from-primary via-accent to-primary-light px-5 pt-6 pb-10"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.5 }}
      >
        <div className="text-center mb-6">
          <h1 className="text-2xl font-semibold text-white mb-2">现场临时挂号</h1>
          <p className="text-white/80 text-sm">请选择您要就诊的科室</p>
        </div>

        {/* 搜索框 */}
        <SearchBar 
          placeholder="搜索科室名称" 
          value={searchValue}
          onChange={setSearchValue}
          className="!rounded-full"
          style={{
            '--background': 'rgba(255, 255, 255, 0.95)',
            '--border-radius': '9999px',
            '--height': '48px',
          } as React.CSSProperties}
        />
      </motion.div>

      {/* 科室列表 */}
      <div className="px-4 -mt-4 pb-6">
        <Card variant="elevated" padding="md" className="relative z-10">
          <h2 className="text-lg font-semibold text-foreground mb-4 flex items-center gap-2">
            <span className="w-1 h-5 bg-gradient-to-b from-primary to-accent rounded-full" />
            全部科室
          </h2>

          {loading ? (
            <div className="space-y-4">
              <Skeleton.Paragraph lineCount={3} animated />
              <Skeleton.Paragraph lineCount={3} animated />
            </div>
          ) : filteredDepts.length === 0 ? (
            <div className="py-12 text-center text-muted-foreground">
              {searchValue ? '未找到匹配的科室' : '暂无科室信息'}
            </div>
          ) : (
            <motion.div
              variants={stagger}
              initial="hidden"
              animate="visible"
            >
              <Grid columns={3} gap={12}>
                {filteredDepts.map((dept) => (
                  <Grid.Item key={dept.id}>
                    <motion.div
                      variants={fadeInUp}
                      className="flex flex-col items-center py-4 px-2 rounded-2xl 
                                 bg-gradient-to-br from-muted to-background
                                 hover:from-primary/10 hover:to-accent/10
                                 active:scale-95 transition-all duration-200 cursor-pointer
                                 border border-transparent hover:border-primary/20"
                      onClick={() => handleSelectDepartment(dept)}
                      whileHover={{ y: -2 }}
                      whileTap={{ scale: 0.95 }}
                    >
                      <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-primary to-accent 
                                      flex items-center justify-center text-white mb-3 shadow-primary">
                        {deptIcons[dept.name] || (
                          <svg className="w-7 h-7" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} 
                                  d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
                          </svg>
                        )}
                      </div>
                      <span className="text-sm font-medium text-foreground text-center leading-tight">
                        {dept.name}
                      </span>
                    </motion.div>
                  </Grid.Item>
                ))}
              </Grid>
            </motion.div>
          )}
        </Card>

        {/* 温馨提示 */}
        <motion.div
          className="mt-4"
          variants={fadeInUp}
          initial="hidden"
          whileInView="visible"
          viewport={viewportOptions}
        >
          <Card variant="flat" padding="md">
            <div className="flex items-start gap-3">
              <div className="w-10 h-10 rounded-xl bg-warning/10 flex items-center justify-center flex-shrink-0">
                <svg className="w-5 h-5 text-warning" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} 
                        d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
              <div className="flex-1">
                <h3 className="font-medium text-foreground mb-1">温馨提示</h3>
                <ul className="text-sm text-muted-foreground space-y-1">
                  <li>• 请携带有效身份证件就诊</li>
                  <li>• 临时挂号需现场排队等候</li>
                  <li>• 建议提前通过预约挂号节省时间</li>
                </ul>
              </div>
            </div>
          </Card>
        </motion.div>
      </div>
    </div>
  );
};

export default HomePage;

