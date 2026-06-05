/**
 * Taro Page Generator - Unit Tests
 *
 * Tests the exported functions from page-generator.ts:
 * generatePage, generateImports, generateState, generateEffects,
 * generateEventHandlers, generateJsx.
 */

import { describe, it, expect } from 'vitest';
import {
  generatePage,
  generateImports,
  generateState,
  generateEffects,
  generateEventHandlers,
  generateJsx,
  type StateVariable,
} from '../generators/taro/page-generator';
import type {
  LowCodeSchema,
  LowCodeNode,
  ApiDataSource,
  EventHandler,
} from '@hospital/shared/types/lowcode';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Build a minimal LowCodeNode */
function node(
  id: string,
  componentName: string,
  props: Record<string, any> = {},
  extras: Partial<LowCodeNode> = {},
): LowCodeNode {
  return { id, componentName, props, ...extras };
}

/** Build a Page schema root */
function pageSchema(
  children: LowCodeNode[],
  props: Record<string, any> = { navigationBarTitleText: 'Test' },
): LowCodeSchema {
  return { componentName: 'Page', props, children };
}

/** Build a data source with sensible defaults */
function ds(overrides: Partial<ApiDataSource> & { id: string; url: string }): ApiDataSource {
  return { method: 'GET', ...overrides };
}

// =========================================================================
// Test Suite
// =========================================================================

describe('taro-generator', () => {
  // ---------------------------------------------------------------
  // 1. Simple page with one text component generates valid TSX
  // ---------------------------------------------------------------
  describe('1) Simple page with one text component', () => {
    it('generates valid TSX with Text child inside View', () => {
      const schema = pageSchema([node('t1', 'NutText', { text: 'Hello' })]);
      const output = generatePage(schema);

      // Should import Text from @tarojs/components (View is always included too)
      expect(output).toMatch(/import \{[^}]*Text[^}]*\} from '@tarojs\/components'/);

      // JSX should contain <Text> tag with the text content
      expect(output).toContain('<Text>');
      expect(output).toContain('Hello');
      expect(output).toContain('</Text>');

      // Page wrapper
      expect(output).toContain('<View className="page">');
      expect(output).toContain('</View>');
    });
  });

  // ---------------------------------------------------------------
  // 2. Page with multiple components generates correct nesting
  // ---------------------------------------------------------------
  describe('2) Page with multiple components - correct nesting', () => {
    it('nests children inside parent View', () => {
      const schema = pageSchema([
        node('v1', 'NutView', {}, {
          children: [
            node('t1', 'NutText', { text: 'Title' }),
            node('b1', 'NutButton', { text: 'Click' }),
          ],
        }),
      ]);
      const output = generatePage(schema);

      // Both View and Text should be imported from @tarojs/components
      expect(output).toContain("import { Button } from '@nutui/nutui-react-taro'");
      expect(output).toMatch(/import \{[^}]*Text[^}]*\} from '@tarojs\/components'/);
      expect(output).toMatch(/import \{[^}]*View[^}]*\} from '@tarojs\/components'/);

      // NutText content becomes child of Text
      expect(output).toContain('<Text>');
      expect(output).toContain('Title');

      // NutButton content becomes child of Button
      expect(output).toContain('<Button>');
      expect(output).toContain('Click');
    });
  });

  // ---------------------------------------------------------------
  // 3. Page with data source generates useState and useEffect
  // ---------------------------------------------------------------
  describe('3) Page with data source - useState and useEffect', () => {
    it('generates state variables and fetch effect', () => {
      const dataSources: ApiDataSource[] = [
        ds({
          id: 'doctors',
          url: '/api/v1/doctors',
          method: 'GET',
        }),
      ];
      const schema = pageSchema([node('t1', 'NutText', { text: 'list' })]);
      const output = generatePage(schema, dataSources);

      // Should generate useState for the data store and loading flag
      expect(output).toContain('const [doctorsData, setDoctorsData] = useState<any>(null)');
      expect(output).toContain('const [doctorsLoading, setDoctorsLoading] = useState<boolean>(false)');

      // Should generate a fetch callback
      expect(output).toContain('const fetchDoctors = useCallback(async () => {');

      // Should generate useEffect with auto-fetch
      expect(output).toContain('useEffect(() => {');
      expect(output).toContain('fetchDoctors();');

      // Should call Taro.request
      expect(output).toContain("Taro.request({");
      expect(output).toContain("method: 'GET'");
      expect(output).toContain("url: '/api/v1/doctors'");
    });
  });

  // ---------------------------------------------------------------
  // 4. Page with loop generates .map() call
  // ---------------------------------------------------------------
  describe('4) Page with loop - .map() call', () => {
    it('generates .map() for loop-rendered nodes', () => {
      const schema = pageSchema([
        node('list1', 'NutCell', {}, {
          loop: {
            dataSource: '{{api.doctors.data}}',
            itemName: 'doc',
            indexName: 'i',
          },
          children: [node('name1', 'NutText', { text: 'item name' })],
        }),
      ]);
      const output = generatePage(schema);

      // Should produce a .map() call
      expect(output).toContain('.map((doc, i) => (');

      // Should use React.Fragment with key
      expect(output).toContain('<React.Fragment key={i}>');
      expect(output).toContain('</React.Fragment>');

      // The data source expression should be resolved
      expect(output).toContain('apiData.doctors.data');
    });
  });

  // ---------------------------------------------------------------
  // 5. Page with conditional rendering generates ternary / guard
  // ---------------------------------------------------------------
  describe('5) Page with conditional rendering - visible guard', () => {
    it('generates conditional wrapper for visible nodes', () => {
      const schema = pageSchema([
        node('hdr', 'NutText', { text: 'Header' }, {
          visible: '{{state.showHeader}}',
        }),
      ]);
      const output = generatePage(schema);

      // Should wrap with a guard expression using &&
      // resolveExpression converts {{state.showHeader}} -> ${state.showHeader}
      expect(output).toContain('${state.showHeader}');
      expect(output).toContain('&&');
      expect(output).toContain('<Text>');
      expect(output).toContain('Header');
    });
  });

  // ---------------------------------------------------------------
  // 6. Page with events generates handler functions
  // ---------------------------------------------------------------
  describe('6) Page with events - handler functions', () => {
    it('generates useCallback handler bound to the event', () => {
      const events: EventHandler[] = [
        {
          event: 'onClick',
          actions: [
            { type: 'navigate', payload: { url: '/pages/detail/index' } },
          ],
        },
      ];
      const schema = pageSchema([
        node('btn1', 'NutButton', { text: 'Go' }, { events }),
      ]);
      const output = generatePage(schema);

      // Should generate a handler function
      expect(output).toMatch(/const handleBtn1Click = useCallback\(\(\) => \{/);

      // Should contain the navigate action
      expect(output).toContain("Taro.navigateTo({ url: '/pages/detail/index' })");

      // Should bind the handler in JSX
      expect(output).toContain('onClick={handleBtn1Click}');
    });
  });

  // ---------------------------------------------------------------
  // 7. Import deduplication works correctly
  // ---------------------------------------------------------------
  describe('7) Import deduplication', () => {
    it('deduplicates components that map to the same import', () => {
      const schema = pageSchema([
        node('v1', 'NutView', {}, {
          children: [
            node('v2', 'NutView', {}, {
              children: [node('t1', 'NutText', { text: 'nested' })],
            }),
          ],
        }),
      ]);
      const imports = generateImports(
        new Set(['Page', 'NutView', 'NutText', 'NutView']),
      );

      // There should be exactly one @tarojs/components import line
      const taroImportLines = imports.match(/import \{[^}]+\} from '@tarojs\/components'/g);
      expect(taroImportLines).toHaveLength(1);

      // Both Text and View should be on the same line (sorted alphabetically)
      expect(taroImportLines![0]).toContain('Text');
      expect(taroImportLines![0]).toContain('View');
    });
  });

  // ---------------------------------------------------------------
  // 8. NutUI components get correct import path
  // ---------------------------------------------------------------
  describe('8) NutUI components - correct import path', () => {
    it('maps NutUI components to @nutui/nutui-react-taro', () => {
      const schema = pageSchema([
        node('tabs1', 'NutTabs', {}, {
          children: [
            node('pane1', 'NutTabPane', { title: 'Tab 1' }),
            node('pane2', 'NutTabPane', { title: 'Tab 2' }),
          ],
        }),
        node('cell1', 'NutCell', { title: 'A cell' }),
        node('card1', 'NutCard', { title: 'Card title' }),
      ]);
      const output = generatePage(schema);

      // All NutUI components should come from @nutui/nutui-react-taro
      expect(output).toContain("from '@nutui/nutui-react-taro'");
      expect(output).toContain('Cell');
      expect(output).toContain('Card');
      expect(output).toContain('Tabs');
      expect(output).toContain('TabPane');

      // Should NOT import NutUI components from @tarojs/components
      const taroImport = output
        .split('\n')
        .find((l) => l.includes("from '@tarojs/components'"));
      expect(taroImport).toBeDefined();
      expect(taroImport).not.toContain('Cell');
      expect(taroImport).not.toContain('Card');
      expect(taroImport).not.toContain('Tabs');
    });
  });

  // ---------------------------------------------------------------
  // 9. Complex page with 5+ nesting levels generates valid code
  // ---------------------------------------------------------------
  describe('9) Complex page with 5+ nesting levels', () => {
    it('generates valid code for deeply nested structures', () => {
      // Build 6 levels: Page > View > View > View > View > View > Text
      const level6 = node('L6', 'NutView', {}, {
        children: [node('txt', 'NutText', { text: 'Deep leaf' })],
      });
      const level5 = node('L5', 'NutView', {}, { children: [level6] });
      const level4 = node('L4', 'NutView', {}, { children: [level5] });
      const level3 = node('L3', 'NutView', {}, { children: [level4] });
      const level2 = node('L2', 'NutView', {}, { children: [level3] });
      const level1 = node('L1', 'NutView', {}, { children: [level2] });

      const schema = pageSchema([level1]);
      const output = generatePage(schema);

      // Output should contain all 6 levels of View tags
      const viewOpenTags = output.match(/<View/g) || [];
      // 6 nested + 1 page wrapper = 7
      expect(viewOpenTags.length).toBeGreaterThanOrEqual(7);

      // The leaf text should be present
      expect(output).toContain('Deep leaf');

      // Output should still be structurally valid (has function export)
      expect(output).toContain('export default function Page()');
      expect(output).toContain('return (');
    });
  });

  // ---------------------------------------------------------------
  // 10. Output includes auto-generated header
  // ---------------------------------------------------------------
  describe('10) Output includes auto-generated header', () => {
    it('starts with the standard header comments', () => {
      const schema = pageSchema([]);
      const output = generatePage(schema);

      expect(output).toMatch(/^\/\/ Auto-generated by lowcode codegen/);
      expect(output).toContain('// Do not edit manually');
      expect(output).toContain('// Generated at:');
    });
  });

  // ---------------------------------------------------------------
  // Sub-function tests: generateState
  // ---------------------------------------------------------------
  describe('generateState', () => {
    it('returns empty code when no dataSources and no stateSchema', () => {
      const { code } = generateState([], {});
      expect(code).toBe('');
    });

    it('generates page state variables from stateSchema', () => {
      const stateSchema: Record<string, StateVariable> = {
        count: { type: 'number', defaultValue: 0, label: 'Count' },
        name: { type: 'string', defaultValue: 'test', label: 'Name' },
      };
      const { code } = generateState([], stateSchema);

      expect(code).toContain('const [count, setCount] = useState(0)');
      expect(code).toContain("const [name, setName] = useState(\"test\")");
    });

    it('generates API data store states and returns correct apiStateNames map', () => {
      const dataSources: ApiDataSource[] = [
        ds({ id: 'users', url: '/api/users' }),
      ];
      const { code, apiStateNames } = generateState(dataSources);

      expect(code).toContain('const [usersData, setUsersData] = useState<any>(null)');
      expect(code).toContain('const [usersLoading, setUsersLoading] = useState<boolean>(false)');
      expect(apiStateNames.get('users')).toBe('usersData');
    });
  });

  // ---------------------------------------------------------------
  // Sub-function tests: generateEffects
  // ---------------------------------------------------------------
  describe('generateEffects', () => {
    it('returns empty string when no dataSources', () => {
      const output = generateEffects([], new Map());
      expect(output).toBe('');
    });

    it('generates fetch function and useEffect for auto sources', () => {
      const dataSources: ApiDataSource[] = [
        ds({ id: 'list', url: '/api/list', method: 'GET' }),
      ];
      const apiStateNames = new Map([['list', 'listData']]);
      const output = generateEffects(dataSources, apiStateNames);

      expect(output).toContain('const fetchList = useCallback(async () => {');
      expect(output).toContain('setListLoading(true)');
      expect(output).toContain('setListData(res.data)');
      expect(output).toContain('setListLoading(false)');
      expect(output).toContain('useEffect(() => {');
      expect(output).toContain('fetchList();');
    });

    it('does not auto-fetch manual data sources', () => {
      const dataSources: ApiDataSource[] = [
        ds({ id: 'search', url: '/api/search', manual: true }),
      ];
      const apiStateNames = new Map([['search', 'searchData']]);
      const output = generateEffects(dataSources, apiStateNames);

      // Should have fetch function but no useEffect auto-fetch block
      expect(output).toContain('const fetchSearch = useCallback(async () => {');
      expect(output).not.toMatch(/useEffect\(\(\) => \{[^}]*fetchSearch/);
    });
  });

  // ---------------------------------------------------------------
  // Sub-function tests: generateEventHandlers
  // ---------------------------------------------------------------
  describe('generateEventHandlers', () => {
    it('generates handler with multiple action types', () => {
      const events: EventHandler[] = [
        {
          event: 'onTap',
          actions: [
            { type: 'showToast', payload: { title: 'Done', icon: 'success' } },
            { type: 'setData', payload: { key: 'visible', value: true } },
          ],
        },
      ];
      const nodes: LowCodeNode[] = [node('a', 'NutButton', {}, { events })];
      const output = generateEventHandlers(nodes, new Map());

      expect(output).toContain('const handleATap = useCallback(() => {');
      expect(output).toContain("Taro.showToast({ title: 'Done', icon: 'success' })");
      expect(output).toContain('setVisible(true)');
    });

    it('deduplicates handlers with the same name', () => {
      const events: EventHandler[] = [
        {
          event: 'onClick',
          actions: [{ type: 'showToast', payload: { title: 'hi' } }],
        },
      ];
      // Two nodes with the same id => same handler name
      const nodes: LowCodeNode[] = [
        node('dup', 'NutButton', {}, { events }),
        node('dup', 'NutButton', {}, { events }),
      ];
      const output = generateEventHandlers(nodes, new Map());

      // Handler should appear exactly once
      const matches = output.match(/const handleDupClick = useCallback/g) || [];
      expect(matches).toHaveLength(1);
    });
  });

  // ---------------------------------------------------------------
  // Sub-function tests: generateJsx
  // ---------------------------------------------------------------
  describe('generateJsx', () => {
    it('renders Page root by rendering its children', () => {
      const pageNode: LowCodeNode = {
        id: 'root',
        componentName: 'Page',
        props: {},
        children: [node('t', 'NutText', { text: 'Hi' })],
      };
      const jsx = generateJsx(pageNode);

      // Page node itself should not appear as a <Page> tag
      expect(jsx).not.toContain('<Page');
      // Child should be rendered
      expect(jsx).toContain('<Text>');
      expect(jsx).toContain('Hi');
    });

    it('returns self-closing View for empty Page', () => {
      const pageNode: LowCodeNode = {
        id: 'root',
        componentName: 'Page',
        props: {},
        children: [],
      };
      const jsx = generateJsx(pageNode);
      expect(jsx).toContain('<View />');
    });
  });

  // ---------------------------------------------------------------
  // Sub-function tests: generateImports
  // ---------------------------------------------------------------
  describe('generateImports', () => {
    it('always includes React, Taro, and View imports', () => {
      const imports = generateImports(new Set(['Page']));
      expect(imports).toContain("import React, { useState, useEffect, useCallback } from 'react'");
      expect(imports).toContain("import Taro from '@tarojs/taro'");
      expect(imports).toContain("import { View } from '@tarojs/components'");
    });

    it('includes @hospital/api import when useHospitalApi is true', () => {
      const imports = generateImports(new Set(['Page']), { useHospitalApi: true });
      expect(imports).toContain("import { request } from '@hospital/api'");
    });

    it('sorts component names alphabetically in import', () => {
      const imports = generateImports(new Set(['NutCell', 'NutButton', 'NutText']));
      // NutButton -> Button, NutCell -> Cell, NutText -> Text
      const nutuiLine = imports
        .split('\n')
        .find((l) => l.includes('@nutui/nutui-react-taro'));
      expect(nutuiLine).toBeDefined();
      expect(nutuiLine).toMatch(/Button.*Cell/);
    });
  });

  // ---------------------------------------------------------------
  // generatePage integration: pageStyle option
  // ---------------------------------------------------------------
  describe('generatePage - pageStyle option', () => {
    it('applies pageStyle to the View wrapper', () => {
      const schema = pageSchema([node('t', 'NutText', { text: 'x' })]);
      const output = generatePage(schema, [], {}, {
        pageStyle: { background: '#fff', padding: '16px' },
      });

      expect(output).toContain('style={');
      expect(output).toContain('"background":"#fff"');
    });
  });

  // ---------------------------------------------------------------
  // generatePage integration: custom page title
  // ---------------------------------------------------------------
  describe('generatePage - navigationBarTitleText', () => {
    it('uses page title from schema props in definePageConfig', () => {
      const schema: LowCodeSchema = {
        componentName: 'Page',
        props: { navigationBarTitleText: 'My Custom Title' },
        children: [],
      };
      const output = generatePage(schema);

      expect(output).toContain("navigationBarTitleText: 'My Custom Title'");
    });

    it('falls back to Chinese default when no title is set', () => {
      const schema: LowCodeSchema = {
        componentName: 'Page',
        props: {},
        children: [],
      };
      const output = generatePage(schema);

      // Default is '页面' (from the source code)
      expect(output).toContain('页面');
    });
  });
});
