export const meta = {
  name: 'lowcode-phase2-sprint5',
  description: 'Sprint 5: Native generator + editor code preview + integration',
  phases: [
    { title: 'Native Generator', detail: 'Build WXML/WXSS/JS generator' },
    { title: 'Code Preview', detail: 'Build editor code preview modal' },
    { title: 'Integration', detail: 'Wire everything together and verify' },
    { title: 'Verify', detail: 'Final verification' },
  ],
};

// Phase 1: Native Generator
phase('Native Generator');

await parallel([
  () => agent(
    "Create the WXML generator for native mini-program output. Create file: packages/codegen/src/generators/native/wxml-generator.ts. This module converts a LowCodeSchema into WXML template markup. Mapping rules: View/NutView -> <view>, Text/NutText -> <text>, Image/NutImage -> <image>, NutButton -> <button>, NutSwiper -> <swiper>, NutCell -> <view class='nut-cell'>. Support: 1) Conditional rendering: wx:if='{{condition}}'. 2) List rendering: wx:for='{{items}}' wx:key='id'. 3) Event binding: bindtap='onXxx', bindinput='onXxx'. 4) Data binding: {{variableName}}. 5) Style binding: style='...'. Generate clean, properly indented WXML. Read packages/shared/src/types/lowcode.ts first.",
    { label: 'create:wxml-gen', phase: 'Native Generator', isolation: 'worktree' }
  ),
  () => agent(
    "Create the page JS and JSON generators for native output. Create files: 1) packages/codegen/src/generators/native/js-generator.ts - generates page.js with data(), onLoad(), event handlers, setData calls for API responses. 2) packages/codegen/src/generators/native/json-generator.ts - generates page.json with navigationBarTitleText, usingComponents map. The JS generator should: map dataSources to wx.request calls in onLoad, generate event handler methods for each event in the schema, use this.setData() to update state. Read packages/shared/src/types/lowcode.ts first.",
    { label: 'create:js-json-gen', phase: 'Native Generator', isolation: 'worktree' }
  ),
]);

// Phase 2: Code Preview
phase('Code Preview');

await agent(
  "Create the code preview modal for the low-code editor. Create file: apps/admin/src/pages/lowcode/editor/components/CodePreviewModal.tsx. This modal shows the generated code for the current page. Features: 1) Modal with tabs for each generated file (index.tsx, index.config.ts, index.module.css). 2) Syntax-highlighted code display (use Ant Design's Typography.Paragraph with copyable, or a simple <pre><code> block). 3) Tabs switch between Taro output and Native output. 4) Copy all button to copy all files to clipboard. 5) Download button to download as .tar.gz (calls backend /codegen/download endpoint). 6) Loading state while generating. Use Ant Design Modal, Tabs, Button, Spin, message components. Read apps/admin/src/pages/lowcode/editor/store.ts to understand how to get the current schema.",
  { label: 'create:code-preview', phase: 'Code Preview' }
);

// Phase 3: Integration
phase('Integration');

await agent(
  "Wire everything together and add the code generation button to the editor toolbar. Modify file: apps/admin/src/pages/lowcode/editor/index.tsx. Add a 'Generate Code' button in the toolbar (between Preview and Publish). When clicked, it opens the CodePreviewModal with the current schema. Also: 1) Import CodePreviewModal. 2) Add state for modal visibility. 3) Add button with CodeOutlined icon. 4) Pass current schema and dataSources to the modal. Ensure the button is disabled when there are unsaved changes (warn user to save first). Read the file first, then add the integration.",
  { label: 'integrate:editor', phase: 'Integration' }
);

// Phase 4: Verify
phase('Verify');

await agent(
  "Final Phase 2 verification: 1) Check WXML generator: ls packages/codegen/src/generators/native/wxml-generator.ts, 2) Check JS generator: ls packages/codegen/src/generators/native/js-generator.ts, 3) Check JSON generator: ls packages/codegen/src/generators/native/json-generator.ts, 4) Check CodePreviewModal: ls apps/admin/src/pages/lowcode/editor/components/CodePreviewModal.tsx, 5) Check editor has codegen button: grep -i 'codegen\|generate.*code\|CodePreview' apps/admin/src/pages/lowcode/editor/index.tsx | head -3, 6) Count total codegen files: find packages/codegen -type f | wc -l, 7) Count total editor component files: find apps/admin/src/pages/lowcode/editor/components -type f -name '*.tsx' | wc -l. Report each as PASS or FAIL.",
  { label: 'verify:sprint5', phase: 'Verify' }
);

log('Phase 2 Sprint 5 completed');
return { status: 'completed', sprint: 5, phase2Complete: true };
