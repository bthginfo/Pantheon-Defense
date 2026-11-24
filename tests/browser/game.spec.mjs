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

test('a phone can recruit, move troops, place a building and fight fullscreen', async ({browser,baseURL}, testInfo) => {
  const context = await browser.newContext({baseURL,viewport:{width:390,height:844},isMobile:true,hasTouch:true,deviceScaleFactor:2});
  const page = await context.newPage();
  const failures = [];
  page.on('pageerror', error => failures.push(error.message));
  try {
    await signUp(page,testAccount('solo'));
    await page.locator('#challenge').selectOption('rush');
    const mobileArena = page.waitForResponse(response => new URL(response.url()).pathname==='/assets/mobile/arena_aegean.glb');
    await page.locator('#create-match').tap();
    expect((await mobileArena).ok()).toBe(true);
    await expect(page.locator('#stage')).toHaveAttribute('data-rendered','true',{timeout:45_000});
    await expect(page.locator('#stage')).toHaveAttribute('data-models','ready',{timeout:45_000});
    await expect(page.locator('.build-slot:visible')).toHaveCount(32);
    await expect(page.locator('#fullscreen-button')).toHaveAttribute('aria-pressed','true');
    expect(await page.evaluate(() => document.querySelector('#match').getBoundingClientRect().height)).toBe(844);
    expect(await page.evaluate(() => document.documentElement.scrollHeight)).toBe(844);
    const sound = page.locator('#match-sound');
    await expect(sound).toHaveAttribute('data-sound','playing',{timeout:18_000});
    await sound.tap();
    await expect(sound).toHaveAttribute('data-sound','off');
    await sound.tap();
    await expect(sound).toHaveAttribute('data-sound','playing');
    await page.getByRole('button',{name:/Partie starten/}).tap();
    const recruitButton = page.getByRole('button',{name:/^Rekrutieren/});
    await expect(recruitButton).toBeEnabled();
    const sheet = page.locator('#command-sheet');
    const stageBefore = await page.locator('#stage').boundingBox();
    await page.getByRole('button',{name:'Helden · Rezepte'}).tap();
    await expect(sheet.getByRole('heading',{name:'Helden beschwören'})).toBeVisible();
    await expect(sheet.locator('[data-ritual="thekla"]')).toBeDisabled();
    await expect(sheet.locator('.ritual-status')).toContainText('Einheiten aus dem Rezept');
    expect((await sheet.boundingBox()).height).toBeGreaterThan(420);
    expect((await page.locator('#stage').boundingBox()).height).toBe(stageBefore.height);
    await sheet.getByRole('button',{name:'Ansicht schließen'}).tap();
    await recruitButton.tap();
    const filled = page.locator('.build-slot.filled');
    await expect(filled).toHaveCount(1);
    await expect(page.locator('[data-pane="recruit"] b')).toBeHidden();
    await expect(sheet).toBeHidden();
    const initialSlot = Number(await filled.getAttribute('data-slot'));
    const chosen = page.locator(`[data-slot="${initialSlot}"]`);
    const target = page.locator(`[data-slot="${initialSlot === 23 ? 19 : 23}"]`);
    const sourceRect = await chosen.boundingBox();
    const targetRect = await target.boundingBox();
    const touch = await context.newCDPSession(page);
    const point = (rect,x=.5) => ({x:rect.x+rect.width*x,y:rect.y+rect.height/2});
    await touch.send('Input.dispatchTouchEvent',{type:'touchStart',touchPoints:[point(sourceRect)]});
    await touch.send('Input.dispatchTouchEvent',{type:'touchMove',touchPoints:[point(targetRect,1.04)]});
    await expect(page.locator('#drag-figure')).toBeVisible();
    await expect(target).toHaveClass(/drag-aim/);
    await touch.send('Input.dispatchTouchEvent',{type:'touchEnd',touchPoints:[]});
    await touch.detach();
    await expect(target).toHaveClass(/filled/);
    await expect(chosen).not.toHaveClass(/filled/);
    expect((await page.locator('#stage').boundingBox()).height).toBe(stageBefore.height);
    await page.getByRole('button',{name:'Verschieben',exact:true}).tap();
    await chosen.tap();
    await expect(chosen).toHaveClass(/filled/);
    await page.getByRole('button',{name:'Bauen',exact:true}).tap();
    await page.locator('.building-card').filter({hasText:'Ägäis-Balliste'}).getByRole('button',{name:/Bauen/}).tap();
    await expect(sheet).toBeHidden();
    await expect(page.locator('.field-context')).toContainText('Freien Bauplatz wählen');
    await expect(filled).toHaveCount(1);
    await page.locator(`[data-slot="${initialSlot === 16 ? 18 : 16}"]`).tap();
    await page.locator('.field-context-open').tap();
    await expect(page.locator('.formation-summary')).toHaveText(/Ägäis-Balliste/);
    await expect(page.getByRole('button',{name:'Verschieben',exact:true})).toHaveCount(0);
    await sheet.getByRole('button',{name:'Ansicht schließen'}).tap();
    await expect(page.locator('#wave')).toHaveText(/^[1-9]\d* \/ 16$/,{timeout:25_000});
    await expect(page.locator('#kills')).not.toHaveText('0 besiegt',{timeout:25_000});
    await expect(page.locator('#wave-reward')).toContainText('Trainingsmarke',{timeout:24_000});
    await page.screenshot({path:testInfo.outputPath('arena.png')});
    await page.locator('#back-to-hub').tap();
    await page.locator('[data-resume]').first().tap();
    await expect(page.locator('#stage')).toHaveAttribute('data-rendered','true',{timeout:25_000});
    await expect(chosen).toHaveClass(/filled/);
    await page.getByRole('button',{name:'Partiemenü öffnen'}).tap();
    await page.getByRole('button',{name:'Partie aufgeben',exact:true}).tap();
    await page.locator('#leave-dialog').getByRole('button',{name:'Aufgeben',exact:true}).tap();
    await expect(page.getByRole('heading',{name:'Die Bastion ist gefallen'})).toBeVisible({timeout:22_000});
    await page.getByRole('button',{name:'Chronik öffnen'}).tap();
    await expect(page.getByRole('heading',{name:'Deine Chronik'})).toBeVisible();
    await expect(page.locator('.history')).toContainText('Die Hetzjagd');
    await expect(page.locator('.history')).toContainText(/\+\d+ EP/);
    await expect(page.locator('.history')).toContainText('Trainingsmarke');
    expect(failures.filter(error => !error.includes('control flow'))).toEqual([]);
  } finally {
    await context.close();
  }
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
    const link = host.getByRole('textbox',{name:'Einladungslink',exact:true});
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
    await expect(host.locator('#connection')).toHaveText(/^(Live|Verbunden)$/,{timeout:35_000});
    await expect(guest.locator('#connection')).toHaveText(/^(Live|Verbunden)$/,{timeout:35_000});
    await host.getByRole('button',{name:/Partie starten/}).click();
    const placed = await matchAction(hostContext,id,{type:'place',actor:'ballista',slot:18});
    expect(placed.status()).toBe(200);
    const game = (await placed.json()).game;
    const actor = game.pieces.find(piece => piece.actor === 'ballista');
    expect((await matchAction(guestContext,id,{type:'move',id:actor.id,slot:14})).status()).toBe(409);
    const token = randomUUID();
    const drawn = await matchAction(guestContext,id,{type:'recruit'},token);
    expect(drawn.status()).toBe(200);
    const duplicate = await matchAction(guestContext,id,{type:'recruit'},token);
    expect(duplicate.status()).toBe(200);
    const direct = (await duplicate.json()).game;
    const recruits = direct.pieces.filter(piece => piece.owner === 1);
    expect(recruits).toHaveLength(1);
    const [recruit] = recruits;
    expect(recruit.slot).toBeLessThan(16);
    expect(direct.players[1].reserve).toHaveLength(0);
    expect((await matchAction(guestContext,id,{type:'move',id:recruit.id,slot:19})).status()).toBe(409);
    const targetSlot = recruit.slot === 14 ? 13 : 14;
    expect((await matchAction(guestContext,id,{type:'move',id:recruit.id,slot:targetSlot})).status()).toBe(200);
    await expect(host.locator(`[data-slot="${targetSlot}"]`)).toHaveClass(/filled/,{timeout:25_000});
    await expect(host.locator('[data-slot="18"]')).toHaveAttribute('aria-label',/Ägäis-Balliste/,{timeout:25_000});
    await expect(guest.locator('[data-slot="18"]')).toHaveAttribute('aria-label',/Ägäis-Balliste/,{timeout:25_000});
    await guest.reload();
    await guest.locator('[data-resume]').first().click();
    await expect(guest.locator('#stage-legend')).toContainText(target.name);
    await expect(guest.locator('[data-slot="18"]')).toHaveAttribute('aria-label',/Ägäis-Balliste/,{timeout:25_000});
    // Free the host's software renderer before verifying timed waves in the guest.
    await host.goto('/');
    await expect(guest.locator('#wave')).toHaveText(/^[1-9]\d* \/ 30$/,{timeout:30_000});
    expect((await matchAction(hostContext,id,{type:'forfeit'})).status()).toBe(200);
    await expect(guest.getByRole('heading',{name:'Die Bastion ist gefallen'})).toBeVisible({timeout:20_000});
  } finally {
    await Promise.all([hostContext.close(),guestContext.close(),otherContext.close()]);
  }
});
