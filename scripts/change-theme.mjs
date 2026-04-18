#!/usr/bin/env node

/**
 * Deprecated theme switch script.
 *
 * The patient miniapp now uses runtime themes driven by shared constants in:
 *   packages/shared/src/constants/miniapp-theme.ts
 *
 * To change available themes or default mappings, update the shared constants
 * instead of mutating generated style/config files with this script.
 */

console.error(
  [
    'The theme switch script is deprecated.',
    'Update packages/shared/src/constants/miniapp-theme.ts instead.',
    'The patient miniapp theme now comes from shared runtime presets.',
  ].join('\n')
);

process.exitCode = 1;
