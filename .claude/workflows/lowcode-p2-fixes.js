export const meta = {
  name: 'lowcode-phase1-p2-fixes',
  description: 'Fix P2 issues: page copy, image upload, user guide',
  phases: [
    { title: 'Page Copy', detail: 'Add page duplication feature' },
    { title: 'Image Upload', detail: 'Integrate image upload for NutImage' },
    { title: 'User Guide', detail: 'Create editor user guide' },
    { title: 'Verify', detail: 'Verify all P2 fixes' },
  ],
};

// Phase 1: Page Copy
phase('Page Copy');

await agent(
  'Add page duplication feature to the low-code editor. File: apps/admin/src/pages/lowcode/list.tsx. Add a "复制" button in the action column that: 1) Calls lowcodeApi.createPage with the same schema_data but a new name (原名称 + " 副本") and new slug (原slug + "-copy"), 2) Navigates to the editor with the new page ID. Read the file first, then add the copy functionality.',
  { label: 'feature:page-copy', phase: 'Page Copy' }
);

// Phase 2: Image Upload
phase('Image Upload');

await agent(
  'Integrate image upload for NutImage component in the low-code editor. File: apps/admin/src/pages/lowcode/editor/components/PropertyPanel.tsx. When the image property type is "image", instead of a plain text input, use the existing ImageUpload component from apps/admin/src/components/ImageUpload/ or a simple upload button that calls the upload API and sets the URL. Read both files to understand the existing patterns, then modify PropertyPanel to support image upload.',
  { label: 'feature:image-upload', phase: 'Image Upload' }
);

// Phase 3: User Guide
phase('User Guide');

await agent(
  'Create a user guide for the low-code editor. Create file: apps/admin/src/pages/lowcode/USER_GUIDE.md. Content should include: 1) Getting Started - how to access the editor, 2) Creating a Page - step by step, 3) Adding Components - drag from panel, 4) Configuring Properties - using property panel, 5) Preview and Publish - how to preview and publish, 6) Tips and Best Practices. Write in Chinese. Keep it concise and practical.',
  { label: 'docs:user-guide', phase: 'User Guide' }
);

// Phase 4: Verify
phase('Verify');

await agent(
  'Verify P2 fixes: 1) Check page copy button exists in list.tsx: grep "复制" apps/admin/src/pages/lowcode/list.tsx, 2) Check image upload in PropertyPanel: grep "upload\|ImageUpload" apps/admin/src/pages/lowcode/editor/components/PropertyPanel.tsx, 3) Check user guide exists: ls apps/admin/src/pages/lowcode/USER_GUIDE.md, 4) Count total lowcode files: find apps/admin/src/pages/lowcode -type f | wc -l. Report each as PASS or FAIL.',
  { label: 'verify:p2', phase: 'Verify' }
);

log('All P2 fixes completed');
return { status: 'completed' };
