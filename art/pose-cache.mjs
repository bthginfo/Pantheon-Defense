import { NodeIO } from '@gltf-transform/core';
import { ALL_EXTENSIONS } from '@gltf-transform/extensions';
import { mat4, quat, vec3 } from 'gl-matrix';
import { mkdir, readFile, writeFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { gzipSync } from 'node:zlib';
import { reindex, simplify } from './mesh-budget.mjs';

const assets = new URL('../public/assets/', import.meta.url);
const catalog = JSON.parse(await readFile(new URL('catalog.json', assets), 'utf8'));
const optimized = new Set((await readFile(new URL('mobile/models.txt', assets), 'utf8')).trim().split('\n'));
const out = new URL('crowd/', assets);
const clips = ['Idle','Walk','Attack','Cast','Hit','Death','Spawn','Ascend','Celebrate'];
const samplesPerSecond = 16;
const crowdFields = [['NORMAL', .12], ['TEXCOORD_0', .06], ['COLOR_0', [.23,.23,.23,.08]],
  ['JOINTS_0', [.015,.015]], ['WEIGHTS_0', .28]];
await mkdir(out, {recursive:true});
const io = new NodeIO().registerExtensions(ALL_EXTENSIONS);

function channels(clip, lookup) {
  return clip.listChannels().map(channel => {
    const sampler = channel.getSampler();
    const mode = sampler.getInterpolation();
    if (mode!=='LINEAR' && mode!=='STEP') throw new Error(`Unsupported baked curve ${mode}`);
    const property = channel.getTargetPath();
    return {
      node:lookup.get(channel.getTargetNode()), property,
      time:sampler.getInput().getArray(), value:sampler.getOutput().getArray(),
      width:property==='rotation' ? 4 : 3, step:mode==='STEP',
    };
  });
}

function sample(curve, t, result) {
  const {time, value, width, step, property} = curve;
  let first = 0;
  let last = time.length-1;
  while (last-first>1) {
    const mid = (last+first) >>> 1;
    if (time[mid]<=t) first = mid;
    else last = mid;
  }
  if (t>=time[last]) first = last;
  const a = value.subarray(first*width,(first+1)*width);
  if (first===last || step || t<=time[first]) {
    result.set(a);
    return;
  }
  const b = value.subarray(last*width,(last+1)*width);
  const blend = (t-time[first])/(time[last]-time[first]);
  if (property==='rotation') quat.slerp(result,a,b,blend);
  else vec3.lerp(result,a,b,blend);
}

function bakedPoses(document, skin) {
  const root = document.getRoot();
  const nodes = root.listNodes();
  const lookup = new Map(nodes.map((node,index) => [node,index]));
  const base = nodes.map(node=>({
    parent:lookup.get(node.getParentNode()),
    translation:node.getTranslation(), rotation:node.getRotation(), scale:node.getScale(),
  }));
  const poses = base.map(node => ({
    translation:vec3.clone(node.translation), rotation:quat.clone(node.rotation), scale:vec3.clone(node.scale),
  }));
  const world = nodes.map(()=>mat4.create());
  const local = nodes.map(()=>mat4.create());
  const ready = new Uint8Array(nodes.length);
  const joints = skin.listJoints().map(joint=>lookup.get(joint));
  const inverses = skin.getInverseBindMatrices().getArray();
  const videos = new Map(root.listAnimations().map(clip=>[clip.getName(),clip]));
  const palette = [];
  const timings = [];
  const matrix = mat4.create();

  function worldMatrix(index) {
    if (ready[index]) return world[index];
    const pose = poses[index];
    mat4.fromRotationTranslationScale(local[index],pose.rotation,pose.translation,pose.scale);
    const parent = base[index].parent;
    if (parent!==undefined) mat4.multiply(world[index],worldMatrix(parent),local[index]);
    else mat4.copy(world[index],local[index]);
    ready[index] = 1;
    return world[index];
  }

  let row = 0;
  for (const name of clips) {
    const clip = videos.get(name) ?? videos.get('Idle');
    if (!clip) throw new Error('Missing idle animation');
    const curves = channels(clip,lookup);
    const start = Math.min(...curves.map(curve=>curve.time[0]));
    const end = Math.max(...curves.map(curve=>curve.time.at(-1)));
    const duration = Math.max(.001,end-start);
    const frames = Math.max(2,Math.ceil(duration*samplesPerSecond)+1);
    timings.push({row,frames,duration});
    for (let frame=0; frame<frames; frame++) {
      for (const [index, original] of base.entries()) {
        const pose = poses[index];
        pose.translation.set(original.translation);
        pose.rotation.set(original.rotation);
        pose.scale.set(original.scale);
      }
      ready.fill(0);
      const t = start+duration*frame/(frames-1);
      for (const curve of curves) sample(curve,t,poses[curve.node][curve.property]);
      for (const [index, node] of joints.entries()) {
        mat4.multiply(matrix,worldMatrix(node),inverses.subarray(index*16,(index+1)*16));
        for (let axis=0; axis<3; axis++) palette.push(matrix[axis],matrix[4+axis],matrix[8+axis],matrix[12+axis]);
      }
      row++;
    }
  }
  return {joints:joints.length,rows:row,timings,palette:Float32Array.from(palette)};
}

function field(primitive, name, width, Type = Float32Array) {
  const accessor = primitive.getAttribute(name);
  if (!accessor) throw new Error(`Missing mesh attribute ${name}`);
  if (accessor.getElementSize()===width && !accessor.getNormalized()) return Type.from(accessor.getArray());
  const result = new Type(accessor.getCount()*width);
  const element = [];
  for (let index=0; index<accessor.getCount(); index++) {
    accessor.getElement(index,element);
    for (let c=0; c<width; c++) result[index*width+c] = element[c] ?? 1;
  }
  return result;
}

const requested = new Set(process.argv.slice(2));
for (const {id,kind} of [...catalog.actors,...catalog.enemies]) {
  if (requested.size && !requested.has(id)) continue;
  const pathname = new URL(`${optimized.has(id)?'mobile':'models'}/${id}.glb`,assets);
  const document = await io.read(fileURLToPath(pathname));
  const node = document.getRoot().listNodes().find(node=>node.getMesh() && node.getSkin());
  if (!node) throw new Error(`Expected a skinned Blender mesh for ${id}`);
  const [primitive] = node.getMesh().listPrimitives();
  const triangles = primitive.getIndices().getCount() / 3;
  if (triangles >= 1_667) {
    // Keep paint and joints aligned while cutting small geometry visible only in close-ups.
    const hero = kind === 'hero';
    const indices = simplify(primitive, crowdFields, hero ? .82 : .7, hero ? .022 : .03);
    if (indices.length && indices.length < triangles * 3 * .89) reindex(primitive, indices);
  }
  const paint = primitive.getMaterial()?.getBaseColorTexture()?.getImage();
  if (!paint || paint[0]!==137 || paint[1]!==80) throw new Error(`Expected a PNG paint atlas for ${id}`);
  const {joints,rows,timings,palette} = bakedPoses(document,node.getSkin());
  const positions = field(primitive,'POSITION',3);
  const index = Uint32Array.from(primitive.getIndices().getArray());
  const layout = Buffer.alloc(24+clips.length*12);
  layout.write('PDM1',0);
  [positions.length/3,index.length,joints,rows,paint.length].forEach((v,i)=>layout.writeUInt32LE(v,4+i*4));
  for (const [i,timing] of timings.entries()) {
    layout.writeUInt32LE(timing.row,24+i*12);
    layout.writeUInt32LE(timing.frames,28+i*12);
    layout.writeFloatLE(timing.duration,32+i*12);
  }
  const source = [positions, field(primitive,'NORMAL',3), field(primitive,'TEXCOORD_0',2),
    field(primitive,'COLOR_0',4), field(primitive,'JOINTS_0',4,Uint16Array), field(primitive,'WEIGHTS_0',4),
    index, palette, paint];
  const binary = Buffer.concat([layout,...source.map(arr=>Buffer.from(arr.buffer,arr.byteOffset,arr.byteLength))]);
  const packed = gzipSync(binary, {level:6});
  await writeFile(new URL(`${id}.figure`,out),packed);
  console.log(`${id} ${positions.length/3} vertices, ${rows} poses, ${Math.round(packed.length/1024)} KiB`);
}
