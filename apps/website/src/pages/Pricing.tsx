import { useState } from 'react';
import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import {
  CheckCircle2, X, ArrowRight, Calendar,
  BarChart3, MessageSquare, FileDown, Code2, Palette,
  ShieldCheck, KeyRound, Smartphone,
} from 'lucide-react';
import { SEO } from '@/components/SEO';
import { fadeInUp, stagger, viewportOptions } from '@/components/ui/animations';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { SectionLabel } from '@/components/ui/SectionLabel';
import { GradientHeading, GradientText } from '@/components/ui/GradientText';
import { InvertedSection } from '@/components/ui/InvertedSection';

/* ============================================
   Static plan data (mirrors backend seed script)
   ============================================ */

type BillingCycle = 'monthly' | 'yearly';

interface Plan {
  code: string;
  name: string;
  description: string;
  priceMonthly: number;
  priceYearly: number;
  highlighted: boolean;
  quotas: { label: string; value: string }[];
  features: string[];
}

const plans: Plan[] = [
  {
    code: 'basic',
    name: '基础版',
    description: '适合小型诊所试用',
    priceMonthly: 299,
    priceYearly: 2990,
    highlighted: false,
    quotas: [
      { label: '门店数', value: '1 个' },
      { label: '管理员', value: '3 个' },
      { label: '医生数', value: '10 个' },
      { label: '月预约量', value: '500 次' },
      { label: '存储空间', value: '512 MB' },
    ],
    features: ['basic_appointment', 'basic_schedule', 'basic_statistics'],
  },
  {
    code: 'pro',
    name: '专业版',
    description: '适合中型医院',
    priceMonthly: 699,
    priceYearly: 6990,
    highlighted: true,
    quotas: [
      { label: '门店数', value: '5 个' },
      { label: '管理员', value: '10 个' },
      { label: '医生数', value: '50 个' },
      { label: '月预约量', value: '3,000 次' },
      { label: '存储空间', value: '2 GB' },
    ],
    features: [
      'basic_appointment', 'basic_schedule', 'basic_statistics',
      'advanced_statistics', 'wechat_integration', 'sms_notification', 'export_data',
    ],
  },
  {
    code: 'enterprise',
    name: '企业版',
    description: '适合连锁医疗集团',
    priceMonthly: 1999,
    priceYearly: 19990,
    highlighted: false,
    quotas: [
      { label: '门店数', value: '50 个' },
      { label: '管理员', value: '100 个' },
      { label: '医生数', value: '500 个' },
      { label: '月预约量', value: '50,000 次' },
      { label: '存储空间', value: '10 GB' },
    ],
    features: [
      'basic_appointment', 'basic_schedule', 'basic_statistics',
      'advanced_statistics', 'wechat_integration', 'sms_notification', 'export_data',
      'api_access', 'custom_branding', 'priority_support', 'sso',
    ],
  },
];

/* Feature definitions for comparison table */
interface FeatureDef {
  key: string;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  category: string;
}

const featureDefs: FeatureDef[] = [
  { key: 'basic_appointment', label: '在线预约挂号', icon: Calendar, category: '预约管理' },
  { key: 'basic_schedule', label: '排班管理', icon: Calendar, category: '预约管理' },
  { key: 'basic_statistics', label: '基础数据统计', icon: BarChart3, category: '数据分析' },
  { key: 'advanced_statistics', label: '高级数据分析', icon: BarChart3, category: '数据分析' },
  { key: 'wechat_integration', label: '微信小程序', icon: Smartphone, category: '渠道集成' },
  { key: 'sms_notification', label: '短信通知', icon: MessageSquare, category: '渠道集成' },
  { key: 'export_data', label: '数据导出', icon: FileDown, category: '数据管理' },
  { key: 'api_access', label: 'API 接口访问', icon: Code2, category: '高级功能' },
  { key: 'custom_branding', label: '自定义品牌', icon: Palette, category: '高级功能' },
  { key: 'priority_support', label: '专属技术支持', icon: ShieldCheck, category: '高级功能' },
  { key: 'sso', label: '单点登录 (SSO)', icon: KeyRound, category: '高级功能' },
];

/* ============================================
   Helpers
   ============================================ */

function formatPrice(price: number): string {
  return price === 0 ? '免费' : `¥${price.toLocaleString()}`;
}

function yearlyDiscount(monthly: number, yearly: number): number {
  if (monthly === 0) return 0;
  return Math.round((1 - yearly / (monthly * 12)) * 100);
}

/* ============================================
   Sections
   ============================================ */

function PricingHeader() {
  return (
    <motion.div
      initial="hidden"
      whileInView="visible"
      viewport={viewportOptions}
      variants={stagger}
      className="text-center"
    >
      <motion.div variants={fadeInUp} className="flex justify-center">
        <SectionLabel>定价方案</SectionLabel>
      </motion.div>
      <motion.div variants={fadeInUp} className="mt-6">
        <GradientHeading level={1}>
          选择适合您的<GradientText>方案</GradientText>
        </GradientHeading>
      </motion.div>
      <motion.p variants={fadeInUp} className="mx-auto mt-4 max-w-2xl text-lg text-muted-foreground">
        所有方案均含 14 天免费试用，无需信用卡。按年付费可享 8 折优惠。
      </motion.p>
    </motion.div>
  );
}

function BillingToggle({
  cycle,
  onChange,
}: {
  cycle: BillingCycle;
  onChange: (c: BillingCycle) => void;
}) {
  return (
    <motion.div
      initial="hidden"
      whileInView="visible"
      viewport={viewportOptions}
      variants={fadeInUp}
      className="mt-10 flex items-center justify-center gap-4"
    >
      <span className={`text-sm font-medium transition-colors ${cycle === 'monthly' ? 'text-foreground' : 'text-muted-foreground'}`}>
        月付
      </span>
      <button
        type="button"
        onClick={() => onChange(cycle === 'monthly' ? 'yearly' : 'monthly')}
        className="relative h-7 w-12 rounded-full bg-muted transition-colors hover:bg-muted/80"
        aria-label="切换计费周期"
      >
        <span
          className={`absolute top-0.5 left-0.5 h-6 w-6 rounded-full bg-white shadow-sm transition-transform duration-200 ${
            cycle === 'yearly' ? 'translate-x-5' : ''
          }`}
        />
      </button>
      <span className={`text-sm font-medium transition-colors ${cycle === 'yearly' ? 'text-foreground' : 'text-muted-foreground'}`}>
        年付
        <span className="ml-1.5 inline-block rounded-full bg-accent/10 px-2 py-0.5 text-xs font-semibold text-accent">
          省 20%
        </span>
      </span>
    </motion.div>
  );
}

function PlanCards({ cycle }: { cycle: BillingCycle }) {
  return (
    <motion.div
      initial="hidden"
      whileInView="visible"
      viewport={viewportOptions}
      variants={stagger}
      className="mt-12 grid gap-6 md:grid-cols-3"
    >
      {plans.map((plan) => {
        const price = cycle === 'monthly' ? plan.priceMonthly : plan.priceYearly;
        const period = cycle === 'monthly' ? '/月' : '/年';
        const discount = yearlyDiscount(plan.priceMonthly, plan.priceYearly);

        return (
          <motion.div key={plan.code} variants={fadeInUp}>
            <Card
              variant={plan.highlighted ? 'gradient-border' : 'default'}
              hoverable
              padding="lg"
              className={`relative flex h-full flex-col ${plan.highlighted ? 'shadow-accent' : ''}`}
            >
              {plan.highlighted && (
                <span className="absolute -top-3 left-1/2 -translate-x-1/2 rounded-full bg-gradient-to-r from-accent to-accent-secondary px-4 py-1 text-xs font-medium text-white">
                  推荐
                </span>
              )}

              <div>
                <h3 className="font-display text-xl text-foreground">{plan.name}</h3>
                <p className="mt-1 text-sm text-muted-foreground">{plan.description}</p>
              </div>

              <div className="mt-6">
                <span className="font-display text-4xl text-foreground">{formatPrice(price)}</span>
                {price > 0 && <span className="text-muted-foreground">{period}</span>}
                {cycle === 'yearly' && price > 0 && discount > 0 && (
                  <span className="ml-2 text-xs text-accent">省 {discount}%</span>
                )}
              </div>

              {/* Quotas */}
              <ul className="mt-6 space-y-2.5 border-t border-border pt-6">
                {plan.quotas.map((q) => (
                  <li key={q.label} className="flex items-center justify-between text-sm">
                    <span className="text-muted-foreground">{q.label}</span>
                    <span className="font-medium text-foreground">{q.value}</span>
                  </li>
                ))}
              </ul>

              {/* CTA */}
              <div className="mt-auto pt-8">
                <Link to="/register">
                  <Button
                    variant={plan.highlighted ? 'primary' : 'outline'}
                    className="w-full"
                    icon={<ArrowRight />}
                  >
                    {price === 0 ? '免费开始' : '开始试用'}
                  </Button>
                </Link>
              </div>
            </Card>
          </motion.div>
        );
      })}
    </motion.div>
  );
}

function ComparisonTable() {
  // Group features by category
  const categories = featureDefs.reduce<Record<string, FeatureDef[]>>((acc, f) => {
    (acc[f.category] ??= []).push(f);
    return acc;
  }, {});

  return (
    <section className="py-28">
      <div className="mx-auto max-w-6xl px-6">
        <motion.div
          initial="hidden"
          whileInView="visible"
          viewport={viewportOptions}
          variants={stagger}
          className="text-center"
        >
          <motion.div variants={fadeInUp} className="flex justify-center">
            <SectionLabel>功能对比</SectionLabel>
          </motion.div>
          <motion.div variants={fadeInUp} className="mt-6">
            <GradientHeading level={2}>
              详细<GradientText>功能对比</GradientText>
            </GradientHeading>
          </motion.div>
        </motion.div>

        <motion.div
          initial="hidden"
          whileInView="visible"
          viewport={viewportOptions}
          variants={fadeInUp}
          className="mt-12 overflow-x-auto"
        >
          <table className="w-full min-w-[640px] border-collapse">
            <thead>
              <tr className="border-b border-border">
                <th className="pb-4 pr-6 text-left text-sm font-medium text-muted-foreground">
                  功能
                </th>
                {plans.map((p) => (
                  <th
                    key={p.code}
                    className={`pb-4 text-center text-sm font-semibold ${
                      p.highlighted ? 'text-accent' : 'text-foreground'
                    }`}
                  >
                    {p.name}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {Object.entries(categories).map(([category, features]) => (
                <>
                  <tr key={`cat-${category}`}>
                    <td
                      colSpan={4}
                      className="pb-2 pt-6 text-xs font-semibold uppercase tracking-wider text-muted-foreground"
                    >
                      {category}
                    </td>
                  </tr>
                  {features.map((f) => {
                    const Icon = f.icon;
                    return (
                      <tr key={f.key} className="border-b border-border/50">
                        <td className="flex items-center gap-2.5 py-3.5 pr-6 text-sm text-foreground">
                          <Icon className="h-4 w-4 text-muted-foreground" />
                          {f.label}
                        </td>
                        {plans.map((p) => (
                          <td key={p.code} className="py-3.5 text-center">
                            {p.features.includes(f.key) ? (
                              <CheckCircle2 className="mx-auto h-5 w-5 text-accent" />
                            ) : (
                              <X className="mx-auto h-5 w-5 text-muted-foreground/30" />
                            )}
                          </td>
                        ))}
                      </tr>
                    );
                  })}
                </>
              ))}
            </tbody>
          </table>
        </motion.div>
      </div>
    </section>
  );
}

function PricingFAQ() {
  const faqs = [
    {
      q: '免费试用期间有什么限制吗？',
      a: '14 天免费试用期间可使用所选方案的全部功能，无需绑定信用卡。试用到期后可选择付费续期或降级为基础版。',
    },
    {
      q: '可以中途升级或降级方案吗？',
      a: '可以。升级立即生效，按剩余天数补差价；降级在当前计费周期结束后生效。',
    },
    {
      q: '数据安全如何保障？',
      a: '所有数据采用 AES-256 加密存储，传输使用 TLS 1.3。每个租户数据完全隔离，支持定期备份和数据导出。',
    },
    {
      q: '支持哪些支付方式？',
      a: '支持微信支付、支付宝、银行转账。企业版客户可申请对公转账和开具增值税专用发票。',
    },
  ];

  return (
    <section className="py-28">
      <div className="mx-auto max-w-3xl px-6">
        <motion.div
          initial="hidden"
          whileInView="visible"
          viewport={viewportOptions}
          variants={stagger}
          className="text-center"
        >
          <motion.div variants={fadeInUp} className="flex justify-center">
            <SectionLabel>常见问题</SectionLabel>
          </motion.div>
          <motion.div variants={fadeInUp} className="mt-6">
            <GradientHeading level={2}>
              常见<GradientText>问题</GradientText>
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
          {faqs.map((faq, i) => (
            <motion.div key={i} variants={fadeInUp}>
              <Card padding="lg">
                <h3 className="text-base font-semibold text-foreground">{faq.q}</h3>
                <p className="mt-2 text-sm leading-relaxed text-muted-foreground">{faq.a}</p>
              </Card>
            </motion.div>
          ))}
        </motion.div>
      </div>
    </section>
  );
}

function PricingCTA() {
  return (
    <InvertedSection className="py-24">
      <div className="mx-auto max-w-3xl px-6 text-center">
        <motion.div initial="hidden" whileInView="visible" viewport={viewportOptions} variants={stagger}>
          <motion.h2 variants={fadeInUp} className="font-display text-3xl text-white md:text-[3.25rem]">
            立即开始 14 天免费试用
          </motion.h2>
          <motion.p variants={fadeInUp} className="mx-auto mt-4 max-w-xl text-lg text-white/70">
            无需信用卡，即刻体验完整的医院挂号管理方案。
          </motion.p>
          <motion.div variants={fadeInUp} className="mt-10 flex flex-col items-center gap-4 sm:flex-row sm:justify-center">
            <Link to="/register">
              <Button size="lg" icon={<ArrowRight />}>
                免费试用 14 天
              </Button>
            </Link>
            <Link to="/contact">
              <Button variant="ghost" size="lg" className="text-white/70 hover:text-white">
                联系销售
              </Button>
            </Link>
          </motion.div>
        </motion.div>
      </div>
    </InvertedSection>
  );
}

/* ============================================
   Page
   ============================================ */

export function Pricing() {
  const [cycle, setCycle] = useState<BillingCycle>('monthly');

  return (
    <>
      <SEO
        title="定价方案"
        description="基础版、专业版、企业版三档方案，满足不同规模医疗机构需求。所有方案均含 14 天免费试用。"
        url="/pricing"
      />
      {/* Hero area */}
      <section className="relative overflow-hidden pt-28 pb-12">
        <div className="pointer-events-none absolute -right-32 top-0 h-[500px] w-[500px] rounded-full bg-accent/[0.04] blur-[150px]" />
        <div className="mx-auto max-w-6xl px-6">
          <PricingHeader />
          <BillingToggle cycle={cycle} onChange={setCycle} />
          <PlanCards cycle={cycle} />
        </div>
      </section>

      <ComparisonTable />
      <PricingFAQ />
      <PricingCTA />
    </>
  );
}
