import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { setupAuthInterceptor } from './lib/auth';
import App from './App';
import './globals.css';

setupAuthInterceptor();

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
