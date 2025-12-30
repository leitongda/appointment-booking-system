/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ['./src/**/*.{tsx,ts,jsx,js}'],
  theme: {
    extend: {
      colors: {
        background: '#F0FAFA',
        foreground: '#0F172A',
        muted: '#E6F4F4',
        'muted-foreground': '#64748B',
        // 医疗健康蓝绿色调
        primary: '#00A3A3',
        'primary-light': '#4DC9C9',
        'primary-dark': '#007A7A',
        'primary-foreground': '#FFFFFF',
        accent: '#00C4B4',
        'accent-secondary': '#00E5D4',
        'accent-foreground': '#FFFFFF',
        border: '#D0E8E8',
        card: '#FFFFFF',
        ring: '#00A3A3',
        success: '#10B981',
        warning: '#F59E0B',
        error: '#EF4444',
      },
      fontFamily: {
        display: ['Noto Sans SC', 'PingFang SC', 'sans-serif'],
        sans: ['Noto Sans SC', 'PingFang SC', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
      boxShadow: {
        'sm': '0 1px 3px rgba(0,0,0,0.06)',
        'md': '0 4px 6px rgba(0,0,0,0.07)',
        'lg': '0 10px 15px rgba(0,0,0,0.08)',
        'xl': '0 20px 25px rgba(0,0,0,0.1)',
        'primary': '0 4px 14px rgba(0,163,163,0.25)',
        'primary-lg': '0 8px 24px rgba(0,163,163,0.35)',
      },
      animation: {
        'pulse-dot': 'pulseDot 2s infinite',
        'float': 'float 5s ease-in-out infinite',
        'slide-up': 'slideUp 0.3s ease-out',
        'fade-in': 'fadeIn 0.3s ease-out',
        'bounce-gentle': 'bounceGentle 2s infinite',
      },
      keyframes: {
        pulseDot: {
          '0%, 100%': { transform: 'scale(1)', opacity: '1' },
          '50%': { transform: 'scale(1.3)', opacity: '0.7' },
        },
        float: {
          '0%, 100%': { transform: 'translateY(0)' },
          '50%': { transform: 'translateY(-10px)' },
        },
        slideUp: {
          '0%': { transform: 'translateY(20px)', opacity: '0' },
          '100%': { transform: 'translateY(0)', opacity: '1' },
        },
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        bounceGentle: {
          '0%, 100%': { transform: 'translateY(0)' },
          '50%': { transform: 'translateY(-5px)' },
        },
      },
    },
  },
  plugins: [],
};



