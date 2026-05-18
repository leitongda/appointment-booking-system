import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import {
  Smartphone,
  ArrowRight, Monitor, Stethoscope, Bell,
  FileText, Layers, Globe, Lock, Zap, ChevronRight,
} from 'lucide-react';
import { fadeInUp, stagger, viewportOptions } from '@/components/ui/animations';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { SectionLabel } from '@/components/ui/SectionLabel';
import { GradientHeading, GradientText } from '@/components/ui/GradientText';
import { InvertedSection } from '@/components/ui/InvertedSection';
import { SEO } from '@/components/SEO';

/* ============================================
   Data
   ============================================ */

const platforms = [
  {
    icon: Monitor,
    name: '机构端管理后台',
    desc: '功能完整的 Web 管理后台，支持多门店管理、科室配置、医生排班、预约管理、数据统计等全部管理功能。',
    features: ['多门店统一管理', '可视化排班', '预约全链路管理', '数据看板与报表'],
    color: 'from-accent to-accent-secondary',
  },
  {
    icon: Smartphone,
    name: '患者端 H5 / 小程序',
    desc: '面向患者的轻量级移动端，支持微信小程序和 H5，患者可在线预约挂号、查看排队、管理就诊卡。',
    features: ['在线预约挂号', '实时排队查看', '就诊卡管理', '历史记录查询'],
    color: 'from-green-500 to-emerald-500',
  },
  {
    icon: Stethoscope,
    name: '医生端工作台',
    desc: '医生专属工作台，查看排班、管理预约、处理叫号，高效完成日常诊疗工作。',
    features: ['排班日历', '预约患者列表', '叫号与签到', '工作量统计'],
    color: 'from-violet-500 to-purple-500',
  },
];

const workflows = [
  { step: '01', title: '机构注册', desc: '注册账号，创建机构，开启 14 天免费试用。' },
  { step: '02', title: '基础配置', desc: '设置门店信息、科室、医生，配置排班模板。' },
  { step: '03', title: '发布上线', desc: '生成患者端小程序/H5，患者即可在线预约。' },
  { step: '04', title: '运营管理', desc: '通过数据看板监控运营，持续优化服务。' },
];

const highlights = [
  { icon: Layers, title: 'SaaS 多租户', desc: '数据完全隔离，独立配置，一套系统服务多家机构。' },
  { icon: Globe, title: '多端覆盖', desc: '机构后台 + 患者 H5/小程序 + 医生工作台，全场景覆盖。' },
  { icon: Lock, title: '安全可靠', desc: '数据加密存储，传输 TLS 加密，定期备份保障数据安全。' },
  { icon: Zap, title: '高性能', desc: '异步架构 + Redis 缓存，支撑高并发预约场景。' },
  { icon: Bell, title: '消息通知', desc: '预约提醒、排队通知、爽约预警，多渠道触达患者。' },
  { icon: FileText, title: '数据导出', desc: '预约记录、统计数据一键导出，支持 Excel/CSV 格式。' },
];

/* ============================================
   Sections
   ============================================ */

function HeroSection() {
  return (
    <section className="relative overflow-hidden py-28 md:py-36">
      <div className="pointer-events-none absolute -right-32 top-0 h-[500px] w-[500px] rounded-full bg-accent/[0.04] blur-[150px]" />
      <div className="mx-auto max-w-6xl px-6">
        <motion.div
          initial="hidden"
          whileInView="visible"
          viewport={viewportOptions}
          variants={stagger}
          className="text-center"
        >
          <motion.div variants={fadeInUp} className="flex justify-center">
            <SectionLabel>产品介绍</SectionLabel>
          </motion.div>
          <motion.div variants={fadeInUp} className="mt-6">
            <GradientHeading level={1}>
              全场景<GradientText>医院挂号</GradientText>解决方案
            </GradientHeading>
          </motion.div>
          <motion.p variants={fadeInUp} className="mx-auto mt-6 max-w-2xl text-lg leading-relaxed text-muted-foreground">
            从机构管理到患者预约，从医生排班到数据分析，一套系统覆盖医院挂号业务的全部场景。
          </motion.p>
          <motion.div variants={fadeInUp} className="mt-10 flex flex-col items-center gap-4 sm:flex-row sm:justify-center">
            <Link to="/register">
              <Button size="lg" icon={<ArrowRight />}>
                免费试用 14 天
              </Button>
            </Link>
            <Link to="/pricing">
              <Button variant="outline" size="lg">
                查看定价
              </Button>
            </Link>
          </motion.div>
        </motion.div>
      </div>
    </section>
  );
}

function PlatformsSection() {
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
            <SectionLabel>多端覆盖</SectionLabel>
          </motion.div>
          <motion.div variants={fadeInUp} className="mt-6">
            <GradientHeading level={2}>
              三大<GradientText>产品端</GradientText>
            </GradientHeading>
          </motion.div>
          <motion.p variants={fadeInUp} className="mx-auto mt-4 max-w-2xl text-lg text-muted-foreground">
            机构端、患者端、医生端三端协同，覆盖医院挂号业务全流程。
          </motion.p>
        </motion.div>

        <motion.div
          initial="hidden"
          whileInView="visible"
          viewport={viewportOptions}
          variants={stagger}
          className="mt-16 grid gap-8 lg:grid-cols-3"
        >
          {platforms.map((p, i) => (
            <motion.div key={i} variants={fadeInUp}>
              <Card hoverable padding="lg" className="group h-full">
                <div className={`mb-5 flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-br ${p.color} shadow-sm transition-transform duration-300 group-hover:scale-110`}>
                  <p.icon className="h-7 w-7 text-white" />
                </div>
                <h3 className="text-xl font-semibold text-foreground">{p.name}</h3>
                <p className="mt-3 text-sm leading-relaxed text-muted-foreground">{p.desc}</p>
                <ul className="mt-5 space-y-2">
                  {p.features.map((f, j) => (
                    <li key={j} className="flex items-center gap-2 text-sm text-muted-foreground">
                      <ChevronRight className="h-3.5 w-3.5 text-accent" />
                      {f}
                    </li>
                  ))}
                </ul>
              </Card>
            </motion.div>
          ))}
        </motion.div>
      </div>
    </section>
  );
}

function WorkflowSection() {
  return (
    <InvertedSection className="py-28">
      <div className="mx-auto max-w-6xl px-6">
        <motion.div
          initial="hidden"
          whileInView="visible"
          viewport={viewportOptions}
          variants={stagger}
          className="text-center"
        >
          <motion.h2 variants={fadeInUp} className="font-display text-3xl text-white md:text-[3.25rem]">
            四步开启数字化挂号
          </motion.h2>
          <motion.p variants={fadeInUp} className="mx-auto mt-4 max-w-xl text-lg text-white/70">
            从注册到上线，最快 10 分钟完成部署。
          </motion.p>
        </motion.div>

        <motion.div
          initial="hidden"
          whileInView="visible"
          viewport={viewportOptions}
          variants={stagger}
          className="mt-16 grid gap-8 sm:grid-cols-2 lg:grid-cols-4"
        >
          {workflows.map((w, i) => (
            <motion.div key={i} variants={fadeInUp} className="text-center">
              <span className="inline-block font-display text-5xl text-accent-secondary/30">{w.step}</span>
              <h3 className="mt-3 text-lg font-semibold text-white">{w.title}</h3>
              <p className="mt-2 text-sm leading-relaxed text-white/60">{w.desc}</p>
            </motion.div>
          ))}
        </motion.div>
      </div>
    </InvertedSection>
  );
}

function HighlightsSection() {
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
            <SectionLabel>技术优势</SectionLabel>
          </motion.div>
          <motion.div variants={fadeInUp} className="mt-6">
            <GradientHeading level={2}>
              为什么<GradientText>选择我们</GradientText>
            </GradientHeading>
          </motion.div>
        </motion.div>

        <motion.div
          initial="hidden"
          whileInView="visible"
          viewport={viewportOptions}
          variants={stagger}
          className="mt-16 grid gap-6 sm:grid-cols-2 lg:grid-cols-3"
        >
          {highlights.map((h, i) => (
            <motion.div key={i} variants={fadeInUp}>
              <Card hoverable padding="lg" className="group h-full">
                <div className="mb-4 flex h-11 w-11 items-center justify-center rounded-xl bg-accent/10 text-accent transition-colors group-hover:bg-accent group-hover:text-white">
                  <h.icon className="h-5 w-5" />
                </div>
                <h3 className="text-base font-semibold text-foreground">{h.title}</h3>
                <p className="mt-2 text-sm leading-relaxed text-muted-foreground">{h.desc}</p>
              </Card>
            </motion.div>
          ))}
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
            立即体验完整功能
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
            <Link to="/experience">
              <Button variant="ghost" size="lg" className="text-white/70 hover:text-white">
                在线体验
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

export function Products() {
  return (
    <>
      <SEO
        title="产品介绍"
        description="机构端管理后台、患者端 H5/小程序、医生端工作台，三端协同覆盖医院挂号业务全流程。"
        url="/products"
      />
      <HeroSection />
      <PlatformsSection />
      <WorkflowSection />
      <HighlightsSection />
      <CTASection />
    </>
  );
}
