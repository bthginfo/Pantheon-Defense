import { MeshoptEncoder, MeshoptSimplifier } from 'meshoptimizer';

await Promise.all([MeshoptEncoder.ready, MeshoptSimplifier.ready]);

export function simplify(primitive, fields, fraction, error) {
  const vertex = primitive.getAttribute('POSITION');
  const positions = vertex.getArray();
  const indices = primitive.getIndices().getArray();
  const inputs = fields.flatMap(([name, weight]) => {
    const accessor = primitive.getAttribute(name);
    if (!accessor) return [];
    return [{accessor, weights: Array.isArray(weight) ? weight : Array(accessor.getElementSize()).fill(weight)}];
  });
  const weights = inputs.flatMap(input => input.weights);
  const samples = new Float32Array(vertex.getCount() * weights.length);
  const tuple = [];
  for (let i = 0; i < vertex.getCount(); i++) {
    let offset = i * weights.length;
    for (const {accessor, weights} of inputs) {
      accessor.getElement(i, tuple);
      for (let component = 0; component < weights.length; component++) {
        samples[offset++] = tuple[component];
      }
    }
  }
  const target = Math.floor(indices.length * fraction / 3) * 3;
  const [result] = MeshoptSimplifier.simplifyWithAttributes(
    Uint32Array.from(indices), positions, 3, samples, weights.length, weights, null,
    target, error / MeshoptSimplifier.getScale(positions, 3), ['Permissive', 'Prune'],
  );
  return result;
}

export function reindex(primitive, indices) {
  const [remap, count] = MeshoptEncoder.reorderMesh(indices, true, true);
  primitive.getIndices().setArray(count <= 65_535 ? Uint16Array.from(indices) : indices);
  for (const attribute of primitive.listAttributes()) {
    const original = attribute.getArray();
    const size = attribute.getElementSize();
    const compact = new original.constructor(count * size);
    for (let index = 0; index < remap.length; index++) {
      if (remap[index] === 0xffffffff) continue;
      compact.set(original.subarray(index * size, (index + 1) * size), remap[index] * size);
    }
    attribute.setArray(compact);
  }
}
