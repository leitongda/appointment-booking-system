import { NavBar, SearchBar, Image, Empty, Skeleton } from 'antd-mobile';
import { history } from 'umi';
import { useState, useCallback } from 'react';
import { motion } from 'framer-motion';
import { doctorApi, departmentApi } from '@hospital/api';
import type { Doctor, Department } from '@hospital/shared';
import { Card, SectionLabel } from '@/components/ui';
import { fadeInUp, stagger } from '@/components/ui/animations';

// Debounce function
const debounce = <T extends (...args: any[]) => any>(fn: T, delay: number) => {
  let timer: NodeJS.Timeout;
  return (...args: Parameters<T>) => {
    clearTimeout(timer);
    timer = setTimeout(() => fn(...args), delay);
  };
};

const SearchPage: React.FC = () => {
  const [keyword, setKeyword] = useState('');
  const [searching, setSearching] = useState(false);
  const [doctors, setDoctors] = useState<Doctor[]>([]);
  const [departments, setDepartments] = useState<Department[]>([]);
  const [searched, setSearched] = useState(false);

  const doSearch = async (value: string) => {
    if (!value.trim()) {
      setDoctors([]);
      setDepartments([]);
      setSearched(false);
      return;
    }

    setSearching(true);
    setSearched(true);
    try {
      const [doctorResult, deptResult] = await Promise.all([
        doctorApi.search(value),
        departmentApi.search(value),
      ]);
      setDoctors(doctorResult);
      setDepartments(deptResult);
    } catch (error) {
      console.error('搜索失败', error);
    } finally {
      setSearching(false);
    }
  };

  const debouncedSearch = useCallback(debounce(doSearch, 300), []);

  const handleChange = (value: string) => {
    setKeyword(value);
    debouncedSearch(value);
  };

  const handleSelectDoctor = (id: string) => {
    history.push(`/doctor/${id}`);
  };

  const handleSelectDept = (id: string, name: string) => {
    history.push(`/doctor?departmentId=${id}&departmentName=${encodeURIComponent(name)}`);
  };

  const hasResults = doctors.length > 0 || departments.length > 0;
  const showEmpty = searched && !searching && !hasResults;

  return (
    <div className="min-h-screen bg-background">
      <NavBar 
        onBack={() => history.back()}
        className="!bg-card border-b border-border"
      >
        搜索
      </NavBar>
      
      {/* Search Header */}
      <div className="p-4 bg-card border-b border-border">
        <SearchBar
          placeholder="搜索科室/医生"
          value={keyword}
          onChange={handleChange}
          onSearch={doSearch}
          showCancelButton
          onCancel={() => history.back()}
          style={{
            '--background': '#F1F5F9',
            '--border-radius': '12px',
            '--height': '44px',
          } as React.CSSProperties}
        />
      </div>

      <div className="p-4">
        {/* Initial State */}
        {!keyword && !searched && (
          <motion.div 
            className="flex flex-col items-center justify-center py-20"
            variants={fadeInUp}
            initial="hidden"
            animate="visible"
          >
            <div className="w-16 h-16 rounded-2xl bg-accent/10 flex items-center justify-center text-accent mb-4">
              <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
            </div>
            <p className="text-muted-foreground">输入关键词搜索科室或医生</p>
          </motion.div>
        )}

        {/* Loading State */}
        {searching && (
          <div className="py-4">
            <Skeleton.Paragraph lineCount={5} animated />
          </div>
        )}

        {/* Empty State */}
        {showEmpty && (
          <div className="flex items-center justify-center py-20">
            <Empty description="未找到相关结果" />
          </div>
        )}

        {/* Departments Results */}
        {!searching && departments.length > 0 && (
          <motion.div 
            className="mb-6"
            variants={stagger}
            initial="hidden"
            animate="visible"
          >
            <div className="mb-3">
              <SectionLabel animated={false}>科室</SectionLabel>
            </div>
            <div className="space-y-2">
              {departments.map((dept) => (
                <motion.div
                  key={dept.id}
                  variants={fadeInUp}
                  whileTap={{ scale: 0.98 }}
                >
                  <Card 
                    variant="default" 
                    padding="md"
                    animated={false}
                    className="cursor-pointer"
                    onClick={() => handleSelectDept(dept.id, dept.name)}
                  >
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 rounded-xl bg-accent/10 flex items-center justify-center text-accent">
                        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
                        </svg>
                      </div>
                      <span className="flex-1 font-medium text-foreground">{dept.name}</span>
                      <svg className="w-5 h-5 text-muted-foreground" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                      </svg>
                    </div>
                  </Card>
                </motion.div>
              ))}
            </div>
          </motion.div>
        )}

        {/* Doctors Results */}
        {!searching && doctors.length > 0 && (
          <motion.div
            variants={stagger}
            initial="hidden"
            animate="visible"
          >
            <div className="mb-3">
              <SectionLabel animated={false}>医生</SectionLabel>
            </div>
            <div className="space-y-3">
              {doctors.map((doctor) => (
                <motion.div
                  key={doctor.id}
                  variants={fadeInUp}
                  whileTap={{ scale: 0.98 }}
                >
                  <Card 
                    variant="default" 
                    padding="md"
                    animated={false}
                    className="cursor-pointer"
                    onClick={() => handleSelectDoctor(doctor.id)}
                  >
                    <div className="flex gap-3">
                      <Image
                        src={doctor.avatar || ''}
                        width={56}
                        height={56}
                        fit="cover"
                        className="rounded-xl bg-muted flex-shrink-0"
                      />
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1">
                          <span className="font-semibold text-foreground">{doctor.name}</span>
                          {doctor.title && (
                            <span className="text-xs text-accent bg-accent/10 px-2 py-0.5 rounded-full">
                              {doctor.title}
                            </span>
                          )}
                        </div>
                        <p className="text-sm text-muted-foreground">{doctor.departmentName}</p>
                        {doctor.specialty && (
                          <p className="text-xs text-muted-foreground/70 mt-1 truncate">
                            擅长：{doctor.specialty}
                          </p>
                        )}
                      </div>
                      <svg className="w-5 h-5 text-muted-foreground self-center flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                      </svg>
                    </div>
                  </Card>
                </motion.div>
              ))}
            </div>
          </motion.div>
        )}
      </div>
    </div>
  );
};

export default SearchPage;
