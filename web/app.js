import '@fontsource-variable/cormorant-garamond';
import '@fontsource-variable/dm-sans';
import './style.css';
import './circuit.css';
import './commands.css';
import { $, esc, portrait, numeral, number, price, pieceLabel, groupNames, themeHeroes, colorThemes, actorCard, historyRow, signCard, spoilsText, rarities } from './presentation.js';
import { battleSound, score, soundState, toggleSound, unlockSound } from './audio.js';
import { updateCircuitOrders, isCircuit, ownerOf, preferredHero, pressureLimit } from './circuit-ui.js';
import { bindScreen, enterFullscreen, handheld, leaveFullscreen } from './screen.js';
import { difficultyProgress, materials } from '../shared/progression.js';

const catalog = await fetch('/assets/catalog.json').then(answer => answer.json());
const actors = new Map(catalog.actors.map(actor => [actor.id, actor]));
const themes = new Map(catalog.themes.map(theme => [theme.id, theme]));
const challenges = new Map(catalog.challenges.map(challenge => [challenge.id, challenge]));
const difficulties = new Map(catalog.difficulties.map(stage => [stage.id, stage]));
const enemies = new Map(catalog.enemies.map(enemy => [enemy.id, enemy]));
let user = null;
let currentVersion = '1.0.0';
let theme = 'aegean';
let factionFilter = 'aegean';
let challenge = 'campaign';
let difficulty = 'normal';
let mode = 'solo';
let tab = 'bastion';
let authMode = 'login';
let friendDraft = '';
let room = null;
let selected = null;
let pending = null;
let arena = null;
let arenaInit = null;
let renderedGame = null;
let renderedMove = null;
let movePreview = null;
let loadedBoard = '';
let socket = null;
let polling = null;
let restore = null;
let failures = 0;
let recentEvents = new Set();
let locked = false;
let toastTimer;
let invitation = new URLSearchParams(location.hash.slice(1)).get('einladung');
let talking = false;
let menuPane = null;
let focusHero = null;
let orderSignature = '';
let slotSignature = '';
let legendSignature = '';
let lastPhase = '';
let drawNoticeTimer;
let waveRewardTimer;
let dragStart = null;
let suppressedClick=null;
let slowSamples=0;
let severeSamples=0;
let fastSamples=0;
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
  const state = soundState();
  const label = state === 'off' ? 'Ton einschalten' : ['tap','retry'].includes(state) ? 'Ton starten' : 'Ton ausschalten';
  for (const button of [$('sound-button'), $('match-sound')]) {
    button.dataset.sound = state;
    button.setAttribute('aria-pressed', String(['on','loading','playing'].includes(state)));
    button.setAttribute('aria-label', label);
    button.title = label;
    button.classList.toggle('muted', state === 'off');
  }
}

function changeAccount(next) {
  user = next;
  const button = $('account-button');
  button.textContent = user ? `${user.name} · Stufe ${user.level}` : 'Anmelden';
  button.setAttribute('aria-label', user ? `Profil von ${user.name}, Stufe ${user.level}` : 'Anmelden');
  paintLobby();
  if (room) paintMatch();
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
    ? 'Rekrutiere Einheiten, stelle Trupps zusammen und verteidige den Rundkurs. Spiele allein oder zu zweit.'
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
  if (!difficultyProgress(difficulties.get(difficulty), catalog.difficulties, user).unlocked) difficulty = 'normal';
  paintDifficulties();
  $('friend-row').hidden = mode !== 'duo';
  if (document.activeElement !== $('friend')) $('friend').value = friendDraft;
  $('create-match').textContent = mode === 'duo' ? 'Koop-Partie erstellen ›' : 'Solo-Partie erstellen ›';
}

function paintDifficulties(preview = difficulty) {
  const list = $('difficulty-list');
  if (!list.childElementCount) {
    list.innerHTML = catalog.difficulties.map(stage => `<button type="button" data-difficulty="${stage.id}"
      aria-describedby="difficulty-detail">${esc(stage.name)}</button>`).join('');
  }
  for (const button of list.children) {
    const stage = difficulties.get(button.dataset.difficulty);
    button.setAttribute('aria-disabled', String(!difficultyProgress(stage, catalog.difficulties, user).unlocked));
    button.setAttribute('aria-pressed', String(stage.id === difficulty));
  }
  const stage = difficulties.get(preview);
  const { unlocked, prior, wins, ranks } = difficultyProgress(stage, catalog.difficulties, user);
  $('difficulty-detail').textContent = unlocked
    ? `${stage.detail}${stage.rank ? ' Zusätzliche Beute in Meilensteinwellen.' : ''}`
    : `${Math.min(wins, stage.clears)}/${stage.clears} Feldzugssiege auf ${prior.name} · ${Math.min(ranks, stage.mastery)}/${stage.mastery} Meisterschaftsstufen`;
}

function paintCollection() {
  const level = user?.level ?? 1;
  $('collection-level').textContent = user
    ? `Profilstufe ${level} · ${number(user.xp)} EP`
    : 'Spiele Partien, um Einheiten, Gebäude und Helden freizuschalten.';
  const balances = $('material-balances');
  balances.hidden = !user;
  if (user) balances.innerHTML = Object.entries(materials).map(([key, label]) =>
    `<div><dt>${label}</dt><dd>${number(key === 'seals' ? user.seals : user.materials?.[key] ?? 0)}</dd></div>`).join('');
  $('field-signs').hidden = !user;
  if (user) $('field-sign-list').innerHTML = catalog.fieldSigns.map(sign => signCard(sign, user)).join('');
  $('collection-filters').innerHTML = catalog.themes.map(item => `<button data-faction="${item.id}"
    aria-pressed="${item.id === factionFilter}">${esc(item.name)}</button>`).join('');
  const items = catalog.actors.filter(actor => actor.theme === factionFilter);
  $('actor-cards').innerHTML = Object.entries(groupNames).map(([kind,label]) => `<section>
    <h2>${label}</h2><div class="card-grid">${items.filter(a => a.kind === kind).map(a => actorCard(a,level,user?.masteries?.[a.id]??0,user)).join('')}</div>
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
    <div><h2>${esc(user.name)}</h2><p>@${esc(user.handle)} · ${number(user.xp)} EP · ${number(user.seals??0)} Siegel</p>
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
      <span><strong>${esc(themes.get(item.theme)?.map)}</strong><small>${item.mode === 'duo' ? 'Koop' : 'Solo'} · ${esc(difficulties.get(item.difficulty)?.name)} · ${esc(challenges.get(item.challenge)?.name)}</small></span>
      <span>${item.phase === 'lobby' ? 'Lobby' : item.phase === 'won' ? 'Sieg' : item.phase === 'lost' ? 'Niederlage' : `Welle ${item.wave}`} ›</span></button>`).join('');
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
    : 'Melde dich mit dem eingeladenen Konto an.';
  $('invite-error').textContent = '';
  $('accept-invite').textContent = user ? 'Einladung annehmen' : 'Anmelden';
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
  connection('Verbindet …', 'pending');
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
      connection('Verbindet erneut …', 'pending');
      async function fallback() {
        if (talking || room?.id !== id) return;
        talking = true;
        try { receive(await request('board', undefined, {id})); connection('Verbunden', 'live'); }
        catch (error) { if (error.status === 401 || error.status === 403) stopNetwork(); }
        finally { talking = false; }
      }
      if (!polling) polling = setInterval(fallback, 850);
      void fallback();
      restore = setTimeout(start, Math.min(14_000, 1400 * 2 ** failures++));
    };
    opened.onerror = () => {
      if (socket === opened) connection('Verbindet erneut …', 'pending');
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
    try { renderer.play_arena(handheld()); }
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
  if (renderedGame !== room.game || renderedMove !== movePreview) {
    let game = room.game;
    const preview = movePreview;
    if (preview?.room === room.id && game.pieces.some(piece => piece.id === preview.id && piece.slot === preview.from)
      && game.pieces.find(piece => piece.slot === preview.to)?.id === preview.other) {
      game = { ...game, pieces: game.pieces.map(piece => {
        if (piece.id === preview.id) return { ...piece, slot: preview.to };
        if (piece.id === preview.other) return { ...piece, slot: preview.from };
        return piece;
      }) };
    }
    arena.set_viewer(room.viewer);
    arena.set_room_state(room.id, JSON.stringify(game));
    renderedGame = room.game;
    renderedMove = movePreview;
  }
  const piece = room.game.pieces.find(item => item.id === selected);
  const definition = piece && actors.get(piece.actor);
  arena.set_board_focus(piece?.slot ?? -1, definition ? definition.range + (piece.rank - 1) * 0.23 + (piece.tier - 1) * 0.45 : 0);
}

function openMatch(packet) {
  stopNetwork();
  clearDrag();
  movePreview = null;
  room = null;
  selected = null;
  pending = null;
  menuPane = isCircuit(packet.game) ? null : 'building';
  focusHero = null;
  lastPhase = '';
  recentEvents = new Set();
  orderSignature = '';
  slotSignature = '';
  legendSignature = '';
  clearTimeout(waveRewardTimer);
  $('wave-reward').hidden = true;
  delete $('wave-reward').dataset.wave;
  delete $('stage').dataset.rendered;
  if (loadedBoard!==boardAsset(packet.game)) {
    delete $('stage').dataset.models;
    $('render-notice').hidden=false;
  }
  delete $('stage').dataset.resolution;
  slowSamples=0;
  severeSamples=0;
  fastSamples=0;
  $('hub').hidden = true;
  $('match').hidden = false;
  $('footer').hidden = true;
  document.body.classList.add('in-match');
  document.body.classList.toggle('circuit-game',isCircuit(packet.game));
  window.scrollTo({top:0,behavior:'instant'});
  receive(packet, true);
  score(['won','lost'].includes(packet.game.phase) ? '' : packet.game.theme);
  void startArena();
  connectRoom(packet.id);
}

function leaveView() {
  stopNetwork();
  clearDrag();
  movePreview = null;
  arena?.close_board();
  room = null;
  renderedGame = null;
  score('');
  $('match').hidden = true;
  $('hub').hidden = false;
  $('footer').hidden = false;
  document.body.classList.remove('in-match','circuit-game');
  leaveFullscreen();
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
  if (pending?.type==='deploy' && !game.players[room.viewer].reserve?.some(recruit=>recruit.id===pending.id)) pending=null;
  if (selected && !game.pieces.some(piece => piece.id === selected)) {
    selected = null;
    if (pending?.type === 'move' || pending?.type === 'cast') pending = null;
  }
  if (lastPhase !== game.phase && ['won','lost'].includes(game.phase)) {
    pending = null;
    menuPane = null;
    clearDrag();
    void refreshAccount();
    score('');
  }
  if (game.phase === 'combat' && lastPhase === 'lobby') score(game.theme);
  lastPhase = game.phase;
  for (const event of game.events) {
    if (recentEvents.has(event.id) || event.tick + 24 < game.tick) continue;
    recentEvents.add(event.id);
    if (!force) battleSound(event);
    if (event.kind==='oracle_miss') sceneNotice('Das Orakel hat keine Einheit beschworen.',1700);
    if (event.kind === 'boss_windup') sceneNotice('Schockwelle im markierten Bereich. Verschiebe deinen Trupp.', 1900);
    if (event.kind === 'boss') sceneNotice(`${enemies.get(event.actor)?.name ?? 'Boss'} nähert sich`, 2800);
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
  if (!pending || isCircuit(room?.game)) {
    if ($('scene-note').dataset.selection === 'true') sceneNotice('');
    $('scene-note').dataset.selection = 'false';
    return;
  }
  const hint = pending.type === 'move' ? 'Tippe auf ein Zielfeld'
    : pending.type === 'cast' ? 'Wähle ein Zielfeld oder lass den Helden automatisch zielen.'
    : `${actors.get(pending.actor)?.name} · freien Bauplatz wählen`;
  $('scene-note').dataset.selection = 'true';
  sceneNotice(hint);
}

function displayCountdown(game) {
  if (game.phase === 'prep') {
    if (!game.phase_until) return 'Verteidigung aufstellen';
    return `Start in ${Math.max(0, Math.ceil((game.phase_until - game.tick) / 20))} s`;
  }
  if (game.phase === 'combat') {
    if (!isCircuit(game)) return 'Angriff läuft';
    const timeLeft=Math.ceil((game.phase_until-game.tick)/20);
    return timeLeft>0 ? `${timeLeft} s` : 'Letzte Gegner';
  }
  if (game.phase === 'lobby') return 'Bereit zum Start';
  return game.phase === 'won' ? 'Tor gehalten' : 'Partie beendet';
}

function showWaveReward(reward) {
  if (!reward) return;
  const notice = $('wave-reward');
  if (Number(notice.dataset.wave) === reward.wave) return;
  notice.dataset.wave = reward.wave;
  const essence = reward.essence ? ` · +${reward.essence} Essenz` : '';
  const loot = spoilsText({ [reward.material]: reward.amount, runedust: reward.runedust, cores: reward.cores });
  notice.innerHTML = `<strong>Welle ${reward.wave}</strong><span>+${reward.gold} Gold${essence} · ${loot}</span>`;
  notice.hidden = false;
  clearTimeout(waveRewardTimer);
  waveRewardTimer = setTimeout(() => { notice.hidden = true; }, 6500);
}

function paintMatch() {
  if (!room) return;
  const {game, viewer, host, guest} = room;
  const character = themes.get(game.theme);
  const stage = difficulties.get(game.difficulty ?? 'normal');
  const player = game.players[viewer];
  $('match-map').textContent = character.map;
  $('match-type').textContent = `${guest ? 'Koop' : 'Solo'} · ${stage.name} · ${challenges.get(game.challenge)?.name}`;
  const circuit=isCircuit(game);
  const limit=circuit?pressureLimit(game,game.difficulty ? stage : null):game.max_life;
  const filled=circuit?game.enemies.length:game.life;
  $('life-label').textContent=circuit?'Gegner':'Torleben';
  $('life').textContent=`${filled} / ${limit}`;
  $('life-meter').max=limit;
  $('life-meter').value=filled;
  $('life-meter').classList.toggle('danger',circuit && filled>limit*0.68);
  $('essence-stat').hidden=!circuit;
  $('essence').textContent=number(player.essence??0);
  $('battle-meter').classList.toggle('four-stats',circuit);
  $('wave').textContent = `${game.wave} / ${game.wave_limit}`;
  $('wave-phase').textContent = displayCountdown(game);
  $('gold').textContent = number(player.gold);
  $('kills').textContent = `${game.kills} besiegt`;
  $('stage').style.setProperty('--theme-accent', colorThemes[game.theme]);
  $('stage').dataset.theme=game.theme;
  $('match').dataset.theme=game.theme;
  const membership=JSON.stringify([host.name,guest?.name,viewer]);
  if (legendSignature!==membership) {
    legendSignature=membership;
    $('stage-legend').innerHTML = `<span><i></i>${esc(host.name)}${viewer === 0 ? ' · Du' : ''}</span>
      ${guest ? `<span><i></i>${esc(guest.name)}${viewer === 1 ? ' · Du' : ''}</span>` : ''}`;
  }
  const boss = game.enemies.find(enemy => ['titan','golem'].includes(enemies.get(enemy.kind)?.archetype ?? enemy.kind));
  $('boss-health').hidden = !boss;
  if (boss) $('boss-health').innerHTML = `<strong>${esc(enemies.get(boss.kind)?.name)}${game.boss_cast ? ' · Schockwelle' : boss.deadline ? ` · ${Math.max(0,Math.ceil((boss.deadline-game.tick)/20))} s` : ''}</strong>
    <meter min="0" max="${Math.ceil(boss.max_hp)}" value="${Math.max(0,boss.hp)}" aria-label="Boss-Lebenspunkte"></meter>`;
  showWaveReward(game.treasury?.latest);
  paintSlots();
  stageCaption();
  paintOrders();
}

function paintSlots() {
  if (!room) return;
  const inactive = ['lobby','won','lost'].includes(room.game.phase);
  const game=room.game;
  const circuit=isCircuit(game);
  const reserve=pending?.type==='deploy' ? game.players[room.viewer].reserve.find(item=>item.id===pending.id) : null;
  const revision=JSON.stringify([inactive,selected,pending,room.viewer,reserve,
    game.pieces.map(piece=>[piece.id,piece.slot,piece.tier,piece.rank,piece.stack])]);
  if (revision===slotSignature) return;
  slotSignature=revision;
  const bySlot=new Map(game.pieces.map(piece=>[piece.slot,piece]));
  const movingPiece=pending?.type==='move' ? game.pieces.find(piece=>piece.id===pending.id) : null;
  const count=circuit?32:24;
  for (const [index, button] of grid.entries()) {
    if(index>=count){button.hidden=true; continue;}
    const piece=bySlot.get(index);
    const own=!room.guest || ownerOf(game,index)===room.viewer;
    const active=piece?.id===selected;
    const building=piece && actors.get(piece.actor)?.kind==='building';
    const validDeploy=reserve && (!piece || (piece.owner===room.viewer && matchesTroop(reserve,piece) && piece.stack<3));
    const moving=movingPiece && canMoveTo(movingPiece,index,piece);
    const target=!inactive && (pending?.type==='cast' || (own && (validDeploy || (pending?.type==='place'&&!piece) || moving)));
    button.classList.toggle('marked',active);
    button.classList.toggle('own',own);
    button.classList.toggle('filled',Boolean(piece));
    button.classList.toggle('movable',Boolean(piece && own && !building && circuit));
    button.classList.toggle('merge-ready',Boolean(circuit && piece?.stack===3 && piece.tier<5));
    button.classList.toggle('target',Boolean(target));
    button.classList.toggle('locked-tile',Boolean(reserve && !validDeploy));
    button.disabled=inactive || (!own && pending?.type!=='cast') || Boolean(reserve && !validDeploy)
      || (circuit && pending?.type==='place' && Boolean(piece))
      || (circuit && pending?.type==='move' && !moving);
    button.tabIndex=button.disabled?-1:0;
    button.setAttribute('aria-label',piece
      ? pieceLabel(actors.get(piece.actor),piece,circuit)
      : `Freies Feld ${index+1}`);
    button.setAttribute('aria-pressed',String(active));
    const pips=piece ? circuit && piece.stack>1 ? `×${piece.stack}` : piece.tier>1 ? numeral(piece.tier) : '' : '';
    if (button.dataset.pips!==pips || button.dataset.circuit!==String(circuit)) {
      button.dataset.pips=pips;
      button.dataset.circuit=String(circuit);
      button.innerHTML=circuit && pips ? `<span class="stack-badge">${pips}</span>` : pips;
    }
    button.dataset.rarity=piece?.tier??0;
  }
}

function piecePanel(piece, game) {
  const actor = actors.get(piece.actor);
  const gold = game.players[room.viewer].gold;
  const matches = game.pieces.filter(other => other.owner === room.viewer && other.actor === piece.actor && other.tier === piece.tier).length;
  const cooldown = Math.max(0,Math.ceil((piece.cast_ready - game.tick)/20));
  const mastery = piece.mastery ?? 0;
  return `<section class="selected-piece" style="--actor-color:${actor.color}">
    <div class="piece-heading">${portrait(actor.id)}<div><small>${esc(actor.role)} · ${actor.kind === 'troop' ? `Rang ${numeral(piece.tier)}` : actor.kind === 'hero' ? 'Held' : 'Gebäude'}</small>
    <h3>${esc(actor.name)}</h3><p>Stufe ${piece.rank} / 4</p></div></div>
    <p class="piece-note">${esc(actor.note)}</p>
    <p class="piece-numbers">${Math.round(actor.damage * [1,2.65,6.95][piece.tier-1] * (1+0.42*(piece.rank-1)) * (1+0.07*mastery))} Grundschaden · ${(actor.range+0.23*(piece.rank-1)+0.45*(piece.tier-1)).toFixed(1).replace('.',',')} Reichweite${mastery ? ` · Meisterschaft ${mastery}` : ''}</p>
    <div class="piece-actions">
      ${actor.kind === 'building' ? '' : '<button class="minibutton" data-order="move">Verschieben</button>'}
      <button class="minibutton" data-order="upgrade" ${piece.rank >= 4 || gold < price(piece.rank,piece.tier) ? 'disabled' : ''}>${piece.rank >= 4 ? 'Höchste Stufe' : `Aufwerten · ${price(piece.rank,piece.tier)} Gold`}</button>
      ${actor.kind === 'troop' && piece.tier < 3 ? `<button class="minibutton merge" data-order="merge" ${matches < 3 ? 'disabled' : ''}>Verschmelzen · ${Math.min(matches,3)}/3</button>` : ''}
      ${actor.kind === 'hero' ? `<button class="minibutton cast" data-order="cast" ${cooldown || game.phase !== 'combat' ? 'disabled' : ''}>${esc(actor.role)}${cooldown ? ` · ${cooldown} s` : ''}</button>` : ''}
      <button class="minibutton sell" data-order="sell">Verkaufen</button>
    </div></section>`;
}

function rosterPanel(game) {
  const player = game.players[room.viewer];
  const availableLevel = Math.max(player.level, themes.get(game.theme).unlock);
  const canPlaceHero = !game.pieces.some(piece => piece.owner === room.viewer && actors.get(piece.actor)?.kind === 'hero');
  const levy = game.challenge === 'levy';
  const pane = levy ? 'hero' : menuPane;
  const filtered = catalog.actors.filter(actor => actor.theme === game.theme && actor.kind === pane);
  return `<div class="order-tabs segment" aria-label="Bauaufträge">
    <button aria-pressed="${pane === 'building'}" data-pane="building" ${levy ? 'disabled' : ''}>Gebäude</button>
    <button aria-pressed="${pane === 'hero'}" data-pane="hero">Helden</button>
  </div>
  <div class="roster">${filtered.map(actor => {
    const lock = availableLevel < actor.unlock;
    const off = lock || player.gold < actor.cost || (actor.kind === 'hero' && !canPlaceHero);
    const marked = pending?.type === 'place' && pending.actor === actor.id;
    return `<button class="roster-card ${marked ? 'active' : ''}" data-place="${actor.id}" title="${esc(actor.note)}" ${off ? 'disabled' : ''}
      aria-pressed="${marked}"><span class="roster-image">${portrait(actor.id)}</span>
      <span class="roster-copy"><strong>${esc(actor.name)}</strong><small>${esc(actor.role)}</small></span>
      <span class="roster-cost">${lock ? `Stufe ${actor.unlock}` : `${actor.cost} Gold`}</span></button>`;
  }).join('')}</div>`;
}

function paintOrders() {
  if (!room) return;
  const {game, viewer, guest, host, joined} = room;
  const player = game.players[viewer];
  const result = user?.records?.find(record => record.id === room.id);
  const loot = spoilsText(game.treasury?.spoils);
  const drawCost = game.challenge === 'levy' ? 50 : 65;
  const circuit=isCircuit(game);
  const boardReady=$('stage').dataset.rendered==='true' && (!circuit || loadedBoard===boardAsset(game));
  const signature = JSON.stringify([boardReady,result?.xp,result?.seals,loot,game.phase,game.wave,player.gold,player.essence,
    player.temper,player.favor,player.recruits,player.reserve,game.prepared,joined,selected,pending,menuPane,focusHero,room.invite,game.rituals?.[viewer],
    game.pieces.map(p=>[p.id,p.slot,p.rank,p.tier,p.stack,Math.max(0,Math.ceil((p.cast_ready-game.tick)/20))]),locked]);
  if(signature===orderSignature)return;
  orderSignature=signature;
  const orders=$('orders');
  const focused=orders.contains(document.activeElement)?document.activeElement:null;
  $('match-options').hidden = !['prep','combat'].includes(game.phase);
  orders.classList.toggle('circuit-orders',circuit);
  orders.classList.toggle('live-deck',circuit && !['lobby','won','lost'].includes(game.phase));
  if (game.phase === 'lobby') {
    const sign = catalog.fieldSigns.find(sign => sign.id === player.field_sign?.id);
    orders.innerHTML = `<div class="orders-heading"><h2>${guest ? 'Koop-Lobby' : 'Solo-Partie'}</h2></div>
      <div class="lobby-members"><div><i></i><span>${esc(host.name)}</span><small>Gastgeber</small></div>
      ${guest ? `<div><i></i><span>${esc(guest.name)}</span><small>${joined ? 'Bereit' : 'Eingeladen'}</small></div>` : ''}</div>
      ${guest && viewer === 0 && !joined ? `<p class="hint">Teile den Link mit @${esc(guest.handle)}. Nur dieses Konto kann beitreten.</p>
        ${room.invite ? `<div class="invite-copy"><input id="room-invite" aria-label="Einladungslink" value="${esc(inviteUrl(room.invite))}" readonly>
          <button class="minibutton" data-order="copy">Kopieren</button></div>` :
        '<button class="minibutton" data-order="renew">Neuen Einladungslink erstellen</button>'}` : ''}
      ${viewer === 0 ? `<button class="primary" data-order="start" ${!joined || locked || !boardReady ? 'disabled' : ''}>Partie starten ▸</button>` :
        '<p class="hint">Der Gastgeber startet eure Partie.</p>'}
      ${sign ? `<p class="hint guide-note">${esc(sign.name)} · Stufe ${player.field_sign.rank}</p>` : ''}
      <p class="hint guide-note">${circuit ? 'Wähle für eine neue Einheitenart das erste Feld. Weitere Exemplare bilden automatisch einen Trupp aus bis zu drei Einheiten.' :
        `Rekrutiere für ${drawCost} Gold. Drei gleiche Einheiten kannst du verschmelzen.`}</p>`;
  } else if (['won','lost'].includes(game.phase)) {
    orders.innerHTML = `<div class="orders-heading"><p class="kicker">Schlachtbericht</p><h2>${game.phase === 'won' ? 'Die Bastion hält' : 'Die Bastion ist gefallen'}</h2></div>
      <dl class="end-stats"><div><dt>Erreichte Wellen</dt><dd>${game.wave} / ${game.wave_limit}</dd></div><div><dt>Besiegte Gegner</dt><dd>${game.kills}</dd></div>
      <div><dt>Verschmelzungen</dt><dd>${player.merges}</dd></div><div><dt>Eingesetzte Fähigkeiten</dt><dd>${player.casts}</dd></div>
      ${loot ? `<div><dt>Wellenbeute</dt><dd>${loot}</dd></div>` : ''}
      ${result ? `<div><dt>Belohnung für Welle ${result.wave}</dt><dd>+${result.xp} EP ${result.seals ? `· +${result.seals} Siegel` : ''}</dd></div>` : ''}</dl>
      <button class="primary" data-order="home">Zur Bastion ›</button><button class="quiet" data-order="history">Chronik öffnen</button>`;
  } else if(circuit) {
    updateCircuitOrders(orders,{room,selected,pending,menuPane,focusHero,actors,catalog,
      level:Math.max(player.level,themes.get(game.theme).unlock),locked});
  } else {
    const piece = game.pieces.find(item => item.id === selected);
    orders.innerHTML = `<div class="orders-heading"><p class="kicker">Deine Verteidigung</p><h2>Befehle</h2></div>
      <button class="primary recruit" data-order="recruit" ${player.gold < drawCost || locked ? 'disabled' : ''}>
        <span aria-hidden="true">✦</span> Rekrutieren <small>${drawCost} Gold</small></button>
      ${pending ? '<div class="pending-controls"><button class="quiet" data-order="cancel">Auswahl abbrechen</button>'
        + (pending.type === 'cast' ? '<button class="minibutton" data-order="cast-auto">Automatisch zielen</button>' : '') + '</div>' : ''}
      ${piece ? piecePanel(piece,game) : game.wave === 0
        ? `<p class="hint order-hint">${game.challenge==='levy' ? 'Rekrutiere Einheiten. Verschmelze drei gleiche für einen höheren Rang.'
          : 'Sichere den Weg mit Gebäuden und Einheiten.'} Starte dann die erste Welle.</p>`
        : '<p class="hint order-hint">Tippe auf ein Feld, um den Trupp auszuwählen.</p>'}
      ${rosterPanel(game)}
      <div class="orders-footer">
        ${game.phase === 'prep' ? `<button class="secondary" data-order="ready" ${game.prepared[viewer] || locked ? 'disabled' : ''}>
          ${game.prepared[viewer] ? 'Warten auf Mitspieler' : 'Bereit für die Welle'}</button>` : ''}
        <button class="quiet surrender" data-order="forfeit">Partie aufgeben</button></div>`;
  }
  const sheet = orders.querySelector('.command-sheet');
  $('slot-overlay').inert = Boolean(handheld() && sheet && !sheet.hidden);
  if (focused && !focused.isConnected) {
    const type = Object.keys(focused.dataset).find(key => ['order','place','pane','recruitId','releaseId','oracle','ritual','temper','heroSelect'].includes(key));
    if (type) [...orders.querySelectorAll('button')].find(button => button.dataset[type] === focused.dataset[type]
      && !button.disabled && !button.closest('[hidden]'))?.focus({preventScroll:true});
  }
}

function revealRecruit(unit, detail) {
  const definition=actors.get(unit.actor);
  const label=$('draw-reveal');
  label.className=`draw-reveal rarity-${unit.tier}`;
  label.innerHTML=`${portrait(definition.id)}<span><strong>${esc(definition.name)}</strong><small>${rarities[unit.tier]} · ${detail}</small></span>`;
  label.hidden=false;
  clearTimeout(drawNoticeTimer);
  drawNoticeTimer=setTimeout(()=>{label.hidden=true;},1600);
}

function chooseReserve(recruit) {
  selected=null;
  pending={type:'deploy',id:recruit.id};
  menuPane=null;
  revealRecruit(recruit,'Feld wählen');
}

async function command(order, hint) {
  if (locked || !room) return false;
  locked=true;
  paintOrders();
  try {
    const id=room.id;
    const before=new Set(room.game.players[room.viewer].reserve?.map(r=>r.id)??[]);
    const firstNewId=room.game.next_id;
    const result=await request('action',{id,nonce:crypto.randomUUID(),command:order});
    if(room?.id!==id)return false;
    receive(result);
    if(isCircuit(result.game) && ['recruit','recruit_many','oracle'].includes(order.type)) {
      const recruit=result.game.players[result.viewer].reserve.find(r=>!before.has(r.id));
      if(recruit)chooseReserve(recruit);
      else if (!pending) {
        const added=result.game.events.findLast(event=>event.id>=firstNewId && ['draw','stack'].includes(event.kind)
          && result.game.pieces.some(piece=>piece.id===event.source && piece.owner===result.viewer));
        const piece=result.game.pieces.find(piece=>piece.id===added?.source);
        if(piece) {
          selected=piece.id;
          revealRecruit(piece,added.kind==='stack'?`${piece.stack}/3 im Trupp`:'Neues Feld');
        }
      }
    }
    if(typeof hint==='function')hint(result);
    paintMatch();
    supplyArena();
    return true;
  } catch(error) {toast(error.message,true);return false;}
  finally {locked=false;paintOrders();}
}

async function tapSlot(slot) {
  if(!room||locked||['lobby','won','lost'].includes(room.game.phase))return;
  if(pending){
    const action={...pending,slot};
    if(action.type==='move' && isCircuit(room.game)) {
      await movePiece(action.id,slot);
      return;
    }
    await command(action,result=>{
      pending=null;
      const piece=result.game.pieces.find(item=>item.slot===slot&&item.owner===result.viewer);
      if(piece&&action.type!=='cast'){
        selected=piece.id;
        if(isCircuit(result.game))menuPane=null;
      }
      if(action.type==='deploy'){
        const next=result.game.players[result.viewer].reserve[0];
        if(next)chooseReserve(next);
      }
      paintMatch();
      supplyArena();
    });
    return;
  }
  const piece=room.game.pieces.find(item=>item.slot===slot&&item.owner===room.viewer);
  selected=piece?.id??null;
  if(isCircuit(room.game)) menuPane=piece?'piece':null;
  paintMatch();
  supplyArena();
}

function matchesTroop(a,b) {
  return a.actor===b.actor && a.tier===b.tier && actors.get(a.actor)?.kind==='troop';
}

function canMoveTo(piece,slot,destination) {
  if(!piece || actors.get(piece.actor)?.kind==='building' || slot===piece.slot) return false;
  if(room.guest && ownerOf(room.game,slot)!==room.viewer) return false;
  return !destination || (destination.owner===room.viewer && actors.get(destination.actor)?.kind!=='building'
    && (!matchesTroop(piece,destination) || destination.stack<3));
}

async function movePiece(id,slot) {
  if(!room || locked) return;
  const piece=room.game.pieces.find(item=>item.owner===room.viewer && item.id===id);
  const destination=room.game.pieces.find(item=>item.slot===slot);
  if(!canMoveTo(piece,slot,destination)) return;
  if (!destination || !matchesTroop(piece,destination)) {
    movePreview={room:room.id,id,from:piece.slot,to:slot,other:destination?.id};
    supplyArena();
  }
  try {
    await command({type:'move',id,slot},result=>{
      pending=null;
      selected=result.game.pieces.find(item=>item.slot===slot && item.owner===result.viewer)?.id??null;
      menuPane=null;
    });
  } finally {
    movePreview=null;
    supplyArena();
  }
}

function dragTarget(drag,event) {
  let closest=null;
  let distance=1.5;
  for(const tile of drag.tiles) {
    const delta=Math.hypot((event.clientX-tile.x)/tile.halfWidth,(event.clientY-tile.y)/tile.halfHeight);
    if(delta<distance){distance=delta;closest=tile.index;}
  }
  return drag.valid.has(closest)?closest:null;
}

function paintDrag(event) {
  const drag=dragStart;
  if(!drag || drag.pointer!==event.pointerId) return;
  if(!drag.tiles) {
    if(Math.hypot(event.clientX-drag.x,event.clientY-drag.y)<(event.pointerType==='touch'?10:6)) return;
    const board=$('stage').getBoundingClientRect();
    drag.board=board;
    drag.tiles=grid.flatMap((button,index)=>{
      if(button.hidden)return [];
      const rect=button.getBoundingClientRect();
      return [{index,x:rect.x+rect.width/2,y:rect.y+rect.height/2,halfWidth:rect.width*.62,halfHeight:rect.height*.62}];
    });
    const occupied=new Map(room.game.pieces.map(item=>[item.slot,item]));
    const piece=occupied.get(drag.slot);
    if(piece?.id!==drag.id){clearDrag();return;}
    drag.valid=new Set(drag.tiles.filter(tile=>canMoveTo(piece,tile.index,occupied.get(tile.index))).map(tile=>tile.index));
    const guide=$('drag-figure');
    guide.className=`drag-figure rarity-${piece.tier}`;
    guide.innerHTML=`${portrait(piece.actor)}<b>${piece.stack}</b>`;
    guide.hidden=false;
    grid[drag.slot].classList.add('drag-origin');
    for(const i of drag.valid)grid[i].classList.add('drag-target');
  }
  const aim=dragTarget(drag,event);
  if(drag.target!==aim) {
    grid[drag.target]?.classList.remove('drag-aim');
    grid[aim]?.classList.add('drag-aim');
    drag.target=aim;
  }
  $('drag-figure').style.transform=`translate(${event.clientX-drag.board.left}px,${event.clientY-drag.board.top}px)`;
}

function clearDrag() {
  if(!dragStart)return;
  grid[dragStart.slot]?.classList.remove('drag-origin');
  for(const i of dragStart.valid??[])grid[i].classList.remove('drag-target','drag-aim');
  $('drag-figure').hidden=true;
  dragStart=null;
}

for (let i=0;i<32;i++) {
  const button = document.createElement('button');
  button.type = 'button';
  button.className = 'build-slot';
  button.hidden = true;
  button.dataset.slot = String(i);
  button.addEventListener('click', event => {
    if (event.detail && suppressedClick?.slot === i && performance.now() < suppressedClick.until) return;
    void tapSlot(i);
  });
  button.addEventListener('pointerdown',event=>{
    if(!isCircuit(room?.game)||pending||locked||!event.isPrimary||event.button!==0)return;
    const piece=room.game.pieces.find(item=>item.slot===i&&item.owner===room.viewer);
    if(piece&&actors.get(piece.actor)?.kind!=='building'){
      dragStart={id:piece.id,x:event.clientX,y:event.clientY,slot:i,pointer:event.pointerId};
      button.setPointerCapture(event.pointerId);
    }
  });
  button.addEventListener('pointermove',paintDrag);
  button.addEventListener('pointerup',event=>{
    if(!dragStart||dragStart.pointer!==event.pointerId)return;
    const drag=dragStart;
    const slot=drag.tiles?dragTarget(drag,event):null;
    clearDrag();
    if(!drag.tiles)return;
    suppressedClick={slot:i,until:performance.now()+240};
    if(slot!==null)void movePiece(drag.id,slot);
  });
  button.addEventListener('pointercancel',clearDrag);
  button.addEventListener('lostpointercapture',clearDrag);
  $('slot-overlay').append(button);
  grid.push(button);
}
window.addEventListener('pantheon-slots', event => {
  if (!room) return;
  const data = JSON.parse(event.detail);
  const circuit=isCircuit(room.game);
  const width=$('stage').clientWidth;
  const tileSize=circuit?Math.min(68,Math.max(32,width/8.6)):Math.min(52,Math.max(17,width/30));
  for (const [index, button] of grid.entries()) {
    if(!data.slots[index]){button.hidden=true;continue;}
    const [x,y]=data.slots[index];
    button.style.left = `${x/data.width*100}%`;
    button.style.top = `${y/data.height*100}%`;
    button.style.setProperty('--tile-size',`${tileSize}px`);
    button.hidden = false;
  }
  if (!$('stage').dataset.rendered) markRendered();
});
window.addEventListener('pantheon-frame-rate',event=>{
  const stage=$('stage');
  stage.dataset.renderFps=event.detail;
  if(!isCircuit(room?.game)||!handheld()||!stage.dataset.rendered||document.hidden)return;
  const fps=Number(event.detail);
  const resolution=stage.dataset.resolution;
  slowSamples=fps<(resolution==='sharp'?42:26) ? slowSamples+1 : 0;
  severeSamples=fps<15 ? severeSamples+1 : 0;
  fastSamples=fps>=54 ? fastSamples+1 : 0;
  if(severeSamples>=2) stage.dataset.resolution='economy';
  else if(slowSamples>=2 && resolution==='sharp') delete stage.dataset.resolution;
  else if(slowSamples>=3 && !resolution) stage.dataset.resolution='performance';
  else if(fastSamples>=8) {
    if(resolution==='economy') stage.dataset.resolution='performance';
    else if(resolution==='performance') delete stage.dataset.resolution;
    else if(!resolution && devicePixelRatio>1.25) stage.dataset.resolution='sharp';
    fastSamples=0;
  }
});
function boardAsset(game) {
  return isCircuit(game) ? game.theme : 'gate';
}

window.addEventListener('pantheon-board-models', event => {
  loadedBoard=event.detail;
  if (room && loadedBoard===boardAsset(room.game)) {
    $('stage').dataset.models='ready';
    if ($('stage').dataset.rendered) markRendered();
  }
});
function markRendered() {
  $('stage').dataset.rendered = 'true';
  $('render-notice').hidden = !room || !isCircuit(room.game) || loadedBoard===boardAsset(room.game);
  paintOrders();
}

function closeBattleSheet() {
  const trigger = $('orders').querySelector(`[data-pane="${menuPane}"]`);
  menuPane = null;
  paintOrders();
  trigger?.focus({ preventScroll:true });
}

function confirmForfeit() {
  if (!room || !['prep','combat'].includes(room.game.phase)) return;
  $('leave-note').textContent = room.guest ? 'Die Partie endet für euch beide. Ihr erhaltet EP für die erreichte Welle.'
    : 'Du erhältst EP für die erreichte Welle.';
  $('leave-dialog').returnValue = 'cancel';
  $('leave-dialog').showModal();
}

$('orders').addEventListener('click', async event => {
  const button = event.target.closest('button');
  if (!button || !room || button.disabled) return;
  if (button.dataset.pane) {
    const pane = button.dataset.pane;
    if (isCircuit(room.game) && menuPane===pane) { closeBattleSheet(); return; }
    menuPane = pane;
    if (pane==='hero') focusHero = preferredHero(room);
    paintOrders();
    if (event.detail===0) $('command-title')?.focus({ preventScroll:true });
    return;
  }
  if (button.dataset.heroSelect) {
    focusHero = button.dataset.heroSelect;
    paintOrders();
    return;
  }
  if (button.dataset.recruitId) {
    const recruit=room.game.players[room.viewer].reserve?.find(item=>item.id===Number(button.dataset.recruitId));
    if(recruit){chooseReserve(recruit);paintMatch();supplyArena();}
    return;
  }
  if (button.dataset.releaseId) {
    await command({type:'stow',id:Number(button.dataset.releaseId)});
    return;
  }
  if(button.dataset.oracle){await command({type:'oracle',tier:Number(button.dataset.oracle)});return;}
  if(button.dataset.temper){await command({type:'temper',tier:Number(button.dataset.temper)});return;}
  if(button.dataset.ritual){
    const actor = button.dataset.ritual;
    await command({type:'ritual',actor},result=>{
      selected=result.game.pieces.filter(p=>p.actor===actor&&p.owner===result.viewer).at(-1)?.id??null;
      pending = null;
      menuPane = null;
      toast(`${actors.get(actor).name} beschworen.`);
    });
    return;
  }
  if (button.dataset.place) {
    pending = pending?.actor === button.dataset.place ? null : {type:'place',actor:button.dataset.place};
    selected = null;
    if (isCircuit(room.game)) menuPane = null;
    paintMatch();
    supplyArena();
    if (pending && handheld() && !isCircuit(room.game)) $('stage').scrollIntoView({block:'center'});
    return;
  }
  const kind = button.dataset.order;
  if (kind==='close-sheet') { closeBattleSheet(); return; }
  if(kind==='recruit-many'){await command({type:'recruit_many',count:3});return;}
  if(kind==='fortune'){await command({type:'fortune'});return;}
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
    pending = {type:kind,id:selected};
    if (isCircuit(room.game)) menuPane = null;
    paintMatch();
  } else if (kind === 'cast-auto') {
    const choice = pending;
    pending = null;
    if (choice?.type === 'cast') await command({...choice, slot:null});
  } else if (kind === 'forfeit') {
    confirmForfeit();
  } else if (kind === 'merge') {
    const before = room.game.pieces.find(p => p.id === selected);
    if (before) await command({type:kind,id:before.id}, result => {
      selected = result.game.pieces.find(p => p.slot === before.slot)?.id ?? null;
      supplyArena();
      paintMatch();
    });
  } else if (['start','ready','recruit','upgrade','sell'].includes(kind)) {
    if(kind==='start') { unlockSound(); enterFullscreen(); }
    await command({type:kind, ...(selected && {id:selected})});
  }
});

$('leave-dialog').addEventListener('close', () => {
  if ($('leave-dialog').returnValue === 'confirm') void command({type:'forfeit'});
});
$('account-button').addEventListener('click', () => { if (user) chooseTab('chronicle'); else auth(); });
$('home-button').addEventListener('click', () => chooseTab('bastion'));
$('back-to-hub').addEventListener('click', () => chooseTab('bastion'));
$('match-options').addEventListener('click', () => $('match-menu').showModal());
$('open-forfeit').addEventListener('click', () => { $('match-menu').close(); confirmForfeit(); });
$('sound-button').addEventListener('click', toggleSound);
$('match-sound').addEventListener('click', toggleSound);
window.addEventListener('pantheon-sound', soundLabel);
document.addEventListener('click', event => {
  if (room && soundState()==='tap' && !event.target.closest('#match-sound')) unlockSound();
}, {capture:true});

$('hero-play').addEventListener('click', () => $('preparation').scrollIntoView({behavior:'smooth',block:'start'}));
$('friend').addEventListener('input', event => { friendDraft = event.target.value; });
$('challenge').addEventListener('change', event => {
  challenge = event.target.value;
  $('challenge-detail').textContent = challenges.get(challenge).detail;
});
$('create-match').addEventListener('click', async () => {
  if (!user) { auth('register'); return; }
  unlockSound();
  enterFullscreen();
  const button = $('create-match');
  if (button.disabled) return;
  button.disabled = true;
  try { openMatch(await request('new',{mode,theme,challenge,difficulty,friend:friendDraft})); }
  catch (error) { toast(error.message,true); }
  finally { button.disabled = false; }
});

document.addEventListener('click', async event => {
  const button = event.target.closest('button');
  if (!button) return;
  const target = button.dataset;
  if (target.tab) chooseTab(target.tab);
  if (target.mode) { mode = target.mode; paintPreparation(); }
  if (target.difficulty) {
    if (button.getAttribute('aria-disabled') !== 'true') difficulty = target.difficulty;
    paintDifficulties(target.difficulty);
  }
  if (target.theme) {
    if (button.getAttribute('aria-disabled') === 'true') {
      toast(`Diesen Schauplatz schaltest du ab Profilstufe ${themes.get(target.theme).unlock} frei.`);
    } else { theme = target.theme; paintPreparation(); }
  }
  if (target.faction) { factionFilter = target.faction; paintCollection(); }
  if (target.mastery) {
    button.disabled = true;
    try {
      const {user:updated} = await request('mastery',{actor:target.mastery,expected:user?.masteries?.[target.mastery]??0});
      changeAccount(updated);
      toast(`${actors.get(target.mastery).name} ist jetzt auf Meisterschaft ${updated.masteries[target.mastery]}.`);
    } catch (error) {
      button.disabled = false;
      toast(error.message,true);
    }
  }
  if (target.sign) {
    button.disabled = true;
    const id = target.signAction === 'equip' && user?.fieldSign === target.sign ? null : target.sign;
    try {
      const {user:updated} = await request('field-sign', { id, action:target.signAction, expected:user?.fieldSigns?.[target.sign] ?? 0 });
      changeAccount(updated);
    } catch (error) {
      button.disabled = false;
      toast(error.message,true);
    }
  }
  if (target.auth) auth(target.auth);
  if (target.close) $(target.close).close();
  if (target.resume) {
    unlockSound();
    enterFullscreen();
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
  unlockSound();
  enterFullscreen();
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
  if (event.key === 'Escape' && !event.target.closest('dialog') && isCircuit(room.game) && menuPane) {
    event.preventDefault(); closeBattleSheet(); return;
  }
  if (event.key === 'Escape' && pending) { pending = null; paintMatch(); return; }
  const hotkeys = {r:'recruit', m:'move', u:'upgrade', f:'cast', ' ':'ready'};
  const kind = hotkeys[event.key.toLowerCase()];
  if (kind && event.target.tagName !== 'BUTTON') {
    if (selected && isCircuit(room.game) && ['move','upgrade','cast'].includes(kind) && menuPane!=='piece') {
      menuPane = 'piece';
      paintOrders();
    }
    const button = [...$('orders').querySelectorAll(`[data-order="${kind}"]:not(:disabled)`)]
      .find(candidate => !candidate.closest('[hidden]'));
    if (button) { event.preventDefault(); button.click(); }
  }
});

bindScreen();
paintPreparation();
soundLabel();
versionLabel();
void request('health').then(data => { currentVersion = data.version; versionLabel(); }).catch(() => {});
void refreshAccount().then(() => { void recentRooms(); showInvite(); });
