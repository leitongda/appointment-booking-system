import { createBrowserRouter, Navigate } from 'react-router-dom';
import { AuthGuard } from '@/auth/auth-guard';
import AdminLayout from '@/layout/AdminLayout';
import LoginPage from '@/pages/login';
import DashboardPage from '@/pages/dashboard';
import NotFoundPage from '@/pages/not-found';

export const router = createBrowserRouter([
  {
    path: '/login',
    element: <LoginPage />,
  },
  {
    path: '/404',
    element: <NotFoundPage />,
  },
  {
    element: (
      <AuthGuard>
        <AdminLayout />
      </AuthGuard>
    ),
    children: [
      {
        index: true,
        element: <Navigate to="/dashboard" replace />,
      },
      {
        path: '/dashboard',
        element: <DashboardPage />,
      },
    ],
  },
  {
    path: '*',
    element: <Navigate to="/404" replace />,
  },
]);
