import { lazy, Suspense } from 'react';
import { createBrowserRouter } from 'react-router-dom';
import { RootLayout } from '@/components/layout/RootLayout';

const Home = lazy(() => import('@/pages/Home').then((m) => ({ default: m.Home })));
const Products = lazy(() => import('@/pages/Products').then((m) => ({ default: m.Products })));
const Experience = lazy(() => import('@/pages/Experience').then((m) => ({ default: m.Experience })));
const Pricing = lazy(() => import('@/pages/Pricing').then((m) => ({ default: m.Pricing })));
const Login = lazy(() => import('@/pages/Login').then((m) => ({ default: m.Login })));
const Register = lazy(() => import('@/pages/Register').then((m) => ({ default: m.Register })));
const Profile = lazy(() => import('@/pages/Profile').then((m) => ({ default: m.Profile })));
const ConsoleRedirect = lazy(() => import('@/pages/ConsoleRedirect').then((m) => ({ default: m.ConsoleRedirect })));

function PageFallback() {
  return (
    <div className="flex min-h-[60vh] items-center justify-center">
      <div className="h-8 w-8 animate-spin rounded-full border-2 border-accent border-t-transparent" />
    </div>
  );
}

export const router = createBrowserRouter([
  {
    path: '/',
    element: <RootLayout />,
    children: [
      { index: true, element: <Suspense fallback={<PageFallback />}><Home /></Suspense> },
      { path: 'products', element: <Suspense fallback={<PageFallback />}><Products /></Suspense> },
      { path: 'experience', element: <Suspense fallback={<PageFallback />}><Experience /></Suspense> },
      { path: 'pricing', element: <Suspense fallback={<PageFallback />}><Pricing /></Suspense> },
      { path: 'login', element: <Suspense fallback={<PageFallback />}><Login /></Suspense> },
      { path: 'register', element: <Suspense fallback={<PageFallback />}><Register /></Suspense> },
      { path: 'profile', element: <Suspense fallback={<PageFallback />}><Profile /></Suspense> },
      { path: 'console', element: <Suspense fallback={<PageFallback />}><ConsoleRedirect /></Suspense> },
    ],
  },
]);
