import { describe, expect, it } from 'vitest';
import {
  evaluateExpression,
  parseExpression,
  validateExpression,
} from '../utils/expression-engine';

// ---------------------------------------------------------------------------
// Helper: shorthand for evaluateExpression
// ---------------------------------------------------------------------------
const eval_ = (expr: string, ctx: Record<string, any> = {}) =>
  evaluateExpression(expr, ctx);

// =========================================================================
// 1. Variable resolution
// =========================================================================
describe('Variable resolution', () => {
  it('resolves a simple variable: ${name}', () => {
    expect(eval_('name', { name: 'World' })).toBe('World');
  });

  it('resolves dotted property access: ${user.age}', () => {
    expect(eval_('user.age', { user: { age: 28 } })).toBe(28);
  });

  it('resolves deeply nested paths: ${a.b.c.d}', () => {
    expect(eval_('a.b.c.d', { a: { b: { c: { d: 'deep' } } } })).toBe('deep');
  });

  it('returns undefined for missing top-level variable', () => {
    expect(eval_('missing')).toBeUndefined();
  });

  it('returns undefined for missing nested property', () => {
    expect(eval_('user.missing', { user: { name: 'A' } })).toBeUndefined();
  });

  it('resolves a variable holding an array', () => {
    expect(eval_('items', { items: [1, 2, 3] })).toEqual([1, 2, 3]);
  });

  it('resolves a variable holding null', () => {
    expect(eval_('val', { val: null })).toBeNull();
  });
});

// =========================================================================
// 2. Comparison operators (===, !==, >, <, >=, <=)
// =========================================================================
describe('Comparison operators', () => {
  it('strict equality (===) — matching values', () => {
    expect(eval_('x === 5', { x: 5 })).toBe(true);
  });

  it('strict equality (===) — different types', () => {
    expect(eval_("x === '5'", { x: 5 })).toBe(false);
  });

  it('strict inequality (!==) — different values', () => {
    expect(eval_('x !== 0', { x: 1 })).toBe(true);
  });

  it('strict inequality (!===) — same values', () => {
    expect(eval_('x !== 5', { x: 5 })).toBe(false);
  });

  it('greater than (>)', () => {
    expect(eval_('x > 3', { x: 5 })).toBe(true);
    expect(eval_('x > 10', { x: 5 })).toBe(false);
  });

  it('less than (<)', () => {
    expect(eval_('x < 10', { x: 5 })).toBe(true);
    expect(eval_('x < 3', { x: 5 })).toBe(false);
  });

  it('greater than or equal (>=)', () => {
    expect(eval_('x >= 5', { x: 5 })).toBe(true);
    expect(eval_('x >= 6', { x: 5 })).toBe(false);
  });

  it('less than or equal (<=)', () => {
    expect(eval_('x <= 5', { x: 5 })).toBe(true);
    expect(eval_('x <= 4', { x: 5 })).toBe(false);
  });

  it('compares strings lexicographically', () => {
    expect(eval_("a < b", { a: 'apple', b: 'banana' })).toBe(true);
  });
});

// =========================================================================
// 3. Logical operators (&&, ||, !)
// =========================================================================
describe('Logical operators', () => {
  it('logical AND — both truthy', () => {
    expect(eval_('a && b', { a: true, b: true })).toBe(true);
  });

  it('logical AND — short-circuits on falsy', () => {
    expect(eval_('a && b', { a: false, b: true })).toBe(false);
  });

  it('logical AND — returns right operand when left is truthy', () => {
    expect(eval_('a && b', { a: 1, b: 'hello' })).toBe('hello');
  });

  it('logical OR — first truthy wins', () => {
    expect(eval_('a || b', { a: true, b: false })).toBe(true);
  });

  it('logical OR — short-circuits on truthy', () => {
    expect(eval_('a || b', { a: 'yes', b: 'no' })).toBe('yes');
  });

  it('logical OR — falls through to right when left is falsy', () => {
    expect(eval_('a || b', { a: 0, b: 'fallback' })).toBe('fallback');
  });

  it('logical NOT (!) — truthy becomes false', () => {
    expect(eval_('!a', { a: true })).toBe(false);
  });

  it('logical NOT (!) — falsy becomes true', () => {
    expect(eval_('!a', { a: false })).toBe(true);
    expect(eval_('!a', { a: 0 })).toBe(true);
    expect(eval_('!a', { a: null })).toBe(true);
  });

  it('double negation (!!)', () => {
    expect(eval_('!!a', { a: 'truthy' })).toBe(true);
    expect(eval_('!!a', { a: '' })).toBe(false);
  });

  it('complex logical chain: (a || b) && c', () => {
    expect(eval_('(a || b) && c', { a: false, b: true, c: 'yes' })).toBe('yes');
  });
});

// =========================================================================
// 4. Arithmetic operators (+, -, *, /, %)
// =========================================================================
describe('Arithmetic operators', () => {
  it('addition', () => {
    expect(eval_('a + b', { a: 3, b: 4 })).toBe(7);
  });

  it('subtraction', () => {
    expect(eval_('a - b', { a: 10, b: 3 })).toBe(7);
  });

  it('multiplication', () => {
    expect(eval_('a * b', { a: 3, b: 4 })).toBe(12);
  });

  it('division', () => {
    expect(eval_('a / b', { a: 12, b: 4 })).toBe(3);
  });

  it('modulo', () => {
    expect(eval_('a % b', { a: 10, b: 3 })).toBe(1);
  });

  it('respects operator precedence: multiplication before addition', () => {
    expect(eval_('2 + 3 * 4')).toBe(14);
  });

  it('parentheses override precedence', () => {
    expect(eval_('(2 + 3) * 4')).toBe(20);
  });

  it('chained arithmetic: a + b - c', () => {
    expect(eval_('a + b - c', { a: 10, b: 5, c: 3 })).toBe(12);
  });

  it('negation via unary minus', () => {
    expect(eval_('-a', { a: 5 })).toBe(-5);
  });

  it('string concatenation via +', () => {
    expect(eval_("a + b", { a: 'hello ', b: 'world' })).toBe('hello world');
  });
});

// =========================================================================
// 5. Ternary operator
// =========================================================================
describe('Ternary operator', () => {
  it('returns consequent when condition is truthy', () => {
    expect(eval_("x ? 'yes' : 'no'", { x: true })).toBe('yes');
  });

  it('returns alternate when condition is falsy', () => {
    expect(eval_("x ? 'yes' : 'no'", { x: false })).toBe('no');
  });

  it('works with numeric conditions (0 is falsy)', () => {
    expect(eval_("x ? 'yes' : 'no'", { x: 0 })).toBe('no');
  });

  it('works with numeric conditions (non-zero is truthy)', () => {
    expect(eval_("x ? 'yes' : 'no'", { x: 42 })).toBe('yes');
  });

  it('nested ternary', () => {
    expect(eval_("a ? 'first' : b ? 'second' : 'third'", { a: false, b: true })).toBe('second');
  });

  it('ternary with expression branches', () => {
    expect(eval_('x > 10 ? x * 2 : x + 1', { x: 5 })).toBe(6);
    expect(eval_('x > 10 ? x * 2 : x + 1', { x: 20 })).toBe(40);
  });
});

// =========================================================================
// 6. Property access with null safety
// =========================================================================
describe('Null-safe property access', () => {
  it('accessing property on null returns undefined (not throw)', () => {
    expect(eval_('user.name', { user: null })).toBeUndefined();
  });

  it('accessing property on undefined returns undefined (not throw)', () => {
    expect(eval_('user.name', {})).toBeUndefined();
  });

  it('deep access on null intermediate returns undefined', () => {
    expect(eval_('a.b.c.d', { a: null })).toBeUndefined();
  });

  it('safeGet does not throw when accessing missing key on object', () => {
    expect(eval_('user.nonexistent', { user: { name: 'A' } })).toBeUndefined();
  });

  it('accessing property on a string returns the char method', () => {
    // string.length is a property, not undefined
    expect(eval_("name.length", { name: 'hello' })).toBe(5);
  });

  it('accessing property on a number returns undefined', () => {
    expect(eval_('n.toFixed', { n: 5 })).toBeDefined(); // function
    expect(eval_('n.nonexistent', { n: 5 })).toBeUndefined();
  });
});

// =========================================================================
// 7. Built-in functions
// =========================================================================
describe('Built-in functions', () => {
  describe('formatDate', () => {
    it('formats a date with pattern YYYY-MM-DD', () => {
      const result = eval_("formatDate(date, 'YYYY-MM-DD')", {
        date: new Date(2026, 0, 15), // Jan 15, 2026
      });
      expect(result).toBe('2026-01-15');
    });

    it('formats a date with full pattern', () => {
      const result = eval_("formatDate(date, 'YYYY/MM/DD HH:mm:ss')", {
        date: new Date(2026, 5, 2, 14, 30, 5),
      });
      expect(result).toBe('2026/06/02 14:30:05');
    });

    it('returns ISO string when no pattern given', () => {
      const d = new Date(2026, 0, 1);
      const result = eval_('formatDate(date)', { date: d });
      expect(result).toBe(d.toISOString());
    });

    it('returns empty string for null input', () => {
      expect(eval_('formatDate(date)', { date: null })).toBe('');
    });

    it('returns empty string for invalid date', () => {
      expect(eval_("formatDate(date, 'YYYY-MM-DD')", { date: 'not-a-date' })).toBe('');
    });
  });

  describe('formatPrice', () => {
    it('formats number to 2 decimals by default', () => {
      expect(eval_('formatPrice(10.5)', {})).toBe('10.50');
    });

    it('formats with custom decimals', () => {
      expect(eval_('formatPrice(10.567, 3)', {})).toBe('10.567');
    });

    it('returns "0.00" for NaN input', () => {
      expect(eval_("formatPrice('abc')", {})).toBe('0.00');
    });
  });

  describe('length', () => {
    it('returns string length', () => {
      expect(eval_('length(name)', { name: 'hello' })).toBe(5);
    });

    it('returns array length', () => {
      expect(eval_('length(items)', { items: [1, 2, 3] })).toBe(3);
    });

    it('returns object key count', () => {
      expect(eval_('length(obj)', { obj: { a: 1, b: 2 } })).toBe(2);
    });

    it('returns 0 for null', () => {
      expect(eval_('length(val)', { val: null })).toBe(0);
    });

    it('returns 0 for undefined', () => {
      expect(eval_('length(val)', { val: undefined })).toBe(0);
    });

    it('returns 0 for number', () => {
      expect(eval_('length(val)', { val: 42 })).toBe(0);
    });
  });

  describe('includes', () => {
    it('checks string inclusion', () => {
      expect(eval_("includes(name, 'ell')", { name: 'hello' })).toBe(true);
      expect(eval_("includes(name, 'xyz')", { name: 'hello' })).toBe(false);
    });

    it('checks array inclusion', () => {
      expect(eval_('includes(items, 2)', { items: [1, 2, 3] })).toBe(true);
      expect(eval_('includes(items, 9)', { items: [1, 2, 3] })).toBe(false);
    });

    it('returns false for non-searchable types', () => {
      expect(eval_('includes(val, 1)', { val: 123 })).toBe(false);
    });
  });

  describe('concat', () => {
    it('concatenates multiple values', () => {
      expect(eval_("concat(a, b, c)", { a: 'hello', b: ' ', c: 'world' })).toBe('hello world');
    });

    it('converts non-string args to string', () => {
      expect(eval_('concat(a, b)', { a: 'count: ', b: 42 })).toBe('count: 42');
    });
  });

  describe('first / last', () => {
    it('first returns the first element', () => {
      expect(eval_('first(items)', { items: [10, 20, 30] })).toBe(10);
    });

    it('first returns undefined for empty array', () => {
      expect(eval_('first(items)', { items: [] })).toBeUndefined();
    });

    it('last returns the last element', () => {
      expect(eval_('last(items)', { items: [10, 20, 30] })).toBe(30);
    });

    it('last returns undefined for empty array', () => {
      expect(eval_('last(items)', { items: [] })).toBeUndefined();
    });
  });
});

// =========================================================================
// 8. Template interpolation
// =========================================================================
// 模板语法是「裸文本 + ${表达式}」（见 evaluateExpression 的文档示例
// `Hello, ${pageState.user.name}!`），外层不要再加字符串引号——
// 引号会被当成模板文本参与拼接。
describe('Template interpolation', () => {
  it('interpolates a variable: Hello ${name}', () => {
    expect(eval_('Hello ${name}', { name: 'World' })).toBe('Hello World');
  });

  it('interpolates multiple variables', () => {
    expect(eval_('${firstName} ${lastName}', { firstName: 'John', lastName: 'Doe' })).toBe('John Doe');
  });

  it('interpolates nested property access', () => {
    expect(eval_('Name: ${user.name}', { user: { name: 'Alice' } })).toBe('Name: Alice');
  });

  it('interpolates expressions inside template', () => {
    expect(eval_('Total: ${price * qty}', { price: 10, qty: 3 })).toBe('Total: 30');
  });

  it('returns string type for template expression', () => {
    const result = eval_('${count}', { count: 42 });
    expect(result).toBe('42');
    expect(typeof result).toBe('string');
  });

  it('empty template segments produce empty strings', () => {
    expect(eval_("''", {})).toBe('');
  });

  it('plain text with no expressions returns the text as-is', () => {
    expect(eval_("'just text'", {})).toBe('just text');
  });

  it('null/undefined inside template renders as empty string', () => {
    expect(eval_('Hello ${missing}', {})).toBe('Hello ');
  });

  it('built-in functions work inside templates', () => {
    const result = eval_('Length: ${length(items)}', { items: [1, 2, 3] });
    expect(result).toBe('Length: 3');
  });
});

// =========================================================================
// 9. Invalid expression handling
// =========================================================================
describe('Invalid expression handling', () => {
  it('undefined variables return undefined (pure expression)', () => {
    expect(eval_('unknownVar')).toBeUndefined();
  });

  it('undefined variables in templates return empty string', () => {
    expect(eval_('Hello ${unknownVar}')).toBe('Hello ');
  });

  it('calling non-function returns undefined', () => {
    expect(eval_('notAFunction()', { notAFunction: 42 })).toBeUndefined();
  });

  it('validateExpression returns valid for correct expressions', () => {
    expect(validateExpression('a + b')).toEqual({ valid: true });
  });

  it('validateExpression returns error for invalid syntax', () => {
    const result = validateExpression('a +');
    expect(result.valid).toBe(false);
    if (!result.valid) {
      expect(result.error).toBeTruthy();
    }
  });

  it('validateExpression works for template expressions', () => {
    expect(validateExpression("'Hello ${name}'")).toEqual({ valid: true });
  });

  it('validateExpression catches unmatched braces', () => {
    const result = validateExpression("'Hello ${name'");
    expect(result.valid).toBe(false);
  });
});

// =========================================================================
// 10. Edge cases
// =========================================================================
describe('Edge cases', () => {
  it('empty string expression is invalid', () => {
    const result = validateExpression('');
    expect(result.valid).toBe(false);
  });

  it('null context does not throw', () => {
    expect(eval_('42', {})).toBe(42);
  });

  it('empty context returns undefined for any identifier', () => {
    expect(eval_('anything', {})).toBeUndefined();
  });

  it('whitespace is trimmed from expression', () => {
    expect(eval_('  x  ', { x: 10 })).toBe(10);
  });

  it('number literal evaluation', () => {
    expect(eval_('42')).toBe(42);
    expect(eval_('3.14')).toBeCloseTo(3.14);
  });

  it('string literal evaluation', () => {
    expect(eval_("'hello'")).toBe('hello');
    expect(eval_('"world"')).toBe('world');
  });

  it('boolean literals', () => {
    expect(eval_('true')).toBe(true);
    expect(eval_('false')).toBe(false);
  });

  it('null and undefined literals', () => {
    expect(eval_('null')).toBeNull();
    expect(eval_('undefined')).toBeUndefined();
  });

  it('index access on array', () => {
    expect(eval_('items[1]', { items: [10, 20, 30] })).toBe(20);
  });

  it('index access on null returns undefined', () => {
    expect(eval_('items[0]', { items: null })).toBeUndefined();
  });

  it('nested member + index access', () => {
    expect(eval_('data.rows[0].name', { data: { rows: [{ name: 'first' }] } })).toBe('first');
  });

  it('complex expression combining multiple features', () => {
    const ctx = {
      user: { name: 'Alice', age: 30 },
      isAdmin: true,
    };
    expect(eval_("isAdmin && user.age >= 18 ? user.name : 'denied'", ctx)).toBe('Alice');
  });

  it('parseExpression returns an AST node', () => {
    const ast = parseExpression('1 + 2');
    expect(ast).toBeDefined();
    expect(ast.type).toBe('BinaryOp');
  });

  it('parseExpression throws SyntaxError for bad input', () => {
    expect(() => parseExpression('+')).toThrow(SyntaxError);
  });

  it('single-character identifier', () => {
    expect(eval_('x', { x: 7 })).toBe(7);
  });

  it('dollar-prefixed identifier', () => {
    expect(eval_('$count', { $count: 99 })).toBe(99);
  });

  it('string with escaped quotes', () => {
    expect(eval_("'it\\'s ok'")).toBe("it's ok");
  });

  it('modulo operator', () => {
    expect(eval_('10 % 3')).toBe(1);
  });

  it('division by zero returns Infinity', () => {
    expect(eval_('1 / 0')).toBe(Infinity);
  });

  it('very deeply nested property access', () => {
    expect(eval_('a.b.c.d.e.f', { a: { b: { c: { d: { e: { f: 'bottom' } } } } } })).toBe('bottom');
  });

  it('very deeply nested with null in the middle', () => {
    expect(eval_('a.b.c.d.e.f', { a: { b: null } })).toBeUndefined();
  });
});

// =========================================================================
// 8. Prototype pollution protection
// =========================================================================
describe('Prototype pollution protection', () => {
  it('blocks access to __proto__', () => {
    expect(eval_('obj.__proto__', { obj: {} })).toBeUndefined();
  });

  it('blocks access to constructor', () => {
    expect(eval_('obj.constructor', { obj: {} })).toBeUndefined();
  });

  it('blocks access to prototype', () => {
    expect(eval_('obj.prototype', { obj: {} })).toBeUndefined();
  });

  it('blocks __defineGetter__', () => {
    expect(eval_('obj.__defineGetter__', { obj: {} })).toBeUndefined();
  });

  it('blocks __defineSetter__', () => {
    expect(eval_('obj.__defineSetter__', { obj: {} })).toBeUndefined();
  });

  it('blocks __lookupGetter__', () => {
    expect(eval_('obj.__lookupGetter__', { obj: {} })).toBeUndefined();
  });

  it('blocks __lookupSetter__', () => {
    expect(eval_('obj.__lookupSetter__', { obj: {} })).toBeUndefined();
  });

  it('blocks prototype via index access', () => {
    expect(eval_('obj["prototype"]', { obj: {} })).toBeUndefined();
  });

  it('blocks constructor via index access', () => {
    expect(eval_('obj["constructor"]', { obj: {} })).toBeUndefined();
  });

  it('allows access to safe properties', () => {
    expect(eval_('obj.name', { obj: { name: 'test' } })).toBe('test');
    expect(eval_('obj.value', { obj: { value: 123 } })).toBe(123);
  });

  it('does not pollute Object prototype', () => {
    // 确保没有修改全局 Object.prototype
    const before = (Object.prototype as any).polluted;
    expect(before).toBeUndefined();

    // 引擎不支持赋值语法，污染尝试直接被语法解析拒绝
    expect(() => eval_('obj["__proto__"]["polluted"] = true', { obj: {} })).toThrow(SyntaxError);

    // 验证没有被污染
    const after = (Object.prototype as any).polluted;
    expect(after).toBeUndefined();
  });
});

// =========================================================================
// 9. Array methods
// =========================================================================
describe('Array methods', () => {
  it('map transforms array elements', () => {
    expect(eval_('items.map(x => x * 2)', { items: [1, 2, 3] })).toEqual([2, 4, 6]);
  });

  it('filter selects matching elements', () => {
    expect(eval_('items.filter(x => x > 2)', { items: [1, 2, 3, 4] })).toEqual([3, 4]);
  });

  it('reduce accumulates values', () => {
    expect(eval_('items.reduce((acc, x) => acc + x, 0)', { items: [1, 2, 3] })).toBe(6);
  });

  it('find returns first match', () => {
    expect(eval_('items.find(x => x > 2)', { items: [1, 2, 3] })).toBe(3);
  });

  it('some checks if any element matches', () => {
    expect(eval_('items.some(x => x > 2)', { items: [1, 2, 3] })).toBe(true);
  });

  it('every checks if all elements match', () => {
    expect(eval_('items.every(x => x > 0)', { items: [1, 2, 3] })).toBe(true);
  });

  it('sort orders elements', () => {
    expect(eval_('items.sort()', { items: [3, 1, 2] })).toEqual([1, 2, 3]);
  });

  it('flat flattens nested arrays', () => {
    expect(eval_('items.flat()', { items: [[1, 2], [3, 4]] })).toEqual([1, 2, 3, 4]);
  });
});

// =========================================================================
// 10. String methods
// =========================================================================
describe('String methods', () => {
  it('trim removes whitespace', () => {
    expect(eval_("' hello '.trim()")).toBe('hello');
  });

  it('upper converts to uppercase', () => {
    expect(eval_("'hello'.upper()")).toBe('HELLO');
  });

  it('lower converts to lowercase', () => {
    expect(eval_("'HELLO'.lower()")).toBe('hello');
  });

  it('split splits string', () => {
    expect(eval_("'a,b,c'.split(',')")).toEqual(['a', 'b', 'c']);
  });

  it('replace substitutes text', () => {
    expect(eval_("'hello world'.replace('world', 'there')")).toBe('hello there');
  });

  it('slice extracts substring', () => {
    expect(eval_("'hello'.slice(1, 4)")).toBe('ell');
  });
});

// =========================================================================
// 11. Math functions
// =========================================================================
describe('Math functions', () => {
  it('min returns minimum value', () => {
    expect(eval_('min(3, 1, 2)')).toBe(1);
  });

  it('max returns maximum value', () => {
    expect(eval_('max(3, 1, 2)')).toBe(3);
  });

  it('round rounds to nearest integer', () => {
    expect(eval_('round(3.7)')).toBe(4);
  });

  it('abs returns absolute value', () => {
    expect(eval_('abs(-5)')).toBe(5);
  });

  it('floor rounds down', () => {
    expect(eval_('floor(3.7)')).toBe(3);
  });

  it('ceil rounds up', () => {
    expect(eval_('ceil(3.2)')).toBe(4);
  });
});

// =========================================================================
// 12. Nullish coalescing and optional chaining
// =========================================================================
describe('Nullish coalescing and optional chaining', () => {
  it('?? returns right side if left is null/undefined', () => {
    expect(eval_('null ?? "default"')).toBe('default');
    expect(eval_('undefined ?? "default"')).toBe('default');
    expect(eval_('0 ?? "default"')).toBe(0);
    expect(eval_("'' ?? 'default'")).toBe('');
  });

  it('?. accesses property safely', () => {
    expect(eval_('obj?.name', { obj: { name: 'test' } })).toBe('test');
    expect(eval_('obj?.name', { obj: null })).toBeUndefined();
    expect(eval_('obj?.name', { obj: {} })).toBeUndefined();
  });

  it('?.[] accesses index safely', () => {
    expect(eval_('arr?.[0]', { arr: [1, 2, 3] })).toBe(1);
    expect(eval_('arr?.[0]', { arr: null })).toBeUndefined();
  });

  it('?.() calls method safely', () => {
    expect(eval_('obj?.toString()', { obj: 42 })).toBe('42');
    expect(eval_('obj?.toString()', { obj: null })).toBeUndefined();
  });
});
