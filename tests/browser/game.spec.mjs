import { test, expect } from '@playwright/test';
import { randomUUID } from 'node:crypto';

function testAccount(label) {
  return { handle: `qa_${label}_${randomUUID().slice(0,7)}`, name: `Prüfung ${label}`, password: `qa-${randomUUID()}` };
}

async function signUp(page, account) {
  await page.goto('/');
  await page.getByRole('button',{ name:'Anmelden', exact:true }).click();
  await page.getByRole('button',{ name:'Neues Konto erstellen', exact:true }).click();
  const dialog = page.locator('#account-dialog');
  await dialog.locator('input[name=name]').fill(account.name);
  await dialog.getByLabel('Rufname').fill(account.handle);
  await dialog.getByLabel('Passwort').fill(account.password);
  await dialog.getByRole('button',{ name:'Konto erstellen',exact:true }).click();
  await expect(page.locator('#account-button')).toContainText(account.name);
}

async function api(context, op, data, params = {}) {
  const result = await context.pages()[0].evaluate(async ({op,data,params}) => {
    const response = await fetch('/api/game?' + new URLSearchParams({op,...params}), {
      method: data ? 'POST' : 'GET',
      ...(data && {headers:{'Content-Type':'application/json'},body:JSON.stringify(data)}),
    });
    return {status:response.status,data:await response.json()};
  },{op,data,params});
  return {status:()=>result.status,json:async()=>result.data};
}

function matchAction(context, id, command, nonce = randomUUID()) {
  return api(context,'action',{id,command,nonce});
}

test('mobile lobby, collection and account interface fit a narrow viewport', async ({page}) => {
  await page.setViewportSize({width:390,height:844});
  await page.goto('/');
  await expect(page.getByRole('heading',{name:'Das Tor der Ägäis'})).toBeVisible();
  await expect(page.getByRole('button',{name:'Sammlung',exact:true})).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBe(390);
  await page.getByRole('button',{name:'Sammlung',exact:true}).click();
  await expect(page.getByRole('heading',{name:'Deine Sammlung'})).toBeVisible();
  await expect(page.getByRole('heading',{name:'Thekla',exact:true})).toBeVisible();
  await page.getByRole('button',{name:'Japan',exact:true}).click();
  await expect(page.getByRole('heading',{name:'Akari',exact:true})).toBeVisible();
});

test('a solo match renders the Bevy arena and persists results', async ({page}, testInfo) => {
  const failures = [];
  page.on('pageerror', error => failures.push(error.message));
  await signUp(page,testAccount('solo'));
  await page.locator('#challenge').selectOption('rush');
  await page.locator('#create-match').click();
  await expect(page.locator('#stage')).toHaveAttribute('data-rendered','true',{timeout:45000});
  await expect(page.locator('#stage')).toHaveAttribute('data-models','ready',{timeout:45000});
  await expect(page.getByRole('button',{name:/Partie starten/})).toBeEnabled();
  await page.getByRole('button',{name:/Partie starten/}).click();
  await page.getByRole('button',{name:/Ägäis-Balliste/}).click();
  await page.getByRole('button',{name:'Bauplatz 3',exact:true}).click();
  await expect(page.getByRole('heading',{name:'Ägäis-Balliste',exact:true})).toBeVisible();
  await expect(page.getByRole('button',{name:'Umstellen',exact:true})).toHaveCount(0);
  await page.getByRole('button',{name:/Truppe ziehen/}).click();
  const ready = page.getByRole('button',{name:/Bereit für die Welle/});
  if (await ready.isVisible()) await ready.click();
  await expect(page.locator('#wave')).toHaveText('1 / 8',{timeout:25_000});
  await expect(page.locator('#kills')).not.toHaveText('0 besiegt',{timeout:25_000});
  await page.screenshot({path:testInfo.outputPath('arena.png')});
  await page.getByRole('button',{name:'Partie aufgeben',exact:true}).click();
  await page.getByRole('button',{name:'Aufgeben',exact:true}).click();
  await expect(page.getByRole('heading',{name:'Das Tor ist gefallen'})).toBeVisible({timeout:22_000});
  await page.getByRole('button',{name:'Chronik öffnen'}).click();
  await expect(page.getByRole('heading',{name:'Deine Chronik'})).toBeVisible();
  await expect(page.locator('.history')).toContainText('Die Hetzjagd');
  await expect(page.locator('.history')).toContainText(/\+\d+ EP/);
  expect(failures.filter(error => !error.includes('control flow'))).toEqual([]);
});

test('an invitation grants only the chosen account and both browsers see the same game', async ({browser, baseURL}) => {
  const hostContext = await browser.newContext({baseURL, viewport:{width:1020,height:680}});
  const guestContext = await browser.newContext({baseURL, viewport:{width:1020,height:680}});
  const otherContext = await browser.newContext({baseURL, viewport:{width:1020,height:680}});
  try {
    const host = await hostContext.newPage();
    const guest = await guestContext.newPage();
    const other = await otherContext.newPage();
    const target = testAccount('duo_guest');
    await signUp(host,testAccount('duo_host'));
    await signUp(guest,target);
    await signUp(other,testAccount('other'));
    await host.getByRole('button',{name:'Zu zweit',exact:true}).click();
    await host.locator('#friend').fill(target.handle);
    await host.locator('#create-match').click();
    const link = host.getByRole('textbox',{name:'Kontogebundener Einladungslink'});
    await expect(link).toBeVisible();
    const href = await link.inputValue();
    const invite = new URLSearchParams(new URL(href).hash.slice(1)).get('einladung');
    const id = invite.split('.')[0];
    const forbidden = await api(otherContext,'accept',{invite});
    expect(forbidden.status()).toBe(403);
    expect((await api(otherContext,'board',undefined,{id})).status()).toBe(403);
    expect((await matchAction(hostContext,id,{type:'start'})).status()).toBe(409);
    await guest.goto(href);
    await guest.getByRole('button',{name:'Einladung annehmen'}).click();
    await expect(guest.locator('#match')).toBeVisible();
    await expect(host.getByRole('button',{name:/Partie starten/})).toBeEnabled({timeout:20_000});
    await expect(host.locator('#connection')).toHaveText(/^(Live|Synchronisiert)$/,{timeout:35_000});
    await expect(guest.locator('#connection')).toHaveText(/^(Live|Synchronisiert)$/,{timeout:35_000});
    await host.getByRole('button',{name:/Partie starten/}).click();
    const placed = await matchAction(hostContext,id,{type:'place',actor:'ballista',slot:2});
    expect(placed.status()).toBe(200);
    const game = (await placed.json()).game;
    const actor = game.pieces.find(piece => piece.actor === 'ballista');
    expect((await matchAction(guestContext,id,{type:'move',id:actor.id,slot:14})).status()).toBe(409);
    const token = randomUUID();
    expect((await matchAction(guestContext,id,{type:'recruit',slot:14},token)).status()).toBe(200);
    const duplicate = await matchAction(guestContext,id,{type:'recruit',slot:14},token);
    expect(duplicate.status()).toBe(200);
    expect((await duplicate.json()).game.pieces.length).toBe(2);
    await expect(host.locator('[data-slot="2"]')).toHaveAttribute('aria-label',/Ägäis-Balliste/,{timeout:25_000});
    await expect(guest.locator('[data-slot="2"]')).toHaveAttribute('aria-label',/Ägäis-Balliste/,{timeout:25_000});
    await guest.reload();
    await guest.locator('[data-resume]').first().click();
    await expect(guest.locator('#stage-legend')).toContainText(target.name);
    await expect(guest.locator('[data-slot="2"]')).toHaveAttribute('aria-label',/Ägäis-Balliste/,{timeout:25_000});
    const ready = await Promise.all([matchAction(hostContext,id,{type:'ready'}),matchAction(guestContext,id,{type:'ready'})]);
    for (const answer of ready) expect([200,409]).toContain(answer.status());
    await expect(guest.locator('#wave')).toHaveText(/^[1-9]\d* \/ 12$/,{timeout:25_000});
    expect((await matchAction(hostContext,id,{type:'forfeit'})).status()).toBe(200);
    await expect(guest.getByRole('heading',{name:'Das Tor ist gefallen'})).toBeVisible({timeout:20_000});
  } finally {
    await Promise.all([hostContext.close(),guestContext.close(),otherContext.close()]);
  }
});
