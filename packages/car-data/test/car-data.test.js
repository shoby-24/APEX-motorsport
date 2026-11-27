import { test } from 'node:test';
import assert from 'node:assert/strict';
import { defaultCar, validateCar, computeSpec, writeCarFile, readCarFile, migrate, toRacingSpec } from '../src/index.js';
import { loadCatalogue } from '../src/catalogue.js';

const cat = loadCatalogue();
const p1 = cat.models.mclaren_p1_gtr_2015;

test('catalogue loads the P1 GTR and its parts', () => {
  assert.ok(p1);
  for (const id of Object.values(p1.defaults.parts)) assert.ok(cat.parts[id], `missing part ${id}`);
});

test('default car is valid', () => {
  assert.deepEqual(validateCar(defaultCar(p1)), []);
});

test('validation catches bad values', () => {
  const c = defaultCar(p1);
  c.paint.body.color = 'red'; c.tune.aero = 2; c.parts.wing = {};
  const errs = validateCar(c);
  assert.equal(errs.length, 3, errs.join('\n'));
});

test('parts and tune change the spec deterministically', () => {
  const c = defaultCar(p1);
  const a = computeSpec(c, cat);
  c.parts.wing = { id: 'wing_none' };
  const b = computeSpec(c, cat);
  assert.ok(b.downforce < a.downforce && b.drag < a.drag);
  c.tune.aero = 1;
  assert.ok(computeSpec(c, cat).downforce > b.downforce);
  assert.deepEqual(computeSpec(c, cat), computeSpec(structuredClone(c), cat));
});

test('export -> import round trip keeps everything', () => {
  const c = defaultCar(p1, 'Midnight P1');
  c.paint.body = { color: '#0b1d3a', finish: 'pearl', flake: 0.7, clearcoat: 1 };
  c.livery.layers.push({ type: 'stripe', preset: 'twin_center', color: '#ffffff' });
  const text = writeCarFile(c, cat);
  assert.ok(text.length < 4096, 'car file should stay small');
  const { car, spec, tampered } = readCarFile(text, cat);
  assert.deepEqual(car, c);
  assert.equal(tampered, false);
  assert.deepEqual(spec, computeSpec(c, cat));
});

test('an edited stored spec is ignored (spec is always recomputed)', () => {
  const obj = JSON.parse(writeCarFile(defaultCar(p1), cat));
  obj.spec.powerKw = 9999;
  const { spec, tampered } = readCarFile(JSON.stringify(obj), cat);
  assert.equal(tampered, false, 'hash covers the recomputed spec, so editing the stored copy alone changes nothing');
  assert.equal(spec.powerKw, computeSpec(migrate(obj), cat).powerKw);
});

test('unknown model still imports (games show a stand-in)', () => {
  const c = defaultCar(p1); c.model.id = 'future_car_x';
  const r = readCarFile(JSON.stringify(c), cat);
  assert.equal(r.knownModel, false); assert.equal(r.spec, null);
});

test('v1 Stage 1 files migrate to v2', () => {
  const v1 = { format: 'claude-car', version: 1, model: 'mclaren_p1_gtr_2015', paint: { color: '#aa0000', finish: 'gloss' },
               parts: { wing: 'wing_p1_gtr' }, tune: { aero: 0.8 } };
  const v2 = migrate(v1);
  assert.equal(v2.version, 2); assert.equal(v2.parts.wing.id, 'wing_p1_gtr'); assert.equal(v2.tune.aero, 0.8);
  assert.deepEqual(validateCar(v2), []);
});

test('racing spec mapping has physics fields', () => {
  const r = toRacingSpec(computeSpec(defaultCar(p1), cat));
  for (const k of ['mass', 'torque', 'drag', 'df', 'grip']) assert.ok(r[k] !== undefined, k);
});
