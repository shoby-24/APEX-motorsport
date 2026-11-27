// Node helper: load the bundled catalogue from disk. Browser games import the JSON through their bundler instead.
import { readFileSync, readdirSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { join, dirname } from 'node:path';
import { createCatalogue } from './index.js';
const root = join(dirname(fileURLToPath(import.meta.url)), '..', 'catalogue');
export function loadCatalogue() {
  const models = readdirSync(join(root, 'models')).filter(f => f.endsWith('.json')).map(f => JSON.parse(readFileSync(join(root, 'models', f), 'utf8')));
  const parts = readdirSync(join(root, 'parts')).filter(f => f.endsWith('.json')).flatMap(f => JSON.parse(readFileSync(join(root, 'parts', f), 'utf8')));
  return createCatalogue(models, parts);
}
