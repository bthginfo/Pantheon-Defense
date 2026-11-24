import { readFileSync } from 'node:fs';
import { test } from 'node:test';
import assert from 'node:assert/strict';
import core from '../server/generated/simulation.js';

const catalog = JSON.parse(readFileSync(new URL('../public/assets/catalog.json', import.meta.url),'utf8'));
const assets = new URL('../public/assets/models/', import.meta.url);

function clipNames(id) {
  const data = readFileSync(new URL(`${id}.glb`,assets));
  assert.equal(data.toString('ascii',0,4),'glTF',id);
  const json = JSON.parse(data.toString('utf8',20,20+data.readUInt32LE(12)));
  return new Set(json.animations?.map(clip => clip.name) ?? []);
}

test('exported Blender actors include the clips used by Bevy', () => {
  for (const actor of catalog.actors) {
    const names = clipNames(actor.id);
    for (const clip of ['Idle','Attack','Cast']) assert.ok(names.has(clip), `${actor.id}: ${clip}`);
    if (actor.kind !== 'building') assert.ok(names.has('Walk'),actor.id);
  }
  for (const actor of catalog.enemies) {
    const names = clipNames(actor.id);
    for (const clip of ['Walk','Hit','Death']) assert.ok(names.has(clip), `${actor.id}: ${clip}`);
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
