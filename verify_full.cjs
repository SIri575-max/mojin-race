const { JSDOM } = require('jsdom');
const fs = require('fs');
const { compile } = require('@vue/compiler-dom');

const html = fs.readFileSync('frontend/index.html', 'utf-8');
const start = html.indexOf('<div id="app">');
let pos = start + '<div id="app">'.length;
let depth = 1, i = pos;
while (depth > 0) {
  const o = html.indexOf('<div', i);
  const c = html.indexOf('</div>', i);
  if (o !== -1 && o < c) { depth++; i = o + 5; }
  else { depth--; i = c + 6; }
}
const tpl = html.slice(start, i);

// Simulate browser: parse raw HTML into DOM, then read innerHTML (browser rewrites self-closing tags)
const dom = new JSDOM(tpl, { contentType: 'text/html' });
const inner = dom.window.document.querySelector('#app').innerHTML;

// Now compile the rewritten innerHTML, exactly like Vue runtime does
const res = compile(inner, { mode: 'function' });
const errs = res.errors || [];
console.log('=== DOM-rewritten innerHTML compile ===');
console.log('errors:', errs.length);
for (const e of errs) {
  console.log('  ERR line', e.loc?.start?.line, 'col', e.loc?.start?.column, '-', e.message);
}

// Sanity: count v-else and check each has adjacent v-if sibling in DOM
const doc = dom.window.document;
let bad = 0, total = 0;
function walk(el) {
  const kids = el.children;
  for (let k = 0; k < kids.length; k++) {
    const node = kids[k];
    if (node.hasAttribute && node.hasAttribute('v-else')) {
      total++;
      let prev = node.previousElementSibling;
      while (prev && prev.nodeType === 8) prev = prev.previousElementSibling; // skip comments
      const ok = prev && (prev.hasAttribute('v-if') || prev.hasAttribute('v-else-if'));
      if (!ok) { bad++; console.log('  BAD v-else without adjacent v-if: <' + node.tagName.toLowerCase() + '> parent <' + node.parentElement.tagName.toLowerCase() + '>'); }
    }
    walk(node);
  }
}
walk(doc.querySelector('#app'));
console.log('v-else check: total', total, 'bad', bad);
console.log(bad === 0 && errs.length === 0 ? '=== PASS ===' : '=== FAIL ===');
