import { View, Image } from '@tarojs/components';

interface IconProps {
  size?: number;
  color?: string;
  className?: string;
}

// SVG 转 data URI 辅助函数
const svgToDataUri = (svg: string) => {
  const encoded = encodeURIComponent(svg)
    .replace(/'/g, '%27')
    .replace(/"/g, '%22');
  return `data:image/svg+xml,${encoded}`;
};

// 通用 SVG 图标组件
const SvgIcon = ({
  size = 24,
  color = 'currentColor',
  className = '',
  svg,
}: IconProps & { svg: string }) => {
  const svgWithColor = svg.replace(/\{color\}/g, color);
  return (
    <View
      className={className}
      style={{
        width: size,
        height: size,
        display: 'inline-flex',
        alignItems: 'center',
        justifyContent: 'center',
      }}
    >
      <Image
        src={svgToDataUri(svgWithColor)}
        style={{ width: size, height: size }}
        mode="aspectFit"
      />
    </View>
  );
};

// SVG 字符串定义
const svgs = {
  hospital: `<svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M19 3H5C3.9 3 3 3.9 3 5V19C3 20.1 3.9 21 5 21H19C20.1 21 21 20.1 21 19V5C21 3.9 20.1 3 19 3ZM13 17H11V13H7V11H11V7H13V11H17V13H13V17Z" fill="{color}"/></svg>`,
  calendar: `<svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M19 4H18V2H16V4H8V2H6V4H5C3.89 4 3 4.9 3 6V20C3 21.1 3.89 22 5 22H19C20.1 22 21 21.1 21 20V6C21 4.9 20.1 4 19 4ZM19 20H5V9H19V20ZM7 11H12V16H7V11Z" fill="{color}"/></svg>`,
  record: `<svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M14 2H6C4.9 2 4 2.9 4 4V20C4 21.1 4.9 22 6 22H18C19.1 22 20 21.1 20 20V8L14 2ZM16 18H8V16H16V18ZM16 14H8V12H16V14ZM13 9V3.5L18.5 9H13Z" fill="{color}"/></svg>`,
  user: `<svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M12 12C14.21 12 16 10.21 16 8C16 5.79 14.21 4 12 4C9.79 4 8 5.79 8 8C8 10.21 9.79 12 12 12ZM12 14C9.33 14 4 15.34 4 18V20H20V18C20 15.34 14.67 14 12 14Z" fill="{color}"/></svg>`,
  doctor: `<svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M12 2C9.79 2 8 3.79 8 6C8 8.21 9.79 10 12 10C14.21 10 16 8.21 16 6C16 3.79 14.21 2 12 2ZM12 8C10.9 8 10 7.1 10 6C10 4.9 10.9 4 12 4C13.1 4 14 4.9 14 6C14 7.1 13.1 8 12 8Z" fill="{color}"/><path d="M12 11C9.33 11 4 12.34 4 15V17H9V22H15V17H20V15C20 12.34 14.67 11 12 11Z" fill="{color}"/><path d="M11 13H13V15H15V17H13V19H11V17H9V15H11V13Z" fill="white"/></svg>`,
  search: `<svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M15.5 14H14.71L14.43 13.73C15.41 12.59 16 11.11 16 9.5C16 5.91 13.09 3 9.5 3C5.91 3 3 5.91 3 9.5C3 13.09 5.91 16 9.5 16C11.11 16 12.59 15.41 13.73 14.43L14 14.71V15.5L19 20.49L20.49 19L15.5 14ZM9.5 14C7.01 14 5 11.99 5 9.5C5 7.01 7.01 5 9.5 5C11.99 5 14 7.01 14 9.5C14 11.99 11.99 14 9.5 14Z" fill="{color}"/></svg>`,
  heart: `<svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M12 21.35L10.55 20.03C5.4 15.36 2 12.27 2 8.5C2 5.41 4.42 3 7.5 3C9.24 3 10.91 3.81 12 5.08C13.09 3.81 14.76 3 16.5 3C19.58 3 22 5.41 22 8.5C22 12.27 18.6 15.36 13.45 20.03L12 21.35Z" fill="{color}"/></svg>`,
  heartOutline: `<svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M16.5 3C14.76 3 13.09 3.81 12 5.08C10.91 3.81 9.24 3 7.5 3C4.42 3 2 5.41 2 8.5C2 12.27 5.4 15.36 10.55 20.03L12 21.35L13.45 20.03C18.6 15.36 22 12.27 22 8.5C22 5.41 19.58 3 16.5 3ZM12.1 18.55L12 18.65L11.9 18.55C7.14 14.24 4 11.39 4 8.5C4 6.5 5.5 5 7.5 5C9.04 5 10.54 5.99 11.07 7.36H12.93C13.46 5.99 14.96 5 16.5 5C18.5 5 20 6.5 20 8.5C20 11.39 16.86 14.24 12.1 18.55Z" fill="{color}"/></svg>`,
  scan: `<svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M4 6H6V4H4C2.9 4 2 4.9 2 6V8H4V6Z" fill="{color}"/><path d="M4 18H6V20H4C2.9 20 2 19.1 2 18V16H4V18Z" fill="{color}"/><path d="M20 4H18V6H20V8H22V6C22 4.9 21.1 4 20 4Z" fill="{color}"/><path d="M20 18H18V20H20C21.1 20 22 19.1 22 18V16H20V18Z" fill="{color}"/><path d="M3 11H21V13H3V11Z" fill="{color}"/><path d="M7 7H10V10H7V7Z" fill="{color}"/><path d="M14 7H17V10H14V7Z" fill="{color}"/><path d="M7 14H10V17H7V14Z" fill="{color}"/><path d="M14 14H17V17H14V14Z" fill="{color}"/></svg>`,
  card: `<svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M20 4H4C2.9 4 2 4.9 2 6V18C2 19.1 2.9 20 4 20H20C21.1 20 22 19.1 22 18V6C22 4.9 21.1 4 20 4ZM20 18H4V6H20V18Z" fill="{color}"/><path d="M4 8H20V10H4V8Z" fill="{color}"/><path d="M7 12H12V14H7V12Z" fill="{color}"/><path d="M7 15H10V16H7V15Z" fill="{color}"/></svg>`,
  addUser: `<svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M15 12C17.21 12 19 10.21 19 8C19 5.79 17.21 4 15 4C12.79 4 11 5.79 11 8C11 10.21 12.79 12 15 12ZM6 10V7H4V10H1V12H4V15H6V12H9V10H6ZM15 14C12.33 14 7 15.34 7 18V20H23V18C23 15.34 17.67 14 15 14Z" fill="{color}"/></svg>`,
  team: `<svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M16 11C17.66 11 18.99 9.66 18.99 8C18.99 6.34 17.66 5 16 5C14.34 5 13 6.34 13 8C13 9.66 14.34 11 16 11ZM8 11C9.66 11 10.99 9.66 10.99 8C10.99 6.34 9.66 5 8 5C6.34 5 5 6.34 5 8C5 9.66 6.34 11 8 11ZM8 13C5.67 13 1 14.17 1 16.5V19H15V16.5C15 14.17 10.33 13 8 13ZM16 13C15.71 13 15.38 13.02 15.03 13.05C16.19 13.89 17 15.02 17 16.5V19H23V16.5C23 14.17 18.33 13 16 13Z" fill="{color}"/></svg>`,
  bell: `<svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M12 22C13.1 22 14 21.1 14 20H10C10 21.1 10.89 22 12 22ZM18 16V11C18 7.93 16.36 5.36 13.5 4.68V4C13.5 3.17 12.83 2.5 12 2.5C11.17 2.5 10.5 3.17 10.5 4V4.68C7.63 5.36 6 7.92 6 11V16L4 18V19H20V18L18 16Z" fill="{color}"/></svg>`,
  chat: `<svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M20 2H4C2.9 2 2 2.9 2 4V22L6 18H20C21.1 18 22 17.1 22 16V4C22 2.9 21.1 2 20 2ZM6 9H18V11H6V9ZM14 14H6V12H14V14ZM18 8H6V6H18V8Z" fill="{color}"/></svg>`,
  info: `<svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M12 2C6.48 2 2 6.48 2 12C2 17.52 6.48 22 12 22C17.52 22 22 17.52 22 12C22 6.48 17.52 2 12 2ZM13 17H11V11H13V17ZM13 9H11V7H13V9Z" fill="{color}"/></svg>`,
  phone: `<svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M6.62 10.79C8.06 13.62 10.38 15.94 13.21 17.38L15.41 15.18C15.69 14.9 16.08 14.82 16.43 14.93C17.55 15.3 18.75 15.5 20 15.5C20.55 15.5 21 15.95 21 16.5V20C21 20.55 20.55 21 20 21C10.61 21 3 13.39 3 4C3 3.45 3.45 3 4 3H7.5C8.05 3 8.5 3.45 8.5 4C8.5 5.25 8.7 6.45 9.07 7.57C9.18 7.92 9.1 8.31 8.82 8.59L6.62 10.79Z" fill="{color}"/></svg>`,
  clock: `<svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M11.99 2C6.47 2 2 6.48 2 12C2 17.52 6.47 22 11.99 22C17.52 22 22 17.52 22 12C22 6.48 17.52 2 11.99 2ZM12 20C7.58 20 4 16.42 4 12C4 7.58 7.58 4 12 4C16.42 4 20 7.58 20 12C20 16.42 16.42 20 12 20ZM12.5 7H11V13L16.25 16.15L17 14.92L12.5 12.25V7Z" fill="{color}"/></svg>`,
  star: `<svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M12 17.27L18.18 21L16.54 13.97L22 9.24L14.81 8.62L12 2L9.19 8.62L2 9.24L7.45 13.97L5.82 21L12 17.27Z" fill="{color}"/></svg>`,
  surgery: `<svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M20.71 7.04C21.1 6.65 21.1 6.02 20.71 5.63L18.37 3.29C17.98 2.9 17.35 2.9 16.96 3.29L15.12 5.12L18.87 8.87L20.71 7.04Z" fill="{color}"/><path d="M3 17.25V21H6.75L17.81 9.94L14.06 6.19L3 17.25ZM5.92 19H5V18.08L14.06 9.02L14.98 9.94L5.92 19Z" fill="{color}"/></svg>`,
  baby: `<svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><circle cx="12" cy="6" r="3" fill="{color}"/><path d="M12 10C8.13 10 5 13.13 5 17V22H7V17C7 15.9 7.9 15 9 15H15C16.1 15 17 15.9 17 17V22H19V17C19 13.13 15.87 10 12 10Z" fill="{color}"/></svg>`,
  gynecology: `<svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><circle cx="12" cy="8" r="5" fill="{color}"/><path d="M11 14V19H9V21H11V23H13V21H15V19H13V14" fill="{color}"/></svg>`,
  bone: `<svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M8 4C6.9 4 6 4.9 6 6C6 6.74 6.4 7.39 7 7.73V16.27C6.4 16.61 6 17.26 6 18C6 19.1 6.9 20 8 20C9.1 20 10 19.1 10 18C10 17.26 9.6 16.61 9 16.27V7.73C9.6 7.39 10 6.74 10 6C10 4.9 9.1 4 8 4Z" fill="{color}"/><path d="M16 4C14.9 4 14 4.9 14 6C14 6.74 14.4 7.39 15 7.73V16.27C14.4 16.61 14 17.26 14 18C14 19.1 14.9 20 16 20C17.1 20 18 19.1 18 18C18 17.26 17.6 16.61 17 16.27V7.73C17.6 7.39 18 6.74 18 6C18 4.9 17.1 4 16 4Z" fill="{color}"/></svg>`,
  eye: `<svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M12 4.5C7 4.5 2.73 7.61 1 12C2.73 16.39 7 19.5 12 19.5C17 19.5 21.27 16.39 23 12C21.27 7.61 17 4.5 12 4.5ZM12 17C9.24 17 7 14.76 7 12C7 9.24 9.24 7 12 7C14.76 7 17 9.24 17 12C17 14.76 14.76 17 12 17ZM12 9C10.34 9 9 10.34 9 12C9 13.66 10.34 15 12 15C13.66 15 15 13.66 15 12C15 10.34 13.66 9 12 9Z" fill="{color}"/></svg>`,
  tooth: `<svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M12 2C10.5 2 9.2 2.5 8.2 3.2C7.2 2.5 5.9 2 4.5 2C3.1 2 2 3.1 2 4.5C2 6.5 3.5 8.5 5 10C5.5 10.5 6 12 6 14C6 16 6.5 22 9 22C11 22 11 18 12 18C13 18 13 22 15 22C17.5 22 18 16 18 14C18 12 18.5 10.5 19 10C20.5 8.5 22 6.5 22 4.5C22 3.1 20.9 2 19.5 2C18.1 2 16.8 2.5 15.8 3.2C14.8 2.5 13.5 2 12 2Z" fill="{color}"/></svg>`,
  hand: `<svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M18 12V8C18 6.9 17.1 6 16 6C14.9 6 14 6.9 14 8V3.5C14 2.67 13.33 2 12.5 2C11.67 2 11 2.67 11 3.5V8C11 6.9 10.1 6 9 6C7.9 6 7 6.9 7 8V11C7 9.9 6.1 9 5 9C3.9 9 3 9.9 3 11V17C3 20.31 5.69 23 9 23H15C18.31 23 21 20.31 21 17V15C21 13.9 20.1 13 19 13C18.45 13 17.95 13.22 17.59 13.59" fill="{color}"/></svg>`,
  ear: `<svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M17 20C17 21.1 16.1 22 15 22H14C12.9 22 12 21.1 12 20V19H10V20C10 22.21 11.79 24 14 24H15C17.21 24 19 22.21 19 20V14C19 11.8 18.5 10.4 17.2 9.3C18.4 8 19 6.4 19 4.5C19 1.5 16.5 0 14 0C11.5 0 9 1.5 9 4.5V5H11V4.5C11 3 12.5 2 14 2C15.5 2 17 3 17 4.5C17 6 16 7.5 14.5 8L13 9L14.5 10C16.5 11.5 17 12.5 17 14V20Z" fill="{color}"/></svg>`,
  brain: `<svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M13 3C13.6 3 14.2 3.2 14.7 3.5C15.5 2.6 16.6 2 17.8 2C19.5 2 21 3.2 21.5 4.9C22.4 5.4 23 6.4 23 7.5C23 8.6 22.4 9.5 21.5 10C21.8 10.5 22 11.2 22 12C22 13.5 21 14.8 19.5 15.4C19.5 17.4 17.9 19 15.9 19C15.5 19 15.2 18.9 14.8 18.8C14.3 20.1 13.1 21 11.6 21C10.1 21 8.9 20.1 8.4 18.8C8 18.9 7.6 19 7.2 19C5.2 19 3.6 17.4 3.6 15.4C2.1 14.8 1 13.5 1 12C1 11.2 1.2 10.5 1.5 10C0.6 9.5 0 8.6 0 7.5C0 6.4 0.6 5.4 1.5 4.9C2 3.2 3.5 2 5.2 2C6.4 2 7.5 2.6 8.3 3.5C8.8 3.2 9.4 3 10 3H13ZM12 5V19" stroke="{color}" stroke-width="2"/></svg>`,
  psychology: `<svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M9.5 2C6.46 2 4 4.46 4 7.5C4 9.57 5.12 11.37 6.79 12.33C5.45 13.2 4.5 14.74 4.5 16.5C4.5 19.26 6.74 21.5 9.5 21.5C11.16 21.5 12.63 20.68 13.5 19.42C14.37 20.68 15.84 21.5 17.5 21.5C20.26 21.5 22.5 19.26 22.5 16.5C22.5 14.74 21.55 13.2 20.21 12.33C21.88 11.37 23 9.57 23 7.5C23 4.46 20.54 2 17.5 2C15.84 2 14.37 2.82 13.5 4.08C12.63 2.82 11.16 2 9.5 2ZM13.5 7V16.5C13.5 16.5 13.5 19.5 9.5 19.5C7.57 19.5 6 17.93 6 16C6 14.07 7.57 12.5 9.5 12.5L10 12.5V10.5L9.5 10.5C7.57 10.5 6 8.93 6 7C6 5.07 7.57 3.5 9.5 3.5C11.43 3.5 13 5.07 13 7L13.5 7Z" fill="{color}"/></svg>`,
  herb: `<svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M17 8C17 6.07 15.21 4.5 13 4.06V2H11V4.06C8.79 4.5 7 6.07 7 8C7 10.22 9.13 12 12 12C9.13 12 7 13.78 7 16C7 17.93 8.79 19.5 11 19.94V22H13V19.94C15.21 19.5 17 17.93 17 16C17 13.78 14.87 12 12 12C14.87 12 17 10.22 17 8Z" fill="{color}"/></svg>`,
  check: `<svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M9 16.17L4.83 12L3.41 13.41L9 19L21 7L19.59 5.59L9 16.17Z" fill="{color}"/></svg>`,
  checkCircle: `<svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M12 2C6.48 2 2 6.48 2 12C2 17.52 6.48 22 12 22C17.52 22 22 17.52 22 12C22 6.48 17.52 2 12 2ZM10 17L5 12L6.41 10.59L10 14.17L17.59 6.58L19 8L10 17Z" fill="{color}"/></svg>`,
  close: `<svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M19 6.41L17.59 5L12 10.59L6.41 5L5 6.41L10.59 12L5 17.59L6.41 19L12 13.41L17.59 19L19 17.59L13.41 12L19 6.41Z" fill="{color}"/></svg>`,
  closeCircle: `<svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M12 2C6.47 2 2 6.47 2 12C2 17.53 6.47 22 12 22C17.53 22 22 17.53 22 12C22 6.47 17.53 2 12 2ZM17 15.59L15.59 17L12 13.41L8.41 17L7 15.59L10.59 12L7 8.41L8.41 7L12 10.59L15.59 7L17 8.41L13.41 12L17 15.59Z" fill="{color}"/></svg>`,
};

// 图标导出
export const HospitalIcon = (props: IconProps) => (
  <SvgIcon {...props} svg={svgs.hospital} />
);
export const CalendarIcon = (props: IconProps) => (
  <SvgIcon {...props} svg={svgs.calendar} />
);
export const RecordIcon = (props: IconProps) => (
  <SvgIcon {...props} svg={svgs.record} />
);
export const UserIcon = (props: IconProps) => (
  <SvgIcon {...props} svg={svgs.user} />
);
export const DoctorIcon = (props: IconProps) => (
  <SvgIcon {...props} svg={svgs.doctor} />
);
export const SearchIcon = (props: IconProps) => (
  <SvgIcon {...props} svg={svgs.search} />
);
export const HeartIcon = (props: IconProps) => (
  <SvgIcon {...props} svg={svgs.heart} />
);
export const HeartOutlineIcon = (props: IconProps) => (
  <SvgIcon {...props} svg={svgs.heartOutline} />
);
export const ScanIcon = (props: IconProps) => (
  <SvgIcon {...props} svg={svgs.scan} />
);
export const CardIcon = (props: IconProps) => (
  <SvgIcon {...props} svg={svgs.card} />
);
export const AddUserIcon = (props: IconProps) => (
  <SvgIcon {...props} svg={svgs.addUser} />
);
export const TeamIcon = (props: IconProps) => (
  <SvgIcon {...props} svg={svgs.team} />
);
export const BellIcon = (props: IconProps) => (
  <SvgIcon {...props} svg={svgs.bell} />
);
export const ChatIcon = (props: IconProps) => (
  <SvgIcon {...props} svg={svgs.chat} />
);
export const InfoIcon = (props: IconProps) => (
  <SvgIcon {...props} svg={svgs.info} />
);
export const PhoneIcon = (props: IconProps) => (
  <SvgIcon {...props} svg={svgs.phone} />
);
export const ClockIcon = (props: IconProps) => (
  <SvgIcon {...props} svg={svgs.clock} />
);
export const StarIcon = (props: IconProps) => (
  <SvgIcon {...props} svg={svgs.star} />
);
export const StethoscopeIcon = (props: IconProps) => (
  <SvgIcon {...props} svg={svgs.stethoscope || svgs.hospital} />
);
export const BookIcon = (props: IconProps) => (
  <SvgIcon {...props} svg={svgs.book || svgs.record} />
);
export const HealthIcon = (props: IconProps) => (
  <SvgIcon {...props} svg={svgs.health || svgs.heart} />
);
export const ServiceIcon = (props: IconProps) => (
  <SvgIcon {...props} svg={svgs.service || svgs.hospital} />
);
export const TipIcon = (props: IconProps) => (
  <SvgIcon {...props} svg={svgs.tip || svgs.info} />
);
export const FileIcon = (props: IconProps) => (
  <SvgIcon {...props} svg={svgs.file || svgs.record} />
);
export const ReportIcon = (props: IconProps) => (
  <SvgIcon {...props} svg={svgs.report || svgs.record} />
);
export const SettingsIcon = (props: IconProps) => (
  <SvgIcon {...props} svg={svgs.settings || svgs.info} />
);
export const CheckIcon = (props: IconProps) => (
  <SvgIcon {...props} svg={svgs.check} />
);
export const CheckCircleIcon = (props: IconProps) => (
  <SvgIcon {...props} svg={svgs.checkCircle} />
);
export const CloseIcon = (props: IconProps) => (
  <SvgIcon {...props} svg={svgs.close} />
);
export const CloseCircleIcon = (props: IconProps) => (
  <SvgIcon {...props} svg={svgs.closeCircle} />
);

export const BabyIcon = (props: IconProps) => (
  <SvgIcon {...props} svg={svgs.baby} />
);

// 科室图标映射
const DeptIconMap: Record<string, React.ComponentType<IconProps>> = {
  '外科': (props: IconProps) => <SvgIcon {...props} svg={svgs.surgery} />,
  '儿科': (props: IconProps) => <SvgIcon {...props} svg={svgs.baby} />,
  '妇科': (props: IconProps) => <SvgIcon {...props} svg={svgs.gynecology} />,
  '骨科': (props: IconProps) => <SvgIcon {...props} svg={svgs.bone} />,
  '眼科': (props: IconProps) => <SvgIcon {...props} svg={svgs.eye} />,
  '口腔科': (props: IconProps) => <SvgIcon {...props} svg={svgs.tooth} />,
  '皮肤科': (props: IconProps) => <SvgIcon {...props} svg={svgs.hand} />,
  '耳鼻喉科': (props: IconProps) => <SvgIcon {...props} svg={svgs.ear} />,
  '神经内科': (props: IconProps) => <SvgIcon {...props} svg={svgs.brain} />,
  '精神科': (props: IconProps) => <SvgIcon {...props} svg={svgs.psychology} />,
  '中医科': (props: IconProps) => <SvgIcon {...props} svg={svgs.herb} />,
};

export const getDeptIcon = (name: string): React.ComponentType<IconProps> => {
  for (const key in DeptIconMap) {
    if (name.includes(key.replace('科', ''))) {
      return DeptIconMap[key];
    }
  }
  return HospitalIcon;
};
