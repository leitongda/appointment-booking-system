import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import App from './App';
import { initApiConfig } from './config/api';
import './globals.css';

// 初始化 API 配置（拦截器、baseURL）
initApiConfig();

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>
);
