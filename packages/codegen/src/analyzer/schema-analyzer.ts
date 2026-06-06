/**
 * Schema Analyzer Module
 *
 * Validates and enriches a LowCodeSchema before code generation.
 * Performs structure validation, component collection, data source extraction,
 * and dependency graph construction.
 */

import type {
  LowCodeSchema,
  LowCodeNode,
  ApiDataSource,
} from '@hospital/shared/types/lowcode';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

/** Dependency edge: a component depends on a data source */
export interface DependencyEdge {
  /** The node id of the component that has the dependency */
  nodeId: string;
  /** The componentName of the dependent component */
  componentName: string;
  /** The id of the data source it depends on */
  dataSourceId: string;
  /** How the dependency is expressed */
  kind: 'api' | 'dataBinding' | 'loop' | 'dependOn' | 'expression';
}

/** Unique component summary */
export interface ComponentSummary {
  componentName: string;
  /** Number of instances in the schema tree */
  count: number;
  /** Node ids of all instances */
  nodeIds: string[];
}

/** Analysis warning severity */
export type WarningSeverity = 'error' | 'warning' | 'info';

/** Analysis warning */
export interface AnalysisWarning {
  severity: WarningSeverity;
  /** Machine-readable code, e.g. "MISSING_ID", "ORPHAN_DATASOURCE" */
  code: string;
  message: string;
  /** Optional node id where the warning originates */
  nodeId?: string;
  /** Optional data source id */
  dataSourceId?: string;
}

/** Full analysis result returned by analyzeSchema */
export interface AnalysisResult {
  /** All unique components used in the schema */
  components: ComponentSummary[];
  /** All data sources (page-level + node-level), deduplicated by id */
  dataSources: ApiDataSource[];
  /** Dependency edges between components and data sources */
  dependencies: DependencyEdge[];
  /** Validation warnings and informational notices */
  warnings: AnalysisWarning[];
}

// ---------------------------------------------------------------------------
// Expression helpers
// ---------------------------------------------------------------------------

/** Regex to match data source references like {{api.someId.data}} */
const EXPRESSION_RE = /\{\{([^}]+)\}\}/g;

/** Known expression prefixes that refer to data sources */
const DATA_SOURCE_PREFIXES = ['api.', 'dataSource.', 'ds.'];

/**
 * Extract data source ids referenced inside a template expression string.
 * Recognises patterns like `{{api.users.data}}`, `{{dataSource.list}}`,
 * `{{ds.orders.items}}`.
 */
function extractDataSourceRefsFromExpression(expression: string): string[] {
  const refs: string[] = [];
  let match: RegExpExecArray | null;

  while ((match = EXPRESSION_RE.exec(expression)) !== null) {
    const expr = match[1].trim();
    for (const prefix of DATA_SOURCE_PREFIXES) {
      if (expr.startsWith(prefix)) {
        const rest = expr.slice(prefix.length);
        // The first segment after the prefix is the data source id.
        const dataSourceId = rest.split('.')[0];
        if (dataSourceId) {
          refs.push(dataSourceId);
        }
      }
    }
  }

  return refs;
}

// ---------------------------------------------------------------------------
// collectUsedComponents
// ---------------------------------------------------------------------------

/**
 * Walk the schema tree and return a deduplicated list of all componentNames
 * found in the tree (including the root).
 */
export function collectUsedComponents(schema: LowCodeSchema): string[] {
  const seen = new Set<string>();

  function walk(node: { componentName: string; children?: any[] }) {
    seen.add(node.componentName);
    if (node.children) {
      for (const child of node.children) {
        walk(child);
      }
    }
  }

  walk(schema);
  return [...seen];
}

// ---------------------------------------------------------------------------
// extractDataSources
// ---------------------------------------------------------------------------

/**
 * Collect all API data sources from the schema, including page-level
 * `schema.dataSources` and per-node `node.api` declarations.
 * Deduplicates by `id` (last-write-wins for duplicates, with a warning).
 */
export function extractDataSources(schema: LowCodeSchema): {
  dataSources: ApiDataSource[];
  duplicates: string[];
} {
  const byId = new Map<string, ApiDataSource>();
  const duplicates: string[] = [];

  // Page-level data sources
  if (schema.dataSources) {
    for (const ds of schema.dataSources) {
      if (byId.has(ds.id)) {
        duplicates.push(ds.id);
      }
      byId.set(ds.id, ds as ApiDataSource);
    }
  }

  // Walk nodes for per-node api declarations
  function walkNodes(nodes: LowCodeNode[]) {
    for (const node of nodes) {
      if (node.api) {
        if (byId.has(node.api.id)) {
          duplicates.push(node.api.id);
        }
        byId.set(node.api.id, node.api as ApiDataSource);
      }
      if (node.children) {
        walkNodes(node.children);
      }
    }
  }

  walkNodes(schema.children ?? []);

  return { dataSources: [...byId.values()], duplicates: [...new Set(duplicates)] };
}

// ---------------------------------------------------------------------------
// buildDependencyGraph
// ---------------------------------------------------------------------------

/**
 * Identify which components depend on which data sources by inspecting:
 *  - `node.api` (direct API binding)
 *  - `node.dataBinding.bindings` values (expression references)
 *  - `node.loop.dataSource` (loop data expression)
 *  - `node.dependOn` (explicit dependency declarations)
 *  - `node.visible` (visibility expression)
 */
export function buildDependencyGraph(
  schema: LowCodeSchema,
  knownDataSourceIds: Set<string>,
): { edges: DependencyEdge[]; warnings: AnalysisWarning[] } {
  const edges: DependencyEdge[] = [];
  const warnings: AnalysisWarning[] = [];

  function walk(nodes: LowCodeNode[]) {
    for (const node of nodes) {
      const addEdge = (dsId: string, kind: DependencyEdge['kind']) => {
        edges.push({
          nodeId: node.id,
          componentName: node.componentName,
          dataSourceId: dsId,
          kind,
        });
      };

      // 1. Direct API binding
      if (node.api) {
        addEdge(node.api.id, 'api');
        if (!knownDataSourceIds.has(node.api.id)) {
          warnings.push({
            severity: 'warning',
            code: 'UNKNOWN_DATASOURCE_REF',
            message: `Component "${node.componentName}" (id=${node.id}) references unknown data source "${node.api.id}" via api binding.`,
            nodeId: node.id,
            dataSourceId: node.api.id,
          });
        }
      }

      // 2. Data binding expressions
      if (node.dataBinding?.bindings) {
        for (const [prop, expression] of Object.entries(node.dataBinding.bindings)) {
          const refs = extractDataSourceRefsFromExpression(expression);
          for (const dsId of refs) {
            addEdge(dsId, 'dataBinding');
            if (!knownDataSourceIds.has(dsId)) {
              warnings.push({
                severity: 'warning',
                code: 'UNKNOWN_DATASOURCE_REF',
                message: `Component "${node.componentName}" (id=${node.id}) prop "${prop}" references unknown data source "${dsId}".`,
                nodeId: node.id,
                dataSourceId: dsId,
              });
            }
          }
        }
      }

      // 3. Loop data source
      if (node.loop?.dataSource) {
        const refs = extractDataSourceRefsFromExpression(node.loop.dataSource);
        for (const dsId of refs) {
          addEdge(dsId, 'loop');
          if (!knownDataSourceIds.has(dsId)) {
            warnings.push({
              severity: 'warning',
              code: 'UNKNOWN_DATASOURCE_REF',
              message: `Component "${node.componentName}" (id=${node.id}) loop references unknown data source "${dsId}".`,
              nodeId: node.id,
              dataSourceId: dsId,
            });
          }
        }
      }

      // 4. Explicit dependOn
      if (node.dependOn) {
        for (const dep of node.dependOn) {
          // dependOn can reference data source ids or state keys.
          // If it looks like a known data source id, record the edge.
          if (knownDataSourceIds.has(dep)) {
            addEdge(dep, 'dependOn');
          }
        }
      }

      // 5. Visible expression
      if (node.visible) {
        const refs = extractDataSourceRefsFromExpression(node.visible);
        for (const dsId of refs) {
          addEdge(dsId, 'expression');
          if (!knownDataSourceIds.has(dsId)) {
            warnings.push({
              severity: 'warning',
              code: 'UNKNOWN_DATASOURCE_REF',
              message: `Component "${node.componentName}" (id=${node.id}) visible expression references unknown data source "${dsId}".`,
              nodeId: node.id,
              dataSourceId: dsId,
            });
          }
        }
      }

      // Recurse
      if (node.children) {
        walk(node.children);
      }
    }
  }

  walk(schema.children ?? []);

  return { edges, warnings };
}

// ---------------------------------------------------------------------------
// validateSchema (structural)
// ---------------------------------------------------------------------------

/**
 * Perform basic structural validation on a LowCodeSchema.
 * Returns a list of warnings/errors found.
 */
function validateStructure(schema: LowCodeSchema): AnalysisWarning[] {
  const warnings: AnalysisWarning[] = [];

  // Root must be 'Page'
  if (schema.componentName !== 'Page') {
    warnings.push({
      severity: 'error',
      code: 'INVALID_ROOT',
      message: `Root componentName should be "Page", got "${schema.componentName}".`,
    });
  }

  if (!schema.children || schema.children.length === 0) {
    warnings.push({
      severity: 'warning',
      code: 'EMPTY_CHILDREN',
      message: 'Root Page has no children; the generated page will be empty.',
    });
  }

  // Walk nodes for per-node validation
  const idSet = new Set<string>();

  function walkNodes(nodes: LowCodeNode[]) {
    for (const node of nodes) {
      // Missing id
      if (!node.id) {
        warnings.push({
          severity: 'error',
          code: 'MISSING_ID',
          message: `Node "${node.componentName}" is missing a required "id" field.`,
          nodeId: node.id,
        });
      }

      // Duplicate id
      if (node.id && idSet.has(node.id)) {
        warnings.push({
          severity: 'error',
          code: 'DUPLICATE_ID',
          message: `Duplicate node id "${node.id}" found. Each node must have a unique id.`,
          nodeId: node.id,
        });
      }
      if (node.id) {
        idSet.add(node.id);
      }

      // Missing componentName
      if (!node.componentName) {
        warnings.push({
          severity: 'error',
          code: 'MISSING_COMPONENT_NAME',
          message: `Node (id=${node.id}) is missing a required "componentName" field.`,
          nodeId: node.id,
        });
      }

      // Empty props (info only)
      if (!node.props || Object.keys(node.props).length === 0) {
        warnings.push({
          severity: 'info',
          code: 'EMPTY_PROPS',
          message: `Component "${node.componentName}" (id=${node.id}) has no props.`,
          nodeId: node.id,
        });
      }

      // Recurse
      if (node.children) {
        walkNodes(node.children);
      }
    }
  }

  walkNodes(schema.children ?? []);

  return warnings;
}

// ---------------------------------------------------------------------------
// analyzeSchema (main entry)
// ---------------------------------------------------------------------------

/**
 * Analyze a LowCodeSchema: validate structure, collect components,
 * extract data sources, and build the dependency graph.
 *
 * Returns a complete AnalysisResult.
 */
export function analyzeSchema(schema: LowCodeSchema): AnalysisResult {
  const warnings: AnalysisWarning[] = [];

  // 1. Structural validation
  warnings.push(...validateStructure(schema));

  // 2. Collect used components (with counts)
  const componentMap = new Map<string, { count: number; nodeIds: string[] }>();

  function walkForComponents(node: { componentName: string; id?: string; children?: any[] }) {
    const existing = componentMap.get(node.componentName);
    if (existing) {
      existing.count += 1;
      if (node.id) existing.nodeIds.push(node.id);
    } else {
      componentMap.set(node.componentName, { count: 1, nodeIds: node.id ? [node.id] : [] });
    }
    if (node.children) {
      for (const child of node.children) {
        walkForComponents(child);
      }
    }
  }

  walkForComponents(schema);

  const components: ComponentSummary[] = [...componentMap.entries()].map(
    ([componentName, { count, nodeIds }]) => ({
      componentName,
      count,
      nodeIds,
    }),
  );

  // 3. Extract data sources
  const { dataSources, duplicates } = extractDataSources(schema);
  for (const dupId of duplicates) {
    warnings.push({
      severity: 'warning',
      code: 'DUPLICATE_DATASOURCE',
      message: `Data source id "${dupId}" is declared more than once. Later declarations overwrite earlier ones.`,
      dataSourceId: dupId,
    });
  }

  // 4. Build dependency graph
  const knownDsIds = new Set(dataSources.map((ds) => ds.id));
  const { edges, warnings: depWarnings } = buildDependencyGraph(schema, knownDsIds);
  warnings.push(...depWarnings);

  // 5. Check for orphan data sources (declared but never referenced)
  const referencedDsIds = new Set(edges.map((e) => e.dataSourceId));
  for (const ds of dataSources) {
    if (!referencedDsIds.has(ds.id)) {
      warnings.push({
        severity: 'info',
        code: 'ORPHAN_DATASOURCE',
        message: `Data source "${ds.id}" (${ds.method} ${ds.url}) is declared but never referenced by any component.`,
        dataSourceId: ds.id,
      });
    }
  }

  return {
    components,
    dataSources,
    dependencies: edges,
    warnings,
  };
}
