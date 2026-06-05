/**
 * Native WXML Generator
 *
 * Converts a LowCodeSchema into native WeChat Mini Program WXML template markup.
 * Generates clean, properly indented WXML with support for:
 * - Conditional rendering (wx:if)
 * - List rendering (wx:for)
 * - Event binding (bindtap, bindinput)
 * - Data binding ({{variableName}})
 * - Style binding (style='...')
 */

import type {
  LowCodeSchema,
  LowCodeNode,
  EventHandler,
} from '@hospital/shared/types/lowcode';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

/** Options for WXML generation */
export interface GenerateWxmlOptions {
  /** Custom page wrapper class */
  pageClass?: string;
  /** Custom page wrapper style */
  pageStyle?: Record<string, string>;
  /** Whether to include WXS script imports */
  includeWxs?: boolean;
  /** WXS module path */
  wxsPath?: string;
}

// ---------------------------------------------------------------------------
// Component mapping: LowCode componentName -> native WXML tag
// ---------------------------------------------------------------------------

/** Mapping from lowcode componentName to native WXML tag name and optional class */
const COMPONENT_WXML_MAP: Record<string, { tag: string; className?: string }> = {
  // Basic components
  View:       { tag: 'view' },
  NutView:    { tag: 'view' },
  Text:       { tag: 'text' },
  NutText:    { tag: 'text' },
  Image:      { tag: 'image' },
  NutImage:   { tag: 'image' },

  // NutUI -> native equivalents
  NutButton:  { tag: 'button' },
  NutSwiper:  { tag: 'swiper' },
  NutCell:    { tag: 'view', className: 'nut-cell' },
  NutDivider: { tag: 'view', className: 'nut-divider' },
  NutCard:    { tag: 'view', className: 'nut-card' },
  NutTabs:    { tag: 'view', className: 'nut-tabs' },
  NutTabPane: { tag: 'view', className: 'nut-tab-pane' },
  NutEmpty:   { tag: 'view', className: 'nut-empty' },
  NutInput:   { tag: 'input' },
  NutTextarea: { tag: 'textarea' },
  NutSwitch:  { tag: 'switch' },
  NutForm:    { tag: 'form' },
  NutRow:     { tag: 'view', className: 'nut-row' },
  NutCol:     { tag: 'view', className: 'nut-col' },
  NutSwiperItem: { tag: 'swiper-item' },
};

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Sanitize a string to be a valid WXS/JS identifier */
function sanitizeId(raw: string): string {
  return raw.replace(/[^a-zA-Z0-9_$]/g, '_');
}

/** Escape a string for WXML attribute values */
function escapeAttr(val: string): string {
  return val
    .replace(/&/g, '&amp;')
    .replace(/'/g, '&apos;')
    .replace(/"/g, '&quot;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
}

/** Escape text content for WXML */
function escapeTextContent(val: string): string {
  return val
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
}

/**
 * Extract the inner expression from a {{expression}} wrapper.
 * Returns null if the expression is not a simple binding.
 */
function extractBinding(expression: string): string | null {
  const match = expression.trim().match(/^\{\{([^}]+)\}\}$/);
  return match ? match[1].trim() : null;
}

/**
 * Convert an event name from the schema to a WXML bind event.
 * Maps: onTap -> bindtap, onInput -> bindinput, onChange -> bindchange, etc.
 */
function eventNameToWxmlBind(eventName: string): string {
  // Strip 'on' prefix and lowercase
  const stripped = eventName.replace(/^on/, '');
  const wxmlEvent = stripped.charAt(0).toLowerCase() + stripped.slice(1);
  return `bind${wxmlEvent}`;
}

/**
 * Build a handler function name for an event.
 * Convention: on<Component><Event>, e.g. onButtonTap, onInputChange
 */
function buildHandlerName(node: LowCodeNode, handler: EventHandler): string {
  const eventPascal = handler.event
    .replace(/^on/, '')
    .replace(/^./, (c) => c.toUpperCase());
  const componentPascal = node.componentName
    .replace(/^Nut/, '')
    .replace(/^./, (c) => c.toUpperCase());
  return `on${componentPascal}${eventPascal}`;
}

// ---------------------------------------------------------------------------
// Style helpers
// ---------------------------------------------------------------------------

/** Convert a style object to an inline style string */
function styleObjectToString(style: Record<string, string>): string {
  return Object.entries(style)
    .map(([key, value]) => `${camelToKebab(key)}: ${value}`)
    .join('; ');
}

/** Convert camelCase to kebab-case */
function camelToKebab(str: string): string {
  return str.replace(/([A-Z])/g, '-$1').toLowerCase();
}

/** Build style attribute from node props */
function buildStyleAttr(node: LowCodeNode): string | null {
  const props = node.props || {};

  // Check for explicit style prop
  if (props.style && typeof props.style === 'object') {
    return styleObjectToString(props.style);
  }

  if (props.style && typeof props.style === 'string') {
    return props.style;
  }

  // Check for width/height/color etc. in props
  const styleParts: string[] = [];
  const styleProps = ['width', 'height', 'fontSize', 'fontWeight', 'color', 'backgroundColor', 'padding', 'margin', 'borderRadius'];

  for (const prop of styleProps) {
    if (props[prop] !== undefined) {
      styleParts.push(`${camelToKebab(prop)}: ${props[prop]}`);
    }
  }

  return styleParts.length > 0 ? styleParts.join('; ') : null;
}

/** Build class attribute from node props and component mapping */
function buildClassAttr(node: LowCodeNode, mapping: { tag: string; className?: string }): string | null {
  const classes: string[] = [];

  // Add component-specific class from mapping
  if (mapping.className) {
    classes.push(mapping.className);
  }

  // Add className from props
  const props = node.props || {};
  if (props.className) {
    classes.push(props.className);
  }
  if (props.class) {
    classes.push(props.class);
  }

  return classes.length > 0 ? classes.join(' ') : null;
}

// ---------------------------------------------------------------------------
// Prop attribute mapping
// ---------------------------------------------------------------------------

/** Props that should be skipped (rendered as children or not applicable in WXML) */
const SKIP_PROPS = new Set([
  'className', 'class', 'style',
  'text', // NutText text is rendered as children
  'description', // NutEmpty description is rendered as children
  'title', // NutCell title is rendered as children
]);

/** Map a lowcode prop to a WXML attribute */
function propToWxmlAttr(key: string, value: any, componentName: string): string | null {
  if (SKIP_PROPS.has(key)) return null;

  // Special mappings
  const attrMap: Record<string, string> = {
    src: 'src',
    mode: 'mode',
    placeholder: 'placeholder',
    disabled: 'disabled',
    type: 'type',
    value: 'value',
    maxlength: 'maxlength',
    checked: 'checked',
  };

  const attrName = attrMap[key] || key;

  // Boolean attributes
  if (typeof value === 'boolean') {
    return value ? `${attrName}="{{true}}"` : `${attrName}="{{false}}"`;
  }

  // Number attributes
  if (typeof value === 'number') {
    return `${attrName}="{{${value}}}"`;
  }

  // String attributes
  if (typeof value === 'string') {
    // Check for data binding expressions
    if (value.includes('{{')) {
      return `${attrName}="${value}"`;
    }
    return `${attrName}="${escapeAttr(value)}"`;
  }

  // Skip null/undefined
  if (value === null || value === undefined) return null;

  // Objects/arrays -> JSON string
  return `${attrName}="${escapeAttr(JSON.stringify(value))}"`;
}

// ---------------------------------------------------------------------------
// Core WXML generation
// ---------------------------------------------------------------------------

/**
 * Recursively generate WXML from a LowCodeNode tree.
 * Returns the WXML string for the given node and its children.
 */
export function generateWxml(
  node: LowCodeNode,
  depth: number = 0,
): string {
  const pad = '  '.repeat(depth);

  // Skip the Page root — it is rendered as the page wrapper
  if (node.componentName === 'Page') {
    if (node.children && node.children.length > 0) {
      return node.children
        .map((child) => generateWxml(child, depth))
        .join('\n');
    }
    return `${pad}<!-- Empty page -->`;
  }

  const mapping = COMPONENT_WXML_MAP[node.componentName] || { tag: 'view' };
  const tag = mapping.tag;

  // Build attributes
  const attrs: string[] = [];

  // Class attribute
  const classAttr = buildClassAttr(node, mapping);
  if (classAttr) {
    attrs.push(`class="${escapeAttr(classAttr)}"`);
  }

  // Style attribute
  const styleAttr = buildStyleAttr(node);
  if (styleAttr) {
    attrs.push(`style="${escapeAttr(styleAttr)}"`);
  }

  // Conditional rendering (wx:if)
  if (node.visible) {
    const binding = extractBinding(node.visible);
    if (binding) {
      attrs.push(`wx:if="{{${binding}}}"`);
    } else {
      // Complex expression — wrap in wx:if
      attrs.push(`wx:if="${escapeAttr(node.visible)}"`);
    }
  }

  // List rendering (wx:for)
  if (node.loop) {
    const loop = node.loop;
    const itemName = loop.itemName || 'item';
    const indexName = loop.indexName || 'index';

    // Resolve data source expression
    const dataSourceExpr = resolveLoopDataSource(loop.dataSource);
    attrs.push(`wx:for="{{${dataSourceExpr}}}"`);
    attrs.push(`wx:key="id"`);
    attrs.push(`wx:for-item="${itemName}"`);
    attrs.push(`wx:for-index="${indexName}"`);
  }

  // Data binding on props
  const props = node.props || {};
  for (const [key, value] of Object.entries(props)) {
    if (SKIP_PROPS.has(key)) continue;

    // Check for data binding on this prop
    const bindingExpr = node.dataBinding?.bindings?.[key];
    if (bindingExpr) {
      const binding = extractBinding(bindingExpr);
      if (binding) {
        attrs.push(`${key}="{{${binding}}}"`);
      } else {
        attrs.push(`${key}="${escapeAttr(bindingExpr)}"`);
      }
      continue;
    }

    // Regular prop
    const attr = propToWxmlAttr(key, value, node.componentName);
    if (attr) attrs.push(attr);
  }

  // Event binding
  if (node.events) {
    for (const handler of node.events) {
      const wxmlEvent = eventNameToWxmlBind(handler.event);
      const handlerName = buildHandlerName(node, handler);
      attrs.push(`${wxmlEvent}="${handlerName}"`);
    }
  }

  // Build opening tag
  const attrStr = attrs.length > 0 ? ' ' + attrs.join(' ') : '';

  // Self-closing tag for void elements
  const voidTags = new Set(['input', 'image', 'switch']);
  const hasChildren = node.children && node.children.length > 0;
  const nodeHasText = hasTextContent(node);

  if (voidTags.has(tag) && !hasChildren && !nodeHasText) {
    return `${pad}<${tag}${attrStr} />`;
  }

  // Text content
  if (nodeHasText && !hasChildren) {
    const text = extractTextContent(node);
    return `${pad}<${tag}${attrStr}>${escapeTextContent(text)}</${tag}>`;
  }

  // Container with children
  if (hasChildren) {
    const childrenWxml = node.children!
      .map((child) => generateWxml(child, depth + 1))
      .join('\n');
    return `${pad}<${tag}${attrStr}>\n${childrenWxml}\n${pad}</${tag}>`;
  }

  // Empty container
  return `${pad}<${tag}${attrStr}></${tag}>`;
}

/**
 * Resolve a loop data source expression for WXML.
 * Converts {{api.users.data.list}} -> usersData.list
 * Converts {{state.items}} -> items
 */
function resolveLoopDataSource(expression: string): string {
  const binding = extractBinding(expression);
  if (!binding) return expression.replace(/\{\{|\}\}/g, '').trim();

  // api.xxx.yyy -> xxxData.yyy
  if (binding.startsWith('api.')) {
    const rest = binding.slice(4);
    const parts = rest.split('.');
    const dsId = parts[0];
    const suffix = parts.length > 1 ? '.' + parts.slice(1).join('.') : '';
    return `${sanitizeId(dsId)}Data${suffix}`;
  }

  // dataSource.xxx -> xxxData
  if (binding.startsWith('dataSource.')) {
    const rest = binding.slice(11);
    const parts = rest.split('.');
    const dsId = parts[0];
    const suffix = parts.length > 1 ? '.' + parts.slice(1).join('.') : '';
    return `${sanitizeId(dsId)}Data${suffix}`;
  }

  // ds.xxx -> xxxData
  if (binding.startsWith('ds.')) {
    const rest = binding.slice(3);
    const parts = rest.split('.');
    const dsId = parts[0];
    const suffix = parts.length > 1 ? '.' + parts.slice(1).join('.') : '';
    return `${sanitizeId(dsId)}Data${suffix}`;
  }

  // state.xxx -> xxx
  if (binding.startsWith('state.')) {
    return binding.slice(6);
  }

  return binding;
}

/** Check if a node has text content in its props */
function hasTextContent(node: LowCodeNode): boolean {
  const props = node.props || {};
  switch (node.componentName) {
    case 'NutText':
    case 'Text':
      return !!props.text;
    case 'NutButton':
      return !!props.text;
    case 'NutEmpty':
      return !!props.description;
    case 'NutCell':
      return !!(props.title || props.description);
    default:
      return false;
  }
}

/** Extract text content from a leaf node */
function extractTextContent(node: LowCodeNode): string {
  const props = node.props || {};
  switch (node.componentName) {
    case 'NutText':
    case 'Text':
      return props.text || '';
    case 'NutButton':
      return props.text || '';
    case 'NutEmpty':
      return props.description || '暂无数据';
    case 'NutCell':
      return props.title || props.description || '';
    default:
      return '';
  }
}

// ---------------------------------------------------------------------------
// Collect all event handlers for JS generation
// ---------------------------------------------------------------------------

/** Collected event handler info */
export interface CollectedHandler {
  /** Handler function name */
  name: string;
  /** Original event name from schema */
  event: string;
  /** Actions to execute */
  actions: { type: string; payload: Record<string, any> }[];
  /** Source node id */
  nodeId: string;
}

/**
 * Collect all unique event handlers from the schema tree.
 * Used for generating the corresponding .js file.
 */
export function collectEventHandlers(schema: LowCodeSchema): CollectedHandler[] {
  const handlers: CollectedHandler[] = [];
  const seen = new Set<string>();

  function walk(nodes: LowCodeNode[]) {
    for (const node of nodes) {
      if (node.events) {
        for (const handler of node.events) {
          const name = buildHandlerName(node, handler);
          if (seen.has(name)) continue;
          seen.add(name);
          handlers.push({
            name,
            event: handler.event,
            actions: handler.actions,
            nodeId: node.id,
          });
        }
      }
      if (node.children) walk(node.children);
    }
  }

  walk(schema.children ?? []);
  return handlers;
}

/**
 * Collect all data-binding expressions from the schema tree.
 * Returns a set of variable names referenced in bindings.
 */
export function collectDataBindings(schema: LowCodeSchema): Set<string> {
  const bindings = new Set<string>();

  function walk(nodes: LowCodeNode[]) {
    for (const node of nodes) {
      // Data binding props
      if (node.dataBinding?.bindings) {
        for (const expr of Object.values(node.dataBinding.bindings)) {
          const binding = extractBinding(expr);
          if (binding) {
            // Extract variable name (strip prefixes like state., api., etc.)
            const varName = resolveVarName(binding);
            if (varName) bindings.add(varName);
          }
        }
      }

      // Visibility expression
      if (node.visible) {
        const binding = extractBinding(node.visible);
        if (binding) {
          const varName = resolveVarName(binding);
          if (varName) bindings.add(varName);
        }
      }

      // Loop data source
      if (node.loop?.dataSource) {
        const binding = extractBinding(node.loop.dataSource);
        if (binding) {
          const varName = resolveVarName(binding);
          if (varName) bindings.add(varName);
        }
      }

      // Props with {{}} expressions
      const props = node.props || {};
      for (const value of Object.values(props)) {
        if (typeof value === 'string' && value.includes('{{')) {
          const matches = value.match(/\{\{([^}]+)\}\}/g);
          if (matches) {
            for (const match of matches) {
              const inner = match.slice(2, -2).trim();
              const varName = resolveVarName(inner);
              if (varName) bindings.add(varName);
            }
          }
        }
      }

      if (node.children) walk(node.children);
    }
  }

  walk(schema.children ?? []);
  return bindings;
}

/** Resolve a binding expression to a variable name */
function resolveVarName(expr: string): string | null {
  if (expr.startsWith('state.')) {
    return expr.slice(6).split('.')[0];
  }
  if (expr.startsWith('api.') || expr.startsWith('dataSource.') || expr.startsWith('ds.')) {
    return null; // Data sources are handled separately
  }
  // Direct variable reference
  return expr.split('.')[0];
}

// ---------------------------------------------------------------------------
// Main entry: generateWxmlPage
// ---------------------------------------------------------------------------

/**
 * Generate a complete WXML page from a LowCodeSchema.
 *
 * @param schema - The page schema root (componentName should be 'Page')
 * @param options - Generation options
 * @returns Complete WXML source string
 */
export function generateWxmlPage(
  schema: LowCodeSchema,
  options: GenerateWxmlOptions = {},
): string {
  const sections: string[] = [];

  // --- Header comment ---
  sections.push(
    [
      '<!-- Auto-generated by lowcode codegen -->',
      '<!-- Do not edit manually — changes will be overwritten on next generation. -->',
      `<!-- Generated at: ${new Date().toISOString()} -->`,
      '',
    ].join('\n'),
  );

  // --- Page wrapper ---
  const pageClass = options.pageClass || 'page';
  const pageStyle = options.pageStyle
    ? ` style="${escapeAttr(styleObjectToString(options.pageStyle))}"`
    : '';

  // --- Generate inner WXML ---
  const innerWxml = generateWxml(
    { ...schema, componentName: 'Page' } as LowCodeNode,
    1,
  );

  sections.push(`<view class="${pageClass}"${pageStyle}>`);
  sections.push(innerWxml);
  sections.push('</view>');

  return sections.join('\n');
}

/**
 * Generate a WXML import statement for a template file.
 * Used when the page imports reusable component templates.
 */
export function generateTemplateImport(
  templateName: string,
  templatePath: string,
): string {
  return `<import src="${escapeAttr(templatePath)}" />\n<template is="${escapeAttr(templateName)}" data="{{...${sanitizeId(templateName)}Data}}" />`;
}

/**
 * Generate WXS module import for utility functions.
 */
export function generateWxsImport(moduleName: string, src: string): string {
  return `<wxs module="${escapeAttr(moduleName)}" src="${escapeAttr(src)}" />`;
}
