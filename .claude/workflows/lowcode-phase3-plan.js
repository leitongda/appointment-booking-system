export const meta = {
  name: 'lowcode-phase3-plan',
  description: 'Phase 3 planning: SaaS multi-tenancy, template marketplace, deployment pipeline',
  phases: [
    { title: 'Multi-Tenancy', detail: 'Research SaaS multi-tenancy for low-code platform' },
    { title: 'Template Market', detail: 'Research template marketplace design' },
    { title: 'Deployment', detail: 'Research deployment and publishing pipeline' },
    { title: 'Synthesize', detail: 'Create Phase 3 implementation plan' },
  ],
};

// Phase 1: Multi-Tenancy Research
phase('Multi-Tenancy');

const multiTenancy = await agent(
  "Research SaaS multi-tenancy for the low-code platform. The current system already has tenant_id isolation at the database level, but the low-code platform needs additional multi-tenancy features for SaaS output. Research: 1) How to allow each tenant to have their own low-code pages with independent schemas. 2) How to isolate tenant-specific components/materials (some tenants may have custom components). 3) Subscription plan integration - which features are available per plan tier. 4) Tenant-level publishing - each tenant publishes to their own mini-program AppID. 5) Data isolation for templates - shared templates vs tenant-specific templates. Search the web for: SaaS multi-tenancy low-code platform architecture, tenant isolation patterns, subscription-based feature gating. Also read the existing tenant model at apps/server/app/models/tenant.py to understand current multi-tenancy. Return a structured report.",
  { label: 'research:multi-tenancy', phase: 'Multi-Tenancy' }
);

// Phase 2: Template Market Research
phase('Template Market');

const templateMarket = await agent(
  "Research template marketplace design for the low-code platform. The current system has 5 hardcoded templates. Phase 3 needs a proper template marketplace. Research: 1) Template data model - what fields are needed (name, category, preview, schema, author, version, ratings). 2) Template sharing - tenant-to-marketplace publishing workflow. 3) Template forking - when a tenant uses a template, they get a copy they can modify. 4) Template categories for medical scenarios (department intro, activity page, appointment form, health article). 5) Template versioning - how to handle template updates. 6) Template search and filtering. 7) Community features - ratings, reviews, usage counts. Search the web for: marketplace template design patterns, no-code template marketplace architecture, component marketplace. Return a structured report.",
  { label: 'research:template-market', phase: 'Template Market' }
);

// Phase 3: Deployment Research
phase('Deployment');

const deployment = await agent(
  "Research deployment and publishing pipeline for the low-code platform. Currently there's a basic build/release system in miniapp_platform. Phase 3 needs a complete pipeline. Research: 1) How to trigger Taro build from the low-code editor (push Schema -> codegen -> build -> upload). 2) WeChat mini-program upload API integration (access_token, upload, submit audit). 3) CI/CD pipeline design - GitHub Actions or similar for automated builds. 4) Rollback strategy - how to revert to a previous version. 5) Preview before publish - generating a preview QR code. 6) Multi-environment support (dev/staging/production). 7) Build artifact management - storing compiled mini-program packages. Search the web for: WeChat mini-program CI/CD, Taro build automation, mini-program deployment pipeline. Also read the existing build/release models at apps/server/app/models/miniapp_platform.py. Return a structured report.",
  { label: 'research:deployment', phase: 'Deployment' }
);

// Phase 4: Synthesize
phase('Synthesize');

const synthesis = await agent(
  "Synthesize all Phase 3 research into a concrete implementation plan. Given: 1) Current state: Phase 1 (editor + runtime) and Phase 2 (data binding + codegen) complete. 2) Multi-tenancy needs: tenant isolation, subscription gating, per-tenant publishing. 3) Template marketplace: sharing, forking, versioning, categories. 4) Deployment pipeline: codegen -> build -> upload -> audit. Create a Phase 3 plan covering: Multi-Tenancy Module (data model, feature gating, tenant isolation), Template Marketplace (data model, sharing workflow, search, categories), Deployment Pipeline (trigger flow, WeChat API integration, rollback, preview), Implementation Order (sprint breakdown with dependencies), Effort Estimates. Return a detailed actionable plan.",
  { label: 'research:synthesis', phase: 'Synthesize' }
);

return {
  multiTenancy,
  templateMarket,
  deployment,
  plan: synthesis,
};
