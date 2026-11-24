import assert from 'node:assert/strict';
import { randomUUID } from 'node:crypto';
import { setGlobalProxyFromEnv } from 'node:http';
import { WebSocket } from 'ws';
import { HttpsProxyAgent } from 'https-proxy-agent';

if (process.env.NODE_USE_ENV_PROXY === '1') setGlobalProxyFromEnv();

const base = new URL(process.argv[2] ?? 'http://127.0.0.1:4173');
const usePolling = process.argv.includes('--poll');
const proxy = base.protocol === 'https:' && (process.env.HTTPS_PROXY ?? process.env.https_proxy);
const socketAgent = proxy ? new HttpsProxyAgent(proxy) : undefined;
const wait = ms => new Promise(resolve => setTimeout(resolve, ms));

function browserSession() {
  let cookie;
  async function call(op, payload, params = {}) {
    const url = new URL('/api/game', base);
    url.search = new URLSearchParams({op, ...params});
    const answer = await fetch(url, {
      method: payload === undefined ? 'GET' : 'POST',
      headers: {...(cookie && {Cookie:cookie}), ...(payload !== undefined && {
        'Content-Type':'application/json', Origin:base.origin,
      })},
      ...(payload === undefined ? {} : {body:JSON.stringify(payload)}),
      signal: AbortSignal.timeout(14_000),
      redirect: 'error',
    });
    const set = answer.headers.get('set-cookie');
    if (set) {
      assert.match(set, /HttpOnly/i);
      assert.match(set, /SameSite=Lax/i);
      if (base.protocol === 'https:') assert.match(set, /Secure/i);
      cookie = set.split(';', 1)[0];
    }
    return {status:answer.status, data:await answer.json()};
  }
  function live(id) {
    if (usePolling) {
      return {
        close() {},
        async until(predicate, time=20_000) {
          const end=Date.now()+time;
          while (Date.now()<end) {
            const data=result(await call('board',undefined,{id}),200);
            if (predicate(data)) return data;
            await wait(650);
          }
          throw new Error('HTTP synchronization did not publish expected state before timeout.');
        },
      };
    }
    const url = new URL('/api/live',base);
    url.protocol = base.protocol === 'https:' ? 'wss:' : 'ws:';
    url.searchParams.set('id',id);
    const ws = new WebSocket(url,{headers:{Cookie:cookie, Origin:base.origin},agent:socketAgent,handshakeTimeout:12_000});
    let current, failure;
    ws.on('message', message => { current = JSON.parse(String(message)); });
    ws.on('error', error => { failure = error; });
    async function until(predicate, time=14_000) {
      const end = Date.now()+time;
      while (Date.now() < end) {
        if (failure) throw failure;
        if (current && predicate(current)) return current;
        await wait(80);
      }
      throw new Error('WebSocket did not publish expected state before timeout.');
    }
    return {until, close:()=>ws.close()};
  }
  return {call, live};
}

function account(label) {
  return {handle:'qa_'+label+'_'+randomUUID().slice(0,7), name:'Probe '+label, password:'pd-'+randomUUID()};
}
function result(actual, status) {
  assert.equal(actual.status,status,String(actual.status)+': '+(actual.data.error ?? 'unexpected status'));
  return actual.data;
}
function action(client,id,command,nonce=randomUUID()) {
  return client.call('action',{id,command,nonce});
}

const host=browserSession(), guest=browserSession(), observer=browserSession(), solo=browserSession();
const users=['host','guest','other','solo'].map(account);
const clients=[host,guest,observer,solo];
const metadata=result(await host.call('health'),200);
console.log('Testing release '+metadata.version+' at '+base.origin);
for (const [index,client] of clients.entries()) {
  const {user}=result(await client.call('register',users[index]),201);
  assert.equal(user.handle,users[index].handle);
}
assert.equal((await observer.call('register',users[2])).status,409);
console.log('Four isolated accounts and unique account handles verified.');

const {id,invite}=result(await host.call('new',{
  mode:'duo',theme:'aegean',challenge:'campaign',friend:users[1].handle,
}),201);
assert.equal((await observer.call('accept',{invite})).status,403);
assert.equal((await observer.call('board',undefined,{id})).status,403);
assert.equal((await action(host,id,{type:'start'})).status,409);
const a=host.live(id);
await a.until(p=>!p.joined);
const invited=result(await guest.call('accept',{invite}),200);
assert.equal(invited.viewer,1);
const b=guest.live(id);
try {
  await Promise.all([a.until(p=>p.joined && p.viewer===0),b.until(p=>p.joined && p.viewer===1)]);
  result(await action(host,id,{type:'start'}),200);
  const [placed,drawn]=await Promise.all([
    action(host,id,{type:'place',actor:'ballista',slot:2}),
    action(guest,id,{type:'recruit',slot:14}),
  ]);
  assert.equal(placed.status,200);
  assert.equal(drawn.status,200);
  const owner=await a.until(p=>p.game.pieces.length===2);
  const partner=await b.until(p=>p.game.pieces.length===2);
  assert.deepEqual(owner.game.pieces.map(p=>p.id),partner.game.pieces.map(p=>p.id));
  const cannon=owner.game.pieces.find(p=>p.owner===0);
  assert.equal((await action(guest,id,{type:'move',id:cannon.id,slot:15})).status,409);
  assert.equal((await action(host,id,{type:'move',id:cannon.id,slot:3})).status,409);
  const recruit=partner.game.pieces.find(p=>p.owner===1);
  const nonce=randomUUID();
  result(await action(guest,id,{type:'upgrade',id:recruit.id},nonce),200);
  const duplicate=result(await action(guest,id,{type:'upgrade',id:recruit.id},nonce),200);
  assert.equal(duplicate.game.pieces.find(p=>p.id===recruit.id).rank,2);
  const ready=await Promise.all([action(host,id,{type:'ready'}),action(guest,id,{type:'ready'})]);
  assert.ok(ready.every(r=>r.status===200 || r.status===409));
  await Promise.all([a.until(p=>p.game.wave>=1),b.until(p=>p.game.wave>=1)]);
  b.close();
  const restored=guest.live(id);
  try {
    const resumed=await restored.until(p=>p.id===id && p.game.wave>=1);
    assert.equal(resumed.viewer,1);
    assert.equal(resumed.game.pieces.length,2);
  } finally { restored.close(); }
  result(await action(host,id,{type:'forfeit'}),200);
  const record=result(await guest.call('session'),200).user.records.find(item=>item.id===id);
  assert.ok(record && record.xp>0 && record.duo);
  console.log('Bound invitation, denied third account, '+(usePolling?'HTTP synchronization':'live sockets')
    +', concurrent orders, reconnect and saved co-op XP verified.');
} finally { a.close(); b.close(); }

const soloRoom=result(await solo.call('new',{theme:'aegean',challenge:'rush',mode:'solo'}),201);
result(await action(solo,soloRoom.id,{type:'start'}),200);
result(await action(solo,soloRoom.id,{type:'place',actor:'ballista',slot:6}),200);
await action(solo,soloRoom.id,{type:'ready'});
const s=solo.live(soloRoom.id);
try {
  await s.until(p=>p.game.wave>=1 && p.game.kills>0,28_000);
  result(await action(solo,soloRoom.id,{type:'forfeit'}),200);
  const profile=result(await solo.call('session'),200).user;
  assert.ok(profile.records.some(m=>m.id===soloRoom.id && m.challenge==='rush' && m.xp>0));
} finally { s.close(); }
result(await solo.call('logout',{}),200);
assert.equal(result(await solo.call('session'),200).user,null);
const login=result(await solo.call('login',users[3]),200).user;
assert.ok(login.xp>0);
console.log('Solo challenge combat, profile persistence and logout/login verified.');
