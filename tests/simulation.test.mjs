import { readFileSync } from 'node:fs';
import { test } from 'node:test';
import assert from 'node:assert/strict';
import core from '../server/generated/simulation.js';

const catalog = JSON.parse(readFileSync(new URL('../public/assets/catalog.json', import.meta.url),'utf8'));
const assets = new URL('../public/assets/models/', import.meta.url);
const mobileAssets = new URL('../public/assets/mobile/', import.meta.url);

function model(id, folder = assets) {
  const data = readFileSync(new URL(`${id}.glb`,folder));
  assert.equal(data.toString('ascii',0,4),'glTF',id);
  return JSON.parse(data.toString('utf8',20,20+data.readUInt32LE(12)));
}

test('exported Blender actors include the clips used by Bevy', () => {
  for (const actor of [...catalog.actors,...catalog.enemies]) {
    const asset=model(actor.id);
    const clips=new Set(asset.animations.map(clip=>clip.name));
    const needed=actor.kind==='building'
      ? ['Idle','Attack','Cast']
      : ['Idle','Walk','Attack','Cast','Hit','Death','Spawn','Ascend','Celebrate'];
    for (const clip of needed) assert.ok(clips.has(clip),`${actor.id}: ${clip}`);
    assert.equal(asset.skins.length,1,actor.id);
    assert.equal(asset.meshes.length,1,actor.id);
    assert.equal(asset.meshes[0].primitives.length,1,actor.id);
    const attributes=asset.meshes[0].primitives[0].attributes;
    assert.ok(Number.isInteger(attributes.COLOR_0) && Number.isInteger(attributes.JOINTS_0),actor.id);
    const material = asset.materials[0].pbrMetallicRoughness;
    assert.ok(Number.isInteger(attributes.TEXCOORD_0), `${actor.id}: surface coordinates`);
    assert.ok(Number.isInteger(attributes.TEXCOORD_1), `${actor.id}: material finish coordinates`);
    assert.ok(Number.isInteger(material.baseColorTexture?.index), `${actor.id}: painted colour atlas`);
    assert.equal(material.baseColorTexture.texCoord ?? 0, 0, `${actor.id}: painted surface UVs`);
    assert.ok(Number.isInteger(material.metallicRoughnessTexture?.index), `${actor.id}: packed finishes`);
    assert.equal(material.metallicRoughnessTexture.texCoord,1,actor.id);
    if (actor.kind==='hero') {
      assert.ok(Number.isInteger(attributes.TANGENT), `${actor.id}: normal-map tangents`);
      assert.ok(Number.isInteger(asset.materials[0].normalTexture?.index), `${actor.id}: woven and tooled surfaces`);
      assert.equal(material.baseColorTexture.texCoord ?? 0, asset.materials[0].normalTexture.texCoord ?? 0,
        `${actor.id}: colour and relief share the surface UVs`);
    }
  }
});

test('the three Blender arenas ship as vertex-lit static meshes', () => {
  for (const {id} of catalog.themes) {
    const arena=model(`arena_${id}`);
    assert.equal(arena.meshes.length,1,id);
    assert.equal(arena.meshes[0].primitives.length,1,id);
    assert.ok(Number.isInteger(arena.meshes[0].primitives[0].attributes.COLOR_0),id);
    assert.ok(arena.materials[0].extensions.KHR_materials_unlit,id);
    assert.ok(!arena.animations?.length,id);
  }
});

test('mobile models reduce the geometry budget and preserve paint and animation bindings', () => {
  const variants = readFileSync(new URL('models.txt', mobileAssets), 'utf8').trim().split('\n');
  for (const { id } of catalog.themes) assert.ok(!variants.includes(`arena_${id}`), `${id}: boards keep their full export on phones`);
  const mesh = glb => glb.meshes[0].primitives[0];
  const indices = glb => glb.accessors[mesh(glb).indices].count;
  const clips = glb => glb.animations?.map(clip => clip.name).sort() ?? [];
  for (const id of variants) {
    const desktop = model(id);
    const mobile = model(id, mobileAssets);
    assert.ok(indices(mobile) <= indices(desktop) * .75, id);
    assert.deepEqual(Object.keys(mesh(mobile).attributes).sort(), Object.keys(mesh(desktop).attributes).sort(), id);
    assert.deepEqual(clips(mobile), clips(desktop), id);
    assert.equal(mobile.skins?.[0].joints.length, desktop.skins?.[0].joints.length, id);
    assert.equal(mobile.images?.length, desktop.images?.length, id);
  }
});

test('the campaign introduces regional formations and each difficulty has its own final boss and reward metals', () => {
  function state(theme, difficulty) {
    return JSON.parse(core.create_game(JSON.stringify({ theme,difficulty,rule_version:2,challenge:'campaign',levels:[1],seed:46 })));
  }
  function spawn(game, wave, spawned) {
    return JSON.parse(core.advance_game(JSON.stringify({ ...game, phase:'combat', wave, wave_tick:0, spawned }), 1)).enemies[0];
  }
  for (const region of catalog.themes) {
    const normal = state(region.id,'normal');
    assert.equal(spawn(normal,1,0).kind,region.wave_pack[0]);
    assert.equal(spawn(normal,6,0).kind,region.wave_pack[1]);
    let previousHealth = 0;
    let previousTime = Infinity;
    for (const stage of catalog.difficulties) {
      const game = state(region.id,stage.id);
      // The boss is the last enemy of the final wave.
      const finalSpawn = Math.max(6, Math.floor(Math.min(14 + Math.floor(game.wave_limit * 3 / 4), 42) / 3)) + stage.rank - 1;
      const boss = spawn(game, game.wave_limit, finalSpawn);
      assert.equal(boss.kind, region.boss_pack[stage.rank]);
      assert.ok(boss.hp > previousHealth);
      assert.ok(boss.deadline < previousTime);
      previousHealth = boss.hp;
      previousTime = boss.deadline;
      const rewarded = JSON.parse(core.advance_game(JSON.stringify({
        ...game, phase:'combat', wave:5, wave_tick:259, spawned:20,
      }), 261));
      assert.equal(rewarded.treasury.wave, 6);
      assert.equal(rewarded.treasury.spoils.shards, 1 + Math.floor(stage.rank / 2));
      assert.equal(rewarded.treasury.spoils.runedust, stage.rank ? 1 + Math.floor(stage.rank / 2) : 0);
      assert.equal(rewarded.treasury.spoils.cores, Math.max(0, stage.rank - 1));
    }
  }
});

function playMatch(theme, challenge, levels, seed) {
  let value = core.create_game(JSON.stringify({theme,challenge,levels,seed}));
  let state = JSON.parse(value);
  const send = (index, action) => {
    try {
      value = core.apply_action(value,index,JSON.stringify(action));
      state = JSON.parse(value);
      return true;
    } catch { return false; }
  };
  const defs = catalog.actors.filter(a=>a.theme===theme);
  const towers = [...defs.filter(a=>a.kind==='building')];
  const hero = defs.find(a=>a.kind==='hero');
  const has = slot=>state.pieces.some(piece=>piece.slot===slot);
  const plans = levels.length===1
    ? [[[6,0],[10,1],[18,0],[22,1],[2,0],[14,0],[3,2],[15,2]]]
    : [[[6,0],[10,1],[2,0],[3,2]],[[18,0],[22,1],[14,0],[15,2]]];
  send(0,{type:'start'});
  let lastPrep = -1;
  let bossCount = 0;
  let seen = new Set();
  for (let i=0; i<1200 && !['won','lost'].includes(state.phase); i++) {
    if (state.phase === 'prep' && state.wave !== lastPrep) {
      lastPrep = state.wave;
      for (let p=0; p<levels.length; p++) {
        const plan = plans[p];
        for (const [slot, index] of plan.slice(0, state.wave + 2)) {
          if (!has(slot)) send(p,{type:'place',actor:towers[index].id,slot});
        }
        const slot = p===0?11:23;
        if (!has(slot) && state.wave>=2) send(p,{type:'place',actor:hero.id,slot});
        const pieces = state.pieces.filter(piece=>piece.owner===p);
        for (const piece of pieces) {
          if (piece.rank <= Math.min(3,1+Math.floor(state.wave/2))) send(p,{type:'upgrade',id:piece.id});
        }
        if(state.wave>=2 && state.players[p].gold >= 65) send(p,{type:'recruit'});
        for (const piece of pieces) if (piece.tier < 3) send(p,{type:'merge',id:piece.id});
        send(p,{type:'ready'});
      }
    }
    if (state.phase === 'combat') {
      for (const enemy of state.enemies) seen.add(enemy.kind);
      for (let p=0; p<levels.length; p++) {
        const champion = state.pieces.find(piece=>piece.owner===p && piece.actor===hero.id);
        if (champion && champion.cast_ready<=state.tick && state.enemies.some(e=>e.progress>7)) {
          send(p,{type:'cast',id:champion.id,slot:null});
        }
      }
      bossCount += state.enemies.filter(e=>e.kind==='golem'||e.kind==='titan').length;
    }
    value = core.advance_game(value,20);
    state = JSON.parse(value);
  }
  return { state, seen, bossCount };
}

for (const [theme, challenge, levels] of [
  ['aegean','campaign',[1]],
  ['aegean','campaign',[1,1]],
  ['rome','rush',[4]],
  ['japan','siege',[5,5]],
  ['aegean','endurance',[6]],
]) {
  test(`deterministic play-through reaches a result: ${theme} / ${challenge} / ${levels.length}`, () => {
    const {state, seen, bossCount} = playMatch(theme,challenge,levels,17655);
    assert.ok(['won','lost'].includes(state.phase));
    assert.ok(state.wave >= Math.min(state.wave_limit,8), `Reached wave ${state.wave}`);
    assert.ok(state.kills >= 50);
    assert.ok(seen.size >= 4);
    assert.ok(bossCount > 0);
    assert.ok(state.players.some(player=>player.casts > 0));
    if (challenge === 'campaign') assert.equal(state.phase,'won');
  });
}
