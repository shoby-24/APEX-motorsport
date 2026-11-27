// @apex/car-data — engine-free car data shared by APEX: Racing (Three.js) and APEX: Tuning (PlayCanvas).
// No rendering code lives here, so games, tools, servers and tests can all use it.

export const FORMAT = 'claude-car';
export const VERSION = 2;
export const TUNE_KEYS = ['gear', 'aero', 'ride', 'susp', 'bias', 'diff'];
const HEX = /^#[0-9a-fA-F]{6}$/;
const FINISHES = new Set(['gloss', 'metallic', 'pearl', 'satin', 'matte', 'chrome']);

/** Catalogue = { models: {id: model}, parts: {id: part} }. Games inject their own bundled copy. */
export function createCatalogue(models = [], parts = []) {
  const m = {}, p = {};
  for (const x of models) m[x.id] = x;
  for (const x of parts) p[x.id] = x;
  return { models: m, parts: p };
}

/** Default car file for a model. */
export function defaultCar(model, name = model.name) {
  const parts = {};
  for (const [socket, id] of Object.entries(model.defaults?.parts ?? {})) parts[socket] = { id };
  return {
    format: FORMAT, version: VERSION, id: newId(), name,
    model: { id: model.id, assetVersion: model.assetVersion ?? 1 },
    paint: structuredClone(model.defaults?.paint ?? { body: { color: '#b9bcc0', finish: 'metallic' } }),
    livery: { layers: [] }, parts,
    tune: Object.fromEntries(TUNE_KEYS.map(k => [k, 0.5])),
  };
}

/** Upgrade older car files. v1 (Stage 1 prototype) -> v2. Returns a new object; never mutates input. */
export function migrate(car) {
  if (!car || car.format !== FORMAT) throw new Error('not a claude-car file');
  let c = structuredClone(car);
  if (c.version === 1) {
    const modelId = typeof c.model === 'string' ? c.model : c.model?.id;
    const p1 = c.paint ?? {};
    const parts = {};
    for (const [k, v] of Object.entries(c.parts ?? {})) parts[k] = typeof v === 'string' ? { id: v } : v;
    c = {
      format: FORMAT, version: 2, id: c.id ?? newId(), name: c.name ?? modelId,
      model: { id: modelId, assetVersion: 1 },
      paint: { body: { color: p1.color ?? p1.body?.color ?? '#b9bcc0', finish: p1.finish ?? 'metallic', flake: p1.flake ?? 0.5, clearcoat: 1 },
               ...(p1.accent ? { accent: p1.accent } : {}), ...(p1.caliper ? { caliper: p1.caliper } : {}) },
      livery: c.livery && Array.isArray(c.livery.layers) ? c.livery : { layers: [] },
      parts, tune: { ...Object.fromEntries(TUNE_KEYS.map(k => [k, 0.5])), ...(c.tune ?? {}) },
    };
  }
  if (c.version !== VERSION) throw new Error(`unsupported claude-car version ${c.version}`);
  return c;
}

/** Validate a v2 car. Returns an array of problems (empty = valid). */
export function validateCar(car) {
  const errs = [];
  const need = (cond, msg) => { if (!cond) errs.push(msg); };
  need(car && car.format === FORMAT, 'format must be "claude-car"');
  need(car?.version === VERSION, `version must be ${VERSION}`);
  need(typeof car?.model?.id === 'string' && car.model.id.length > 0, 'model.id required');
  if (car?.name !== undefined) need(typeof car.name === 'string' && car.name.length <= 48, 'name must be a string of at most 48 chars');
  for (const slot of ['body', 'accent']) {
    const p = car?.paint?.[slot];
    if (p === undefined) { need(slot !== 'body', 'paint.body required'); continue; }
    need(HEX.test(p.color ?? ''), `paint.${slot}.color must be #rrggbb`);
    if (p.finish !== undefined) need(FINISHES.has(p.finish), `paint.${slot}.finish invalid`);
    for (const k of ['flake', 'clearcoat']) if (p[k] !== undefined) need(p[k] >= 0 && p[k] <= 1, `paint.${slot}.${k} must be 0..1`);
  }
  if (car?.paint?.caliper !== undefined) need(HEX.test(car.paint.caliper), 'paint.caliper must be #rrggbb');
  need(car?.parts && typeof car.parts === 'object', 'parts required');
  for (const [s, v] of Object.entries(car?.parts ?? {})) need(typeof v?.id === 'string', `parts.${s}.id required`);
  for (const k of TUNE_KEYS) {
    const v = car?.tune?.[k];
    need(typeof v === 'number' && v >= 0 && v <= 1, `tune.${k} must be a number 0..1`);
  }
  const layers = car?.livery?.layers ?? [];
  need(Array.isArray(layers) && layers.length <= 64, 'livery.layers must be an array of at most 64 layers');
  return errs;
}

/** Final performance spec from model base spec + fitted parts + tune. Pure and deterministic. */
export function computeSpec(car, catalogue) {
  const model = catalogue.models[car.model.id];
  if (!model) throw new Error(`unknown model ${car.model.id}`);
  const s = structuredClone(model.baseSpec);
  const unknownParts = [];
  for (const [socket, ref] of Object.entries(car.parts ?? {})) {
    const part = catalogue.parts[ref.id];
    if (!part) { unknownParts.push(ref.id); continue; }
    if (part.socket !== socket) { unknownParts.push(ref.id); continue; }
    for (const [k, v] of Object.entries(part.effects ?? {})) if (typeof s[k] === 'number') s[k] = s[k] + v;
  }
  const t = car.tune;
  // aero slider trades downforce for drag (+/-20 % downforce, +/-10 % drag around the middle)
  s.downforce *= 1 + (t.aero - 0.5) * 0.4;
  s.drag *= 1 + (t.aero - 0.5) * 0.2;
  // gearing slider shortens/lengthens the final drive by up to 12 %
  s.finalDrive *= 1 + (t.gear - 0.5) * 0.24;
  // power scales the torque curve
  const pScale = s.powerKw / model.baseSpec.powerKw;
  s.torqueCurve = s.torqueCurve.map(([rpm, nm]) => [rpm, round(nm * pScale, 1)]);
  for (const k of ['massKg', 'powerKw', 'drag', 'downforce', 'grip', 'brake', 'finalDrive']) s[k] = round(s[k], 4);
  s.tune = { ...t };
  s.unknownParts = unknownParts;
  return s;
}

/** Map a computed spec onto the racing game's physics fields. Field names verified in Stage 6. */
export function toRacingSpec(spec) {
  return {
    mass: spec.massKg, torque: spec.torqueCurve, redline: spec.redline, gears: spec.gears, final: spec.finalDrive,
    drag: spec.drag, df: spec.downforce, grip: spec.grip, brake: spec.brake, drive: spec.drive,
    tune: spec.tune,
  };
}

/** Serialise a car (adds spec + specHash for display and tamper checks). */
export function writeCarFile(car, catalogue) {
  const errs = validateCar(car);
  if (errs.length) throw new Error('invalid car: ' + errs.join('; '));
  const spec = computeSpec(car, catalogue);
  const out = { ...structuredClone(car), spec };
  out.specHash = 'fnv1a64:' + fnv1a64(stableStringify(spec));
  return JSON.stringify(out);
}

/** Parse, migrate, validate and recompute. Never trusts the stored spec. */
export function readCarFile(text, catalogue) {
  const raw = typeof text === 'string' ? JSON.parse(text) : text;
  const car = migrate(raw);
  const stored = car.spec, storedHash = car.specHash;
  delete car.spec; delete car.specHash;
  const errs = validateCar(car);
  if (errs.length) throw new Error('invalid car: ' + errs.join('; '));
  const known = !!catalogue.models[car.model.id];
  const spec = known ? computeSpec(car, catalogue) : null;
  const tampered = !!(stored && spec && storedHash && storedHash !== 'fnv1a64:' + fnv1a64(stableStringify(spec)));
  return { car, spec, knownModel: known, tampered };
}

// ---------- helpers
function round(v, d) { const f = 10 ** d; return Math.round(v * f) / f; }
export function stableStringify(v) {
  if (Array.isArray(v)) return '[' + v.map(stableStringify).join(',') + ']';
  if (v && typeof v === 'object') return '{' + Object.keys(v).sort().map(k => JSON.stringify(k) + ':' + stableStringify(v[k])).join(',') + '}';
  return JSON.stringify(v);
}
export function fnv1a64(str) {
  let h = 0xcbf29ce484222325n; const p = 0x100000001b3n;
  for (const b of new TextEncoder().encode(str)) { h ^= BigInt(b); h = (h * p) & 0xffffffffffffffffn; }
  return h.toString(16).padStart(16, '0');
}
function newId() {
  return globalThis.crypto?.randomUUID ? globalThis.crypto.randomUUID() : 'car-' + Math.random().toString(36).slice(2);
}
