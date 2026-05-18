import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import {
  ArrowRight, Monitor, Smartphone, Stethoscope,
  Calendar, BarChart3, Users, Play,
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

const demoScreens = [
  {
    title: '预约管理面板',
    desc: '一目了然的预约总览，支持按日期、科室、医生筛选，快速处理预约状态变更。',
    icon: Calendar,
    gradient: 'from-accent/20 to-accent-secondary/10',
    mockup: 'dashboard',
  },
  {
    title: '数据统计看板',
    desc: '预约趋势、科室分析、医生工作量等多维度数据，支持自定义时间范围和导出。',
    icon: BarChart3,
    gradient: 'from-green-500/20 to-emerald-500/10',
    mockup: 'chart',
  },
  {
    title: '排班日历',
    desc: '可视化排班管理，拖拽调班、批量操作，支持模板复用和休息日设置。',
    icon: Calendar,
    gradient: 'from-violet-500/20 to-purple-500/10',
    mockup: 'calendar',
  },
  {
    title: '患者管理',
    desc: '患者档案、就诊记录、预约历史全记录，支持搜索和标签分类。',
    icon: Users,
    gradient: 'from-orange-500/20 to-amber-500/10',
    mockup: 'table',
  },
];

/** 线框风格的 UI 模拟图 */
function MockupDashboard() {
  return (
    <div className="flex h-full flex-col gap-2 p-3">
      <div className="flex gap-2">
        <div className="h-3 w-16 rounded bg-foreground/10" />
        <div className="h-3 w-10 rounded bg-accent/20" />
      </div>
      <div className="mt-1 grid grid-cols-3 gap-2">
        {[1, 2, 3].map((i) => (
          <div key={i} className="rounded-lg bg-muted/60 p-2">
            <div className="h-2 w-8 rounded bg-foreground/10" />
            <div className="mt-1 h-4 w-12 rounded bg-accent/15" />
          </div>
        ))}
      </div>
      <div className="mt-1 flex-1 rounded-lg bg-muted/40 p-2">
        <div className="flex gap-1">
          {['周一', '周二', '周三', '周四', '周五'].map((d) => (
            <div key={d} className="flex-1 text-center">
              <div className="text-[8px] text-foreground/30">{d}</div>
              <div className="mt-1 space-y-1">
                <div className="h-2 rounded bg-accent/20" />
                <div className="h-2 rounded bg-green-500/20" />
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function MockupChart() {
  return (
    <div className="flex h-full flex-col gap-2 p-3">
      <div className="flex gap-2">
        <div className="h-3 w-12 rounded bg-foreground/10" />
        <div className="h-3 w-8 rounded bg-foreground/10" />
      </div>
      <div className="mt-1 flex flex-1 items-end gap-1 px-2">
        {[40, 65, 45, 80, 55, 70, 90, 60, 75, 85, 50, 95].map((h, i) => (
          <div
            key={i}
            className="flex-1 rounded-t bg-gradient-to-t from-accent/30 to-accent/10"
            style={{ height: `${h}%` }}
          />
        ))}
      </div>
      <div className="flex justify-between px-2">
        <div className="h-2 w-6 rounded bg-foreground/10" />
        <div className="h-2 w-6 rounded bg-foreground/10" />
        <div className="h-2 w-6 rounded bg-foreground/10" />
      </div>
    </div>
  );
}

function MockupCalendar() {
  const days = Array.from({ length: 28 }, (_, i) => i + 1);
  return (
    <div className="flex h-full flex-col gap-2 p-3">
      <div className="flex items-center justify-between">
        <div className="h-3 w-16 rounded bg-foreground/10" />
        <div className="flex gap-1">
          <div className="h-4 w-4 rounded bg-muted" />
          <div className="h-4 w-4 rounded bg-muted" />
        </div>
      </div>
      <div className="mt-1 grid grid-cols-7 gap-1">
        {days.map((d) => (
          <div
            key={d}
            className={`flex h-5 items-center justify-center rounded text-[8px] ${
              [3, 7, 12, 15, 20, 24].includes(d)
                ? 'bg-accent/15 text-accent/60'
                : 'text-foreground/20'
            }`}
          >
            {d}
          </div>
        ))}
      </div>
    </div>
  );
}

function MockupTable() {
  return (
    <div className="flex h-full flex-col gap-2 p-3">
      <div className="flex gap-2">
        <div className="h-6 flex-1 rounded bg-muted/60" />
        <div className="h-6 w-16 rounded bg-accent/20" />
      </div>
      <div className="mt-1 flex-1 space-y-1.5">
        {[1, 2, 3, 4, 5].map((i) => (
          <div key={i} className="flex items-center gap-2 rounded bg-muted/30 px-2 py-1.5">
            <div className="h-4 w-4 rounded-full bg-foreground/10" />
            <div className="h-2 flex-1 rounded bg-foreground/8" />
            <div className="h-2 w-12 rounded bg-foreground/8" />
            <div className={`h-4 w-10 rounded-full ${i % 2 === 0 ? 'bg-green-500/15' : 'bg-accent/15'}`} />
          </div>
        ))}
      </div>
    </div>
  );
}

const mockupMap: Record<string, React.FC> = {
  dashboard: MockupDashboard,
  chart: MockupChart,
  calendar: MockupCalendar,
  table: MockupTable,
};

const clientDemos = [
  {
    icon: Monitor,
    name: '机构端后台',
    desc: '功能完整的 Web 管理后台，支持多门店、多角色权限管理。',
    tags: ['React', 'Ant Design', 'TypeScript'],
  },
  {
    icon: Smartphone,
    name: '患者端小程序',
    desc: '微信小程序 + H5 双端覆盖，患者无需下载即可预约。',
    tags: ['Taro', 'NutUI', '微信小程序'],
  },
  {
    icon: Stethoscope,
    name: '医生端工作台',
    desc: '轻量高效的工作台，查看排班、管理预约、处理叫号。',
    tags: ['React', 'Ant Design', 'WebSocket'],
  },
];

/* ============================================
   Sections
   ============================================ */

function HeroSection() {
  return (
    <section className="relative overflow-hidden py-28 md:py-36">
      <div className="pointer-events-none absolute -left-32 top-0 h-[400px] w-[400px] rounded-full bg-accent-secondary/[0.03] blur-[120px]" />
      <div className="mx-auto max-w-6xl px-6">
        <motion.div
          initial="hidden"
          whileInView="visible"
          viewport={viewportOptions}
          variants={stagger}
          className="text-center"
        >
          <motion.div variants={fadeInUp} className="flex justify-center">
            <SectionLabel>产品体验</SectionLabel>
          </motion.div>
          <motion.div variants={fadeInUp} className="mt-6">
            <GradientHeading level={1}>
              亲眼看看<GradientText>系统全貌</GradientText>
            </GradientHeading>
          </motion.div>
          <motion.p variants={fadeInUp} className="mx-auto mt-6 max-w-2xl text-lg leading-relaxed text-muted-foreground">
            浏览核心功能截图，了解系统界面和交互体验。注册后可获得 14 天完整试用权限。
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

function ScreenshotsSection() {
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
              功能<GradientText>预览</GradientText>
            </GradientHeading>
          </motion.div>
        </motion.div>

        <motion.div
          initial="hidden"
          whileInView="visible"
          viewport={viewportOptions}
          variants={stagger}
          className="mt-16 grid gap-8 md:grid-cols-2"
        >
          {demoScreens.map((screen, i) => {
            const Mockup = mockupMap[screen.mockup];
            return (
              <motion.div key={i} variants={fadeInUp}>
                <Card hoverable padding="lg" className="group h-full">
                  <div className={`relative mb-6 h-48 overflow-hidden rounded-xl bg-gradient-to-br ${screen.gradient}`}>
                    <div className="absolute inset-2 rounded-lg bg-card shadow-sm">
                      {Mockup && <Mockup />}
                    </div>
                    <div className="absolute inset-0 rounded-xl border border-border/50" />
                  </div>
                  <h3 className="text-lg font-semibold text-foreground">{screen.title}</h3>
                  <p className="mt-2 text-sm leading-relaxed text-muted-foreground">{screen.desc}</p>
                </Card>
              </motion.div>
            );
          })}
        </motion.div>
      </div>
    </section>
  );
}

function VideoDemoSection() {
  return (
    <InvertedSection className="py-28">
      <div className="mx-auto max-w-4xl px-6">
        <motion.div
          initial="hidden"
          whileInView="visible"
          viewport={viewportOptions}
          variants={stagger}
          className="text-center"
        >
          <motion.h2 variants={fadeInUp} className="font-display text-3xl text-white md:text-[3.25rem]">
            产品演示视频
          </motion.h2>
          <motion.p variants={fadeInUp} className="mx-auto mt-4 max-w-xl text-lg text-white/70">
            3 分钟了解系统核心功能和使用流程。
          </motion.p>
        </motion.div>

        <motion.div
          initial="hidden"
          whileInView="visible"
          viewport={viewportOptions}
          variants={fadeInUp}
          className="mt-12"
        >
          {/* Video placeholder with wireframe UI */}
          <div className="relative aspect-video overflow-hidden rounded-2xl bg-white/5 backdrop-blur-sm">
            <div className="absolute inset-0 rounded-2xl border border-white/10" />
            {/* Fake browser chrome */}
            <div className="absolute left-0 right-0 top-0 flex h-8 items-center gap-1.5 border-b border-white/10 px-3">
              <div className="h-2 w-2 rounded-full bg-white/20" />
              <div className="h-2 w-2 rounded-full bg-white/20" />
              <div className="h-2 w-2 rounded-full bg-white/20" />
              <div className="ml-3 h-4 flex-1 rounded bg-white/5" />
            </div>
            {/* Fake dashboard content */}
            <div className="absolute inset-x-4 top-12 bottom-4 flex gap-3">
              <div className="w-1/4 space-y-2 rounded-lg bg-white/5 p-2">
                {[1, 2, 3, 4].map((i) => (
                  <div key={i} className="h-3 rounded bg-white/10" />
                ))}
              </div>
              <div className="flex-1 rounded-lg bg-white/5 p-3">
                <div className="flex gap-2">
                  <div className="h-3 w-20 rounded bg-white/10" />
                  <div className="h-3 w-12 rounded bg-accent/30" />
                </div>
                <div className="mt-3 flex items-end gap-1 h-12">
                  {[30, 50, 35, 70, 45, 60, 80, 55].map((h, i) => (
                    <div
                      key={i}
                      className="flex-1 rounded-t bg-gradient-to-t from-accent/40 to-accent/20"
                      style={{ height: `${h}%` }}
                    />
                  ))}
                </div>
              </div>
            </div>
            {/* Play button overlay */}
            <div className="absolute inset-0 flex items-center justify-center">
              <div className="flex flex-col items-center gap-3">
                <div className="flex h-16 w-16 items-center justify-center rounded-full bg-gradient-to-br from-accent to-accent-secondary shadow-accent-lg transition-transform hover:scale-105">
                  <Play className="h-6 w-6 text-white ml-0.5" />
                </div>
                <span className="text-xs text-white/50">3 分钟演示视频</span>
              </div>
            </div>
          </div>
        </motion.div>
      </div>
    </InvertedSection>
  );
}

function ClientAppsSection() {
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
            <SectionLabel>技术架构</SectionLabel>
          </motion.div>
          <motion.div variants={fadeInUp} className="mt-6">
            <GradientHeading level={2}>
              三端<GradientText>技术栈</GradientText>
            </GradientHeading>
          </motion.div>
          <motion.p variants={fadeInUp} className="mx-auto mt-4 max-w-2xl text-lg text-muted-foreground">
            现代化技术栈，TypeScript 全栈类型安全。
          </motion.p>
        </motion.div>

        <motion.div
          initial="hidden"
          whileInView="visible"
          viewport={viewportOptions}
          variants={stagger}
          className="mt-16 grid gap-6 lg:grid-cols-3"
        >
          {clientDemos.map((client, i) => (
            <motion.div key={i} variants={fadeInUp}>
              <Card hoverable padding="lg" className="group h-full">
                <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-xl bg-accent/10 text-accent transition-colors group-hover:bg-accent group-hover:text-white">
                  <client.icon className="h-6 w-6" />
                </div>
                <h3 className="text-lg font-semibold text-foreground">{client.name}</h3>
                <p className="mt-2 text-sm leading-relaxed text-muted-foreground">{client.desc}</p>
                <div className="mt-4 flex flex-wrap gap-2">
                  {client.tags.map((tag) => (
                    <span key={tag} className="rounded-full bg-muted px-3 py-1 text-xs font-medium text-muted-foreground">
                      {tag}
                    </span>
                  ))}
                </div>
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
            准备好亲自体验了吗？
          </motion.h2>
          <motion.p variants={fadeInUp} className="mx-auto mt-4 max-w-xl text-lg text-white/70">
            注册即可获得 14 天专业版免费试用，无需信用卡。
          </motion.p>
          <motion.div variants={fadeInUp} className="mt-10">
            <Link to="/register">
              <Button size="lg" icon={<ArrowRight />}>
                免费试用 14 天
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

export function Experience() {
  return (
    <>
      <SEO
        title="产品体验"
        description="浏览核心功能截图和演示视频，了解医院挂号系统的界面设计和交互体验。"
        url="/experience"
      />
      <HeroSection />
      <ScreenshotsSection />
      <VideoDemoSection />
      <ClientAppsSection />
      <CTASection />
    </>
  );
}
