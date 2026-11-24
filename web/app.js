import '@fontsource-variable/cormorant-garamond';
import '@fontsource-variable/dm-sans';
import './style.css';
import { $, esc, portrait, numeral, number, price, pieceLabel, groupNames, themeHeroes, shortNames, colorThemes, actorCard, historyRow } from './presentation.js';
import { battleSound, isMuted, score, toggleSound } from './audio.js';

const catalog = await fetch('/assets/catalog.json').then(answer => answer.json());
const actors = new Map(catalog.actors.map(actor => [actor.id, actor]));
const themes = new Map(catalog.themes.map(theme => [theme.id, theme]));
const challenges = new Map(catalog.challenges.map(challenge => [challenge.id, challenge]));
const enemies = new Map(catalog.enemies.map(enemy => [enemy.id, enemy]));
let user = null;
let currentVersion = '1.0.0';
let theme = 'aegean';
let factionFilter = 'aegean';
let challenge = 'campaign';
let mode = 'solo';
let tab = 'bastion';
let authMode = 'login';
let friendDraft = '';
let room = null;
let selected = null;
let pending = null;
let arena = null;
let arenaInit = null;
let socket = null;
let polling = null;
let restore = null;
let failures = 0;
let recentEvents = new Set();
let locked = false;
let toastTimer;
let invitation = new URLSearchParams(location.hash.slice(1)).get('einladung');
let talking = false;
let menuPane = 'building';
let orderSignature = '';
let lastPhase = '';
const grid = [];

async function request(op, body, params = {}) {
  const url = new URL('/api/game', location.href);
  url.search = new URLSearchParams({op, ...params});
  const response = await fetch(url, {
    method: body === undefined ? 'GET' : 'POST',
    headers: body === undefined ? {} : {'Content-Type': 'application/json'},
    ...(body === undefined ? {} : {body: JSON.stringify(body)}),
    cache: 'no-store',
  });
  const result = await response.json().catch(() => ({}));
  if (!response.ok) throw Object.assign(new Error(result.error ?? `Verbindung fehlgeschlagen (${response.status}).`), { status: response.status });
  return result;
}

function toast(text, issue = false) {
  const box = $('toast');
  clearTimeout(toastTimer);
  box.classList.toggle('issue', issue);
  box.textContent = text;
  box.hidden = false;
  toastTimer = setTimeout(() => { box.hidden = true; }, issue ? 5600 : 3800);
}

function versionLabel() {
  $('version').textContent = `v${currentVersion}`;
}

function soundLabel() {
  $('sound-button').setAttribute('aria-pressed', String(!isMuted()));
  $('sound-button').classList.toggle('muted', isMuted());
}

function changeAccount(next) {
  user = next;
  const button = $('account-button');
  button.textContent = user ? `${user.name} · Stufe ${user.level}` : 'Anmelden';
  button.setAttribute('aria-label', user ? `Profil von ${user.name}, Stufe ${user.level}` : 'Anmelden');
  paintLobby();
}

async function refreshAccount() {
  try {
    const result = await request('session');
    changeAccount(result.user);
  } catch (error) { toast(error.message, true); }
}

function chooseTab(next, scroll = true) {
  if (room) leaveView();
  tab = next;
  for (const pane of ['bastion','collection','chronicle']) $(pane).hidden = pane !== tab;
  document.querySelectorAll('.nav [data-tab]').forEach(button => {
    if (button.dataset.tab === tab) button.setAttribute('aria-current','page');
    else button.removeAttribute('aria-current');
  });
  paintLobby();
  if (scroll) window.scrollTo({top:0,behavior:'instant'});
}

function paintLobby() {
  if (tab === 'collection') paintCollection();
  else if (tab === 'chronicle') paintChronicle();
  else paintPreparation();
}

function paintPreparation() {
  const level = user?.level ?? 1;
  if ((themes.get(theme)?.unlock ?? 0) > level) theme = 'aegean';
  if ((challenges.get(challenge)?.unlock ?? 0) > level) challenge = 'campaign';
  const chosen = themes.get(theme);
  const [id, name, role] = themeHeroes[theme];
  const header = $('hero-title');
  if (header.dataset.theme !== theme) {
    header.dataset.theme = theme;
    header.innerHTML = ({aegean:'Das Tor<br>der Ägäis',rome:'Die Rote<br>Zitadelle',japan:'Der<br>Nebelpass'})[theme];
    $('hero-character').src = `/assets/portraits/${id}.png`;
    $('hero-character-name').textContent = name;
    $('hero-character-role').textContent = role;
    document.querySelector('.hero').dataset.theme = theme;
  }
  $('hero-description').textContent = theme === 'aegean'
    ? 'Zieh deine Truppen, schmiede stärkere Ränge und halte die anrückenden Wellen auf. Allein oder zu zweit.'
    : chosen.caption;
  for (const modeButton of document.querySelectorAll('[data-mode]')) {
    modeButton.setAttribute('aria-pressed', String(modeButton.dataset.mode === mode));
  }
  $('theme-list').innerHTML = catalog.themes.map(item => {
    const unavailable = item.unlock > level;
    return `<button class="theme-card ${item.id === theme ? 'chosen' : ''}" data-theme="${item.id}"
      aria-pressed="${item.id === theme}" style="--theme-accent:${item.accent}" ${unavailable ? 'aria-disabled="true"' : ''}>
      <img src="/assets/scenes/${item.id}.webp" alt="">
      <span class="theme-info"><small>${esc(item.name)}</small><strong>${esc(item.map)}</strong>
      ${unavailable ? `<span class="theme-lock">Ab Profilstufe ${item.unlock}</span>` : ''}</span>
    </button>`;
  }).join('');
  $('challenge').innerHTML = catalog.challenges.map(item => `<option value="${item.id}" ${item.unlock > level ? 'disabled' : ''}>
      ${esc(item.name)}${item.unlock > level ? ` · Stufe ${item.unlock}` : ''}</option>`).join('');
  $('challenge').value = challenge;
  $('challenge-detail').textContent = challenges.get(challenge).detail;
  $('friend-row').hidden = mode !== 'duo';
  if (document.activeElement !== $('friend')) $('friend').value = friendDraft;
  $('create-match').textContent = mode === 'duo' ? 'Koop-Raum öffnen ›' : 'Solo-Partie öffnen ›';
}

function paintCollection() {
  const level = user?.level ?? 1;
  $('collection-level').textContent = user ? `Profilstufe ${level} · ${number(user.xp)} EP` : 'Spiele Partien, um neue Figuren freizuschalten.';
  $('collection-filters').innerHTML = catalog.themes.map(item => `<button data-faction="${item.id}"
    aria-pressed="${item.id === factionFilter}">${esc(item.name)}</button>`).join('');
  const items = catalog.actors.filter(actor => actor.theme === factionFilter);
  $('actor-cards').innerHTML = Object.entries(groupNames).map(([kind,label]) => `<section>
    <h2>${label}</h2><div class="card-grid">${items.filter(a => a.kind === kind).map(a => actorCard(a,level)).join('')}</div>
    </section>`).join('');
}

function paintChronicle() {
  if (!user) {
    $('chronicle-content').innerHTML = '<div class="paper-panel"><p>Melde dich an, um deinen Fortschritt und vergangene Partien zu sehen.</p><button class="primary" data-auth="login">Anmelden</button></div>';
    return;
  }
  const threshold = user.level ** 2 * 140;
  $('chronicle-content').innerHTML = `<section class="profile-panel">
    <div class="profile-mark" aria-hidden="true">${esc(user.name.slice(0,1).toUpperCase())}</div>
    <div><h2>${esc(user.name)}</h2><p>@${esc(user.handle)} · ${number(user.xp)} EP</p>
      <meter min="0" max="${Math.max(user.xp,threshold)}" value="${user.xp}" aria-label="Erfahrungspunkte"></meter></div>
    <strong>Stufe ${user.level}</strong><button class="quiet" id="sign-out">Abmelden</button>
  </section>
  ${user.badges.length ? `<div class="medals">${user.badges.map(b => `<span><i aria-hidden="true">✦</i>${esc(b)}</span>`).join('')}</div>` : ''}
  <section class="paper-panel"><h2>Abgeschlossene Partien</h2>
  ${user.records.length ? `<ul class="history">${user.records.map(item => historyRow(item,catalog)).join('')}</ul>` :
    '<p>Deine erste gespielte Partie erscheint hier.</p>'}</section>`;
}

async function recentRooms() {
  if (!user) { $('recent-block').hidden = true; return; }
  try {
    const result = await request('rooms');
    $('recent-block').hidden = !result.rooms.length;
    $('recent').innerHTML = result.rooms.map(item => `<button data-resume="${item.id}" class="resume">
      <span><strong>${esc(themes.get(item.theme)?.map)}</strong><small>${item.mode === 'duo' ? 'Koop' : 'Solo'} · ${esc(challenges.get(item.challenge)?.name)}</small></span>
      <span>${item.phase === 'lobby' ? 'Lobby' : item.phase === 'won' ? 'Sieg' : item.phase === 'lost' ? 'Abgeschlossen' : `Welle ${item.wave}`} ›</span></button>`).join('');
  } catch (error) { if (error.status !== 401) toast(error.message, true); }
}

function auth(next = 'login') {
  authMode = next;
  const register = next === 'register';
  $('name-label').hidden = !register;
  const form = $('account-form');
  form.elements.name.required = register;
  form.elements.password.autocomplete = register ? 'new-password' : 'current-password';
  $('account-error').textContent = '';
  $('account-title').textContent = register ? 'Konto erstellen' : 'Anmelden';
  $('account-submit').textContent = register ? 'Konto erstellen' : 'Anmelden';
  $('account-switch').textContent = register ? 'Ich habe ein Konto' : 'Neues Konto erstellen';
  if (!$('account-dialog').open) $('account-dialog').showModal();
}

function showInvite() {
  if (!invitation || $('account-dialog').open) return;
  $('invite-description').textContent = user
    ? `Du trittst mit dem Konto @${user.handle} bei.`
    : 'Melde dich mit dem eingeladenen Konto an, um dem Spielraum beizutreten.';
  $('invite-error').textContent = '';
  $('accept-invite').textContent = user ? 'Einladung annehmen' : 'Zum Login';
  if (!$('invite-dialog').open) $('invite-dialog').showModal();
}

function inviteUrl(token) {
  return `${location.origin}/#einladung=${encodeURIComponent(token)}`;
}

function connection(text, type) {
  $('connection').className = `connection ${type}`;
  $('connection').querySelector('span').textContent = text;
}

function stopNetwork() {
  clearInterval(polling);
  clearTimeout(restore);
  const old = socket;
  socket = null;
  if (old) old.close();
}

function connectRoom(id) {
  stopNetwork();
  failures = 0;
  connection('Verbindet', 'pending');
  function start() {
    if (room?.id !== id) return;
    const endpoint = new URL('/api/live', location.href);
    endpoint.protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
    endpoint.searchParams.set('id', id);
    const opened = new WebSocket(endpoint);
    socket = opened;
    opened.onopen = () => {
      if (socket !== opened) return;
      failures = 0;
      connection('Live', 'live');
    };
    opened.onmessage = event => {
      if (socket === opened) {
        clearInterval(polling);
        polling = null;
        receive(JSON.parse(event.data));
      }
    };
    opened.onclose = () => {
      if (socket !== opened || room?.id !== id) return;
      socket = null;
      connection('Verbindung wird erneuert', 'pending');
      async function fallback() {
        if (talking || room?.id !== id) return;
        talking = true;
        try { receive(await request('board', undefined, {id})); connection('Synchronisiert', 'live'); }
        catch (error) { if (error.status === 401 || error.status === 403) stopNetwork(); }
        finally { talking = false; }
      }
      if (!polling) polling = setInterval(fallback, 850);
      void fallback();
      restore = setTimeout(start, Math.min(14_000, 1400 * 2 ** failures++));
    };
    opened.onerror = () => {
      if (socket === opened) connection('Verbindung wird erneuert', 'pending');
    };
  }
  start();
}

async function startArena() {
  if (arena) { supplyArena(); return; }
  if (arenaInit) return arenaInit;
  $('render-notice').hidden = false;
  arenaInit = (async () => {
    const wasmPath = '/wasm/arena.js';
    const renderer = await import(/* @vite-ignore */ wasmPath);
    await renderer.default();
    arena = renderer;
    supplyArena();
    try { renderer.play_arena(); }
    catch (error) {
      if (!String(error).includes('control flow') && !String(error).includes('This isn\'t actually an error')) throw error;
    }
  })().catch(error => {
    $('render-notice').textContent = '3D-Ansicht konnte nicht geladen werden. Prüfe, ob WebGL2 im Browser aktiv ist.';
    console.error(error);
  });
  return arenaInit;
}

function supplyArena() {
  if (!arena || !room) return;
  arena.set_room_state(room.id, JSON.stringify(room.game));
  const piece = room.game.pieces.find(item => item.id === selected);
  const definition = piece && actors.get(piece.actor);
  arena.set_board_focus(piece?.slot ?? -1, definition ? definition.range + (piece.rank - 1) * 0.23 + (piece.tier - 1) * 0.45 : 0);
}

function openMatch(packet) {
  stopNetwork();
  room = null;
  selected = null;
  pending = null;
  menuPane = 'building';
  lastPhase = '';
  recentEvents = new Set();
  orderSignature = '';
  $('hub').hidden = true;
  $('match').hidden = false;
  $('footer').hidden = true;
  document.body.classList.add('in-match');
  window.scrollTo({top:0,behavior:'instant'});
  receive(packet, true);
  score(packet.game.theme);
  void startArena();
  connectRoom(packet.id);
}

function leaveView() {
  stopNetwork();
  room = null;
  score('');
  $('match').hidden = true;
  $('hub').hidden = false;
  $('footer').hidden = false;
  document.body.classList.remove('in-match');
  void refreshAccount().then(recentRooms);
}

function receive(packet, force = false) {
  if (!packet?.game) return;
  if (room && (packet.id !== room.id || packet.version < room.version
    || (packet.version === room.version && packet.game.tick < room.game.tick))) return;
  if (!force && room && room.version === packet.version && room.game.tick === packet.game.tick &&
      room.joined === packet.joined && !packet.invite) return;
  room = {...packet, invite:packet.invite ?? room?.invite};
  const game = room.game;
  if (selected && !game.pieces.some(piece => piece.id === selected)) {
    selected = null;
    if (pending?.type === 'move' || pending?.type === 'cast') pending = null;
  }
  if (lastPhase !== game.phase && ['won','lost'].includes(game.phase)) {
    pending = null;
    void refreshAccount();
    score('');
  }
  if (game.phase === 'combat' && lastPhase === 'lobby') score(game.theme);
  lastPhase = game.phase;
  for (const event of game.events) {
    if (recentEvents.has(event.id) || event.tick + 24 < game.tick) continue;
    recentEvents.add(event.id);
    if (!force) battleSound(event);
    if (event.kind === 'boss') sceneNotice(`${enemies.get(event.actor)?.name ?? 'Boss'} rückt an`, 2800);
  }
  if (recentEvents.size > 3000) recentEvents = new Set(game.events.map(event => event.id));
  supplyArena();
  paintMatch();
}

function sceneNotice(text, duration = 0) {
  const element = $('scene-note');
  element.textContent = text;
  element.hidden = !text;
  if (duration) setTimeout(() => {
    if (element.textContent === text) element.hidden = true;
  }, duration);
}

function stageCaption() {
  if (!pending) {
    if ($('scene-note').dataset.selection === 'true') sceneNotice('');
    $('scene-note').dataset.selection = 'false';
    return;
  }
  const hint = pending.type === 'move' ? 'Zielplatz für die Truppe wählen'
    : pending.type === 'cast' ? 'Zielfeld wählen oder Fähigkeit auf den vordersten Gegner wirken'
    : `${actors.get(pending.actor)?.name} · freien Bauplatz wählen`;
  $('scene-note').dataset.selection = 'true';
  sceneNotice(hint);
}

function displayCountdown(game) {
  if (game.phase === 'prep') {
    if (!game.phase_until) return 'Verteidigung aufstellen';
    return `Start in ${Math.max(0, Math.ceil((game.phase_until - game.tick) / 20))} s`;
  }
  if (game.phase === 'combat') return 'Angriff läuft';
  if (game.phase === 'lobby') return 'Bereit zum Start';
  return game.phase === 'won' ? 'Tor gehalten' : 'Partie beendet';
}

function paintMatch() {
  if (!room) return;
  const {game, viewer, host, guest} = room;
  const character = themes.get(game.theme);
  const player = game.players[viewer];
  $('match-map').textContent = character.map;
  $('match-type').textContent = `${guest ? 'Koop' : 'Solo'} · ${challenges.get(game.challenge)?.name}`;
  $('life').textContent = `${game.life} / ${game.max_life}`;
  $('life-meter').max = game.max_life;
  $('life-meter').value = game.life;
  $('wave').textContent = `${game.wave} / ${game.wave_limit}`;
  $('wave-phase').textContent = displayCountdown(game);
  $('gold').textContent = number(player.gold);
  $('kills').textContent = `${game.kills} besiegt`;
  $('stage').style.setProperty('--theme-accent', colorThemes[game.theme]);
  $('stage-legend').innerHTML = `<span><i></i>${esc(host.name)}${viewer === 0 ? ' · Du' : ''}</span>
    ${guest ? `<span><i></i>${esc(guest.name)}${viewer === 1 ? ' · Du' : ''}</span>` : ''}`;
  const boss = game.enemies.find(enemy => enemy.kind === 'titan' || enemy.kind === 'golem');
  $('boss-health').hidden = !boss;
  if (boss) $('boss-health').innerHTML = `<strong>${esc(enemies.get(boss.kind)?.name)}</strong>
    <meter min="0" max="${Math.ceil(boss.max_hp)}" value="${Math.max(0,boss.hp)}" aria-label="Boss-Lebenspunkte"></meter>`;
  paintSlots();
  stageCaption();
  paintOrders();
}

function paintSlots() {
  if (!room) return;
  const bySlot = new Map(room.game.pieces.map(piece => [piece.slot,piece]));
  const inactive = ['lobby','won','lost'].includes(room.game.phase);
  for (const [index, button] of grid.entries()) {
    const piece = bySlot.get(index);
    const own = !room.guest || Math.floor(index / 12) === room.viewer;
    const active = piece?.id === selected;
    button.classList.toggle('marked', active);
    button.classList.toggle('own', own);
    button.classList.toggle('filled', Boolean(piece));
    const moving = pending?.type === 'move' && (!piece || (piece.owner === room.viewer && actors.get(piece.actor)?.kind !== 'building'));
    button.classList.toggle('target', !inactive && (
      (pending?.type === 'cast') || (own && ((pending?.type === 'place' && !piece) || moving))
    ));
    button.disabled = inactive || (!own && pending?.type !== 'cast');
    button.tabIndex = button.disabled ? -1 : 0;
    button.setAttribute('aria-label', piece ? pieceLabel(actors.get(piece.actor),piece) : `Bauplatz ${index+1}`);
    button.setAttribute('aria-pressed', String(active));
    const pips = piece && piece.tier > 1 ? numeral(piece.tier) : '';
    if (button.dataset.pips !== pips) { button.dataset.pips = pips; button.textContent = pips; }
  }
}

function piecePanel(piece, game) {
  const actor = actors.get(piece.actor);
  const gold = game.players[room.viewer].gold;
  const matches = game.pieces.filter(other => other.owner === room.viewer && other.actor === piece.actor && other.tier === piece.tier).length;
  const cooldown = Math.max(0,Math.ceil((piece.cast_ready - game.tick)/20));
  return `<section class="selected-piece" style="--actor-color:${actor.color}">
    <div class="piece-heading">${portrait(actor.id)}<div><small>${esc(actor.role)} · ${actor.kind === 'troop' ? `Rang ${numeral(piece.tier)}` : actor.kind === 'hero' ? 'Held' : 'Gebäude'}</small>
    <h3>${esc(actor.name)}</h3><p>Stufe ${piece.rank} / 4</p></div></div>
    <p class="piece-note">${esc(actor.note)}</p>
    <p class="piece-numbers">${Math.round(actor.damage * [1,2.65,6.95][piece.tier-1] * (1+0.42*(piece.rank-1)))} Grundschaden · ${(actor.range+0.23*(piece.rank-1)+0.45*(piece.tier-1)).toFixed(1).replace('.',',')} Reichweite</p>
    <div class="piece-actions">
      ${actor.kind === 'building' ? '' : '<button class="minibutton" data-order="move">Umstellen</button>'}
      <button class="minibutton" data-order="upgrade" ${piece.rank >= 4 || gold < price(piece.rank,piece.tier) ? 'disabled' : ''}>${piece.rank >= 4 ? 'Voll ausgebaut' : `Ausbauen · ${price(piece.rank,piece.tier)}`}</button>
      ${actor.kind === 'troop' && piece.tier < 3 ? `<button class="minibutton merge" data-order="merge" ${matches < 3 ? 'disabled' : ''}>Verschmelzen · ${Math.min(matches,3)}/3</button>` : ''}
      ${actor.kind === 'hero' ? `<button class="minibutton cast" data-order="cast" ${cooldown || game.phase !== 'combat' ? 'disabled' : ''}>${esc(actor.role)}${cooldown ? ` · ${cooldown} s` : ''}</button>` : ''}
      <button class="minibutton sell" data-order="sell">Verkaufen</button>
    </div></section>`;
}

function rosterPanel(game) {
  const player = game.players[room.viewer];
  const availableLevel = Math.max(player.level, themes.get(game.theme).unlock);
  const canPlaceHero = !game.pieces.some(piece => piece.owner === room.viewer && actors.get(piece.actor)?.kind === 'hero');
  const filtered = catalog.actors.filter(actor => actor.theme === game.theme && actor.kind === menuPane);
  return `<div class="order-tabs segment" aria-label="Bauaufträge">
    <button aria-pressed="${menuPane === 'building'}" data-pane="building">Gebäude</button>
    <button aria-pressed="${menuPane === 'hero'}" data-pane="hero">Helden</button>
  </div>
  <div class="roster">${filtered.map(actor => {
    const lock = availableLevel < actor.unlock;
    const off = lock || player.gold < actor.cost || (actor.kind === 'hero' && !canPlaceHero);
    const marked = pending?.type === 'place' && pending.actor === actor.id;
    return `<button class="roster-card ${marked ? 'active' : ''}" data-place="${actor.id}" title="${esc(actor.note)}" ${off ? 'disabled' : ''}
      aria-pressed="${marked}"><span class="roster-image">${portrait(actor.id)}</span>
      <span class="roster-copy"><strong>${esc(actor.name)}</strong><small>${esc(actor.role)}</small></span>
      <span class="roster-cost">${lock ? `Lv. ${actor.unlock}` : actor.cost}</span></button>`;
  }).join('')}</div>`;
}

function paintOrders() {
  if (!room) return;
  const {game, viewer, guest, host, joined} = room;
  const player = game.players[viewer];
  const signature = JSON.stringify([game.phase, game.wave, player.gold, game.prepared, joined, selected, pending, menuPane,
    room.invite, game.pieces.map(p=>[p.id,p.slot,p.rank,p.tier, Math.max(0,Math.ceil((p.cast_ready-game.tick)/20))]), locked]);
  if (signature === orderSignature) return;
  orderSignature = signature;
  const orders = $('orders');
  const focused = orders.contains(document.activeElement) ? document.activeElement.dataset : null;
  if (game.phase === 'lobby') {
    orders.innerHTML = `<div class="orders-heading"><p class="kicker">${guest ? 'Koop-Raum' : 'Solo-Partie'}</p><h2>Aufstellung</h2></div>
      <div class="lobby-members"><div><i></i><span>${esc(host.name)}</span><small>Gastgeber</small></div>
      ${guest ? `<div><i></i><span>${esc(guest.name)}</span><small>${joined ? 'Bereit' : 'Eingeladen'}</small></div>` : ''}</div>
      ${guest && viewer === 0 && !joined ? `<p class="hint">Teile den Link mit @${esc(guest.handle)}. Nur dieses Konto kann beitreten.</p>
        ${room.invite ? `<div class="invite-copy"><input id="room-invite" aria-label="Kontogebundener Einladungslink" value="${esc(inviteUrl(room.invite))}" readonly>
          <button class="minibutton" data-order="copy">Kopieren</button></div>` :
        '<button class="minibutton" data-order="renew">Neuen Einladungslink erzeugen</button>'}` : ''}
      ${viewer === 0 ? `<button class="primary" data-order="start" ${!joined || locked ? 'disabled' : ''}>Partie starten ▸</button>` :
        '<p class="hint">Der Gastgeber startet eure Partie.</p>'}
      <p class="hint guide-note">Ziehen kostet 65 Gold. Auf dem Feld kannst du drei gleiche Truppen verschmelzen. Gebäude bleiben an ihrem Bauplatz.</p>`;
  } else if (['won','lost'].includes(game.phase)) {
    orders.innerHTML = `<div class="orders-heading"><p class="kicker">Schlachtbericht</p><h2>${game.phase === 'won' ? 'Das Tor hält' : 'Das Tor ist gefallen'}</h2></div>
      <dl class="end-stats"><div><dt>Wellen</dt><dd>${game.wave} / ${game.wave_limit}</dd></div><div><dt>Besiegte Gegner</dt><dd>${game.kills}</dd></div>
      <div><dt>Verschmolzen</dt><dd>${player.merges}</dd></div><div><dt>Fähigkeiten</dt><dd>${player.casts}</dd></div></dl>
      <button class="primary" data-order="home">Zur Bastion ›</button><button class="quiet" data-order="history">Chronik öffnen</button>`;
  } else {
    const piece = game.pieces.find(item => item.id === selected);
    orders.innerHTML = `<div class="orders-heading"><p class="kicker">Deine Verteidigung</p><h2>Befehle</h2></div>
      <button class="primary recruit" data-order="recruit" ${player.gold < 65 || locked ? 'disabled' : ''}>
        <span aria-hidden="true">✦</span> Truppe ziehen <small>65 Gold</small></button>
      ${pending ? '<div class="pending-controls"><button class="quiet" data-order="cancel">Auswahl abbrechen</button>'
        + (pending.type === 'cast' ? '<button class="minibutton" data-order="cast-auto">Auto-Ziel</button>' : '') + '</div>' : ''}
      ${piece ? piecePanel(piece,game) : game.wave === 0
        ? '<p class="hint order-hint">Decke einen Weg mit einer Balliste ab oder ziehe deine ersten Truppen. Starte die erste Welle, sobald du bereit bist.</p>'
        : '<p class="hint order-hint">Wähle ein Feld, um seine Truppe auszubauen, zu verschmelzen oder umzustellen.</p>'}
      ${rosterPanel(game)}
      <div class="orders-footer">
        ${game.phase === 'prep' ? `<button class="secondary" data-order="ready" ${game.prepared[viewer] || locked ? 'disabled' : ''}>
          ${game.prepared[viewer] ? 'Wartet auf Mitspieler' : 'Bereit für die Welle'}</button>` : ''}
        <button class="quiet surrender" data-order="forfeit">Partie aufgeben</button></div>`;
  }
  if (focused) {
    const type = Object.keys(focused).find(key => ['order','place','pane'].includes(key));
    if (type) [...orders.querySelectorAll('button')].find(button => button.dataset[type] === focused[type] && !button.disabled)?.focus({preventScroll:true});
  }
}

async function command(command, hint) {
  if (locked || !room) return;
  locked = true;
  paintOrders();
  try {
    const id = room.id;
    const result = await request('action', {id, nonce: crypto.randomUUID(), command});
    if (room?.id !== id) return;
    receive(result);
    if (typeof hint === 'function') hint(result);
  } catch (error) { toast(error.message,true); }
  finally { locked = false; paintOrders(); }
}

async function tapSlot(slot) {
  if (!room || locked || ['lobby','won','lost'].includes(room.game.phase)) return;
  if (pending) {
    const chosen = pending;
    pending = null;
    const action = {...chosen,slot};
    await command(action, result => {
      const piece = result.game.pieces.find(item => item.slot === slot && item.owner === result.viewer);
      if (piece && action.type !== 'cast') selected = piece.id;
      paintMatch();
      supplyArena();
    });
    paintMatch();
    return;
  }
  const piece = room.game.pieces.find(item => item.slot === slot && item.owner === room.viewer);
  selected = piece?.id ?? null;
  paintMatch();
  supplyArena();
}

for (let i=0;i<24;i++) {
  const button = document.createElement('button');
  button.type = 'button';
  button.className = 'build-slot';
  button.hidden = true;
  button.dataset.slot = String(i);
  button.addEventListener('click', () => { void tapSlot(i); });
  $('slot-overlay').append(button);
  grid.push(button);
}
window.addEventListener('pantheon-slots', event => {
  const data = JSON.parse(event.detail);
  for (const [index, button] of grid.entries()) {
    const [x,y] = data.slots[index];
    button.style.left = `${x/data.width*100}%`;
    button.style.top = `${y/data.height*100}%`;
    button.style.setProperty('--tile-size', `${Math.min(52,Math.max(17,data.width/30))}px`);
    button.hidden = false;
  }
});
window.addEventListener('pantheon-board-models', () => { $('stage').dataset.models = 'ready'; });
window.addEventListener('pantheon-ready', () => {
  $('stage').dataset.rendered = 'true';
  $('render-notice').hidden = true;
});

$('orders').addEventListener('click', async event => {
  const button = event.target.closest('button');
  if (!button || !room || button.disabled) return;
  if (button.dataset.pane) { menuPane = button.dataset.pane; paintOrders(); return; }
  if (button.dataset.place) {
    pending = pending?.actor === button.dataset.place ? null : {type:'place',actor:button.dataset.place};
    selected = null;
    paintMatch();
    supplyArena();
    return;
  }
  const kind = button.dataset.order;
  if (kind === 'copy') {
    try { await navigator.clipboard.writeText(inviteUrl(room.invite)); toast('Einladungslink kopiert.'); }
    catch { $('room-invite')?.select(); toast('Der Link ist markiert und kann kopiert werden.'); }
  } else if (kind === 'renew') {
    try { const data = await request('invite',{id:room.id}); room.invite = data.invite; paintOrders(); }
    catch (error) { toast(error.message,true); }
  } else if (kind === 'home' || kind === 'history') {
    chooseTab(kind === 'history' ? 'chronicle' : 'bastion');
  } else if (kind === 'cancel') {
    pending = null; paintMatch();
  } else if (kind === 'move' || kind === 'cast') {
    if (!selected) return;
    pending = {type:kind,id:selected}; paintMatch();
  } else if (kind === 'cast-auto') {
    const choice = pending;
    pending = null;
    if (choice?.type === 'cast') await command({...choice, slot:null});
  } else if (kind === 'forfeit') {
    $('leave-note').textContent = room.guest ? 'Die gemeinsame Partie endet für euch beide. Der erreichte Wellenstand fließt in eure Chronik ein.'
      : 'Der aktuelle Wellenstand fließt in die Chronik ein.';
    $('leave-dialog').showModal();
  } else if (kind === 'merge') {
    const before = room.game.pieces.find(p => p.id === selected);
    if (before) await command({type:kind,id:before.id}, result => {
      selected = result.game.pieces.find(p => p.slot === before.slot)?.id ?? null;
      supplyArena();
      paintMatch();
    });
  } else if (['start','ready','recruit','upgrade','sell'].includes(kind)) {
    await command({type:kind, ...(selected && {id:selected})});
  }
});

$('leave-dialog').addEventListener('close', () => {
  if ($('leave-dialog').returnValue === 'confirm') void command({type:'forfeit'});
});
$('account-button').addEventListener('click', () => { if (user) chooseTab('chronicle'); else auth(); });
$('home-button').addEventListener('click', () => chooseTab('bastion'));
$('back-to-hub').addEventListener('click', () => chooseTab('bastion'));
$('sound-button').addEventListener('click', () => { toggleSound(); soundLabel(); });

$('hero-play').addEventListener('click', () => $('preparation').scrollIntoView({behavior:'smooth',block:'start'}));
$('friend').addEventListener('input', event => { friendDraft = event.target.value; });
$('challenge').addEventListener('change', event => {
  challenge = event.target.value;
  $('challenge-detail').textContent = challenges.get(challenge).detail;
});
$('create-match').addEventListener('click', async () => {
  if (!user) { auth('register'); return; }
  const button = $('create-match');
  if (button.disabled) return;
  button.disabled = true;
  try { openMatch(await request('new',{mode,theme,challenge,friend:friendDraft})); }
  catch (error) { toast(error.message,true); }
  finally { button.disabled = false; }
});

document.addEventListener('click', async event => {
  const button = event.target.closest('button');
  if (!button) return;
  const target = button.dataset;
  if (target.tab) chooseTab(target.tab);
  if (target.mode) { mode = target.mode; paintPreparation(); }
  if (target.theme) {
    if (button.getAttribute('aria-disabled') === 'true') {
      toast(`Dieser Schauplatz öffnet sich auf Profilstufe ${themes.get(target.theme).unlock}.`);
    } else { theme = target.theme; paintPreparation(); }
  }
  if (target.faction) { factionFilter = target.faction; paintCollection(); }
  if (target.auth) auth(target.auth);
  if (target.close) $(target.close).close();
  if (target.resume) {
    try { openMatch(await request('board',undefined,{id:target.resume})); }
    catch(error) { toast(error.message,true); }
  }
  if (button.id === 'sign-out') {
    try { await request('logout',{}); changeAccount(null); chooseTab('bastion'); await recentRooms(); }
    catch(error) { toast(error.message,true); }
  }
});

$('account-switch').addEventListener('click', () => auth(authMode === 'login' ? 'register' : 'login'));
$('account-form').addEventListener('submit', async event => {
  event.preventDefault();
  const submit = $('account-submit');
  submit.disabled = true;
  $('account-error').textContent = '';
  try {
    const result = await request(authMode,Object.fromEntries(new FormData(event.target)));
    changeAccount(result.user);
    $('account-dialog').close();
    event.target.reset();
    void recentRooms();
    if (invitation) showInvite();
    else toast(`Willkommen, ${result.user.name}.`);
  } catch(error) { $('account-error').textContent = error.message; }
  finally { submit.disabled = false; }
});
$('dismiss-invite').addEventListener('click', () => $('invite-dialog').close());
$('accept-invite').addEventListener('click', async () => {
  if (!user) { $('invite-dialog').close(); auth(); return; }
  const button = $('accept-invite');
  button.disabled = true;
  try {
    const result = await request('accept',{invite:invitation});
    invitation = null;
    history.replaceState(null,'',location.pathname);
    $('invite-dialog').close();
    openMatch(result);
  } catch(error) { $('invite-error').textContent = error.message; }
  finally { button.disabled = false; }
});
window.addEventListener('hashchange', () => {
  invitation = new URLSearchParams(location.hash.slice(1)).get('einladung');
  showInvite();
});
window.addEventListener('keydown', event => {
  if (!room || event.repeat || event.ctrlKey || event.metaKey || event.altKey || event.target.matches('input,select,textarea')) return;
  if (event.key === 'Escape' && pending) { pending = null; paintMatch(); return; }
  const hotkeys = {r:'recruit', m:'move', u:'upgrade', f:'cast', ' ':'ready'};
  const kind = hotkeys[event.key.toLowerCase()];
  if (kind && event.target.tagName !== 'BUTTON') {
    const button = $('orders').querySelector(`[data-order="${kind}"]:not(:disabled)`);
    if (button) { event.preventDefault(); button.click(); }
  }
});

paintPreparation();
soundLabel();
versionLabel();
void request('health').then(data => { currentVersion = data.version; versionLabel(); }).catch(() => {});
void refreshAccount().then(() => { void recentRooms(); showInvite(); });
