const { JSDOM } = require('jsdom');
const html = `<div id="app">
  <el-image v-if="x" src="a" fit="cover" style="width:56px" preview-teleported />
  <span v-else style="color:#888">-</span>
</div>`;
const dom = new JSDOM(html);
console.log('INNERHTML:');
console.log(dom.window.document.querySelector('#app').innerHTML);
console.log('\nspan parent tag:', dom.window.document.querySelector('span').parentElement.tagName);
console.log('span prev sibling:', dom.window.document.querySelector('span').previousElementSibling ? dom.window.document.querySelector('span').previousElementSibling.tagName : 'NONE');
