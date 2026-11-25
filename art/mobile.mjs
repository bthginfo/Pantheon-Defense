import { NodeIO } from '@gltf-transform/core';
import { ALL_EXTENSIONS } from '@gltf-transform/extensions';
import { MeshoptSimplifier } from 'meshoptimizer';
import { mkdir, readFile, stat, writeFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { reindex } from './mesh-budget.mjs';

const assets = new URL('../public/assets/', import.meta.url);
const catalog = JSON.parse(await readFile(new URL('catalog.json', assets), 'utf8'));
const mobile = new URL('mobile/', assets);
await mkdir(mobile, { recursive: true });
const io = new NodeIO().registerExtensions(ALL_EXTENSIONS);

function attributes(primitive, fields, count) {
  const inputs = fields.map(([name, weight]) => ({ accessor: primitive.getAttribute(name), weight }))
    .filter(({ accessor }) => accessor);
  const weights = inputs.flatMap(({ accessor, weight }) => Array(accessor.getElementSize()).fill(weight));
  const samples = new Float32Array(count * weights.length);
  const tuple = [];
  for (let vertex = 0; vertex < count; vertex++) {
    let offset = vertex * weights.length;
    for (const { accessor } of inputs) {
      accessor.getElement(vertex, tuple);
      for (const value of tuple) samples[offset++] = value;
    }
  }
  return { samples, weights };
}

// Boards keep their full export on phones: their painted tiles frame every unit on screen.
const boards = [];
const ids = [...catalog.actors.map(x => x.id), ...catalog.enemies.map(x => x.id)];
const variants = [];
for (const id of ids) {
  const source = new URL(`models/${id}.glb`, assets);
  const document = await io.read(fileURLToPath(source));
  const primitives = document.getRoot().listMeshes().flatMap(mesh => mesh.listPrimitives());
  // Each Blender export has one combined sculpt. Leave other scene layouts untouched.
  if (primitives.length !== 1) continue;
  const [primitive] = primitives;
  const original = primitive.getIndices()?.getArray();
  if (!original || original.length < 7_200 || primitive.getMode() !== 4) continue;
  const vertices = primitive.getAttribute('POSITION');
  const positions = vertices.getArray();
  const board = boards.includes(id);
  // Budget errors in world units, with extra weight on the painted colour and skinning.
  const fields = board ? [['COLOR_0', .17]]
    : [['COLOR_0', .26], ['NORMAL', .088], ['TEXCOORD_0', .08], ['WEIGHTS_0', .32]];
  const { samples, weights } = attributes(primitive, fields, vertices.getCount());
  const bounds = MeshoptSimplifier.getScale(positions, 3);
  const target = Math.floor(original.length * (board ? .35 : .36) / 3) * 3;
  const [indices] = MeshoptSimplifier.simplifyWithAttributes(
    Uint32Array.from(original), positions, 3, samples, weights.length, weights, null,
    target, (board ? .065 : .016) / bounds, ['Permissive', 'Prune'],
  );
  if (!indices.length || indices.length > original.length * .75) continue;
  reindex(primitive, indices);
  const buffer = await io.writeBinary(document);
  if (buffer.length > (await stat(source)).size * .88) continue;
  await writeFile(new URL(`${id}.glb`, mobile), buffer);
  variants.push(id);
  console.log(`${id} ${original.length / 3} → ${indices.length / 3} triangles`);
}
await writeFile(new URL('models.txt', mobile), variants.sort().join('\n') + '\n');
