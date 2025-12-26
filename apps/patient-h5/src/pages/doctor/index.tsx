import { NavBar, Image, Skeleton, Empty } from 'antd-mobile';
import { history, useSearchParams } from 'umi';
import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { doctorApi } from '@hospital/api';
import type { Doctor } from '@hospital/shared';
import { Card } from '@/components/ui';
import { fadeInUp, stagger, viewportOptions } from '@/components/ui/animations';

const DoctorPage: React.FC = () => {
  const [searchParams] = useSearchParams();
  const departmentId = searchParams.get('departmentId');
  const departmentName = searchParams.get('departmentName');
  
  const [loading, setLoading] = useState(true);
  const [doctors, setDoctors] = useState<Doctor[]>([]);

  useEffect(() => {
    if (departmentId) {
      loadDoctors();
    }
  }, [departmentId]);

  const loadDoctors = async () => {
    try {
      const data = await doctorApi.getByDepartment(departmentId!);
      setDoctors(data);
    } catch (error) {
      console.error('加载医生列表失败', error);
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
          {departmentName || '选择医生'}
        </NavBar>
        <div className="p-4">
          <Skeleton.Paragraph lineCount={8} animated />
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background">
      <NavBar 
        onBack={() => history.back()}
        className="!bg-card border-b border-border"
      >
        {departmentName || '选择医生'}
      </NavBar>

      {doctors.length === 0 ? (
        <div className="flex items-center justify-center h-64">
          <Empty description="暂无医生" />
        </div>
      ) : (
        <motion.div
          className="p-4 space-y-3"
          variants={stagger}
          initial="hidden"
          animate="visible"
        >
          {doctors.map((doctor) => (
            <motion.div
              key={doctor.id}
              variants={fadeInUp}
              whileHover={{ y: -2 }}
              whileTap={{ scale: 0.98 }}
            >
              <Card 
                variant="default" 
                padding="md"
                hoverable
                animated={false}
                className="cursor-pointer"
                onClick={() => history.push(`/doctor/${doctor.id}`)}
              >
                <div className="flex gap-4">
                  <Image 
                    src={doctor.avatar || ''} 
                    width={72} 
                    height={72} 
                    fit="cover" 
                    className="rounded-xl bg-muted flex-shrink-0"
                  />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="font-semibold text-lg text-foreground">
                        {doctor.name}
                      </span>
                      {doctor.title && (
                        <span className="text-xs text-accent bg-accent/10 px-2 py-0.5 rounded-full">
                          {doctor.title}
                        </span>
                      )}
                    </div>
                    <p className="text-sm text-muted-foreground mb-1">
                      {doctor.departmentName}
                    </p>
                    <p className="text-xs text-muted-foreground/70 truncate">
                      擅长：{doctor.specialty || '暂无'}
                    </p>
                    <div className="flex items-center justify-between mt-3">
                      <span className="text-accent font-semibold text-lg">
                        ¥{doctor.registrationFee}
                      </span>
                      <span className="text-xs text-muted-foreground">
                        挂号费
                      </span>
                    </div>
                  </div>
                  <svg 
                    className="w-5 h-5 text-muted-foreground self-center flex-shrink-0" 
                    fill="none" 
                    stroke="currentColor" 
                    viewBox="0 0 24 24"
                  >
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                  </svg>
                </div>
              </Card>
            </motion.div>
          ))}
        </motion.div>
      )}
    </div>
  );
};

export default DoctorPage;
