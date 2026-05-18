import { Link } from 'react-router-dom';

export function Footer() {
  return (
    <footer role="contentinfo" className="border-t border-border bg-card">
      <div className="mx-auto max-w-6xl px-6 py-12">
        <div className="flex flex-col items-center justify-between gap-4 md:flex-row">
          <p className="text-sm text-muted-foreground">
            &copy; {new Date().getFullYear()} 医院挂号系统. All rights reserved.
          </p>
          <div className="flex gap-6">
            <Link to="/products" className="text-sm text-muted-foreground hover:text-foreground">
              产品
            </Link>
            <Link to="/pricing" className="text-sm text-muted-foreground hover:text-foreground">
              定价
            </Link>
            <Link to="/login" className="text-sm text-muted-foreground hover:text-foreground">
              登录
            </Link>
          </div>
        </div>
      </div>
    </footer>
  );
}
