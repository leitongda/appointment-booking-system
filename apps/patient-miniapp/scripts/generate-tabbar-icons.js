const fs = require('fs');
const path = require('path');

// 简单的 PNG 图标生成器（使用纯 JavaScript 生成最小化的 PNG）
// 这些是 81x81 的简单图标

// Base64 编码的简单图标 (使用 data URL 格式的简化版本)
// 这些是简单的单色图标，适合 tabBar 使用

const assetsDir = path.join(__dirname, '../src/assets/tabbar');

// 确保目录存在
if (!fs.existsSync(assetsDir)) {
  fs.mkdirSync(assetsDir, { recursive: true });
}

// 简单的 SVG 转 PNG 函数不可用，所以我们使用预制的最小 PNG
// 这里我们创建简单的占位图标

// 创建一个简单的 81x81 PNG 图标的函数
function createSimplePNG(width, height, r, g, b, alpha = 255) {
  // PNG 文件格式
  const signature = Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]);
  
  // IHDR chunk
  const ihdrData = Buffer.alloc(13);
  ihdrData.writeUInt32BE(width, 0);
  ihdrData.writeUInt32BE(height, 4);
  ihdrData[8] = 8;  // bit depth
  ihdrData[9] = 6;  // color type (RGBA)
  ihdrData[10] = 0; // compression
  ihdrData[11] = 0; // filter
  ihdrData[12] = 0; // interlace
  
  const ihdrCrc = crc32(Buffer.concat([Buffer.from('IHDR'), ihdrData]));
  const ihdr = Buffer.alloc(12 + 13);
  ihdr.writeUInt32BE(13, 0);
  ihdr.write('IHDR', 4);
  ihdrData.copy(ihdr, 8);
  ihdr.writeUInt32BE(ihdrCrc, 21);
  
  // IDAT chunk - 创建图像数据
  const rawData = [];
  for (let y = 0; y < height; y++) {
    rawData.push(0); // filter byte
    for (let x = 0; x < width; x++) {
      rawData.push(r, g, b, alpha);
    }
  }
  
  const rawBuffer = Buffer.from(rawData);
  const compressed = deflateSync(rawBuffer);
  
  const idatCrc = crc32(Buffer.concat([Buffer.from('IDAT'), compressed]));
  const idat = Buffer.alloc(12 + compressed.length);
  idat.writeUInt32BE(compressed.length, 0);
  idat.write('IDAT', 4);
  compressed.copy(idat, 8);
  idat.writeUInt32BE(idatCrc, 8 + compressed.length);
  
  // IEND chunk
  const iendCrc = crc32(Buffer.from('IEND'));
  const iend = Buffer.alloc(12);
  iend.writeUInt32BE(0, 0);
  iend.write('IEND', 4);
  iend.writeUInt32BE(iendCrc, 8);
  
  return Buffer.concat([signature, ihdr, idat, iend]);
}

// CRC32 计算
function crc32(buf) {
  let crc = 0xffffffff;
  const table = [];
  for (let n = 0; n < 256; n++) {
    let c = n;
    for (let k = 0; k < 8; k++) {
      c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1;
    }
    table[n] = c;
  }
  for (let i = 0; i < buf.length; i++) {
    crc = table[(crc ^ buf[i]) & 0xff] ^ (crc >>> 8);
  }
  return (crc ^ 0xffffffff) >>> 0;
}

// 使用 zlib 进行压缩
const { deflateSync } = require('zlib');

// 创建带有简单图形的 PNG
function createIconPNG(width, height, iconType, isActive) {
  const rawData = [];
  const centerX = width / 2;
  const centerY = height / 2;
  const radius = width * 0.35;
  
  // 颜色设置
  const activeColor = { r: 102, g: 126, b: 234 }; // #667eea
  const inactiveColor = { r: 153, g: 153, b: 153 }; // #999
  const color = isActive ? activeColor : inactiveColor;
  
  for (let y = 0; y < height; y++) {
    rawData.push(0); // filter byte
    for (let x = 0; x < width; x++) {
      let alpha = 0;
      
      if (iconType === 'home') {
        // 房子图标：三角形屋顶 + 方形房体
        const roofTop = centerY - radius * 0.8;
        const roofBottom = centerY - radius * 0.1;
        const houseBottom = centerY + radius * 0.8;
        const houseLeft = centerX - radius * 0.6;
        const houseRight = centerX + radius * 0.6;
        
        // 三角形屋顶
        if (y >= roofTop && y <= roofBottom) {
          const roofWidth = ((y - roofTop) / (roofBottom - roofTop)) * radius * 0.8;
          if (x >= centerX - roofWidth && x <= centerX + roofWidth) {
            alpha = 255;
          }
        }
        // 方形房体
        if (y > roofBottom && y <= houseBottom) {
          if (x >= houseLeft && x <= houseRight) {
            // 门的位置（中间留空）
            const doorLeft = centerX - radius * 0.15;
            const doorRight = centerX + radius * 0.15;
            const doorTop = centerY + radius * 0.2;
            if (!(x >= doorLeft && x <= doorRight && y >= doorTop)) {
              alpha = 255;
            }
          }
        }
      } else if (iconType === 'appointment') {
        // 日历图标
        const left = centerX - radius * 0.7;
        const right = centerX + radius * 0.7;
        const top = centerY - radius * 0.6;
        const bottom = centerY + radius * 0.8;
        const headerBottom = centerY - radius * 0.2;
        
        if (x >= left && x <= right && y >= top && y <= bottom) {
          // 日历头部
          if (y <= headerBottom) {
            alpha = 255;
          } else {
            // 日历边框
            if (x <= left + 3 || x >= right - 3 || y >= bottom - 3) {
              alpha = 255;
            }
            // 日历内的点（表示日期）
            const gridSize = (right - left) / 4;
            for (let gx = 0; gx < 3; gx++) {
              for (let gy = 0; gy < 2; gy++) {
                const dotX = left + gridSize * (gx + 1);
                const dotY = headerBottom + gridSize * (gy + 0.8);
                const dist = Math.sqrt((x - dotX) ** 2 + (y - dotY) ** 2);
                if (dist < 4) {
                  alpha = 255;
                }
              }
            }
          }
        }
        // 日历顶部的两个挂钩
        const hookY = top - 8;
        const hook1X = centerX - radius * 0.35;
        const hook2X = centerX + radius * 0.35;
        if (y >= hookY && y <= top + 5) {
          if ((x >= hook1X - 3 && x <= hook1X + 3) || (x >= hook2X - 3 && x <= hook2X + 3)) {
            alpha = 255;
          }
        }
      } else if (iconType === 'profile') {
        // 用户图标：圆形头像 + 半圆身体
        const headRadius = radius * 0.35;
        const headCenterY = centerY - radius * 0.25;
        
        // 头部（圆形）
        const headDist = Math.sqrt((x - centerX) ** 2 + (y - headCenterY) ** 2);
        if (headDist <= headRadius) {
          alpha = 255;
        }
        
        // 身体（半圆/弧形）
        const bodyTop = centerY + radius * 0.15;
        const bodyRadius = radius * 0.7;
        const bodyCenterY = centerY + radius * 0.9;
        const bodyDist = Math.sqrt((x - centerX) ** 2 + (y - bodyCenterY) ** 2);
        if (y >= bodyTop && y <= centerY + radius * 0.8 && bodyDist <= bodyRadius && bodyDist >= bodyRadius - 20) {
          alpha = 255;
        }
        if (y >= bodyTop && y <= centerY + radius * 0.8 && bodyDist <= bodyRadius) {
          alpha = 255;
        }
      }
      
      rawData.push(color.r, color.g, color.b, alpha);
    }
  }
  
  const rawBuffer = Buffer.from(rawData);
  const compressed = deflateSync(rawBuffer);
  
  // PNG signature
  const signature = Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]);
  
  // IHDR chunk
  const ihdrData = Buffer.alloc(13);
  ihdrData.writeUInt32BE(width, 0);
  ihdrData.writeUInt32BE(height, 4);
  ihdrData[8] = 8;  // bit depth
  ihdrData[9] = 6;  // color type (RGBA)
  ihdrData[10] = 0; // compression
  ihdrData[11] = 0; // filter
  ihdrData[12] = 0; // interlace
  
  const ihdrCrc = crc32(Buffer.concat([Buffer.from('IHDR'), ihdrData]));
  const ihdr = Buffer.alloc(12 + 13);
  ihdr.writeUInt32BE(13, 0);
  ihdr.write('IHDR', 4);
  ihdrData.copy(ihdr, 8);
  ihdr.writeUInt32BE(ihdrCrc, 21);
  
  // IDAT chunk
  const idatCrc = crc32(Buffer.concat([Buffer.from('IDAT'), compressed]));
  const idat = Buffer.alloc(12 + compressed.length);
  idat.writeUInt32BE(compressed.length, 0);
  idat.write('IDAT', 4);
  compressed.copy(idat, 8);
  idat.writeUInt32BE(idatCrc, 8 + compressed.length);
  
  // IEND chunk
  const iendCrc = crc32(Buffer.from('IEND'));
  const iend = Buffer.alloc(12);
  iend.writeUInt32BE(0, 0);
  iend.write('IEND', 4);
  iend.writeUInt32BE(iendCrc, 8);
  
  return Buffer.concat([signature, ihdr, idat, iend]);
}

// 生成图标
const icons = [
  { name: 'home.png', type: 'home', active: false },
  { name: 'home-active.png', type: 'home', active: true },
  { name: 'appointment.png', type: 'appointment', active: false },
  { name: 'appointment-active.png', type: 'appointment', active: true },
  { name: 'profile.png', type: 'profile', active: false },
  { name: 'profile-active.png', type: 'profile', active: true },
];

icons.forEach(icon => {
  const png = createIconPNG(81, 81, icon.type, icon.active);
  const filePath = path.join(assetsDir, icon.name);
  fs.writeFileSync(filePath, png);
  console.log(`Created: ${filePath}`);
});

console.log('\nAll tabbar icons generated successfully!');

