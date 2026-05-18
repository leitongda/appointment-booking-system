import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { ArrowRight, Building2, User, Phone, Lock, Mail, IdCard } from 'lucide-react';
import { toast } from 'sonner';
import { SEO } from '@/components/SEO';
import { fadeInUp, stagger, viewportOptions } from '@/components/ui/animations';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { Input } from '@/components/ui/Input';
import { SectionLabel } from '@/components/ui/SectionLabel';
import { GradientHeading, GradientText } from '@/components/ui/GradientText';
import { tenantApi } from '@hospital/api';

interface FormField {
  value: string;
  error: string;
}

function initField(value = ''): FormField {
  return { value, error: '' };
}

export function Register() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [form, setForm] = useState<Record<string, FormField>>({
    name: initField(),
    tenantCode: initField(),
    contactName: initField(),
    contactPhone: initField(),
    contactEmail: initField(),
    adminUsername: initField(),
    adminPassword: initField(),
    confirmPassword: initField(),
  });

  function setFieldValue(key: string, value: string) {
    setForm((prev) => ({ ...prev, [key]: { value, error: '' } }));
  }

  function validate(): boolean {
    let valid = true;
    const next = { ...form };

    if (next.name.value.trim().length < 2) {
      next.name = { ...next.name, error: '机构名称至少 2 个字符' };
      valid = false;
    }

    const code = next.tenantCode.value.trim();
    if (!/^[a-z0-9-]{3,50}$/.test(code)) {
      next.tenantCode = { ...next.tenantCode, error: '编码 3-50 位，仅小写字母、数字和连字符' };
      valid = false;
    }

    if (next.contactName.value.trim().length < 2) {
      next.contactName = { ...next.contactName, error: '联系人姓名至少 2 个字符' };
      valid = false;
    }

    if (!/^1[3-9]\d{9}$/.test(next.contactPhone.value.trim())) {
      next.contactPhone = { ...next.contactPhone, error: '请输入有效的手机号' };
      valid = false;
    }

    if (next.contactEmail.value.trim() && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(next.contactEmail.value.trim())) {
      next.contactEmail = { ...next.contactEmail, error: '请输入有效的邮箱地址' };
      valid = false;
    }

    if (next.adminUsername.value.trim().length < 2) {
      next.adminUsername = { ...next.adminUsername, error: '管理员账号至少 2 个字符' };
      valid = false;
    }

    if (next.adminPassword.value.length < 6) {
      next.adminPassword = { ...next.adminPassword, error: '密码至少 6 个字符' };
      valid = false;
    }

    if (next.adminPassword.value !== next.confirmPassword.value) {
      next.confirmPassword = { ...next.confirmPassword, error: '两次密码不一致' };
      valid = false;
    }

    setForm(next);
    return valid;
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!validate()) return;

    setLoading(true);
    try {
      await tenantApi.selfRegister({
        name: form.name.value.trim(),
        tenantCode: form.tenantCode.value.trim(),
        contactName: form.contactName.value.trim(),
        contactPhone: form.contactPhone.value.trim(),
        contactEmail: form.contactEmail.value.trim() || undefined,
        adminUsername: form.adminUsername.value.trim(),
        adminPassword: form.adminPassword.value,
      });
      toast.success('注册成功！14 天免费试用已开启');
      navigate('/login');
    } catch (err: any) {
      const msg = err?.response?.data?.message || err?.message || '注册失败，请稍后重试';
      toast.error(msg);
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="relative overflow-hidden py-20">
      <SEO title="注册" description="注册机构账号，开启 14 天免费试用。" url="/register" />
      <div className="pointer-events-none absolute -right-32 top-0 h-[500px] w-[500px] rounded-full bg-accent/[0.04] blur-[150px]" />

      <div className="mx-auto max-w-2xl px-6">
        <motion.div
          initial="hidden"
          whileInView="visible"
          viewport={viewportOptions}
          variants={stagger}
          className="text-center"
        >
          <motion.div variants={fadeInUp} className="flex justify-center">
            <SectionLabel>免费试用 14 天</SectionLabel>
          </motion.div>
          <motion.div variants={fadeInUp} className="mt-6">
            <GradientHeading level={1}>
              创建您的<GradientText>机构账号</GradientText>
            </GradientHeading>
          </motion.div>
          <motion.p variants={fadeInUp} className="mt-4 text-lg text-muted-foreground">
            注册即可获得 14 天专业版免费试用，无需信用卡。
          </motion.p>
        </motion.div>

        <motion.div
          initial="hidden"
          whileInView="visible"
          viewport={viewportOptions}
          variants={fadeInUp}
          className="mt-12"
        >
          <Card padding="lg" variant="elevated">
            <form onSubmit={handleSubmit} className="space-y-6">
              {/* 机构信息 */}
              <div>
                <h3 className="mb-4 text-sm font-semibold uppercase tracking-wider text-muted-foreground">
                  机构信息
                </h3>
                <div className="space-y-4">
                  <Input
                    label="机构名称"
                    placeholder="如：仁爱医院"
                    value={form.name.value}
                    error={form.name.error}
                    leftIcon={<Building2 />}
                    onChange={(e) => setFieldValue('name', e.target.value)}
                    required
                  />
                  <Input
                    label="机构编码"
                    placeholder="如：renai-hospital"
                    value={form.tenantCode.value}
                    error={form.tenantCode.error}
                    hint="仅小写字母、数字和连字符，3-50 位"
                    leftIcon={<IdCard />}
                    onChange={(e) => setFieldValue('tenantCode', e.target.value.toLowerCase())}
                    required
                  />
                </div>
              </div>

              {/* 联系人信息 */}
              <div>
                <h3 className="mb-4 text-sm font-semibold uppercase tracking-wider text-muted-foreground">
                  联系人信息
                </h3>
                <div className="space-y-4">
                  <Input
                    label="联系人姓名"
                    placeholder="您的姓名"
                    value={form.contactName.value}
                    error={form.contactName.error}
                    leftIcon={<User />}
                    onChange={(e) => setFieldValue('contactName', e.target.value)}
                    required
                  />
                  <div className="grid gap-4 sm:grid-cols-2">
                    <Input
                      label="联系电话"
                      placeholder="手机号"
                      type="tel"
                      value={form.contactPhone.value}
                      error={form.contactPhone.error}
                      leftIcon={<Phone />}
                      onChange={(e) => setFieldValue('contactPhone', e.target.value)}
                      required
                    />
                    <Input
                      label="联系邮箱"
                      placeholder="选填"
                      type="email"
                      value={form.contactEmail.value}
                      error={form.contactEmail.error}
                      leftIcon={<Mail />}
                      onChange={(e) => setFieldValue('contactEmail', e.target.value)}
                    />
                  </div>
                </div>
              </div>

              {/* 管理员账号 */}
              <div>
                <h3 className="mb-4 text-sm font-semibold uppercase tracking-wider text-muted-foreground">
                  管理员账号
                </h3>
                <div className="space-y-4">
                  <Input
                    label="管理员账号"
                    placeholder="用于登录后台"
                    value={form.adminUsername.value}
                    error={form.adminUsername.error}
                    leftIcon={<User />}
                    onChange={(e) => setFieldValue('adminUsername', e.target.value)}
                    required
                  />
                  <div className="grid gap-4 sm:grid-cols-2">
                    <Input
                      label="登录密码"
                      placeholder="至少 6 位"
                      type="password"
                      value={form.adminPassword.value}
                      error={form.adminPassword.error}
                      leftIcon={<Lock />}
                      onChange={(e) => setFieldValue('adminPassword', e.target.value)}
                      required
                    />
                    <Input
                      label="确认密码"
                      placeholder="再次输入密码"
                      type="password"
                      value={form.confirmPassword.value}
                      error={form.confirmPassword.error}
                      leftIcon={<Lock />}
                      onChange={(e) => setFieldValue('confirmPassword', e.target.value)}
                      required
                    />
                  </div>
                </div>
              </div>

              <Button
                type="submit"
                size="lg"
                className="w-full"
                loading={loading}
                icon={<ArrowRight />}
              >
                注册并开始试用
              </Button>
            </form>
          </Card>

          <p className="mt-6 text-center text-sm text-muted-foreground">
            已有账号？{' '}
            <Link to="/login" className="font-medium text-accent hover:text-accent-secondary">
              立即登录
            </Link>
          </p>
        </motion.div>
      </div>
    </section>
  );
}
