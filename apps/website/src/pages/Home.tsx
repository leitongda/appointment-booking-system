import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import {
  Building2, Calendar, Users, BarChart3, Smartphone, Shield,
  ArrowRight, ChevronRight, CheckCircle2,
} from 'lucide-react';
import { SEO } from '@/components/SEO';
import {
  fadeInUp, stagger, viewportOptions,
  floatAnimation, floatAnimationDelayed, rotateAnimation,
} from '@/components/ui/animations';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { SectionLabel } from '@/components/ui/SectionLabel';
import { GradientHeading, GradientText } from '@/components/ui/GradientText';
import { InvertedSection } from '@/components/ui/InvertedSection';

/* ============================================
   Data
   ============================================ */

const features = [
  {
    icon: Building2,
    title: '多门店管理',
    desc: '支持多分院/多门店统一管理，每个门店独立配置科室、医生和排班。',
  },
  {
    icon: Calendar,
    title: '智能排班',
    desc: '灵活的排班模板和自定义排班，支持休息日、停诊、调班管理。',
  },
  {
    icon: Users,
    title: '预约挂号',
    desc: '患者在线预约挂号，选择时段、科室、医生，实时查看排队状态。',
  },
  {
    icon: BarChart3,
    title: '数据统计',
    desc: '预约趋势、科室分析、医生工作量统计，数据驱动运营决策。',
  },
  {
    icon: Smartphone,
    title: '多端覆盖',
    desc: '机构端后台 + 患者端 H5/小程序 + 医生端工作台，全场景覆盖。',
  },
  {
    icon: Shield,
    title: 'SaaS 多租户',
    desc: '数据隔离、独立配置、订阅计费，一套系统服务多家机构。',
  },
];

const stats = [
  { value: '3', suffix: '端', label: '全平台覆盖' },
  { value: '50+', suffix: '', label: '业务模块' },
  { value: '14', suffix: '天', label: '免费试用' },
  { value: '99.9', suffix: '%', label: '可用性保障' },
];

const plans = [
  {
    name: '基础版',
    price: '免费',
    desc: '适合小型诊所试用',
    features: ['1 个门店', '5 个医生', '1000 次/月预约', '基础统计'],
  },
  {
    name: '专业版',
    price: '¥299',
    period: '/月',
    desc: '适合中型医院',
    features: ['5 个门店', '50 个医生', '10000 次/月预约', '高级统计', '微信小程序', '短信通知'],
    highlighted: true,
  },
  {
    name: '企业版',
    price: '¥899',
    period: '/月',
    desc: '适合连锁医疗集团',
    features: ['无限门店', '无限医生', '无限预约', '全部功能', '专属支持', '自定义品牌'],
  },
];

/* ============================================
   Sections
   ============================================ */

function HeroSection() {
  return (
    <section className="relative overflow-hidden py-28 md:py-40">
      {/* Background glow */}
      <div className="pointer-events-none absolute -right-32 top-0 h-[500px] w-[500px] rounded-full bg-accent/[0.04] blur-[150px]" />
      <div className="pointer-events-none absolute -left-32 bottom-0 h-[400px] w-[400px] rounded-full bg-accent-secondary/[0.03] blur-[120px]" />

      <div className="mx-auto max-w-6xl px-6">
        <div className="grid items-center gap-12 md:grid-cols-[1.1fr_0.9fr]">
          {/* Text */}
          <motion.div initial="hidden" whileInView="visible" viewport={viewportOptions} variants={stagger}>
            <motion.div variants={fadeInUp} className="mb-6">
              <SectionLabel pulse>SaaS 多租户架构</SectionLabel>
            </motion.div>

            <motion.h1
              variants={fadeInUp}
              className="relative font-display text-[2.75rem] leading-[1.05] tracking-tight text-foreground md:text-6xl lg:text-[5.25rem]"
            >
              医院挂号
              <br />
              <GradientText>系统解决方案</GradientText>
              <span className="gradient-underline" />
            </motion.h1>

            <motion.p variants={fadeInUp} className="mt-8 max-w-lg text-lg leading-relaxed text-muted-foreground">
              一套完整的 SaaS 多租户医院预约挂号系统，支持多门店、多科室、多医生排班，覆盖机构端、患者端、医生端全场景。
            </motion.p>

            <motion.div variants={fadeInUp} className="mt-10 flex flex-col gap-4 sm:flex-row">
              <Link to="/register">
                <Button size="lg" icon={<ArrowRight />}>
                  免费试用 14 天
                </Button>
              </Link>
              <Link to="/products">
                <Button variant="outline" size="lg">
                  了解更多
                </Button>
              </Link>
            </motion.div>
          </motion.div>

          {/* Hero graphic */}
          <div className="hidden lg:block">
            <div className="relative h-[420px]">
              {/* Rotating ring */}
              <motion.div
                animate={rotateAnimation}
                className="absolute left-1/2 top-1/2 h-72 w-72 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-dashed border-accent/20"
              />
              {/* Floating cards */}
              <motion.div
                animate={floatAnimation}
                className="absolute left-8 top-12 w-56 rounded-xl border border-border bg-card p-4 shadow-lg"
              >
                <div className="flex items-center gap-3">
                  <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-gradient-to-br from-accent to-accent-secondary">
                    <Calendar className="h-5 w-5 text-white" />
                  </div>
                  <div>
                    <p className="text-sm font-semibold text-foreground">今日预约</p>
                    <p className="text-xs text-muted-foreground">128 人次</p>
                  </div>
                </div>
              </motion.div>
              <motion.div
                animate={floatAnimationDelayed}
                className="absolute right-4 top-28 w-52 rounded-xl border border-border bg-card p-4 shadow-lg"
              >
                <div className="flex items-center gap-3">
                  <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-gradient-to-br from-green-500 to-emerald-500">
                    <CheckCircle2 className="h-5 w-5 text-white" />
                  </div>
                  <div>
                    <p className="text-sm font-semibold text-foreground">签到率</p>
                    <p className="text-xs text-muted-foreground">92.5%</p>
                  </div>
                </div>
              </motion.div>
              {/* Center block */}
              <div className="absolute left-1/2 top-1/2 h-20 w-20 -translate-x-1/2 -translate-y-1/2 rounded-2xl bg-gradient-to-br from-accent to-accent-secondary shadow-accent-lg" />
              {/* Dot grid */}
              <div className="absolute bottom-4 left-12 grid grid-cols-3 gap-2">
                {Array.from({ length: 9 }).map((_, i) => (
                  <div key={i} className="h-1.5 w-1.5 rounded-full bg-accent/30" />
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

function FeaturesSection() {
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
            <SectionLabel>核心功能</SectionLabel>
          </motion.div>
          <motion.div variants={fadeInUp} className="mt-6">
            <GradientHeading level={2}>
              覆盖全场景的<GradientText>功能矩阵</GradientText>
            </GradientHeading>
          </motion.div>
          <motion.p variants={fadeInUp} className="mx-auto mt-4 max-w-2xl text-lg text-muted-foreground">
            从预约挂号到数据分析，一站式解决医院信息化管理需求。
          </motion.p>
        </motion.div>

        <motion.div
          initial="hidden"
          whileInView="visible"
          viewport={viewportOptions}
          variants={stagger}
          className="mt-16 grid gap-6 sm:grid-cols-2 lg:grid-cols-3"
        >
          {features.map((f, i) => (
            <motion.div key={i} variants={fadeInUp}>
              <Card hoverable padding="lg" className="group h-full">
                <div className="mb-5 flex h-12 w-12 items-center justify-center rounded-xl bg-gradient-to-br from-accent to-accent-secondary shadow-sm transition-transform duration-300 group-hover:scale-110">
                  <f.icon className="h-6 w-6 text-white" />
                </div>
                <h3 className="text-lg font-semibold text-foreground">{f.title}</h3>
                <p className="mt-2 text-sm leading-relaxed text-muted-foreground">{f.desc}</p>
              </Card>
            </motion.div>
          ))}
        </motion.div>
      </div>
    </section>
  );
}

function StatsSection() {
  return (
    <InvertedSection className="py-24">
      <div className="mx-auto max-w-6xl px-6">
        <motion.div
          initial="hidden"
          whileInView="visible"
          viewport={viewportOptions}
          variants={stagger}
          className="grid grid-cols-2 gap-8 md:grid-cols-4"
        >
          {stats.map((s, i) => (
            <motion.div key={i} variants={fadeInUp} className="text-center">
              <p className="font-display text-4xl text-white md:text-5xl">
                {s.value}
                <span className="text-accent-secondary">{s.suffix}</span>
              </p>
              <p className="mt-2 text-sm text-white/70">{s.label}</p>
            </motion.div>
          ))}
        </motion.div>
      </div>
    </InvertedSection>
  );
}

function PricingPreviewSection() {
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
            <SectionLabel>定价方案</SectionLabel>
          </motion.div>
          <motion.div variants={fadeInUp} className="mt-6">
            <GradientHeading level={2}>
              选择适合您的<GradientText>方案</GradientText>
            </GradientHeading>
          </motion.div>
          <motion.p variants={fadeInUp} className="mx-auto mt-4 max-w-2xl text-lg text-muted-foreground">
            所有方案均含 14 天免费试用，无需信用卡。
          </motion.p>
        </motion.div>

        <motion.div
          initial="hidden"
          whileInView="visible"
          viewport={viewportOptions}
          variants={stagger}
          className="mt-16 grid gap-6 md:grid-cols-3"
        >
          {plans.map((plan, i) => (
            <motion.div key={i} variants={fadeInUp}>
              <Card
                variant={plan.highlighted ? 'gradient-border' : 'default'}
                hoverable
                padding="lg"
                className={`relative h-full ${plan.highlighted ? 'shadow-accent' : ''}`}
              >
                {plan.highlighted && (
                  <span className="absolute -top-3 left-1/2 -translate-x-1/2 rounded-full bg-gradient-to-r from-accent to-accent-secondary px-4 py-1 text-xs font-medium text-white">
                    推荐
                  </span>
                )}
                <h3 className="font-display text-xl text-foreground">{plan.name}</h3>
                <p className="mt-1 text-sm text-muted-foreground">{plan.desc}</p>
                <div className="mt-6">
                  <span className="font-display text-4xl text-foreground">{plan.price}</span>
                  {plan.period && <span className="text-muted-foreground">{plan.period}</span>}
                </div>
                <ul className="mt-8 space-y-3">
                  {plan.features.map((f, j) => (
                    <li key={j} className="flex items-center gap-2 text-sm text-muted-foreground">
                      <CheckCircle2 className="h-4 w-4 shrink-0 text-accent" />
                      {f}
                    </li>
                  ))}
                </ul>
                <div className="mt-8">
                  <Link to="/register">
                    <Button
                      variant={plan.highlighted ? 'primary' : 'outline'}
                      className="w-full"
                    >
                      开始试用
                    </Button>
                  </Link>
                </div>
              </Card>
            </motion.div>
          ))}
        </motion.div>

        <motion.div
          initial="hidden"
          whileInView="visible"
          viewport={viewportOptions}
          variants={fadeInUp}
          className="mt-8 text-center"
        >
          <Link
            to="/pricing"
            className="inline-flex items-center gap-1 text-sm font-medium text-accent transition-colors hover:text-accent-secondary"
          >
            查看完整定价对比
            <ChevronRight className="h-4 w-4" />
          </Link>
        </motion.div>
      </div>
    </section>
  );
}

function CTASection() {
  return (
    <InvertedSection className="py-24">
      <div className="mx-auto max-w-3xl px-6 text-center">
        <motion.div initial="hidden" whileInView="visible" viewport={viewportOptions} variants={stagger}>
          <motion.h2 variants={fadeInUp} className="font-display text-3xl text-white md:text-[3.25rem]">
            开始您的数字化挂号之旅
          </motion.h2>
          <motion.p variants={fadeInUp} className="mx-auto mt-4 max-w-xl text-lg text-white/70">
            14 天免费试用，无需信用卡，即刻体验完整的医院挂号管理方案。
          </motion.p>
          <motion.div variants={fadeInUp} className="mt-10 flex flex-col items-center gap-4 sm:flex-row sm:justify-center">
            <Link to="/register">
              <Button size="lg" icon={<ArrowRight />}>
                免费试用 14 天
              </Button>
            </Link>
            <Link to="/login">
              <Button variant="ghost" size="lg" className="text-white/70 hover:text-white">
                已有账号？登录
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

export function Home() {
  return (
    <>
      <SEO
        title="医院挂号系统解决方案"
        description="一套完整的 SaaS 多租户医院预约挂号系统，支持多门店、多科室、多医生排班，覆盖机构端、患者端、医生端全场景。"
        url="/"
      />
      <HeroSection />
      <FeaturesSection />
      <StatsSection />
      <PricingPreviewSection />
      <CTASection />
    </>
  );
}
