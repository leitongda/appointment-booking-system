# 顶部 Hero 高级动效实现原理与关键代码

> 适用场景：产品官网首屏、AI 产品介绍页、数据大屏首页、科技感 Landing Page。  
> 典型效果：鼠标划过顶部 Hero 区域时，背景像被“拨开”一样露出底图，并带有柔和扩散、残影、水波或水墨感。

---

## 1. 效果本质

顶部 Hero 的高级动效，本质是：

```txt
底图层
+
内容层
+
Canvas 遮罩层
+
鼠标轨迹擦除
+
遮罩自动恢复
```

用户看到的“背景被拨开”，并不是背景真的被改变，而是：

```txt
Canvas 覆盖在 Hero 上
Canvas 上先绘制一层遮罩
鼠标经过时，用 Canvas 合成模式擦除鼠标附近区域
被擦除的地方变透明
于是露出下面的底图
```

如果每一帧再轻微补回遮罩，就会形成：

```txt
鼠标经过 -> 露出底图
鼠标离开 -> 遮罩慢慢恢复
轨迹残影 -> 水波 / 水墨扩散感
```

---

## 2. 页面分层结构

推荐的 DOM 结构如下：

```html
<section class="hero">
  <!-- 1. 底图层：真实可见的背景 -->
  <div class="hero-bg"></div>

  <!-- 2. 内容层：标题、按钮、导航等 -->
  <div class="hero-content">
    <h1>MiMo Code</h1>
    <p>面向开发者的新一代 AI 编程助手</p>
  </div>

  <!-- 3. Canvas 遮罩层：负责高级动效 -->
  <canvas id="heroMask"></canvas>
</section>
```

层级关系：

```txt
z-index: 0    hero-bg         底图 / 光效 / 水墨背景
z-index: 1    heroMask        Canvas 遮罩层
z-index: 2    hero-content    标题、按钮、正文内容
```

也可以让 `canvas` 位于最上层，但需要设置：

```css
pointer-events: none;
```

这样不会影响按钮、链接等交互。

---

## 3. 核心技术点

### 3.1 Canvas 覆盖 Hero 区域

```css
.hero {
  position: relative;
  min-height: 100vh;
  overflow: hidden;
}

#heroMask {
  position: absolute;
  inset: 0;
  z-index: 1;

  width: 100%;
  height: 100%;

  pointer-events: none;
}
```

注意：

```txt
CSS 的 width / height 只控制显示尺寸
canvas.width / canvas.height 控制实际绘制尺寸
高清屏下需要结合 devicePixelRatio 处理
```

---

### 3.2 适配高清屏

Canvas 在 Retina 屏幕上容易模糊，因此需要按 `devicePixelRatio` 放大画布。

```js
function resizeCanvas() {
  const dpr = window.devicePixelRatio || 1;
  const rect = canvas.getBoundingClientRect();

  width = rect.width;
  height = rect.height;

  canvas.width = width * dpr;
  canvas.height = height * dpr;

  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
}
```

这样后续绘制时仍然使用 CSS 像素坐标：

```js
ctx.fillRect(0, 0, width, height);
```

不用手动乘 `dpr`。

---

### 3.3 绘制遮罩层

初始化时，在 Canvas 上画一层遮罩。

```js
function drawInitialMask() {
  ctx.globalCompositeOperation = "source-over";
  ctx.fillStyle = "rgba(8, 10, 16, 0.72)";
  ctx.fillRect(0, 0, width, height);
}
```

这层遮罩就是盖在底图上的“布”。

可以是：

```txt
纯色半透明遮罩
渐变遮罩
水墨纹理图
品牌背景图
噪声图
```

---

### 3.4 使用 destination-out 擦除遮罩

这是整个效果的关键。

```js
ctx.globalCompositeOperation = "destination-out";
```

含义：

```txt
后画上去的图形，不是显示出来
而是把已有内容对应区域擦掉
```

也就是“橡皮擦”。

鼠标附近画一个圆形渐变：

```js
function eraseAt(x, y) {
  ctx.globalCompositeOperation = "destination-out";

  const radius = 160;

  const gradient = ctx.createRadialGradient(
    x,
    y,
    0,
    x,
    y,
    radius
  );

  gradient.addColorStop(0, "rgba(0, 0, 0, 0.9)");
  gradient.addColorStop(0.5, "rgba(0, 0, 0, 0.45)");
  gradient.addColorStop(1, "rgba(0, 0, 0, 0)");

  ctx.fillStyle = gradient;

  ctx.beginPath();
  ctx.arc(x, y, radius, 0, Math.PI * 2);
  ctx.fill();
}
```

视觉效果：

```txt
中心擦除最强
边缘逐渐变弱
所以露出的区域边缘柔和
```

---

## 4. 最小可运行版本

### 4.1 HTML

```html
<section class="hero">
  <div class="hero-bg"></div>

  <div class="hero-content">
    <h1>MiMo Code</h1>
    <p>面向开发者的新一代 AI 编程助手</p>
  </div>

  <canvas id="heroMask"></canvas>
</section>
```

### 4.2 CSS

```css
body {
  margin: 0;
  background: #080a10;
}

.hero {
  position: relative;
  min-height: 100vh;
  overflow: hidden;
}

.hero-bg {
  position: absolute;
  inset: 0;
  z-index: 0;

  background:
    radial-gradient(circle at 20% 25%, rgba(255, 140, 60, 0.45), transparent 24%),
    radial-gradient(circle at 80% 20%, rgba(92, 140, 255, 0.36), transparent 28%),
    radial-gradient(circle at 50% 80%, rgba(255, 255, 255, 0.16), transparent 30%),
    linear-gradient(135deg, #f4eadc, #d9c8ad 48%, #111827);
}

.hero-content {
  position: relative;
  z-index: 2;

  padding: 180px 80px;
  color: #fff;
}

.hero-content h1 {
  margin: 0 0 24px;
  font-size: 88px;
  line-height: 1;
}

.hero-content p {
  font-size: 24px;
}

#heroMask {
  position: absolute;
  inset: 0;
  z-index: 1;

  width: 100%;
  height: 100%;

  pointer-events: none;
}
```

### 4.3 JavaScript

```js
const canvas = document.getElementById("heroMask");
const ctx = canvas.getContext("2d");

let width = 0;
let height = 0;

function resizeCanvas() {
  const dpr = window.devicePixelRatio || 1;
  const rect = canvas.getBoundingClientRect();

  width = rect.width;
  height = rect.height;

  canvas.width = width * dpr;
  canvas.height = height * dpr;

  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

  drawInitialMask();
}

function drawInitialMask() {
  ctx.globalCompositeOperation = "source-over";
  ctx.fillStyle = "rgba(8, 10, 16, 0.72)";
  ctx.fillRect(0, 0, width, height);
}

function eraseAt(x, y) {
  ctx.globalCompositeOperation = "destination-out";

  const radius = 160;

  const gradient = ctx.createRadialGradient(
    x,
    y,
    0,
    x,
    y,
    radius
  );

  gradient.addColorStop(0, "rgba(0, 0, 0, 0.95)");
  gradient.addColorStop(0.45, "rgba(0, 0, 0, 0.5)");
  gradient.addColorStop(1, "rgba(0, 0, 0, 0)");

  ctx.fillStyle = gradient;

  ctx.beginPath();
  ctx.arc(x, y, radius, 0, Math.PI * 2);
  ctx.fill();
}

const hero = canvas.parentElement;

hero.addEventListener("mousemove", (event) => {
  const rect = canvas.getBoundingClientRect();

  const x = event.clientX - rect.left;
  const y = event.clientY - rect.top;

  eraseAt(x, y);
});

window.addEventListener("resize", resizeCanvas);

resizeCanvas();
```

这个版本实现的是：

```txt
鼠标经过哪里
哪里被擦开
露出下面背景
```

但它有一个特点：擦开的区域会一直保留，不会自动恢复。

---

## 5. 自动恢复版本

要实现更高级的“拨开后慢慢合拢”，需要使用 `requestAnimationFrame` 循环。

核心思路：

```txt
每一帧都画一层极淡的遮罩
旧的透明区域会慢慢被盖住
当前鼠标位置继续被擦开
```

关键代码：

```js
function animate() {
  requestAnimationFrame(animate);

  ctx.globalCompositeOperation = "source-over";

  // 恢复速度：值越大，遮罩恢复越快
  ctx.fillStyle = "rgba(8, 10, 16, 0.045)";
  ctx.fillRect(0, 0, width, height);

  if (mouse.active) {
    eraseAt(mouse.x, mouse.y);
  }
}
```

完整版本：

```js
const canvas = document.getElementById("heroMask");
const ctx = canvas.getContext("2d");

let width = 0;
let height = 0;

const mouse = {
  x: 0,
  y: 0,
  active: false,
};

function resizeCanvas() {
  const dpr = window.devicePixelRatio || 1;
  const rect = canvas.getBoundingClientRect();

  width = rect.width;
  height = rect.height;

  canvas.width = width * dpr;
  canvas.height = height * dpr;

  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

  ctx.globalCompositeOperation = "source-over";
  ctx.fillStyle = "rgba(8, 10, 16, 0.72)";
  ctx.fillRect(0, 0, width, height);
}

function eraseAt(x, y) {
  ctx.globalCompositeOperation = "destination-out";

  const radius = 150;

  const gradient = ctx.createRadialGradient(
    x,
    y,
    0,
    x,
    y,
    radius
  );

  gradient.addColorStop(0, "rgba(0, 0, 0, 0.95)");
  gradient.addColorStop(0.5, "rgba(0, 0, 0, 0.48)");
  gradient.addColorStop(1, "rgba(0, 0, 0, 0)");

  ctx.fillStyle = gradient;

  ctx.beginPath();
  ctx.arc(x, y, radius, 0, Math.PI * 2);
  ctx.fill();
}

function animate() {
  requestAnimationFrame(animate);

  ctx.globalCompositeOperation = "source-over";
  ctx.fillStyle = "rgba(8, 10, 16, 0.045)";
  ctx.fillRect(0, 0, width, height);

  if (mouse.active) {
    eraseAt(mouse.x, mouse.y);
  }
}

const hero = canvas.parentElement;

hero.addEventListener("mousemove", (event) => {
  const rect = canvas.getBoundingClientRect();

  mouse.x = event.clientX - rect.left;
  mouse.y = event.clientY - rect.top;
  mouse.active = true;
});

hero.addEventListener("mouseleave", () => {
  mouse.active = false;
});

window.addEventListener("resize", resizeCanvas);

resizeCanvas();
animate();
```

---

## 6. 水波 / 水墨扩散版本

如果只擦当前鼠标点，效果像“聚光灯”。

如果要做高级感，需要引入轨迹点数组。

每个点包含：

```ts
interface RipplePoint {
  x: number;
  y: number;
  radius: number;
  alpha: number;
  life: number;
}
```

每次鼠标移动时添加一个点：

```js
function addPoint(x, y) {
  points.push({
    x,
    y,
    radius: 32,
    alpha: 1,
    life: 1,
  });
}
```

每一帧：

```txt
1. 轻微补回遮罩
2. 绘制所有轨迹点
3. 每个点半径变大
4. 每个点透明度降低
5. 生命周期结束后删除
```

关键代码：

```js
const points = [];

function drawPoint(point) {
  ctx.globalCompositeOperation = "destination-out";

  const gradient = ctx.createRadialGradient(
    point.x,
    point.y,
    0,
    point.x,
    point.y,
    point.radius
  );

  gradient.addColorStop(0, `rgba(0, 0, 0, ${point.alpha})`);
  gradient.addColorStop(0.55, `rgba(0, 0, 0, ${point.alpha * 0.45})`);
  gradient.addColorStop(1, "rgba(0, 0, 0, 0)");

  ctx.fillStyle = gradient;

  ctx.beginPath();
  ctx.arc(point.x, point.y, point.radius, 0, Math.PI * 2);
  ctx.fill();
}

function animate() {
  requestAnimationFrame(animate);

  ctx.globalCompositeOperation = "source-over";
  ctx.fillStyle = "rgba(8, 10, 16, 0.055)";
  ctx.fillRect(0, 0, width, height);

  for (const point of points) {
    drawPoint(point);

    point.radius += 2.6;
    point.alpha *= 0.94;
    point.life -= 0.018;
  }

  for (let i = points.length - 1; i >= 0; i--) {
    if (points[i].life <= 0 || points[i].alpha < 0.025) {
      points.splice(i, 1);
    }
  }
}
```

鼠标监听：

```js
hero.addEventListener("mousemove", (event) => {
  const rect = canvas.getBoundingClientRect();

  addPoint(
    event.clientX - rect.left,
    event.clientY - rect.top
  );
});
```

这个版本效果更接近：

```txt
鼠标经过
产生一串柔和扩散的透明点
点逐渐扩大并消失
遮罩逐渐恢复
形成水波 / 水墨拨开的高级感
```

---

## 7. React 组件封装

下面是适合 React / Vite / Umi 项目的封装版本。

```tsx
import { useEffect, useRef } from "react";

interface RipplePoint {
  x: number;
  y: number;
  radius: number;
  alpha: number;
  life: number;
}

export function HeroMaskCanvas() {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const pointsRef = useRef<RipplePoint[]>([]);
  const frameRef = useRef<number | null>(null);

  useEffect(() => {
    const canvas = canvasRef.current;

    if (!canvas) return;

    const ctx = canvas.getContext("2d");

    if (!ctx) return;

    let width = 0;
    let height = 0;

    const resizeCanvas = () => {
      const dpr = window.devicePixelRatio || 1;
      const rect = canvas.getBoundingClientRect();

      width = rect.width;
      height = rect.height;

      canvas.width = width * dpr;
      canvas.height = height * dpr;

      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

      ctx.globalCompositeOperation = "source-over";
      ctx.fillStyle = "rgba(8, 10, 16, 0.72)";
      ctx.fillRect(0, 0, width, height);
    };

    const drawErasePoint = (point: RipplePoint) => {
      ctx.globalCompositeOperation = "destination-out";

      const gradient = ctx.createRadialGradient(
        point.x,
        point.y,
        0,
        point.x,
        point.y,
        point.radius
      );

      gradient.addColorStop(0, `rgba(0, 0, 0, ${point.alpha})`);
      gradient.addColorStop(0.5, `rgba(0, 0, 0, ${point.alpha * 0.45})`);
      gradient.addColorStop(1, "rgba(0, 0, 0, 0)");

      ctx.fillStyle = gradient;

      ctx.beginPath();
      ctx.arc(point.x, point.y, point.radius, 0, Math.PI * 2);
      ctx.fill();
    };

    const animate = () => {
      frameRef.current = requestAnimationFrame(animate);

      ctx.globalCompositeOperation = "source-over";

      // 遮罩恢复速度，值越大恢复越快
      ctx.fillStyle = "rgba(8, 10, 16, 0.052)";
      ctx.fillRect(0, 0, width, height);

      const points = pointsRef.current;

      for (const point of points) {
        drawErasePoint(point);

        point.radius += 2.6;
        point.alpha *= 0.94;
        point.life -= 0.018;
      }

      pointsRef.current = points.filter((point) => {
        return point.life > 0 && point.alpha > 0.025;
      });
    };

    const handleMouseMove = (event: MouseEvent) => {
      const rect = canvas.getBoundingClientRect();

      pointsRef.current.push({
        x: event.clientX - rect.left,
        y: event.clientY - rect.top,
        radius: 32,
        alpha: 1,
        life: 1,
      });
    };

    resizeCanvas();
    animate();

    const heroElement = canvas.parentElement;

    heroElement?.addEventListener("mousemove", handleMouseMove);
    window.addEventListener("resize", resizeCanvas);

    return () => {
      if (frameRef.current) {
        cancelAnimationFrame(frameRef.current);
      }

      heroElement?.removeEventListener("mousemove", handleMouseMove);
      window.removeEventListener("resize", resizeCanvas);
    };
  }, []);

  return <canvas id="heroMask" ref={canvasRef} className="hero-mask-canvas" />;
}
```

配套 CSS：

```css
.hero {
  position: relative;
  min-height: 100vh;
  overflow: hidden;
}

.hero-mask-canvas {
  position: absolute;
  inset: 0;
  z-index: 1;

  width: 100%;
  height: 100%;

  pointer-events: none;
}

.hero-content {
  position: relative;
  z-index: 2;
}
```

---

## 8. 参数调优

| 参数 | 作用 | 推荐值 |
|---|---|---:|
| `maskAlpha` | 初始遮罩浓度 | `0.6 ~ 0.8` |
| `restoreAlpha` | 每帧恢复速度 | `0.03 ~ 0.08` |
| `radius` | 初始擦除半径 | `24 ~ 48` |
| `radiusGrow` | 波纹扩散速度 | `1.8 ~ 3.5` |
| `alphaDecay` | 透明点衰减速度 | `0.92 ~ 0.97` |
| `lifeDecay` | 点生命周期 | `0.012 ~ 0.026` |
| `dpr` | 高清屏适配 | `window.devicePixelRatio` |

### 轻柔拨开

```js
const config = {
  restoreAlpha: 0.035,
  radius: 40,
  radiusGrow: 2.2,
  alphaDecay: 0.96,
  lifeDecay: 0.014,
};
```

### 水波扩散

```js
const config = {
  restoreAlpha: 0.06,
  radius: 24,
  radiusGrow: 4,
  alphaDecay: 0.92,
  lifeDecay: 0.022,
};
```

### 聚光灯露出

```js
const config = {
  restoreAlpha: 0.02,
  radius: 120,
  radiusGrow: 0,
  alphaDecay: 1,
  lifeDecay: 0.01,
};
```

---

## 9. 进一步增强高级感

### 9.1 使用图片作为遮罩纹理

不是每帧画纯色，而是画一张水墨纹理图。

```js
const maskImage = new Image();
maskImage.src = "/assets/hero-mask-texture.webp";

maskImage.onload = () => {
  ctx.drawImage(maskImage, 0, 0, width, height);
};
```

动画中也可以轻微补回这张图：

```js
ctx.globalCompositeOperation = "source-over";
ctx.globalAlpha = 0.04;
ctx.drawImage(maskImage, 0, 0, width, height);
ctx.globalAlpha = 1;
```

这样效果会更像：

```txt
水墨扩散
纸张纹理
雾面遮罩
高级品牌视觉
```

---

### 9.2 给轨迹点添加随机扰动

```js
function random(min, max) {
  return Math.random() * (max - min) + min;
}

function addNaturalPoint(x, y) {
  points.push({
    x: x + random(-12, 12),
    y: y + random(-8, 8),
    radius: random(24, 48),
    alpha: random(0.65, 1),
    life: 1,
  });
}
```

目的：

```txt
避免圆形太完美
让边缘更自然
更接近水墨 / 雾气扩散
```

---

### 9.3 根据鼠标速度调整半径

```js
let lastX = 0;
let lastY = 0;

function handleMouseMove(event) {
  const rect = canvas.getBoundingClientRect();

  const x = event.clientX - rect.left;
  const y = event.clientY - rect.top;

  const speed = Math.hypot(x - lastX, y - lastY);
  const radius = Math.min(80, 28 + speed * 0.35);

  points.push({
    x,
    y,
    radius,
    alpha: 1,
    life: 1,
  });

  lastX = x;
  lastY = y;
}
```

效果：

```txt
鼠标移动越快
拨开的区域越大
动效更有“流体惯性”
```

---

### 9.4 控制轨迹点数量

为了避免长时间移动鼠标导致点数量过多，需要限制数组长度。

```js
const MAX_POINTS = 80;

function addPoint(x, y) {
  points.push({
    x,
    y,
    radius: 32,
    alpha: 1,
    life: 1,
  });

  if (points.length > MAX_POINTS) {
    points.shift();
  }
}
```

---

## 10. 性能注意事项

### 10.1 不要在 mousemove 里做复杂绘制

推荐：

```txt
mousemove 只记录数据
requestAnimationFrame 统一绘制
```

不推荐：

```txt
mousemove 触发一次就完整重绘一次复杂画面
```

---

### 10.2 控制 Canvas 尺寸

如果只需要顶部区域效果，不要让 Canvas 覆盖整个页面。

推荐：

```txt
只覆盖 Hero 区域
或者只覆盖 Header + Hero 顶部区域
```

---

### 10.3 移动端降级

移动端没有鼠标 hover，建议：

```txt
关闭 heroMask
改成静态背景
或者点击 / touchmove 时触发较轻量效果
```

```css
@media (max-width: 768px) {
  .hero-mask-canvas {
    display: none;
  }
}
```

---

### 10.4 尊重用户减少动画设置

```js
const prefersReducedMotion = window.matchMedia(
  "(prefers-reduced-motion: reduce)"
).matches;

if (prefersReducedMotion) {
  // 不启用动画循环
}
```

---

## 11. 推荐实施方案

### 第一阶段：基础版

实现目标：

```txt
Canvas 覆盖 Hero
绘制半透明遮罩
鼠标划过擦除遮罩
露出底图
```

技术点：

```txt
canvas
getContext("2d")
globalCompositeOperation = "destination-out"
createRadialGradient
mousemove
```

---

### 第二阶段：高级版

实现目标：

```txt
遮罩自动恢复
鼠标轨迹残影
柔和水波扩散
```

技术点：

```txt
requestAnimationFrame
轨迹点数组
radius / alpha / life 衰减
source-over 恢复遮罩
destination-out 擦除遮罩
```

---

### 第三阶段：品牌视觉版

实现目标：

```txt
水墨 / 雾气 / 品牌质感
更接近高级官网
```

技术点：

```txt
遮罩纹理图片
随机扰动
速度影响半径
噪声纹理
限制轨迹点数量
移动端降级
```

---

## 12. 最终核心代码

整个效果最核心的代码其实只有两组。

### 12.1 恢复遮罩

```js
ctx.globalCompositeOperation = "source-over";
ctx.fillStyle = "rgba(8, 10, 16, 0.052)";
ctx.fillRect(0, 0, width, height);
```

含义：

```txt
每一帧补回一点遮罩
让旧的擦除痕迹慢慢消失
```

### 12.2 擦除遮罩

```js
ctx.globalCompositeOperation = "destination-out";

const gradient = ctx.createRadialGradient(
  x,
  y,
  0,
  x,
  y,
  radius
);

gradient.addColorStop(0, `rgba(0, 0, 0, ${alpha})`);
gradient.addColorStop(0.5, `rgba(0, 0, 0, ${alpha * 0.45})`);
gradient.addColorStop(1, "rgba(0, 0, 0, 0)");

ctx.fillStyle = gradient;

ctx.beginPath();
ctx.arc(x, y, radius, 0, Math.PI * 2);
ctx.fill();
```

含义：

```txt
用径向渐变圆擦除遮罩
中心擦除强
边缘擦除弱
所以露出区域柔和自然
```

---

## 13. 一句话总结

顶部 Hero 高级动效的核心是：

```txt
用 Canvas 盖一层遮罩，
再用 destination-out 根据鼠标轨迹擦除遮罩，
通过 requestAnimationFrame 持续补回遮罩并让轨迹点扩散衰减，
最终形成“鼠标拨开背景、水波扩散、遮罩慢慢恢复”的高级视觉效果。
```
