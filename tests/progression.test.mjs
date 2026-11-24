import { mkdtemp, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { credit, profile, register, unlockMastery } from '../server/accounts.mjs';

test('experience and seals are credited once and a repeated purchase does not spend twice', async () => {
  const folder = await mkdtemp(join(tmpdir(), 'pantheon-progression-'));
  process.env.PANTHEON_LOCAL_DB = join(folder,'progress.sqlite');
  const account = {handle:'test_hoplite',name:'Hoplitenprüfung',password:'test-password-for-progression'};
  const figure = {id:'hoplite',unlock:1};
  const advanced = {id:'peltast',unlock:3};
  try {
    await register({headers:{}},{setHeader(){}},account);
    await assert.rejects(unlockMastery(account.handle,'hoplite',0,[figure]),/fehlen dir Siegel/);
    const result = {id:'completed-local-game',won:true,duo:false,challenge:'campaign',merges:3,casts:1,xp:350,seals:3};
    await Promise.all([credit(account.handle,result),credit(account.handle,result)]);
    assert.equal((await profile(account.handle)).xp,350);
    assert.equal((await profile(account.handle)).seals,3);
    await assert.rejects(unlockMastery(account.handle,'peltast',0,[advanced]),/noch gesperrt/);
    const buys = await Promise.allSettled([
      unlockMastery(account.handle,'hoplite',0,[figure]),
      unlockMastery(account.handle,'hoplite',0,[figure]),
    ]);
    assert.equal(buys.filter(item=>item.status==='fulfilled').length,1);
    assert.equal((await profile(account.handle)).masteries.hoplite,1);
    assert.equal((await profile(account.handle)).seals,2);
    const upgraded = await unlockMastery(account.handle,'hoplite',1,[figure]);
    assert.equal(upgraded.masteries.hoplite,2);
    assert.equal(upgraded.seals,0);
  } finally {
    await rm(folder,{recursive:true,force:true});
  }
});
