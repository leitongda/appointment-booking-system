import { readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';

const currentDir = dirname(fileURLToPath(import.meta.url));
const schemaRendererPath = resolve(currentDir, '../SchemaRenderer.tsx');

describe('SchemaRenderer source guards', () => {
  it('keeps selectedNodeIds in NodeRenderer scope for multi-select rendering', () => {
    const source = readFileSync(schemaRendererPath, 'utf8');

    expect(source).toContain('const { isSelected, selectedNodeIds } = useNodeSelection(node.id);');
    expect(source).toContain('const isMultiSelected = selectedNodeIds.length > 1 && selectedNodeIds.includes(node.id);');
  });
});
