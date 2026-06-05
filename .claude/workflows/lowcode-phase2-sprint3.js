export const meta = {
  name: 'lowcode-phase2-sprint3',
  description: 'Sprint 3: Editor UI for data binding configuration',
  phases: [
    { title: 'DataSourcePanel', detail: 'Create data source configuration panel' },
    { title: 'EventConfig', detail: 'Create event handler configuration' },
    { title: 'PropertyPanel Binding', detail: 'Add binding UI to property panel' },
    { title: 'Store Update', detail: 'Extend editor store with data source actions' },
    { title: 'Verify', detail: 'Verify all components' },
  ],
};

// Phase 1: DataSourcePanel
phase('DataSourcePanel');

await agent(
  "Create the DataSourcePanel component for configuring API data sources in the low-code editor. Create file: apps/admin/src/pages/lowcode/editor/components/DataSourcePanel.tsx. This is a panel in the left sidebar (alongside ComponentPanel) that manages page-level data sources. Features: 1) List of configured data sources with name, type (api/static), URL preview, refresh icon. 2) Add button opens a modal/drawer with form: name, url, method (GET/POST/PUT/DELETE), params (key-value pairs), dataPath, pollingInterval, manual toggle. 3) Edit/Delete actions per data source. 4) Test button that calls the backend /lowcode/data-sources/test endpoint and shows sample response. 5) Drag data source to auto-create binding. Use Ant Design components (Form, Select, Input, Button, Modal, List, Tag). Read apps/admin/src/pages/lowcode/editor/store.ts to understand the Zustand store structure, then create the panel.",
  { label: 'create:datasource-panel', phase: 'DataSourcePanel', isolation: 'worktree' }
);

// Phase 2: EventConfig
phase('EventConfig');

await agent(
  "Create the EventConfig component for configuring event handlers. Create file: apps/admin/src/pages/lowcode/editor/components/EventConfig.tsx. This component appears in the PropertyPanel when a component is selected. Features: 1) List of events configured for the selected component (onClick, onChange, onSubmit, onLoad). 2) Add event button opens a modal. 3) Per event, configure action chain: navigate (url param), showToast (message), updateVariable (key+value), fetchApi (data source id). 4) Conditional execution: optional 'when' expression field. 5) Reorder actions within an event. Use Ant Design components. Read the PropertyPanel.tsx file first to understand how to integrate.",
  { label: 'create:event-config', phase: 'EventConfig', isolation: 'worktree' }
);

// Phase 3: PropertyPanel Binding
phase('PropertyPanel Binding');

await agent(
  "Add data binding UI to the PropertyPanel component. Modify file: apps/admin/src/pages/lowcode/editor/components/PropertyPanel.tsx. For each property field in the form, add a toggle button that switches between 'static value' mode and 'expression binding' mode. In expression mode: 1) Show an expression input field with syntax highlighting hint. 2) Show a variable picker dropdown with available variables: pageParams.*, api.*.*, formData.*, custom variables. 3) Show autocomplete suggestions as user types. 4) Validate expression on blur (red border on invalid). 5) Store binding in node.dataBinding[propName] instead of node.props[propName]. Read the file first, then add the binding toggle UI.",
  { label: 'enhance:property-panel', phase: 'PropertyPanel Binding' }
);

// Phase 4: Store Update
phase('Store Update');

await agent(
  "Extend the editor store with data source management actions. Modify file: apps/admin/src/pages/lowcode/editor/store.ts. Add to the store interface: 1) dataSources: DataSource[] - page-level data sources. 2) stateSchema: Record<string, {type, defaultValue, label}> - page state variables. 3) addDataSource(ds: DataSource) - add a new data source. 4) updateDataSource(id: string, updates: Partial<DataSource>) - update. 5) removeDataSource(id: string) - remove. 6) setStateSchema(schema) - set state variables. 7) updateNodeBinding(nodeId: string, propName: string, expression: string) - set a binding expression for a prop. 8) removeNodeBinding(nodeId: string, propName: string) - remove binding. Also update setSchema and reset to handle the new fields. Read the file first, then add the new actions.",
  { label: 'update:store', phase: 'Store Update' }
);

// Phase 5: Verify
phase('Verify');

await agent(
  "Verify Sprint 3 deliverables: 1) Check DataSourcePanel exists: ls apps/admin/src/pages/lowcode/editor/components/DataSourcePanel.tsx, 2) Check EventConfig exists: ls apps/admin/src/pages/lowcode/editor/components/EventConfig.tsx, 3) Check PropertyPanel has binding toggle: grep 'expression\|binding\|static.*mode' apps/admin/src/pages/lowcode/editor/components/PropertyPanel.tsx | head -5, 4) Check store has new actions: grep 'addDataSource\|updateNodeBinding\|stateSchema' apps/admin/src/pages/lowcode/editor/store.ts | head -5, 5) Count total editor files: find apps/admin/src/pages/lowcode/editor -type f -name '*.tsx' -o -name '*.ts' | wc -l. Report each as PASS or FAIL.",
  { label: 'verify:sprint3', phase: 'Verify' }
);

log('Sprint 3 completed');
return { status: 'completed', sprint: 3 };
