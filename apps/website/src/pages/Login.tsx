import { useState } from 'react';
import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { ArrowRight, User, Lock } from 'lucide-react';
import { toast } from 'sonner';
import { SEO } from '@/components/SEO';
import { fadeInUp, stagger, viewportOptions } from '@/components/ui/animations';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { Input } from '@/components/ui/Input';
import { SectionLabel } from '@/components/ui/SectionLabel';
import { GradientHeading, GradientText } from '@/components/ui/GradientText';
import { request, rsaEncrypt, setPublicKey } from '@hospital/api';
import { setToken, setStorage, STORAGE_KEYS } from '@hospital/shared';

const ADMIN_URL = import.meta.env.VITE_ADMIN_URL || 'http://localhost:8006';

export function Login() {
  const [loading, setLoading] = useState(false);
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [errors, setErrors] = useState<{ username?: string; password?: string }>({});

  function validate(): boolean {
    const next: typeof errors = {};
    if (!username.trim()) next.username = '请输入管理员账号';
    if (password.length < 6) next.password = '密码至少 6 位';
    setErrors(next);
    return Object.keys(next).length === 0;
  }

  async function fetchPublicKey(): Promise<string> {
    const res: any = await request.get('/admin/public-key');
    const key = res?.data?.publicKey || res?.publicKey;
    if (!key) throw new Error('获取公钥失败');
    setPublicKey(key);
    return key;
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!validate()) return;

    setLoading(true);
    try {
      // 1. 获取 RSA 公钥
      const publicKey = await fetchPublicKey();

      // 2. 加密密码
      const encryptedPassword = rsaEncrypt(password, publicKey);

      // 3. 调用管理员登录接口
      const result: any = await request.post('/admin/login', {
        username: username.trim(),
        password: encryptedPassword,
        encrypted: true,
      });

      // 4. 存储 token
      setToken(result.accessToken);
      setStorage(STORAGE_KEYS.REFRESH_TOKEN, result.refreshToken);

      // 5. 存储租户和门店信息
      const tenantId = result.admin?.tenantId;
      if (tenantId) {
        localStorage.setItem('hospital_current_tenant_id', tenantId);
      }

      if (result.stores?.length > 0) {
        localStorage.setItem('hospital_current_store', JSON.stringify(result.stores[0]));
      } else if (result.store) {
        localStorage.setItem('hospital_current_store', JSON.stringify(result.store));
      }

      toast.success('登录成功');

      // 6. 跳转到控制台
      window.location.href = ADMIN_URL;
    } catch (err: any) {
      const msg = err?.response?.data?.message || err?.message || '登录失败，请检查账号密码';
      toast.error(msg);
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="relative overflow-hidden py-20">
      <SEO title="登录" description="使用管理员账号登录机构后台。" url="/login" />
      <div className="pointer-events-none absolute -left-32 top-0 h-[400px] w-[400px] rounded-full bg-accent-secondary/[0.03] blur-[120px]" />

      <div className="mx-auto max-w-md px-6">
        <motion.div
          initial="hidden"
          whileInView="visible"
          viewport={viewportOptions}
          variants={stagger}
          className="text-center"
        >
          <motion.div variants={fadeInUp} className="flex justify-center">
            <SectionLabel>欢迎回来</SectionLabel>
          </motion.div>
          <motion.div variants={fadeInUp} className="mt-6">
            <GradientHeading level={1}>
              登录<GradientText>控制台</GradientText>
            </GradientHeading>
          </motion.div>
          <motion.p variants={fadeInUp} className="mt-4 text-lg text-muted-foreground">
            使用管理员账号登录机构后台。
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
            <form onSubmit={handleSubmit} className="space-y-5">
              <Input
                label="管理员账号"
                placeholder="请输入账号"
                value={username}
                error={errors.username}
                leftIcon={<User />}
                onChange={(e) => { setUsername(e.target.value); setErrors((p) => ({ ...p, username: undefined })); }}
                required
              />
              <Input
                label="登录密码"
                placeholder="请输入密码"
                type="password"
                value={password}
                error={errors.password}
                leftIcon={<Lock />}
                onChange={(e) => { setPassword(e.target.value); setErrors((p) => ({ ...p, password: undefined })); }}
                required
              />
              <Button
                type="submit"
                size="lg"
                className="w-full"
                loading={loading}
                icon={<ArrowRight />}
              >
                登录
              </Button>
            </form>
          </Card>

          <div className="mt-6 text-center text-sm">
            <span className="text-muted-foreground">
              没有账号？{' '}
              <Link to="/register" className="font-medium text-accent hover:text-accent-secondary">
                免费注册
              </Link>
            </span>
          </div>
        </motion.div>
      </div>
    </section>
  );
}
