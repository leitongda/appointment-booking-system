import { NavBar, SearchBar, List, Image, Tag, Empty, Skeleton } from 'antd-mobile';
import { history } from 'umi';
import { useState, useCallback } from 'react';
import { doctorApi, departmentApi } from '@hospital/api';
import type { Doctor, Department } from '@hospital/shared';
import styles from './index.less';

// 防抖函数
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

  // 使用防抖进行搜索
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
    <div className={styles.container}>
      <NavBar onBack={() => history.back()}>搜索</NavBar>
      
      <div className={styles.searchHeader}>
        <SearchBar
          placeholder="搜索科室/医生"
          value={keyword}
          onChange={handleChange}
          onSearch={doSearch}
          showCancelButton
          onCancel={() => history.back()}
        />
      </div>

      <div className={styles.content}>
        {!keyword && !searched && (
          <div className={styles.tip}>
            <div className={styles.tipIcon}>🔍</div>
            <div className={styles.tipText}>输入关键词搜索科室或医生</div>
          </div>
        )}

        {searching && (
          <div className={styles.loading}>
            <Skeleton.Paragraph lineCount={5} animated />
          </div>
        )}

        {showEmpty && (
          <Empty description="未找到相关结果" style={{ marginTop: 80 }} />
        )}

        {!searching && departments.length > 0 && (
          <div className={styles.section}>
            <div className={styles.sectionTitle}>科室</div>
            <List>
              {departments.map((dept) => (
                <List.Item
                  key={dept.id}
                  onClick={() => handleSelectDept(dept.id, dept.name)}
                  arrow
                  prefix={<span className={styles.deptIcon}>🏥</span>}
                >
                  {dept.name}
                </List.Item>
              ))}
            </List>
          </div>
        )}

        {!searching && doctors.length > 0 && (
          <div className={styles.section}>
            <div className={styles.sectionTitle}>医生</div>
            <List>
              {doctors.map((doctor) => (
                <List.Item
                  key={doctor.id}
                  onClick={() => handleSelectDoctor(doctor.id)}
                  arrow
                  prefix={
                    <Image
                      src={doctor.avatar || ''}
                      width={48}
                      height={48}
                      fit="cover"
                      style={{ borderRadius: 8, background: '#f5f5f5' }}
                    />
                  }
                  description={
                    <div className={styles.doctorMeta}>
                      <span>{doctor.departmentName}</span>
                      {doctor.specialty && (
                        <span className={styles.specialty}>擅长：{doctor.specialty}</span>
                      )}
                    </div>
                  }
                >
                  <div className={styles.doctorName}>
                    {doctor.name}
                    {doctor.title && (
                      <Tag color="primary" fill="outline" className={styles.doctorTitle}>
                        {doctor.title}
                      </Tag>
                    )}
                  </div>
                </List.Item>
              ))}
            </List>
          </div>
        )}
      </div>
    </div>
  );
};

export default SearchPage;

