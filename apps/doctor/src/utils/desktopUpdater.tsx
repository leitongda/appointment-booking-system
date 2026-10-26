/**
 * Tauri 桌面壳自动更新（仅打包态生效；web 端与 tauri dev 直接返回）
 *
 * 流程：启动后延迟几秒静默向更新源检查（更新源见 src-tauri/tauri.conf.json plugins.updater，
 * 真实域名由 CI --config 注入）→ 有新版本则弹窗展示版本号与更新公告（latest.json 的 notes，
 * 源自 desktop-release/CHANGELOG.md 对应版本段落）→ 用户确认后下载安装 → 提示重启。
 *
 * 刻意不自动重启：医院场景正在挂号/排班操作中被强制重启是事故。「稍后」仅在本次启动内
 * 不再提示，下次启动会再次检查。Windows 下 NSIS passive 安装会由壳自行退出进程，重启提示
 * 可能不会出现，属预期。
 *
 * 零 npm 依赖：壳已开 app.withGlobalTauri，Rust 侧注册 updater/process 插件后，JS API 挂在
 * window.__TAURI__.updater / window.__TAURI__.process 上。与 @hospital/api desktop.ts 同一
 * 兼容承诺：拿不到全局对象立即返回；更新源不可达、签名不符、纯内网机构等任何失败只
 * console.warn，不打扰用户——内网机构仍走安装包手动升级。
 */
import { Modal, notification } from 'antd';
import { isTauriPackaged } from '@hospital/api';

interface UpdaterDownloadEvent {
  event: 'Started' | 'Progress' | 'Finished';
  data: { contentLength?: number; chunkLength?: number };
}

interface DesktopUpdate {
  version: string;
  currentVersion: string;
  /** latest.json 的 notes —— 更新公告正文 */
  body?: string | null;
  date?: string | null;
  downloadAndInstall: (onEvent?: (event: UpdaterDownloadEvent) => void) => Promise<void>;
}

interface TauriUpdaterGlobal {
  updater?: { check: (options?: { timeout?: number }) => Promise<DesktopUpdate | null> };
  process?: { relaunch: () => Promise<void> };
}

// 不与 @hospital/api 的 Window.__TAURI__ 声明合并（重复声明类型冲突），走局部断言
const tauriGlobal = (): TauriUpdaterGlobal | undefined =>
  typeof window === 'undefined'
    ? undefined
    : (window as unknown as { __TAURI__?: TauriUpdaterGlobal }).__TAURI__;

const CHECK_DELAY_MS = 5_000;
const CHECK_TIMEOUT_MS = 10_000;
const PROGRESS_KEY = 'desktop-update-progress';

let checkedThisLaunch = false;

const formatMb = (bytes: number) => `${(bytes / 1024 / 1024).toFixed(1)} MB`;

const downloadWithProgress = async (update: DesktopUpdate) => {
  let total = 0;
  let received = 0;
  notification.open({
    key: PROGRESS_KEY,
    message: `正在下载 v${update.version}…`,
    description: '准备中',
    duration: 0,
  });
  await update.downloadAndInstall((event) => {
    if (event.event === 'Started') {
      total = event.data.contentLength ?? 0;
      return;
    }
    if (event.event === 'Progress') {
      received += event.data.chunkLength ?? 0;
      const percent = total ? Math.min(100, Math.round((received / total) * 100)) : null;
      notification.open({
        key: PROGRESS_KEY,
        message: `正在下载 v${update.version}…`,
        description:
          percent === null ? formatMb(received) : `${percent}%（${formatMb(received)} / ${formatMb(total)}）`,
        duration: 0,
      });
      return;
    }
    notification.open({ key: PROGRESS_KEY, message: '下载完成，正在安装…', duration: 0 });
  });
  notification.destroy(PROGRESS_KEY);
};

const promptRelaunch = (update: DesktopUpdate) => {
  Modal.confirm({
    title: `v${update.version} 已安装`,
    content: '新版本将在下次启动时生效。现在重启应用吗？未保存的内容请先保存。',
    okText: '立即重启',
    cancelText: '稍后重启',
    onOk: async () => {
      try {
        await tauriGlobal()?.process?.relaunch();
      } catch (error) {
        console.warn('[desktop-updater] relaunch 失败，请手动重启应用', error);
      }
    },
  });
};

const promptUpdate = (update: DesktopUpdate) => {
  const releasedOn = update.date ? ` · 发布于 ${update.date.slice(0, 10)}` : '';
  Modal.confirm({
    title: `发现新版本 v${update.version}`,
    width: 520,
    content: (
      <div>
        <div style={{ color: 'rgba(0, 0, 0, 0.45)', marginBottom: 8 }}>
          当前版本 v{update.currentVersion}
          {releasedOn}
        </div>
        <div style={{ whiteSpace: 'pre-wrap', maxHeight: 280, overflow: 'auto' }}>
          {update.body?.trim() || '本次更新未提供说明。'}
        </div>
      </div>
    ),
    okText: '立即更新',
    cancelText: '稍后',
    onOk: async () => {
      try {
        await downloadWithProgress(update);
        promptRelaunch(update);
      } catch (error) {
        notification.destroy(PROGRESS_KEY);
        console.warn('[desktop-updater] 下载/安装失败', error);
        Modal.error({
          title: '更新失败',
          content: '下载或安装新版本时出错，可稍后重试，或联系管理员获取安装包手动升级。',
        });
      }
    },
  });
};

/**
 * 检查桌面端更新。启动时由 app.tsx 经 scheduleDesktopUpdateCheck 以 fire-and-forget 方式
 * 调用（不阻塞首屏）；manual=true 供「检查更新」菜单复用：没有新版本时也给出反馈。
 */
export const checkDesktopUpdate = async (options: { manual?: boolean } = {}): Promise<void> => {
  const { manual = false } = options;
  if (!isTauriPackaged()) return;
  if (!manual && checkedThisLaunch) return;
  checkedThisLaunch = true;

  const updater = tauriGlobal()?.updater;
  if (!updater) {
    console.warn('[desktop-updater] window.__TAURI__.updater 不可用（壳未注册 updater 插件？）');
    return;
  }

  try {
    const update = await updater.check({ timeout: CHECK_TIMEOUT_MS });
    if (!update) {
      if (manual) notification.success({ message: '已是最新版本' });
      return;
    }
    promptUpdate(update);
  } catch (error) {
    // 更新源不可达 / 签名不符 / 纯内网机构：静默，日志可查
    console.warn('[desktop-updater] 检查更新失败', error);
    if (manual) {
      notification.warning({
        message: '暂时无法检查更新',
        description: '请确认网络可访问更新服务器，或联系管理员获取安装包。',
      });
    }
  }
};

/** 启动时延迟检查，避开首屏业务请求高峰 */
export const scheduleDesktopUpdateCheck = (): void => {
  if (!isTauriPackaged()) return;
  window.setTimeout(() => {
    void checkDesktopUpdate();
  }, CHECK_DELAY_MS);
};
