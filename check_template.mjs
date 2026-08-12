import { readFileSync } from 'node:fs';
import { compile } from '@vue/compiler-dom';

const tpl = readFileSync('template.txt', 'utf-8');
try {
  const res = compile(tpl, { mode: 'function' });
  console.log('keys:', Object.keys(res));
  const errs = res.errors || [];
  console.log('compile done, errors =', errs.length);
  for (const e of errs) {
    console.log('ERR line', e.loc?.start?.line, 'col', e.loc?.start?.column, '-', e.message);
  }
} catch (err) {
  console.log('FATAL:', err.message);
}
