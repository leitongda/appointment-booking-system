import { useEffect } from 'react';

const ADMIN_V2_URL = import.meta.env.VITE_ADMIN_URL || 'http://localhost:8006';

export function ConsoleRedirect() {
  useEffect(() => {
    window.location.href = ADMIN_V2_URL;
  }, []);

  return (
    <section className="flex min-h-[60vh] items-center justify-center">
      <p className="text-muted-foreground">正在跳转到控制台...</p>
    </section>
  );
}
