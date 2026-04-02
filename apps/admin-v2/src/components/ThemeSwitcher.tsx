import { Check } from 'lucide-react';
import { useThemePreset } from '@/themes/theme-context';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';

export function ThemeSwitcher() {
  const { themeName, setTheme, presets } = useThemePreset();

  return (
    <Popover>
      <PopoverTrigger asChild>
        <Button variant="ghost" size="icon" title="切换颜色主题">
          <div
            className="h-5 w-5 rounded-full border-2 border-border"
            style={{ backgroundColor: `oklch(0.55 0.2 ${presets.find(p => p.name === themeName)?.cssVars.light.primary?.match(/oklch\([^)]+\)/)?.[0] ? '' : '262'} 0)` }}
          />
          <span className="sr-only">切换颜色主题</span>
        </Button>
      </PopoverTrigger>
      <PopoverContent align="end" className="w-64 p-3">
        <div className="mb-2 text-sm font-medium">选择主题</div>
        <div className="grid grid-cols-2 gap-1.5">
          {presets.map(preset => {
            const primaryColor = preset.cssVars.light.primary;
            return (
              <button
                key={preset.name}
                onClick={() => setTheme(preset.name)}
                className={cn(
                  'flex items-center gap-2 rounded-md px-2 py-1.5 text-sm hover:bg-accent transition-colors w-full text-left',
                  themeName === preset.name && 'bg-accent'
                )}
              >
                <span
                  className="inline-block h-4 w-4 rounded-full shrink-0 border border-border"
                  style={{ backgroundColor: primaryColor }}
                />
                <span className="truncate">{preset.label}</span>
                {themeName === preset.name && (
                  <Check className="h-3.5 w-3.5 ml-auto shrink-0 text-primary" />
                )}
              </button>
            );
          })}
        </div>
      </PopoverContent>
    </Popover>
  );
}
