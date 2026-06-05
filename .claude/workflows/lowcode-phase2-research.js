export const meta = {
  name: 'lowcode-phase2-research',
  description: 'Deep research for Phase 2: data binding and code generation',
  phases: [
    { title: 'Data Binding', detail: 'Research API binding, variable passing, expressions' },
    { title: 'Code Generation', detail: 'Research Taro source and native code generation' },
    { title: 'Synthesize', detail: 'Combine findings into Phase 2 plan' },
  ],
};

// Phase 1: Data Binding Research
phase('Data Binding');

const dataBindingResearch = await agent(
  "Research data binding patterns for low-code platforms. Search for: 1) API Data Source Binding - How amis (Baidu), formily (Alibaba) implement API data source binding. JSON schema for data sources. 2) Component Variable Passing - How variables flow between components. Form data to list filter patterns. 3) Expression Engine - Libraries like expr-eval, jsonata for expression evaluation. 4) State Management - How runtime manages component state and data fetching. 5) Integration with existing @hospital/api package. Search the web for: low-code data binding architecture, amis data source schema, formily data binding, expression engine javascript. Return a structured report with recommended DSL design, variable mechanism, expression engine, and integration approach.",
  { label: 'research:data-binding', phase: 'Data Binding' }
);

// Phase 2: Code Generation Research
phase('Code Generation');

const codeGenResearch = await agent(
  "Research code generation for Taro/mini-program low-code platforms. Search for: 1) Taro Code Generation - How to generate Taro JSX/TSX from Schema DSL. AST tools available. 2) Native Code Generation - Generate WXML/WXSS/JS/JSON from Schema. Mapping rules. 3) Template-based vs AST-based approaches. 4) Existing projects on GitHub for Schema-to-Taro or Schema-to-miniprogram codegen. 5) Dual Output Strategy - Support both Taro source and native code from same Schema. Search the web for: Taro code generation from schema, miniprogram codegen, low-code AST transformation. Return a structured report with recommended architecture, Taro generation approach, native generation approach, and integration with Taro build pipeline.",
  { label: 'research:code-gen', phase: 'Code Generation' }
);

// Phase 3: Synthesize
phase('Synthesize');

const synthesis = await agent(
  "Synthesize Phase 2 research into a concrete implementation plan. Given: 1) Data binding needs: API data source + variable passing + expressions, 2) Code gen needs: Taro source + native mini-program, 3) Stack: Taro 3 + NutUI, React 18, FastAPI, Zustand. Create a plan covering: Data Binding Module (DSL schema, variable syntax, expression engine, runtime manager, API integration, editor UI), Code Generation Module (architecture, Taro generator, native generator, templates, build pipeline, output structure), Implementation Order (dependencies, effort estimates, risks), File Structure (new files, modified files, tests). Return a detailed actionable plan.",
  { label: 'research:synthesis', phase: 'Synthesize' }
);

return {
  dataBinding: dataBindingResearch,
  codeGen: codeGenResearch,
  plan: synthesis,
};
