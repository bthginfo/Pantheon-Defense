import { mkdtemp, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { after, test } from 'node:test';
import assert from 'node:assert/strict';
import { randomUUID } from 'node:crypto';
import { changeFieldSign, credit, creditWaves, profile, register, unlockMastery } from '../server/accounts.mjs';
import { acceptInvite, act, board, catalog, createMatch } from '../server/matches.mjs';
import { mutate } from '../server/store.mjs';

const folder = await mkdtemp(join(tmpdir(), 'pantheon-progression-'));
process.env.PANTHEON_LOCAL_DB = join(folder,'progress.sqlite');
after(() => rm(folder, { recursive: true, force: true }));

async function account(handle) {
  return register({ headers: {} }, { setHeader() {} }, { handle, name: `Prüfung ${handle}`, password: 'test-password-for-progression' });
}

test('experience and seals are credited once and a repeated purchase does not spend twice', async () => {
  const { handle } = await account('test_hoplite');
  const figure = {id:'hoplite',unlock:1};
  const advanced = {id:'peltast',unlock:3};
  await assert.rejects(unlockMastery(handle,'hoplite',0,[figure]),/fehlen dir Siegel/);
  const result = {id:'completed-local-game',won:true,duo:false,challenge:'campaign',merges:3,casts:1,xp:350,seals:3};
  await Promise.all([credit(handle,result),credit(handle,result)]);
  assert.equal((await profile(handle)).xp,350);
  assert.equal((await profile(handle)).seals,3);
  await assert.rejects(unlockMastery(handle,'peltast',0,[advanced]),/noch gesperrt/);
  const buys = await Promise.allSettled([
    unlockMastery(handle,'hoplite',0,[figure]),
    unlockMastery(handle,'hoplite',0,[figure]),
  ]);
  assert.equal(buys.filter(item=>item.status==='fulfilled').length,1);
  assert.equal((await profile(handle)).masteries.hoplite,1);
  assert.equal((await profile(handle)).seals,2);
  const upgraded = await unlockMastery(handle,'hoplite',1,[figure]);
  assert.equal(upgraded.masteries.hoplite,2);
  assert.equal(upgraded.seals,0);
});

test('both players retain wave materials and proportional EP after an unsuccessful match', async () => {
  const host = await account('wave_host');
  const guest = await account('wave_guest');
  const config = { mode: 'duo', friend: guest.handle, theme: 'aegean', challenge: 'campaign', difficulty: 'normal' };
  const { id, invite } = await createMatch(host.handle, config);
  await acceptInvite(guest.handle, invite);
  await act(host.handle, id, { nonce: randomUUID(), command: { type: 'start' } });
  await mutate(`match-${id}`, room => ({ ...room, clockMs: Date.now() - 525 * 50 }));
  const packets = await Promise.all([board(host.handle, id), board(guest.handle, id)]);
  for (const packet of packets) {
    assert.equal(packet.game.wave, 2);
    assert.equal(packet.game.treasury.wave, 1);
    assert.equal(packet.game.treasury.spoils.training, 1);
  }
  for (const member of [host, guest]) assert.equal((await profile(member.handle)).materials.training, 1);
  await act(guest.handle, id, { nonce: randomUUID(), command: { type: 'forfeit' } });
  await Promise.all([board(host.handle, id), board(guest.handle, id)]);
  for (const member of [host, guest]) {
    const saved = await profile(member.handle);
    assert.equal(saved.materials.training, 1);
    assert.equal(saved.xp, 40);
    assert.equal(saved.records[0].won, false);
    assert.equal(saved.records[0].wave, 2);
    assert.equal(saved.campaignWins.normal ?? 0, 0);
  }
});

test('campaign clears and mastery unlock harder rooms and high-wave loot equips a field sign', async () => {
  const { handle } = await account('campaign_host');
  const guest = await account('campaign_guest');
  const settings = { mode: 'solo', theme: 'aegean', challenge: 'campaign', difficulty: 'hard' };
  await assert.rejects(createMatch(handle, settings), /für dein Konto noch gesperrt/);
  await assert.rejects(createMatch(handle, { ...settings, difficulty: 'invalid' }), /gibt es nicht/);
  const wave = { wave: 6, spoils: { training: 9, runedust: 3, cores: 3 } };
  await Promise.all([creditWaves(handle, 'materials', wave), creditWaves(handle, 'materials', wave)]);
  await creditWaves(handle, 'materials', { wave: 4, spoils: { training: 7, runedust: 2, cores: 1 } });
  for (const id of ['hoplite','slinger','toxotes']) await unlockMastery(handle, id, 0, catalog.actors);
  assert.equal((await profile(handle)).materials.training, 0);
  const result = { id: 'won-first', won: true, wave: 30, challenge: 'campaign', xp: 600, seals: 2 };
  await credit(handle, result); // Older Normal victories continue to count.
  await assert.rejects(createMatch(handle, settings), /für dein Konto noch gesperrt/);
  await credit(handle, { ...result, id: 'won-second', difficulty: 'normal' });
  await assert.rejects(createMatch(handle, { ...settings, mode: 'duo', friend: guest.handle }), /für das eingeladene Konto noch gesperrt/);
  await assert.rejects(changeFieldSign(handle, { id: 'supply', action: 'equip' }, catalog.fieldSigns), /Schmiede dieses Feldzeichen zuerst/);
  const forge = { id: 'supply', action: 'forge', expected: 0 };
  const receipts = await Promise.allSettled([changeFieldSign(handle, forge, catalog.fieldSigns), changeFieldSign(handle, forge, catalog.fieldSigns)]);
  assert.equal(receipts.filter(receipt => receipt.status === 'fulfilled').length, 1);
  const upgraded = await changeFieldSign(handle, { ...forge, expected: 1 }, catalog.fieldSigns);
  assert.equal(upgraded.fieldSigns.supply, 2);
  assert.equal(upgraded.materials.runedust, 0);
  assert.equal(upgraded.materials.cores, 0);
  const { game } = await createMatch(handle, settings);
  assert.equal(game.difficulty, 'hard');
  assert.equal(game.players[0].gold, 187 + 64);
  assert.deepEqual(game.players[0].field_sign, { id: 'supply', rank: 2 });
  await changeFieldSign(handle, { id: null, action: 'equip' }, catalog.fieldSigns);
  assert.equal((await createMatch(handle, settings)).game.players[0].gold, 187);
});
