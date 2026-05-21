import { NavBar, Skeleton, Toast, Empty } from 'antd-mobile';
import { history, useParams } from 'umi';
import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { departmentApi } from '@hospital/api';
import type { Department } from '@hospital/shared';
import { Card, SectionLabel } from '@/components/ui';
import { fadeInUp, stagger } from '@/components/ui/animations';

const DepartmentDetailPage: React.FC = () => {
  const { id } = useParams() as { id: string };
  const [loading, setLoading] = useState(true);
  const [department, setDepartment] = useState<Department | null>(null);

  useEffect(() => {
    if (id) {
      loadData();
    }
  }, [id]);

  const loadData = async () => {
    try {
      const data = await departmentApi.getDetail(id!);
      setDepartment(data);
    } catch (error: any) {
      Toast.show({ content: error.message || '加载失败', icon: 'fail' });
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-background">
        <NavBar 
          onBack={() => history.back()}
          className="!bg-card border-b border-border"
        >
          科室详情
        </NavBar>
        <div className="p-4">
          <Skeleton.Paragraph lineCount={6} animated />
        </div>
      </div>
    );
  }

  if (!department) {
    return (
      <div className="min-h-screen bg-background">
        <NavBar 
          onBack={() => history.back()}
          className="!bg-card border-b border-border"
        >
          科室详情
        </NavBar>
        <div className="flex items-center justify-center h-64">
          <Empty description="科室不存在" />
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background pb-6">
      <NavBar 
        onBack={() => history.back()}
        className="!bg-card border-b border-border"
      >
        {department.name}
      </NavBar>
      
      <motion.div
        className="p-4 space-y-4"
        variants={stagger}
        initial="hidden"
        animate="visible"
      >
        {/* Department Header */}
        <motion.div variants={fadeInUp}>
          <Card variant="elevated" padding="lg">
            <div className="flex items-center gap-4">
              <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-accent to-accent-secondary flex items-center justify-center flex-shrink-0">
                <span className="text-2xl text-white">
                  {department.name.charAt(0)}
                </span>
              </div>
              <div className="flex-1">
                <h2 className="text-xl font-semibold text-foreground">{department.name}</h2>
              </div>
            </div>
          </Card>
        </motion.div>

        {/* Description */}
        {department.description && (
          <motion.div variants={fadeInUp}>
            <SectionLabel>科室简介</SectionLabel>
            <Card variant="default" padding="lg" className="mt-3">
              <div 
                className="text-foreground leading-relaxed [&_p]:m-0"
                dangerouslySetInnerHTML={{ __html: department.description }}
              />
            </Card>
          </motion.div>
        )}


        {/* Location */}
        {department.location && (
          <motion.div variants={fadeInUp}>
            <SectionLabel>科室位置</SectionLabel>
            <Card variant="default" padding="lg" className="mt-3">
              <p className="text-foreground">{department.location}</p>
            </Card>
          </motion.div>
        )}

        {/* Contact */}
        {department.phone && (
          <motion.div variants={fadeInUp}>
            <SectionLabel>联系方式</SectionLabel>
            <Card variant="default" padding="lg" className="mt-3">
              <a 
                href={`tel:${department.phone}`}
                className="text-accent font-mono"
              >
                {department.phone}
              </a>
            </Card>
          </motion.div>
        )}
      </motion.div>
    </div>
  );
};

export default DepartmentDetailPage;
