import { esc, portrait, price, rarities } from './presentation.js';

export const isCircuit = game => (game?.rule_version ?? 1) >= 2;
export const ownerOf = (game, slot) => isCircuit(game) ? 1 - Math.floor(slot / 16) : Math.floor(slot / 12);
export const drawPrice = (game, player) => Math.min(118,(game.challenge === 'levy' ? 21 : 26) + player.recruits * 2);
export const pressureLimit = (game, difficulty) => ({scarcity:34,eclipse:43}[game.challenge] ?? 45) + (game.players.length === 2 ? 19 : 0) + (difficulty?.pressure ?? 0);

const disabled = off => off ? 'disabled' : '';
const rarityClass = tier => `rarity-${tier}`;
const a = esc;
const dockSections = new WeakMap();

const panes = [
  ['recruit', 'Reserve', 'reserve'], ['oracle', 'Orakel', 'oracle'], ['hero', 'Helden', 'hero'],
  ['building', 'Bauen', 'building'], ['smith', 'Schmiede', 'smith'],
];

function icon(name) {
  return `<i class="battle-icon" data-icon="${name}" aria-hidden="true"></i>`;
}

function reservePanel(player,pending,actors) {
  const recruits = player.reserve ?? [];
  if (!recruits.length) return '<p class="tray-empty">Rekrutiere eine Einheit oder tippe einen Trupp auf dem Spielfeld an.</p>';
  return `<div class="reserve-list" aria-label="Deine Rekruten">${recruits.map(recruit => {
    const definition = actors.get(recruit.actor);
    const picked = pending?.type === 'deploy' && pending.id === recruit.id;
    return `<button class="reserve-card ${rarityClass(recruit.tier)}" data-recruit-id="${recruit.id}" aria-pressed="${picked}"
       aria-label="${a(definition.name)} platzieren"><span>${portrait(definition.id)}</span>
       <strong>${a(definition.name)}</strong><small>${rarities[recruit.tier]}</small></button>`;
  }).join('')}</div>
  ${pending?.type === 'deploy' ? '<div class="reserve-actions"><span>Tippe auf ein markiertes Feld.</span><button data-order="release" class="text-button">Rekrut entlassen</button></div>' : ''}
  `;
}

function rewards(player) {
  return `<div class="round-goals">
    <span>${Math.min(player.recruits,5)} / 5 Rekrutierungen <b>+2 Essenz</b></span>
    <span>${Math.min(player.merges,2)} / 2 Verschmelzungen <b>+2 Essenz</b></span>
  </div>`;
}

function oracle(game,player,level,catalog) {
  const ratios=[ [2,2,72],[3,3,49],[4,4,32],[5,6,18] ];
  return `<div class="oracle-options">${ratios.map(([tier,cost,chance]) => {
    const unlock = catalog.actors.some(entry => entry.theme===game.theme && entry.kind==='troop' && entry.rarity===tier && entry.unlock<=level);
    return `<button class="ritual-chip ${rarityClass(tier)}" data-oracle="${tier}" ${disabled(!unlock || player.essence < cost || player.reserve.length >= 6)}>
      <strong>${rarities[tier]}</strong><small>${unlock ? `${chance} % Erfolg · ${cost} Essenz` : 'Noch gesperrt'}</small></button>`;
  }).join('')}</div><p class="tray-help">Setze Essenz für eine Chance auf eine seltenere Einheit ein.</p>`;
}

function heroPanel(room,player,level,catalog,actors) {
  const counts=new Map();
  for (const piece of room.game.pieces) if (piece.owner===room.viewer) counts.set(piece.actor,(counts.get(piece.actor)??0)+piece.stack);
  const active=room.game.pieces.filter(p=>p.owner===room.viewer && actors.get(p.actor)?.kind==='hero').length;
  return `<div class="ritual-list">${catalog.actors.filter(entry => entry.theme===room.game.theme && entry.kind==='hero').map(hero => {
    const needs=new Map();
    for(const ingredient of hero.recipe) needs.set(ingredient,(needs.get(ingredient)??0)+1);
    const ready=[...needs].every(([id,need])=>(counts.get(id)??0)>=need);
    const blocked=hero.unlock>level;
    const entries=[...needs].map(([id,need]) => `<span class="${(counts.get(id)??0)>=need?'owned':''}">${a(actors.get(id).name)} ${Math.min(counts.get(id)??0,need)}/${need}</span>`).join('');
    return `<div class="ritual-row">${portrait(hero.id)}
      <div><strong>${a(hero.name)}</strong><small>${a(hero.role)}${blocked ? ` · Stufe ${hero.unlock}` : ''}</small>
      <div class="ingredient-list">${entries}</div></div>
      <button class="minibutton" data-ritual="${hero.id}" ${disabled(blocked || !ready || active>=3 || player.gold<65)}>Beschwören · 65 Gold</button>
      </div>`;
  }).join('')}</div>`;
}

function buildPanel(game,player,level,catalog,pending) {
  const owned=game.pieces.filter(p=>p.owner===game.players.indexOf(player) && catalog.actors.find(a=>a.id===p.actor)?.kind==='building').length;
  if (game.challenge==='levy') return '<p class="tray-empty">In der Würfelwache stehen Einheiten und Helden zur Verfügung.</p>';
  return `<div class="ritual-list">${catalog.actors.filter(entry=>entry.theme===game.theme && entry.kind==='building').map(actor=>{
    const picked=pending?.actor===actor.id;
    return `<div class="ritual-row">${portrait(actor.id)}<div><strong>${a(actor.name)}</strong><small>${a(actor.role)} · ${owned}/2 Gebäude</small></div>
      <button class="minibutton" data-place="${actor.id}" aria-pressed="${picked}"
       ${disabled(actor.unlock>level || player.gold<actor.cost || owned>=2)}>Bauen · ${actor.cost} Gold</button></div>`;
  }).join('')}</div>`;
}

function smith(player) {
  return `<div class="smith-options">${rarities.slice(1).map((name,index)=>{
    const rank=player.temper?.[index]??0;
    const cost=33+16*index+24*rank;
    return `<button class="ritual-chip ${rarityClass(index+1)}" data-temper="${index+1}" ${disabled(rank>=6 || player.gold<cost)}>
       <strong>${name}</strong><small>+${rank*12} % Schaden · ${rank>=6?'Maximum':`${cost} Gold`}</small></button>`;
  }).join('')}</div>
  <div class="favor-row"><span>Glück ${player.favor}/5</span>
     <button class="minibutton" data-order="fortune" title="Höhere Chance auf seltene Einheiten" ${disabled(player.favor>=5 || player.gold<65+player.favor*34)}>Glück erhöhen · ${65+player.favor*34} Gold</button></div>
  ${rewards(player)}`;
}

function detail(piece,game,actors) {
  const actor=actors.get(piece.actor);
  const player=game.players[piece.owner];
  const cooldown=Math.max(0,Math.ceil((piece.cast_ready-game.tick)/20));
  const troop=actor.kind==='troop';
  const boost=troop?(player.temper?.[piece.tier-1]??0):0;
  const damage=Math.round(actor.damage*[1,1.38,1.92,2.68,4.15][piece.tier-1] *
    (1+0.24*(piece.rank-1))*(piece.stack??1)*(1+0.07*(piece.mastery??0))*(1+0.12*boost));
  return `<div class="formation-view ${rarityClass(piece.tier)}">
    <div class="formation-summary">${portrait(actor.id)}<div><strong>${a(actor.name)}</strong><small>
      ${troop?rarities[piece.tier]:actor.kind==='hero'?'Held':'Gebäude'} · Stufe ${piece.rank} · ${damage} Schaden
    </small></div></div>
    <div class="formation-actions">
      ${actor.kind==='building'?'':'<button data-order="move" class="minibutton">Verschieben</button>'}
      ${troop && piece.tier<5?`<button class="minibutton merge" data-order="merge" ${disabled(piece.stack!==3)}>Verschmelzen · ${piece.stack}/3</button>`:''}
      ${actor.kind==='hero'?`<button class="minibutton cast" data-order="cast" ${disabled(cooldown||game.phase!=='combat')}>${a(actor.role)}${cooldown?` · ${cooldown} s`:''}</button>`:''}
      <button class="minibutton" data-order="upgrade" ${disabled(piece.rank>=4 || player.gold<price(piece.rank,piece.tier))}>${piece.rank>=4?'Höchste Stufe':`Aufwerten · ${price(piece.rank,piece.tier)} Gold`}</button>
      <button class="minibutton sell" data-order="sell">Verkaufen</button>
    </div></div>`;
}

function updatePanel(panel, markup) {
  if (dockSections.get(panel) === markup) return;
  dockSections.set(panel, markup);
  const scroll = panel.scrollTop;
  const sideways = panel.querySelector('.reserve-list')?.scrollLeft;
  panel.innerHTML = markup;
  panel.scrollTop = scroll;
  if (sideways) {
    const reserve = panel.querySelector('.reserve-list');
    if (reserve) reserve.scrollLeft = sideways;
  }
}

export function updateCircuitOrders(orders, {room,selected,pending,menuPane,actors,catalog,level,locked,muted}) {
  const {game,viewer}=room;
  const player=game.players[viewer];
  const draw=drawPrice(game,player);
  const rank=game.pieces.find(p=>p.id===selected);
  const section=rank && menuPane==='piece' ? detail(rank,game,actors)
      : menuPane==='oracle' ? oracle(game,player,level,catalog)
      : menuPane==='hero' ? heroPanel(room,player,level,catalog,actors)
      : menuPane==='building' ? buildPanel(game,player,level,catalog,pending)
      : menuPane==='smith' ? smith(player)
      : reservePanel(player,pending,actors);
  if (!orders.querySelector('.battle-quick')) orders.innerHTML=`<div class="battle-quick">
    <button class="draw-button" data-order="recruit">${icon('recruit')}<strong>Rekrutieren</strong>
      <span class="draw-cost">${icon('gold')} <span></span></span></button>
    <button class="draw-many" data-order="recruit-many" aria-label="Bis zu drei Einheiten rekrutieren">×3</button>
    <button class="ready-quick" data-order="ready" hidden></button>
  </div>
  <nav class="battle-tabs" aria-label="Kampfmenü">${panes.map(([id,label,symbol])=>
    `<button data-pane="${id}">${icon(symbol)}<span>${label}</span>${id==='recruit'?'<b hidden></b>':''}</button>`).join('')}</nav>
  <div class="battle-tray" tabindex="0" aria-label="Ausgewählter Bereich"></div>
  <div class="battle-target" hidden></div>
  <div class="battle-end"><button class="text-button" data-order="sound" aria-label="Spielton"></button>
    <button class="text-button" data-order="forfeit">Aufgeben</button></div>`;
  const unable=locked || player.gold<draw || player.reserve.length>=6;
  const recruit=orders.querySelector('[data-order="recruit"]');
  recruit.disabled=unable;
  recruit.querySelector('.draw-cost span').textContent=draw;
  recruit.setAttribute('aria-label',`Rekrutieren · ${draw} Gold`);
  orders.querySelector('[data-order="recruit-many"]').disabled=unable;
  const ready=orders.querySelector('[data-order="ready"]');
  ready.hidden=game.phase!=='prep';
  ready.disabled=locked || game.prepared[viewer];
  ready.textContent=game.prepared[viewer]?'Wartet':'Bereit';
  const pane=menuPane==='piece'?'recruit':menuPane;
  for (const button of orders.querySelectorAll('[data-pane]')) button.setAttribute('aria-pressed',String(button.dataset.pane===pane));
  const remaining=orders.querySelector('.battle-tabs b');
  remaining.hidden=!player.reserve.length;
  remaining.textContent=player.reserve.length;
  const target=orders.querySelector('.battle-target');
  target.hidden=!pending;
  const targetMarkup=pending?.type==='cast'
    ? '<button class="minibutton" data-order="cast-auto">Automatisch zielen</button><button class="text-button" data-order="cancel">Abbrechen</button>'
    : '<button class="text-button" data-order="cancel">Auswahl abbrechen</button>';
  updatePanel(target,targetMarkup);
  updatePanel(orders.querySelector('.battle-tray'),section);
  const sound=orders.querySelector('[data-order="sound"]');
  sound.setAttribute('aria-pressed',String(!muted));
  sound.textContent=`Ton ${muted?'aus':'an'}`;
}
