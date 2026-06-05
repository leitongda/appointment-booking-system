export const meta = {
  name: 'lowcode-phase2-sprint1',
  description: 'Sprint 1: Expression engine + enhanced types + validation',
  phases: [
    { title: 'Expression Engine', detail: 'Build expression parser and evaluator' },
    { title: 'Enhanced Types', detail: 'Extend LowCodeNode types for data binding' },
    { title: 'Backend Validation', detail: 'Add schema validation for new fields' },
    { title: 'Tests', detail: 'Write expression engine unit tests' },
    { title: 'Verify', detail: 'Run all tests and verify' },
  ],
};

// Phase 1: Expression Engine
phase('Expression Engine');

await parallel([
  () => agent(
    "Create the expression engine for the low-code platform. Create file: packages/shared/src/utils/expression-engine.ts. This is a lightweight, safe expression evaluator for dynamic prop values. Requirements: 1) No eval() or Function() - use recursive-descent parser. 2) Support operators: ===, !==, >, <, >=, <=, &&, ||, !, +, -, *, /, %, ?:(ternary). 3) Support property access via dot notation: pageState.doctor.name. 4) Support built-ins: formatDate(), formatPrice(), concat(), length(), first(), last(), includes(). 5) Support ${} template syntax - detect if string starts with ${ and ends with }. 6) Export: evaluateExpression(expr, context), parseExpression(expr), validateExpression(expr). 7) ExpressionContext is a Record<string, any> for variable lookup. 8) Security: expressions validated on save; no arbitrary code execution. Implementation: hand-written recursive-descent parser with operator precedence climbing. Output is an AST evaluated tree-walk style. ~300-400 lines of pure TypeScript, zero dependencies. Read packages/shared/src/types/lowcode.ts first to understand existing types.",
    { label: 'create:expression-engine', phase: 'Expression Engine' }
  ),
  () => agent(
    "Enhance the TypeScript types for data binding support. Modify file: packages/shared/src/types/lowcode.ts. Add these new interfaces: 1) ApiDataSource - {id, method, url, headers?, params?, dataPath?, pollingInterval?, manual?}. 2) EventHandler - {event, actions: EventAction[]}. 3) EventAction - {type: 'setData'|'fetchApi'|'navigate'|'showToast'|'updateVariable', payload}. 4) LoopConfig - {dataSource, itemName?, indexName?}. 5) DataBindingConfig - {bindings: Record<string, string>, events?}. Then extend the existing LowCodeNode interface with optional fields: api?: ApiDataSource, dataBinding?: DataBindingConfig, events?: EventHandler[], loop?: LoopConfig, visible?: string, dependOn?: string[]. Also add PageDataSource type for page-level data source definitions. All new fields must be optional for backward compatibility. Read the file first, then add the new types.",
    { label: 'enhance:types', phase: 'Enhanced Types' }
  ),
]);

// Phase 2: Backend Validation
phase('Backend Validation');

await agent(
  "Add backend validation for the new data binding fields. Modify file: apps/server/app/schemas/lowcode.py. The existing validate_schema_data validator checks componentName, props, children structure. Add validation for: 1) dataSources array - each must have id (string), url (string), method (GET/POST/PUT/DELETE). 2) State at root level - if present, each key must have type and defaultValue. 3) Binding expressions in dataBinding - validate they are strings. 4) Events array - each must have event (string) and actions (array). 5) Loop config - must have dataSource (string). Keep validation lightweight - structural checks only, not semantic. Read the file first, then enhance the validator.",
  { label: 'enhance:validation', phase: 'Backend Validation' }
);

// Phase 3: Tests
phase('Tests');

await agent(
  "Create comprehensive unit tests for the expression engine. Create file: packages/shared/src/__tests__/expression-engine.test.ts. Test cases: 1) Variable resolution: ${name}, ${user.age}, ${nested.deep.value}. 2) Comparison operators: ==, !=, >=, <=, >, <. 3) Logical operators: &&, ||, !. 4) Arithmetic: +, -, *, /. 5) Ternary: condition ? a : b. 6) Property access with null safety: ${user?.name} should not throw. 7) Built-in functions: formatDate, length, includes. 8) Template interpolation: 'Hello ${name}' returns 'Hello World'. 9) Invalid expression handling: undefined variables return undefined, not throw. 10) Edge cases: empty string, null context, deeply nested paths. Use vitest. 30+ test cases minimum. Read the expression engine file first to understand the API.",
  { label: 'tests:expression', phase: 'Tests' }
);

// Phase 4: Verify
phase('Verify');

await agent(
  "Verify Sprint 1 deliverables: 1) Check expression engine exists: ls packages/shared/src/utils/expression-engine.ts, 2) Check types enhanced: grep 'ApiDataSource' packages/shared/src/types/lowcode.ts, 3) Check validation enhanced: grep 'dataSources' apps/server/app/schemas/lowcode.py, 4) Check tests exist: ls packages/shared/src/__tests__/expression-engine.test.ts, 5) Run expression engine tests if possible: cd packages/shared && npx vitest run src/__tests__/expression-engine.test.ts 2>&1 | tail -20. Report each as PASS or FAIL.",
  { label: 'verify:sprint1', phase: 'Verify' }
);

log('Sprint 1 completed');
return { status: 'completed', sprint: 1 };
