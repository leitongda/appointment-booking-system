import { theme } from 'antd';
import { getSpacingMode, SPACING_CONFIG } from '@/utils/spacing';

export function getThemeConfig(): { algorithm: typeof theme.defaultAlgorithm; tokenConfig: Record<string, number> } {
  const spacingMode = getSpacingMode();
  const spacingValues = SPACING_CONFIG[spacingMode];

  const algorithm = spacingMode === 'compact' ? theme.compactAlgorithm : theme.defaultAlgorithm;

  const tokenConfig = {
    padding: spacingValues.padding,
    paddingLG: spacingValues.padding + 8,
    paddingSM: spacingValues.padding - 4,
    paddingXS: spacingValues.padding - 8,
    margin: spacingValues.component,
    marginLG: spacingValues.section,
    marginSM: spacingValues.component - 4,
    marginXS: spacingValues.component - 8,
  };

  return { algorithm, tokenConfig };
}
