// 检查 index.html 标签配对与人工录入相关引用
const fs = require('fs');
const h = fs.readFileSync('frontend/index.html', 'utf8');
const count = (re) => (h.match(re) || []).length;
console.log('el-form-item open:', count(/<el-form-item/g), 'close:', count(/<\/el-form-item>/g));
console.log('template open:', count(/<template/g), 'close:', count(/<\/template>/g));
console.log('script open:', count(/<script/g), 'close:', count(/<\/script>/g));
console.log('div open:', count(/<div/g), 'close:', count(/<\/div>/g));
console.log('el-table open:', count(/<el-table/g), 'close:', count(/<\/el-table>/g));
console.log('el-form-item-col open:', count(/<el-table-column/g), 'close:', count(/<\/el-table-column>/g));
console.log('manual refs:', count(/manualKills|manualScore|manualTotal|manualConsistent|iconList|loadIcons/g));
