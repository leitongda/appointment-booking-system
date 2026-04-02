import { RouterProvider } from 'react-router-dom';
import { QueryClientProvider } from '@tanstack/react-query';
import { ThemeProvider } from 'next-themes';
import { Toaster } from '@/components/ui/sonner';
import { queryClient } from '@/api/query-client';
import { router } from '@/routes';
import { ThemePresetProvider } from '@/themes/theme-context';

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider attribute="class" defaultTheme="system" enableSystem>
        <ThemePresetProvider>
          <RouterProvider router={router} />
          <Toaster />
        </ThemePresetProvider>
      </ThemeProvider>
    </QueryClientProvider>
  );
}
