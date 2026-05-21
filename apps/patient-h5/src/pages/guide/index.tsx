import { useState, useCallback } from 'react';
import { NavBar, SearchBar, Empty, Toast, SpinLoading } from 'antd-mobile';
import { history } from 'umi';
import { motion } from 'framer-motion';
import { departmentApi } from '@hospital/api';
import type { SymptomMatchResult } from '@hospital/api';
import { Card } from '@/components/ui';
import { fadeInUp, stagger } from '@/components/ui/animations';

// 常见症状快捷标签
const QUICK_SYMPTOMS = [
  '头痛', '咳嗽', '发烧', '胃痛', '腰痛',
  '失眠', '心悸', '皮疹', '眼睛不适', '牙痛',
];

const GuidePage: React.FC = () => {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<SymptomMatchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);

  const handleSearch = useCallback(async (keyword: string) => {
    const q = keyword.trim();
    if (!q) return;

    setLoading(true);
    setSearched(true);
    try {
      const res = await departmentApi.symptomMatch(q);
      setResults(res.items || []);
    } catch (error: any) {
      Toast.show({ content: error.message || '搜索失败', icon: 'fail' });
      setResults([]);
    } finally {
      setLoading(false);
    }
  }, []);

  const handleQuickSymptom = (symptom: string) => {
    setQuery(symptom);
    handleSearch(symptom);
  };

  const handleDeptClick = (deptId: string) => {
    history.push(`/department/${deptId}`);
  };

  return (
    <div className="min-h-screen bg-background">
      <NavBar onBack={() => history.back()} className="!bg-card border-b border-border">
        智能导诊
      </NavBar>

      <div className="p-4">
        {/* 搜索框 */}
        <SearchBar
          placeholder="描述您的症状，如头痛、咳嗽..."
          value={query}
          onChange={setQuery}
          onSearch={handleSearch}
          showCancelButton
          onCancel={() => {
            setQuery('');
            setResults([]);
            setSearched(false);
          }}
        />

        {/* 快捷症状标签 */}
        {!searched && (
          <motion.div className="mt-6" variants={stagger} initial="hidden" animate="visible">
            <h3 className="text-sm text-muted-foreground mb-3">常见症状</h3>
            <div className="flex flex-wrap gap-2">
              {QUICK_SYMPTOMS.map((symptom) => (
                <motion.button
                  key={symptom}
                  variants={fadeInUp}
                  className="px-3 py-1.5 bg-card border border-border rounded-full text-sm text-foreground hover:bg-muted transition-colors"
                  onClick={() => handleQuickSymptom(symptom)}
                >
                  {symptom}
                </motion.button>
              ))}
            </div>

            <div className="mt-8 p-4 bg-muted rounded-xl">
              <h3 className="text-sm font-medium text-foreground mb-2">温馨提示</h3>
              <p className="text-xs text-muted-foreground leading-relaxed">
                智能导诊根据您描述的症状推荐可能相关的科室，仅供参考。如有紧急情况，请直接拨打 120 或前往急诊。
              </p>
            </div>
          </motion.div>
        )}

        {/* 搜索结果 */}
        {searched && (
          <div className="mt-4">
            {loading ? (
              <div className="flex items-center justify-center h-48">
                <SpinLoading />
              </div>
            ) : results.length === 0 ? (
              <div className="flex items-center justify-center h-48">
                <Empty description="未找到匹配的科室，请尝试其他症状描述" />
              </div>
            ) : (
              <motion.div className="space-y-3" variants={stagger} initial="hidden" animate="visible">
                <p className="text-sm text-muted-foreground">
                  为您找到 {results.length} 个可能相关的科室
                </p>
                {results.map((dept) => (
                  <motion.div key={dept.id} variants={fadeInUp}>
                    <Card
                      variant="default"
                      padding="md"
                      className="cursor-pointer"
                      onClick={() => handleDeptClick(dept.id)}
                    >
                      <div className="flex items-start gap-3">
                        <div className="w-10 h-10 bg-accent/10 rounded-xl flex items-center justify-center flex-shrink-0">
                          {dept.icon ? (
                            <img src={dept.icon} alt="" className="w-6 h-6" />
                          ) : (
                            <svg className="w-5 h-5 text-accent" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
                            </svg>
                          )}
                        </div>
                        <div className="flex-1 min-w-0">
                          <h3 className="font-medium text-foreground">{dept.name}</h3>
                          {dept.description && (
                            <p className="text-sm text-muted-foreground mt-1 line-clamp-2">{dept.description}</p>
                          )}
                          {dept.matchedKeywords.length > 0 && (
                            <div className="flex flex-wrap gap-1 mt-2">
                              {dept.matchedKeywords.map((kw) => (
                                <span
                                  key={kw}
                                  className="px-2 py-0.5 bg-accent/10 text-accent text-xs rounded-full"
                                >
                                  {kw}
                                </span>
                              ))}
                            </div>
                          )}
                        </div>
                        <svg className="w-4 h-4 text-muted-foreground flex-shrink-0 mt-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                        </svg>
                      </div>
                    </Card>
                  </motion.div>
                ))}
              </motion.div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default GuidePage;
