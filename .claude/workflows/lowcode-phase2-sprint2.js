export const meta = {
  name: 'lowcode-phase2-sprint2',
  description: 'Sprint 2: Runtime data manager + renderer upgrade',
  phases: [
    { title: 'DataManager', detail: 'Build useDataManager hook and DataProvider' },
    { title: 'Renderer Upgrade', detail: 'Enhance LowCodeRenderer with data binding' },
    { title: 'Backend API', detail: 'Add data-source test and preview endpoints' },
    { title: 'Verify', detail: 'Run tests and verify' },
  ],
};

// Phase 1: DataManager
phase('DataManager');

await parallel([
  () => agent(
    "Create the useDataManager hook for the low-code runtime. Create file: apps/patient-miniapp/src/components/LowCodeRenderer/data-manager.ts. This hook manages page-level state for data-bound pages. Requirements: 1) Accept dataSources and stateSchema as parameters. 2) On mount, auto-fetch all refresh:'onMount' data sources via @hospital/api request. 3) Maintain state as Record<string, any> with nested-path setter (dot-notation path resolution). 4) Expose: state, setData(path, value), getData(path), fetchDataSource(id, params), evaluate(expr) for expression evaluation. 5) Use the expression engine from packages/shared/src/utils/expression-engine.ts for expression evaluation. 6) Support variable scoping: pageParams, apiData, formData, custom variables. 7) Use Taro's useState and useEffect hooks. 8) Handle loading and error states for each data source. Read packages/shared/src/utils/expression-engine.ts first to understand the evaluateExpression API.",
    { label: 'create:data-manager', phase: 'DataManager', isolation: 'worktree' }
  ),
  () => agent(
    "Create the DataProvider React context component. Create file: apps/patient-miniapp/src/components/LowCodeRenderer/DataProvider.tsx. This is a React Context provider that wraps the low-code page and provides data management to all child components. Requirements: 1) Create LowCodeDataContext with createContext. 2) Provider component accepts dataSources, stateSchema, pageParams as props. 3) Internal state managed by useDataManager hook. 4) Context value includes: state, setData, getData, fetchDataSource, evaluate. 5) Export a useLowCodeData() hook for consuming the context. 6) Export the DataProvider component. Read apps/patient-miniapp/src/components/LowCodeRenderer/data-manager.ts first (may need to create it first if not exists).",
    { label: 'create:data-provider', phase: 'DataManager', isolation: 'worktree' }
  ),
]);

// Phase 2: Renderer Upgrade
phase('Renderer Upgrade');

await agent(
  "Enhance the LowCodeRenderer to support data binding, conditional rendering, and list rendering. Modify file: apps/patient-miniapp/src/components/LowCodeRenderer/index.tsx. Changes: 1) Import and use DataProvider context. 2) Add conditional rendering: if node.visible is set, evaluate the expression and return null if false. 3) Add list rendering: if node.loop is set, evaluate loop.dataSource to get an array, then render the component once per item with item/index variables in context. 4) Add data binding: for each prop, if node.dataBinding has a binding for that prop key, evaluate the expression instead of using the static value. 5) Add event handling: if node.events is set, bind event handlers that call the DataManager actions (navigate, showToast, updateVariable). 6) Wrap the entire renderer with DataProvider at the Page level. 7) Ensure backward compatibility: pages without dataSources/dataBinding should render exactly as before. Read the file first, then apply changes.",
  { label: 'upgrade:renderer', phase: 'Renderer Upgrade' }
);

// Phase 3: Backend API
phase('Backend API');

await agent(
  "Add backend API endpoints for data source testing and page data preview. Modify file: apps/server/app/modules/lowcode/router.py. Add these new endpoints: 1) POST /lowcode/data-sources/test - Accept a data source config, execute the request in sandboxed way (with timeout 5s, max response 1MB), return sample response and field suggestions. 2) GET /lowcode/pages/{id}/data-preview - Load page schema, return mock data structure based on dataSources config. Both endpoints require the same permission checks as existing lowcode endpoints. Also modify service.py to add a get_with_data_sources method if needed. Read the existing router.py and service.py files first.",
  { label: 'add:backend-api', phase: 'Backend API' }
);

// Phase 4: Verify
phase('Verify');

await agent(
  "Verify Sprint 2 deliverables: 1) Check data-manager.ts exists: ls apps/patient-miniapp/src/components/LowCodeRenderer/data-manager.ts, 2) Check DataProvider.tsx exists: ls apps/patient-miniapp/src/components/LowCodeRenderer/DataProvider.tsx, 3) Check renderer has data binding: grep 'visible\|loop\|dataBinding\|evaluate' apps/patient-miniapp/src/components/LowCodeRenderer/index.tsx | head -5, 4) Check backend has new endpoints: grep 'data-sources/test\|data-preview' apps/server/app/modules/lowcode/router.py, 5) Check types are enhanced: grep 'ApiDataSource\|LoopConfig' packages/shared/src/types/lowcode.ts | head -3. Report each as PASS or FAIL.",
  { label: 'verify:sprint2', phase: 'Verify' }
);

log('Sprint 2 completed');
return { status: 'completed', sprint: 2 };
