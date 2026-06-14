/**
 * Lightweight, safe expression evaluator for low-code dynamic prop values.
 *
 * Design:
 * - Hand-written recursive-descent parser with precedence climbing.
 * - AST output evaluated via tree-walk — no eval(), no Function().
 * - Expressions are validated on save; only the supported grammar is executable.
 *
 * Grammar (precedence low -> high):
 *   expr       -> ternary
 *   ternary    -> logical_or ('?' expr ':' expr)?
 *   logical_or -> logical_and ('||' logical_and)*
 *   logical_and-> equality ('&&' equality)*
 *   equality   -> comparison (('===' | '!==') comparison)*
 *   comparison -> addition (('>' | '<' | '>=' | '<=') addition)*
 *   addition   -> multiplicity (('+' | '-') multiplicity)*
 *   multiplicity-> unary (('*' | '/' | '%') unary)*
 *   unary      -> ('!' | '-') unary | call
 *   call       -> primary ('.' IDENT | '[' expr ']' | '(' args ')')*
 *   primary    -> NUMBER | STRING | 'true' | 'false' | 'null' | 'undefined'
 *               | IDENT | '(' expr ')'
 */

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

/** Variable lookup context for expression evaluation. */
export type ExpressionContext = Record<string, any>;

/** AST node types produced by the parser. */
type NodeType =
  | 'NumberLiteral'
  | 'StringLiteral'
  | 'BooleanLiteral'
  | 'NullLiteral'
  | 'UndefinedLiteral'
  | 'Identifier'
  | 'BinaryOp'
  | 'UnaryOp'
  | 'Ternary'
  | 'MemberAccess'
  | 'IndexAccess'
  | 'FunctionCall'
  | 'ArrowFunction';

interface BaseNode {
  type: NodeType;
}

interface NumberLiteralNode extends BaseNode { type: 'NumberLiteral'; value: number; }
interface StringLiteralNode extends BaseNode { type: 'StringLiteral'; value: string; }
interface BooleanLiteralNode extends BaseNode { type: 'BooleanLiteral'; value: boolean; }
interface NullLiteralNode extends BaseNode { type: 'NullLiteral'; }
interface UndefinedLiteralNode extends BaseNode { type: 'UndefinedLiteral'; }
interface IdentifierNode extends BaseNode { type: 'Identifier'; name: string; }

interface BinaryOpNode extends BaseNode {
  type: 'BinaryOp';
  op: string;
  left: ASTNode;
  right: ASTNode;
}

interface UnaryOpNode extends BaseNode {
  type: 'UnaryOp';
  op: '!' | '-';
  operand: ASTNode;
}

interface TernaryNode extends BaseNode {
  type: 'Ternary';
  condition: ASTNode;
  consequent: ASTNode;
  alternate: ASTNode;
}

interface MemberAccessNode extends BaseNode {
  type: 'MemberAccess';
  object: ASTNode;
  property: string;
}

interface IndexAccessNode extends BaseNode {
  type: 'IndexAccess';
  object: ASTNode;
  index: ASTNode;
}

interface FunctionCallNode extends BaseNode {
  type: 'FunctionCall';
  callee: ASTNode;
  args: ASTNode[];
}

interface ArrowFunctionNode extends BaseNode {
  type: 'ArrowFunction';
  params: string[];
  body: ASTNode;
}

type ASTNode =
  | NumberLiteralNode
  | StringLiteralNode
  | BooleanLiteralNode
  | NullLiteralNode
  | UndefinedLiteralNode
  | IdentifierNode
  | BinaryOpNode
  | UnaryOpNode
  | TernaryNode
  | MemberAccessNode
  | IndexAccessNode
  | FunctionCallNode
  | ArrowFunctionNode;

// ---------------------------------------------------------------------------
// Tokeniser
// ---------------------------------------------------------------------------

type TokenType =
  | 'Number'
  | 'String'
  | 'Ident'
  | 'Operator'
  | 'Punctuation'
  | 'EOF';

interface Token {
  type: TokenType;
  value: string;
  pos: number;
}

const KEYWORDS = new Set(['true', 'false', 'null', 'undefined']);

const TWO_CHAR_OPS = new Set(['===', '!==', '>=', '<=', '&&', '||', '=>']);

function tokenize(input: string): Token[] {
  const tokens: Token[] = [];
  let i = 0;
  const len = input.length;

  while (i < len) {
    const ch = input[i];

    // whitespace
    if (ch === ' ' || ch === '\t' || ch === '\n' || ch === '\r') {
      i++;
      continue;
    }

    // number (supports decimals and leading dots like .5)
    if ((ch >= '0' && ch <= '9') || (ch === '.' && i + 1 < len && input[i + 1] >= '0' && input[i + 1] <= '9')) {
      const start = i;
      while (i < len && input[i] >= '0' && input[i] <= '9') i++;
      if (i < len && input[i] === '.') {
        i++;
        while (i < len && input[i] >= '0' && input[i] <= '9') i++;
      }
      tokens.push({ type: 'Number', value: input.slice(start, i), pos: start });
      continue;
    }

    // string literal (single or double quotes)
    if (ch === "'" || ch === '"') {
      const quote = ch;
      const start = i;
      i++;
      let escaped = false;
      while (i < len) {
        if (escaped) {
          escaped = false;
          i++;
          continue;
        }
        if (input[i] === '\\') {
          escaped = true;
          i++;
          continue;
        }
        if (input[i] === quote) {
          i++;
          break;
        }
        i++;
      }
      tokens.push({ type: 'String', value: input.slice(start + 1, i - 1), pos: start });
      continue;
    }

    // identifier / keyword
    if ((ch >= 'a' && ch <= 'z') || (ch >= 'A' && ch <= 'Z') || ch === '_' || ch === '$') {
      const start = i;
      while (i < len && ((input[i] >= 'a' && input[i] <= 'z') || (input[i] >= 'A' && input[i] <= 'Z') || (input[i] >= '0' && input[i] <= '9') || input[i] === '_' || input[i] === '$')) {
        i++;
      }
      const word = input.slice(start, i);
      tokens.push({ type: 'Ident', value: word, pos: start });
      continue;
    }

    // two-char operators
    if (i + 1 < len) {
      const two = input.slice(i, i + 2);
      if (TWO_CHAR_OPS.has(two)) {
        tokens.push({ type: 'Operator', value: two, pos: i });
        i += 2;
        continue;
      }
    }

    // single-char operators and punctuation
    if ('+-*/%!<>=?:'.includes(ch)) {
      tokens.push({ type: 'Operator', value: ch, pos: i });
      i++;
      continue;
    }

    if ('()[],'.includes(ch)) {
      tokens.push({ type: 'Punctuation', value: ch, pos: i });
      i++;
      continue;
    }

    // dot for member access
    if (ch === '.') {
      tokens.push({ type: 'Punctuation', value: '.', pos: i });
      i++;
      continue;
    }

    // unknown character — skip to avoid hard failure during tokenise
    i++;
  }

  tokens.push({ type: 'EOF', value: '', pos: i });
  return tokens;
}

// ---------------------------------------------------------------------------
// Parser (recursive-descent with precedence climbing)
// ---------------------------------------------------------------------------

class Parser {
  private tokens: Token[];
  private pos: number;

  constructor(tokens: Token[]) {
    this.tokens = tokens;
    this.pos = 0;
  }

  private peek(): Token {
    return this.tokens[this.pos];
  }

  private advance(): Token {
    const t = this.tokens[this.pos];
    this.pos++;
    return t;
  }

  private expect(type: TokenType, value?: string): Token {
    const t = this.advance();
    if (t.type !== type || (value !== undefined && t.value !== value)) {
      throw new SyntaxError(
        `Expected ${type}${value ? ` "${value}"` : ''} at position ${t.pos}, got ${t.type} "${t.value}"`,
      );
    }
    return t;
  }

  parse(): ASTNode {
    const node = this.parseExpr();
    if (this.peek().type !== 'EOF') {
      throw new SyntaxError(`Unexpected token "${this.peek().value}" at position ${this.peek().pos}`);
    }
    return node;
  }

  // ---- precedence levels (low -> high) ----

  private isArrowFunctionParams(): boolean {
    let i = this.pos;
    if (this.tokens[i]?.type !== 'Punctuation' || this.tokens[i]?.value !== '(') return false;
    i++;
    if (this.tokens[i]?.type !== 'Ident') return false;
    i++;
    while (this.tokens[i]?.type === 'Punctuation' && this.tokens[i]?.value === ',') {
      i++;
      if (this.tokens[i]?.type !== 'Ident') return false;
      i++;
    }
    if (this.tokens[i]?.type !== 'Punctuation' || this.tokens[i]?.value !== ')') return false;
    i++;
    return this.tokens[i]?.type === 'Operator' && this.tokens[i]?.value === '=>';
  }

  private parseExpr(): ASTNode {
    if (this.isArrowFunctionParams()) {
      this.advance(); // consume (
      const params: string[] = [this.expect('Ident').value];
      while (this.peek().type === 'Punctuation' && this.peek().value === ',') {
        this.advance();
        params.push(this.expect('Ident').value);
      }
      this.expect('Punctuation', ')');
      this.expect('Operator', '=>');
      const body = this.parseExpr();
      return { type: 'ArrowFunction', params, body };
    }

    const left = this.parseTernary();
    if (this.peek().type === 'Operator' && this.peek().value === '=>') {
      if (left.type !== 'Identifier') {
        throw new SyntaxError('Invalid arrow function parameters');
      }
      this.advance();
      const body = this.parseExpr();
      return { type: 'ArrowFunction', params: [left.name], body };
    }
    return left;
  }

  private parseTernary(): ASTNode {
    const condition = this.parseLogicalOr();
    if (this.peek().type === 'Operator' && this.peek().value === '?') {
      this.advance(); // consume '?'
      const consequent = this.parseExpr();
      this.expect('Operator', ':');
      const alternate = this.parseExpr();
      return { type: 'Ternary', condition, consequent, alternate };
    }
    return condition;
  }

  private parseLogicalOr(): ASTNode {
    let left = this.parseLogicalAnd();
    while (this.peek().type === 'Operator' && this.peek().value === '||') {
      this.advance();
      const right = this.parseLogicalAnd();
      left = { type: 'BinaryOp', op: '||', left, right };
    }
    return left;
  }

  private parseLogicalAnd(): ASTNode {
    let left = this.parseEquality();
    while (this.peek().type === 'Operator' && this.peek().value === '&&') {
      this.advance();
      const right = this.parseEquality();
      left = { type: 'BinaryOp', op: '&&', left, right };
    }
    return left;
  }

  private parseEquality(): ASTNode {
    let left = this.parseComparison();
    while (this.peek().type === 'Operator' && (this.peek().value === '===' || this.peek().value === '!==')) {
      const op = this.advance().value;
      const right = this.parseComparison();
      left = { type: 'BinaryOp', op, left, right };
    }
    return left;
  }

  private parseComparison(): ASTNode {
    let left = this.parseAddition();
    const ops = new Set(['>', '<', '>=', '<=']);
    while (this.peek().type === 'Operator' && ops.has(this.peek().value)) {
      const op = this.advance().value;
      const right = this.parseAddition();
      left = { type: 'BinaryOp', op, left, right };
    }
    return left;
  }

  private parseAddition(): ASTNode {
    let left = this.parseMultiplication();
    while (this.peek().type === 'Operator' && (this.peek().value === '+' || this.peek().value === '-')) {
      const op = this.advance().value;
      const right = this.parseMultiplication();
      left = { type: 'BinaryOp', op, left, right };
    }
    return left;
  }

  private parseMultiplication(): ASTNode {
    let left = this.parseUnary();
    while (this.peek().type === 'Operator' && (this.peek().value === '*' || this.peek().value === '/' || this.peek().value === '%')) {
      const op = this.advance().value;
      const right = this.parseUnary();
      left = { type: 'BinaryOp', op, left, right };
    }
    return left;
  }

  private parseUnary(): ASTNode {
    if (this.peek().type === 'Operator' && (this.peek().value === '!' || this.peek().value === '-')) {
      const op = this.advance().value as '!' | '-';
      const operand = this.parseUnary();
      return { type: 'UnaryOp', op, operand };
    }
    return this.parseCall();
  }

  // call / member access / index access — left-recursive, unrolled into a loop
  private parseCall(): ASTNode {
    let node = this.parsePrimary();
    for (;;) {
      const t = this.peek();
      // member access: .property
      if (t.type === 'Punctuation' && t.value === '.') {
        this.advance();
        const prop = this.expect('Ident');
        node = { type: 'MemberAccess', object: node, property: prop.value };
        continue;
      }
      // index access: [expr]
      if (t.type === 'Punctuation' && t.value === '[') {
        this.advance();
        const index = this.parseExpr();
        this.expect('Punctuation', ']');
        node = { type: 'IndexAccess', object: node, index };
        continue;
      }
      // function call: (args)
      if (t.type === 'Punctuation' && t.value === '(') {
        this.advance();
        const args: ASTNode[] = [];
        if (!(this.peek().type === 'Punctuation' && this.peek().value === ')')) {
          args.push(this.parseExpr());
          while (this.peek().type === 'Punctuation' && this.peek().value === ',') {
            this.advance();
            args.push(this.parseExpr());
          }
        }
        this.expect('Punctuation', ')');
        node = { type: 'FunctionCall', callee: node, args };
        continue;
      }
      break;
    }
    return node;
  }

  private parsePrimary(): ASTNode {
    const t = this.peek();

    // number literal
    if (t.type === 'Number') {
      this.advance();
      return { type: 'NumberLiteral', value: parseFloat(t.value) };
    }

    // string literal
    if (t.type === 'String') {
      this.advance();
      return { type: 'StringLiteral', value: t.value };
    }

    // keywords: true, false, null, undefined
    if (t.type === 'Ident' && KEYWORDS.has(t.value)) {
      this.advance();
      if (t.value === 'true') return { type: 'BooleanLiteral', value: true };
      if (t.value === 'false') return { type: 'BooleanLiteral', value: false };
      if (t.value === 'null') return { type: 'NullLiteral' };
      return { type: 'UndefinedLiteral' };
    }

    // identifier
    if (t.type === 'Ident') {
      this.advance();
      return { type: 'Identifier', name: t.value };
    }

    // parenthesised sub-expression
    if (t.type === 'Punctuation' && t.value === '(') {
      this.advance();
      const inner = this.parseExpr();
      this.expect('Punctuation', ')');
      return inner;
    }

    throw new SyntaxError(`Unexpected token "${t.value}" at position ${t.pos}`);
  }
}

// ---------------------------------------------------------------------------
// AST evaluator (tree-walk)
// ---------------------------------------------------------------------------

/** Built-in functions available inside expressions. */
const BUILTINS: Record<string, (...args: any[]) => any> = {
  formatDate(value: any, pattern?: string): string {
    if (value == null) return '';
    const d = value instanceof Date ? value : new Date(value);
    if (isNaN(d.getTime())) return '';
    // Simple formatter — not a full date-fns replacement.
    if (!pattern) return d.toISOString();
    const pad = (n: number) => String(n).padStart(2, '0');
    return pattern
      .replace('YYYY', String(d.getFullYear()))
      .replace('MM', pad(d.getMonth() + 1))
      .replace('DD', pad(d.getDate()))
      .replace('HH', pad(d.getHours()))
      .replace('mm', pad(d.getMinutes()))
      .replace('ss', pad(d.getSeconds()));
  },

  formatPrice(value: any, decimals: number = 2): string {
    const n = Number(value);
    if (isNaN(n)) return '0.00';
    return n.toFixed(decimals);
  },

  concat(...args: any[]): string {
    return args.map(String).join('');
  },

  length(value: any): number {
    if (value == null) return 0;
    if (typeof value === 'string' || Array.isArray(value)) return value.length;
    if (typeof value === 'object') return Object.keys(value).length;
    return 0;
  },

  first(value: any): any {
    if (Array.isArray(value) && value.length > 0) return value[0];
    return undefined;
  },

  last(value: any): any {
    if (Array.isArray(value) && value.length > 0) return value[value.length - 1];
    return undefined;
  },

  includes(haystack: any, needle: any): boolean {
    if (typeof haystack === 'string') return haystack.includes(String(needle));
    if (Array.isArray(haystack)) return haystack.includes(needle);
    return false;
  },

  // Array methods
  map(arr: any[], fn: (...args: any[]) => any): any[] {
    return arr.map(fn);
  },
  filter(arr: any[], fn: (...args: any[]) => boolean): any[] {
    return arr.filter(fn);
  },
  reduce(arr: any[], fn: (...args: any[]) => any, init: any): any {
    return arr.reduce(fn, init);
  },
  find(arr: any[], fn: (...args: any[]) => boolean): any {
    return arr.find(fn);
  },
  some(arr: any[], fn: (...args: any[]) => boolean): boolean {
    return arr.some(fn);
  },
  every(arr: any[], fn: (...args: any[]) => boolean): boolean {
    return arr.every(fn);
  },
  sort(arr: any[], fn?: (a: any, b: any) => number): any[] {
    return [...arr].sort(fn);
  },
  flat(arr: any[], depth: number = 1): any[] {
    return arr.flat(depth);
  },

  // 数学函数
  min: (...args: number[]) => Math.min(...args),
  max: (...args: number[]) => Math.max(...args),
  round: (n: number) => Math.round(n),
  abs: (n: number) => Math.abs(n),
  floor: (n: number) => Math.floor(n),
  ceil: (n: number) => Math.ceil(n),
};

// 字符串方法映射（非原生方法）
const STRING_METHODS: Record<string, (...args: any[]) => any> = {
  upper: (s: string) => s.toUpperCase(),
  lower: (s: string) => s.toLowerCase(),
  replace: (s: string, search: string, replacement: string) => s.replace(search, replacement),
  slice: (s: string, start: number, end?: number) => s.slice(start, end),
};

// 危险属性名黑名单，防止原型链污染
const DANGEROUS_KEYS = new Set([
  '__proto__',
  'constructor',
  'prototype',
  '__defineGetter__',
  '__defineSetter__',
  '__lookupGetter__',
  '__lookupSetter__',
  'hasOwnProperty',
  'isPrototypeOf',
  'propertyIsEnumerable',
  'toLocaleString',
  'toString',
  'valueOf',
]);

function safeGet(obj: any, key: string): any {
  if (obj == null) return undefined;
  // 阻止访问危险属性（原型链污染防护）
  if (DANGEROUS_KEYS.has(key)) {
    return undefined;
  }
  return obj[key];
}

function evaluate(node: ASTNode, ctx: ExpressionContext): any {
  switch (node.type) {
    case 'NumberLiteral':
      return node.value;
    case 'StringLiteral':
      return node.value;
    case 'BooleanLiteral':
      return node.value;
    case 'NullLiteral':
      return null;
    case 'UndefinedLiteral':
      return undefined;
    case 'Identifier':
      return ctx[node.name];
    case 'BinaryOp': {
      const left = evaluate(node.left, ctx);
      // Short-circuit for logical operators
      if (node.op === '&&') return left ? evaluate(node.right, ctx) : left;
      if (node.op === '||') return left ? left : evaluate(node.right, ctx);
      const right = evaluate(node.right, ctx);
      switch (node.op) {
        case '===': return left === right;
        case '!==': return left !== right;
        case '>': return left > right;
        case '<': return left < right;
        case '>=': return left >= right;
        case '<=': return left <= right;
        case '+': return left + right;
        case '-': return left - right;
        case '*': return left * right;
        case '/': return left / right;
        case '%': return left % right;
        default: return undefined;
      }
    }
    case 'UnaryOp': {
      const operand = evaluate(node.operand, ctx);
      return node.op === '!' ? !operand : -operand;
    }
    case 'Ternary':
      return evaluate(node.condition, ctx)
        ? evaluate(node.consequent, ctx)
        : evaluate(node.alternate, ctx);
    case 'MemberAccess': {
      const obj = evaluate(node.object, ctx);
      return safeGet(obj, node.property);
    }
    case 'IndexAccess': {
      const obj = evaluate(node.object, ctx);
      const key = evaluate(node.index, ctx);
      // 阻止访问危险属性（原型链污染防护）
      if (typeof key === 'string' && DANGEROUS_KEYS.has(key)) {
        return undefined;
      }
      return obj == null ? undefined : obj[key];
    }
    case 'FunctionCall': {
      if (node.callee.type === 'MemberAccess') {
        const obj = evaluate(node.callee.object, ctx);
        const methodName = node.callee.property;
        const args = node.args.map((a) => evaluate(a, ctx));
        // 字符串方法分发
        if (typeof obj === 'string' && methodName in STRING_METHODS) {
          return STRING_METHODS[methodName](obj, ...args);
        }
        const method = safeGet(obj, methodName);
        if (typeof method === 'function') {
          return method.call(obj, ...args);
        }
        return undefined;
      }
      const callee = evaluate(node.callee, ctx);
      const args = node.args.map((a) => evaluate(a, ctx));
      if (typeof callee === 'function') {
        return callee(...args);
      }
      return undefined;
    }
    case 'ArrowFunction': {
      const paramNames = node.params;
      const bodyNode = node.body;
      return (...callArgs: any[]) => {
        const childCtx = { ...ctx };
        paramNames.forEach((name, i) => {
          childCtx[name] = callArgs[i];
        });
        return evaluate(bodyNode, childCtx);
      };
    }
    default:
      return undefined;
  }
}

// ---------------------------------------------------------------------------
// Template syntax detection & expansion
// ---------------------------------------------------------------------------

/**
 * Detects the `${...}` template-literal-like syntax.
 * If the expression is a string that starts with `${` and ends with `}`,
 * and contains no other literal text, it is treated as a pure expression.
 * Otherwise each `${...}` segment is individually evaluated and the results
 * are concatenated into a string.
 */
function isTemplateExpression(expr: string): boolean {
  return expr.startsWith('${') && expr.endsWith('}');
}

function extractTemplateSegments(expr: string): { type: 'text' | 'expr'; value: string }[] {
  const segments: { type: 'text' | 'expr'; value: string }[] = [];
  let i = 0;
  const len = expr.length;

  while (i < len) {
    const dollarIdx = expr.indexOf('${', i);
    if (dollarIdx === -1) {
      // remaining text
      if (i < len) segments.push({ type: 'text', value: expr.slice(i) });
      break;
    }
    // text before ${
    if (dollarIdx > i) {
      segments.push({ type: 'text', value: expr.slice(i, dollarIdx) });
    }
    // find matching }
    let depth = 1;
    let j = dollarIdx + 2;
    while (j < len && depth > 0) {
      if (expr[j] === '{') depth++;
      else if (expr[j] === '}') depth--;
      j++;
    }
    if (depth !== 0) {
      throw new SyntaxError('Unmatched ${ in expression');
    }
    segments.push({ type: 'expr', value: expr.slice(dollarIdx + 2, j - 1) });
    i = j;
  }
  return segments;
}

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

/**
 * Parse an expression string into an AST.
 *
 * @throws {SyntaxError} when the expression has invalid syntax.
 */
export function parseExpression(expr: string): ASTNode {
  const trimmed = expr.trim();
  const tokens = tokenize(trimmed);
  return new Parser(tokens).parse();
}

/**
 * Validate that an expression string is syntactically correct.
 * Returns `{ valid: true }` or `{ valid: false, error }`.
 */
export function validateExpression(expr: string): { valid: true } | { valid: false; error: string } {
  try {
    const trimmed = expr.trim();

    // Template syntax: validate each embedded expression
    if (trimmed.startsWith('${') || trimmed.includes('${')) {
      const segments = extractTemplateSegments(trimmed);
      for (const seg of segments) {
        if (seg.type === 'expr') {
          parseExpression(seg.value);
        }
      }
      return { valid: true };
    }

    parseExpression(trimmed);
    return { valid: true };
  } catch (e: any) {
    return { valid: false, error: e.message || String(e) };
  }
}

/**
 * Evaluate an expression against the given context.
 *
 * Supports:
 * - Plain expressions: `pageState.doctor.name`
 * - Template syntax: `Hello, ${pageState.user.name}!`
 *
 * Built-in functions are injected into the evaluation context automatically.
 *
 * @param expr  The expression string to evaluate.
 * @param ctx   Variable lookup context.
 * @returns     The evaluated result (type depends on the expression).
 */
export function evaluateExpression(expr: string, ctx: ExpressionContext): any {
  const trimmed = expr.trim();

  // Template syntax: evaluate embedded expressions, concatenate into string
  if (trimmed.includes('${')) {
    const segments = extractTemplateSegments(trimmed);
    const result = segments
      .map((seg) => {
        if (seg.type === 'text') return seg.value;
        try {
          const ast = parseExpression(seg.value);
          const merged = { ...BUILTINS, ...ctx };
          const val = evaluate(ast, merged);
          return val == null ? '' : String(val);
        } catch {
          return '';
        }
      })
      .join('');
    return result;
  }

  // Pure expression
  const ast = parseExpression(trimmed);
  const merged = { ...BUILTINS, ...ctx };
  return evaluate(ast, merged);
}
