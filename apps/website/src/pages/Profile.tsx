import { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import {
  Building2, Calendar, Phone, Shield,
  ArrowRight, Clock, CreditCard, LogOut, ExternalLink,
  CheckCircle2, AlertCircle,
} from 'lucide-react';
import { toast } from 'sonner';
import { fadeInUp, stagger, viewportOptions } from '@/components/ui/animations';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { SectionLabel } from '@/components/ui/SectionLabel';
import { GradientHeading } from '@/components/ui/GradientText';
import { SEO } from '@/components/SEO';
import { tenantApi } from '@hospital/api';
import type { CurrentTenant } from '@hospital/api';

const ADMIN_URL = import.meta.env.VITE_ADMIN_URL || 'http://localhost:8006';

function getToken(): string | null {
  try {
    return localStorage.getItem('hospital_token') || localStorage.getItem('token') || null;
  } catch {
    return null;
  }
}

function clearAuth() {
  try {
    localStorage.removeItem('hospital_token');
    localStorage.removeItem('hospital_refresh_token');
    localStorage.removeItem('token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('hospital_current_tenant_id');
    localStorage.removeItem('hospital_current_store');
  } catch {
    // localStorage 清除失败不影响登出流程
  }
}

export function Profile() {
  const navigate = useNavigate();
  const [tenant, setTenant] = useState<CurrentTenant | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const token = getToken();
    if (!token) {
      navigate('/login');
      return;
    }

    tenantApi.getCurrentTenant()
      .then(setTenant)
      .catch((err) => {
        const msg = err?.response?.data?.message || err?.message;
        if (err?.response?.status === 401) {
          navigate('/login');
          return;
        }
        setError(msg || '获取租户信息失败');
      })
      .finally(() => setLoading(false));
  }, [navigate]);

  function handleLogout() {
    clearAuth();
    toast.success('已退出登录');
    navigate('/');
  }

  if (loading) {
    return (
      <section className="py-28">
        <div className="mx-auto max-w-4xl px-6 text-center">
          <div className="mx-auto h-8 w-8 animate-spin rounded-full border-2 border-accent border-t-transparent" />
          <p className="mt-4 text-muted-foreground">加载中...</p>
        </div>
      </section>
    );
  }

  if (error) {
    return (
      <section className="py-28">
        <div className="mx-auto max-w-4xl px-6 text-center">
          <AlertCircle className="mx-auto h-12 w-12 text-red-500" />
          <p className="mt-4 text-lg text-foreground">{error}</p>
          <Button className="mt-6" variant="outline" onClick={() => window.location.reload()}>
            重试
          </Button>
        </div>
      </section>
    );
  }

  if (!tenant) return null;

  const isActive = tenant.isSubscriptionActive;
  const daysLeft = tenant.daysUntilExpiry ?? 0;

  return (
    <section className="relative overflow-hidden py-20">
      <SEO title="个人中心" description="管理您的机构账号和订阅信息。" url="/profile" />

      <div className="pointer-events-none absolute -right-32 top-0 h-[400px] w-[400px] rounded-full bg-accent/[0.04] blur-[150px]" />

      <div className="mx-auto max-w-4xl px-6">
        <motion.div
          initial="hidden"
          whileInView="visible"
          viewport={viewportOptions}
          variants={stagger}
        >
          <motion.div variants={fadeInUp} className="flex justify-center">
            <SectionLabel>个人中心</SectionLabel>
          </motion.div>
          <motion.div variants={fadeInUp} className="mt-6 text-center">
            <GradientHeading level={1}>
              {tenant.name || '我的机构'}
            </GradientHeading>
          </motion.div>
        </motion.div>

        <motion.div
          initial="hidden"
          whileInView="visible"
          viewport={viewportOptions}
          variants={stagger}
          className="mt-12 space-y-6"
        >
          {/* 订阅状态 */}
          <motion.div variants={fadeInUp}>
            <Card padding="lg" variant={isActive ? 'default' : 'elevated'}>
              <div className="flex items-start justify-between">
                <div>
                  <h3 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground">
                    订阅状态
                  </h3>
                  <div className="mt-3 flex items-center gap-3">
                    {isActive ? (
                      <CheckCircle2 className="h-6 w-6 text-green-500" />
                    ) : (
                      <AlertCircle className="h-6 w-6 text-amber-500" />
                    )}
                    <div>
                      <p className="text-lg font-semibold text-foreground">
                        {tenant.subscriptionPlanName || '未订阅'}
                      </p>
                      <p className="text-sm text-muted-foreground">
                        {isActive
                          ? daysLeft > 0
                            ? `${daysLeft} 天后到期`
                            : '长期有效'
                          : '订阅已过期'}
                      </p>
                    </div>
                  </div>
                </div>
                <Link to="/pricing">
                  <Button variant="outline" size="sm" icon={<CreditCard />}>
                    {isActive ? '升级方案' : '立即订阅'}
                  </Button>
                </Link>
              </div>

              {tenant.subscriptionEndAt && (
                <div className="mt-4 border-t border-border pt-4">
                  <div className="flex items-center gap-2 text-sm text-muted-foreground">
                    <Clock className="h-4 w-4" />
                    到期时间：{new Date(tenant.subscriptionEndAt).toLocaleDateString('zh-CN')}
                  </div>
                </div>
              )}
            </Card>
          </motion.div>

          {/* 机构信息 */}
          <motion.div variants={fadeInUp}>
            <Card padding="lg">
              <h3 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground">
                机构信息
              </h3>
              <div className="mt-4 grid gap-4 sm:grid-cols-2">
                <InfoRow icon={Building2} label="机构编码" value={tenant.tenantCode} />
                <InfoRow icon={Shield} label="状态" value={statusLabel(tenant.status)} />
                <InfoRow icon={Phone} label="联系电话" value={tenant.contactPhone || '-'} />
                <InfoRow icon={Calendar} label="开通时间" value={formatDate(tenant.subscriptionStartAt)} />
              </div>
            </Card>
          </motion.div>

          {/* 快捷操作 */}
          <motion.div variants={fadeInUp}>
            <Card padding="lg">
              <h3 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground">
                快捷操作
              </h3>
              <div className="mt-4 grid gap-3 sm:grid-cols-2">
                <a
                  href={ADMIN_URL}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center justify-between rounded-xl border border-border p-4 transition-colors hover:border-accent/30 hover:bg-accent/5"
                >
                  <div className="flex items-center gap-3">
                    <ExternalLink className="h-5 w-5 text-accent" />
                    <span className="text-sm font-medium text-foreground">进入管理后台</span>
                  </div>
                  <ArrowRight className="h-4 w-4 text-muted-foreground" />
                </a>
                <Link
                  to="/pricing"
                  className="flex items-center justify-between rounded-xl border border-border p-4 transition-colors hover:border-accent/30 hover:bg-accent/5"
                >
                  <div className="flex items-center gap-3">
                    <CreditCard className="h-5 w-5 text-accent" />
                    <span className="text-sm font-medium text-foreground">查看定价方案</span>
                  </div>
                  <ArrowRight className="h-4 w-4 text-muted-foreground" />
                </Link>
              </div>
            </Card>
          </motion.div>

          {/* 退出登录 */}
          <motion.div variants={fadeInUp} className="text-center">
            <Button variant="ghost" onClick={handleLogout} icon={<LogOut />}>
              退出登录
            </Button>
          </motion.div>
        </motion.div>
      </div>
    </section>
  );
}

/* ============================================
   Helpers
   ============================================ */

function InfoRow({
  icon: Icon,
  label,
  value,
}: {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  value: string;
}) {
  return (
    <div className="flex items-center gap-3">
      <Icon className="h-4 w-4 text-muted-foreground" />
      <span className="text-sm text-muted-foreground">{label}：</span>
      <span className="text-sm font-medium text-foreground">{value}</span>
    </div>
  );
}

function statusLabel(status: number): string {
  const map: Record<number, string> = {
    0: '已禁用',
    1: '正常',
    2: '欠费',
    3: '试用中',
  };
  return map[status] || '未知';
}

function formatDate(dateStr?: string): string {
  if (!dateStr) return '-';
  return new Date(dateStr).toLocaleDateString('zh-CN');
}
