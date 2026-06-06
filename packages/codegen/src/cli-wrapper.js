#!/usr/bin/env node
/**
 * 代码生成器 CLI 包装脚本
 *
 * 从 stdin 读取 JSON 输入，调用 @hospital/codegen 包，输出 JSON 结果。
 * 用法: echo '{"schema":...}' | node cli-wrapper.js [codegen-path]
 *
 * 参数:
 *   codegen-path: @hospital/codegen 包的路径（可选，默认从 node_modules 查找）
 */
const fs = require('fs');
const path = require('path');

async function main() {
    const input = JSON.parse(fs.readFileSync(0, 'utf-8'));
    const schema = input.schema;
    const dataSources = input.dataSources || [];
    const state = input.state || {};
    const target = input.target || 'taro';
    const options = input.options || {};

    // 解析 codegen 包路径
    const codegenPath = process.argv[2] || path.resolve(__dirname, '../dist/index.js');
    const codegen = require(codegenPath);

    let result;

    if (target === 'taro') {
        const pageCode = codegen.generatePage(schema, dataSources, state, options);
        const analysis = codegen.analyzeSchema
            ? codegen.analyzeSchema(schema)
            : { components: [], dataSources: [], dependencies: [], warnings: [] };

        const pageName = schema.props?.navigationBarTitleText || 'page';
        const safeSlug = pageName.replace(/[^a-zA-Z0-9_-]/g, '_').toLowerCase() || 'page';

        result = {
            files: [
                {
                    path: 'pages/' + safeSlug + '/index.tsx',
                    content: pageCode,
                    type: 'tsx',
                },
            ],
            warnings: analysis.warnings || [],
            dependencies: extractDeps(pageCode),
            metadata: {
                target: 'taro',
                components: analysis.components || [],
                dataSources: (analysis.dataSources || []).map(function(ds) { return ds.id; }),
                generatedAt: new Date().toISOString(),
            },
        };
    } else if (target === 'native') {
        // Native (WeChat mini-program) output — 使用 codegen 包的完整生成器
        const slug = (schema.props?.navigationBarTitleText || 'page').replace(/[^a-zA-Z0-9_-]/g, '_').toLowerCase() || 'page';
        const prefix = 'pages/' + slug;

        // 使用 codegen 包的 generateWxmlPage 生成完整 WXML（支持 dataBinding/loop/visible/事件）
        const wxml = codegen.generateWxmlPage(schema, { pageClass: 'page' });
        const handlers = codegen.collectEventHandlers ? codegen.collectEventHandlers(schema) : [];
        const bindings = codegen.collectDataBindings ? codegen.collectDataBindings(schema) : new Set();

        // 生成 JS 逻辑（含事件处理函数）
        var jsLines = [];
        jsLines.push("Page({");
        jsLines.push("  data: {");
        jsLines.push("    loading: true,");
        var stateKeys = Object.keys(state);
        for (var i = 0; i < stateKeys.length; i++) {
            var key = stateKeys[i];
            var val = state[key];
            var defaultVal = (val && val.defaultValue !== undefined) ? val.defaultValue : '';
            jsLines.push("    " + key + ": " + JSON.stringify(defaultVal) + ",");
        }
        jsLines.push("  },");
        jsLines.push("  onLoad() {");
        for (var j = 0; j < dataSources.length; j++) {
            var ds = dataSources[j];
            jsLines.push("    this.fetch_" + ds.id + "();");
        }
        jsLines.push("    this.setData({ loading: false });");
        jsLines.push("  },");
        for (var k = 0; k < dataSources.length; k++) {
            var ds2 = dataSources[k];
            jsLines.push("  fetch_" + ds2.id + "() {");
            jsLines.push("    wx.request({");
            jsLines.push("      url: '" + (ds2.url || '') + "',");
            jsLines.push("      method: '" + (ds2.method || 'GET') + "',");
            jsLines.push("      success: (res) => {");
            if (ds2.dataPath) {
                jsLines.push("        this.setData({ " + ds2.id + ": res.data." + ds2.dataPath + " });");
            } else {
                jsLines.push("        this.setData({ " + ds2.id + ": res.data });");
            }
            jsLines.push("      },");
            jsLines.push("      fail: (err) => {");
            jsLines.push("        console.error('Failed to fetch " + ds2.id + "', err);");
            jsLines.push("      }");
            jsLines.push("    });");
            jsLines.push("  },");
        }
        // 事件处理函数（从 collectEventHandlers 获取）
        for (var h = 0; h < handlers.length; h++) {
            var handler = handlers[h];
            jsLines.push("  " + handler.name + "(e) {");
            for (var a = 0; a < handler.actions.length; a++) {
                var action = handler.actions[a];
                if (action.type === 'setData') {
                    jsLines.push("    this.setData({ " + action.key + ": " + JSON.stringify(action.value) + " });");
                } else if (action.type === 'navigate') {
                    jsLines.push("    wx.navigateTo({ url: '" + action.url + "' });");
                } else if (action.type === 'showToast') {
                    jsLines.push("    wx.showToast({ title: '" + (action.title || '') + "', icon: 'none' });");
                }
            }
            jsLines.push("  },");
        }
        jsLines.push("});");
        var jsCode = jsLines.join('\n');

        // WXSS: 复用现有样式
        var wxss = '.page {\n  min-height: 100vh;\n  padding: 16rpx;\n  box-sizing: border-box;\n}\n';

        // JSON config
        var pageName = (schema.props && schema.props.navigationBarTitleText) || 'page';
        var config = {
            navigationBarTitleText: pageName,
            usingComponents: {},
        };

        result = {
            files: [
                { path: prefix + '.wxml', content: wxml, type: 'wxml' },
                { path: prefix + '.wxss', content: wxss, type: 'wxss' },
                { path: prefix + '.js', content: jsCode, type: 'js' },
                { path: prefix + '.json', content: JSON.stringify(config, null, 2), type: 'json' },
            ],
            warnings: [],
            dependencies: ['wx'],
            metadata: {
                target: 'native',
                generatedAt: new Date().toISOString(),
            },
        };
    } else {
        throw new Error('Unknown target: ' + target);
    }

    process.stdout.write(JSON.stringify(result));
}

function extractDeps(code) {
    var deps = [];
    var re = /from\s+['"]([^'"]+)['"]/g;
    var m;
    while ((m = re.exec(code)) !== null) {
        var dep = m[1];
        if (!dep.startsWith('.') && !dep.startsWith('/')) {
            deps.push(dep);
        }
    }
    return deps;
}

main().catch(function(err) {
    process.stderr.write(JSON.stringify({ error: err.message, stack: err.stack }));
    process.exit(1);
});
