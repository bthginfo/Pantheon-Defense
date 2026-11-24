import { esc, portrait, price, rarities } from './presentation.js';

export const isCircuit = game => (game?.rule_version ?? 1) >= 2;
export const ownerOf = (game, slot) => isCircuit(game) ? 1 - Math.floor(slot / 16) : Math.floor(slot / 12);
const drawPrice = (game, player) => Math.min(118, (game.challenge === 'levy' ? 21 : 26) + player.recruits * 2);
export const pressureLimit = (game, difficulty) => ({scarcity:34,eclipse:43}[game.challenge] ?? 45) + (game.players.length === 2 ? 19 : 0) + (difficulty?.pressure ?? 0);

const disabled = off => off ? 'disabled' : '';
const rarityClass = tier => `rarity-${tier}`;
const sections = new WeakMap();
const panes = [
  ['recruit', 'Reserve', 'reserve'], ['oracle', 'Orakel', 'oracle'],
  ['building', 'Bauen', 'building'], ['smith', 'Schmiede', 'smith'],
];
const sheetTitles = {
  recruit: 'Deine Reserve', oracle: 'Orakel', hero: 'Helden beschwören',
  building: 'Gebäude errichten', smith: 'Deine Schmiede', piece: 'Ausgewähltes Feld',
};

function icon(name) {
  return `<i class="battle-icon" data-icon="${name}" aria-hidden="true"></i>`;
}

function setText(element, value) {
  const next = String(value);
  if (element.textContent !== next) element.textContent = next;
}

export function preferredHero(room) {
  const offers = room.game.rituals?.[room.viewer]?.offers ?? [];
  return offers.find(offer => !offer.blockers.length)?.actor
    ?? offers.find(offer => !offer.blockers.includes('level'))?.actor
    ?? offers[0]?.actor ?? null;
}

function problem(offer, hero, player, report, short = false) {
  const missing = offer.ingredients.reduce((sum, entry) => sum + Math.max(0, entry.need - entry.have), 0);
  const gold = Math.max(0, report.price - player.gold);
  const messages = {
    level: short ? `Stufe ${hero.unlock}` : `Verfügbar ab Profilstufe ${hero.unlock}.`,
    hero_limit: short ? 'Heldenlimit' : `Du hast bereits ${report.limit} Helden auf dem Feld.`,
    ingredients: short ? `${missing} fehlt` : missing === 1 ? 'Dir fehlt eine Einheit aus dem Rezept.' : `Dir fehlen ${missing} Einheiten aus dem Rezept.`,
    field: short ? 'Kein Feld frei' : 'Mach ein Feld frei, damit der Held erscheinen kann.',
    gold: short ? 'Gold fehlt' : `Dir fehlen ${gold} Gold.`,
  };
  return short ? messages[offer.blockers[0]] ?? 'Bereit' : offer.blockers.map(key => messages[key]).join(' ');
}

function reservePanel(player, pending, actors) {
  if (!player.reserve.length) return '<p class="command-empty">Deine Reserve ist leer. Neue Einheiten warten hier auf ein Feld.</p>';
  return `<div class="reserve-list" aria-label="Deine Rekruten">${player.reserve.map(recruit => {
    const definition = actors.get(recruit.actor);
    const picked = pending?.type === 'deploy' && pending.id === recruit.id;
    return `<div class="reserve-entry ${rarityClass(recruit.tier)}">
      <button class="reserve-card" data-recruit-id="${recruit.id}" aria-pressed="${picked}"
        aria-label="${esc(definition.name)} platzieren">${portrait(definition.id)}
        <span><strong>${esc(definition.name)}</strong><small>${rarities[recruit.tier]}</small></span>
      </button>
      <button class="command-subtle" data-release-id="${recruit.id}" aria-label="${esc(definition.name)} entlassen">Entlassen</button>
    </div>`;
  }).join('')}</div>`;
}

function rewards(player) {
  return `<div class="round-goals">
    <span>${Math.min(player.recruits,5)} / 5 Rekrutierungen <b>+2 Essenz</b></span>
    <span>${Math.min(player.merges,2)} / 2 Verschmelzungen <b>+2 Essenz</b></span>
  </div>`;
}

function oracle(game, player, level, catalog) {
  const ratios = [[2,2,72], [3,3,49], [4,4,32], [5,6,18]];
  return `<p class="command-help">Setze Essenz für eine Chance auf eine seltenere Einheit ein.</p>
    <div class="oracle-options">${ratios.map(([tier,cost,chance]) => {
      const unlock = catalog.actors.some(entry => entry.theme===game.theme && entry.kind==='troop' && entry.rarity===tier && entry.unlock<=level);
      return `<button class="ritual-chip ${rarityClass(tier)}" data-oracle="${tier}" ${disabled(!unlock || player.essence < cost || player.reserve.length >= 6)}>
        <strong>${rarities[tier]}</strong><small>${unlock ? `${chance} % Erfolg · ${cost} Essenz` : 'Noch gesperrt'}</small></button>`;
    }).join('')}</div>`;
}

function heroPanel(body, footer, report, player, actors, focusHero, locked) {
  if (!report?.offers.length) {
    updatePanel(body, '<p class="command-empty">Beschwörungen werden geprüft …</p>');
    footer.hidden = true;
    return;
  }
  const visible = report.offers.find(offer => offer.actor === focusHero) ?? report.offers[0];
  const hero = actors.get(visible.actor);
  const roster = report.offers.map(({actor}) => actor).join(',');
  if (body.dataset.roster !== roster) {
    body.dataset.roster = roster;
    body.innerHTML = `<div class="hero-resources">
      <span class="hero-spaces"></span><span class="hero-gold">${icon('gold')}<b></b></span></div>
      <div class="hero-roster" aria-label="Helden auswählen">${report.offers.map(offer => {
        const card = actors.get(offer.actor);
        return `<button class="hero-portrait" data-hero-select="${card.id}" aria-pressed="false">
          ${portrait(card.id)}<strong>${esc(card.name)}</strong><small></small></button>`;
      }).join('')}</div>
      <article class="hero-feature"></article>`;
  }
  setText(body.querySelector('.hero-spaces'), `${report.active} von ${report.limit} Helden auf dem Feld`);
  setText(body.querySelector('.hero-gold b'), `${player.gold} Gold`);
  for (const tile of body.querySelectorAll('[data-hero-select]')) {
    const offer = report.offers.find(entry => entry.actor === tile.dataset.heroSelect);
    tile.setAttribute('aria-pressed', String(offer === visible));
    tile.dataset.ready = String(!offer.blockers.length);
    const message = problem(offer, actors.get(offer.actor), player, report, true);
    setText(tile.querySelector('small'), message);
    tile.setAttribute('aria-label', `${actors.get(offer.actor).name}, ${message}`);
  }

  const feature = body.querySelector('.hero-feature');
  if (feature.dataset.hero !== hero.id) {
    feature.dataset.hero = hero.id;
    feature.style.setProperty('--hero-pigment', hero.color);
    feature.innerHTML = `<div class="hero-feature-art"><img class="portrait" src="/assets/portraits/${hero.id}.png" alt=""></div>
      <div class="hero-feature-copy"><h3>${esc(hero.name)}</h3><strong>${esc(hero.role)}</strong></div>
      <p class="hero-ability">${esc(hero.note)}</p>
      <p class="hero-recipe-label">Benötigte Einheiten auf deinem Feld</p>
      <ul class="hero-recipe" aria-label="Einheiten auf deinem Spielfeld">${visible.ingredients.map(({actor}) =>
        `<li data-ingredient="${actor}">${portrait(actor)}<span>${esc(actors.get(actor).name)}</span><b></b></li>`
      ).join('')}</ul>`;
  }
  for (const item of feature.querySelectorAll('[data-ingredient]')) {
    const ingredient = visible.ingredients.find(entry => entry.actor === item.dataset.ingredient);
    item.dataset.met = String(ingredient.have >= ingredient.need);
    setText(item.querySelector('b'), `${Math.min(ingredient.have, ingredient.need)} / ${ingredient.need}`);
  }
  if (!footer.querySelector('[data-ritual]')) {
    footer.innerHTML = `<p class="ritual-status" aria-live="polite"></p>
      <button class="summon-button" data-ritual="" aria-describedby="ritual-message">
        ${icon('hero')}<strong>Beschwören</strong><span class="summon-price"></span>
      </button>`;
    footer.querySelector('.ritual-status').id = 'ritual-message';
  }
  const summon = footer.querySelector('[data-ritual]');
  const status = footer.querySelector('.ritual-status');
  const ready = !visible.blockers.length;
  footer.hidden = false;
  summon.dataset.ritual = hero.id;
  summon.disabled = locked || !ready;
  summon.setAttribute('aria-label', `${hero.name} beschwören · ${report.price} Gold`);
  setText(summon.querySelector('.summon-price'), `${report.price} Gold`);
  status.dataset.ready = String(ready);
  setText(status, locked ? 'Befehl wird ausgeführt …' : ready
    ? 'Beschwörung bereit. Die Einheiten aus dem Rezept werden verbraucht.'
    : problem(visible, hero, player, report));
}

function buildPanel(game, player, level, catalog) {
  const owned = game.pieces.filter(p => p.owner===game.players.indexOf(player) && catalog.actors.find(a=>a.id===p.actor)?.kind==='building').length;
  if (game.challenge==='levy') return '<p class="command-empty">In der Würfelwache stehen Einheiten und Helden zur Verfügung.</p>';
  return `<p class="command-help">${owned} von 2 Gebäuden gebaut. Wähle ein Gebäude und danach seinen Bauplatz.</p>
    <div class="building-list">${catalog.actors.filter(entry=>entry.theme===game.theme && entry.kind==='building').map(actor=>{
      const reason = actor.unlock>level ? `Ab Profilstufe ${actor.unlock}` : owned>=2 ? 'Gebäudelimit erreicht' : player.gold<actor.cost ? `Noch ${actor.cost-player.gold} Gold` : '';
      return `<article class="building-card">${portrait(actor.id)}
        <div><h3>${esc(actor.name)}</h3><p>${esc(actor.note)}</p></div>
        <button class="command-action" data-place="${actor.id}" ${disabled(Boolean(reason))}>${reason || `Bauen · ${actor.cost} Gold`}</button>
      </article>`;
    }).join('')}</div>`;
}

function smith(player) {
  return `<p class="command-help">Verbessere alle Einheiten einer Seltenheit für diese Partie.</p>
    <div class="smith-options">${rarities.slice(1).map((name,index)=>{
      const rank=player.temper?.[index]??0;
      const cost=33+16*index+24*rank;
      return `<button class="ritual-chip ${rarityClass(index+1)}" data-temper="${index+1}" ${disabled(rank>=6 || player.gold<cost)}>
        <strong>${name}</strong><small>+${rank*12} % Schaden · ${rank>=6?'Maximum':`${cost} Gold`}</small></button>`;
    }).join('')}</div>
    <div class="favor-row"><span>Glück ${player.favor}/5</span>
      <button class="command-action" data-order="fortune" ${disabled(player.favor>=5 || player.gold<65+player.favor*34)}>Glück erhöhen · ${65+player.favor*34} Gold</button></div>
    ${rewards(player)}`;
}

function detail(piece, game, actors) {
  const actor = actors.get(piece.actor);
  const player = game.players[piece.owner];
  const cooldown = Math.max(0, Math.ceil((piece.cast_ready-game.tick)/20));
  const troop = actor.kind==='troop';
  const boost = troop ? (player.temper?.[piece.tier-1]??0) : 0;
  const damage = Math.round(actor.damage*[1,1.38,1.92,2.68,4.15][piece.tier-1] *
    (1+0.24*(piece.rank-1))*(piece.stack??1)*(1+0.07*(piece.mastery??0))*(1+0.12*boost));
  return `<article class="formation-view ${rarityClass(piece.tier)}">
    <div class="formation-summary">${portrait(actor.id)}<div><h3>${esc(actor.name)}</h3>
      <small>${troop?rarities[piece.tier]:actor.kind==='hero'?'Held':'Gebäude'} · Stufe ${piece.rank} · ${damage} Schaden</small>
      <p>${esc(actor.note)}</p></div></div>
    <div class="formation-actions">
      ${actor.kind==='building'?'':'<button data-order="move" class="command-action">Verschieben</button>'}
      ${troop && piece.tier<5?`<button class="command-action merge" data-order="merge" ${disabled(piece.stack!==3)}>Verschmelzen · ${piece.stack}/3</button>`:''}
      ${actor.kind==='hero'?`<button class="command-action cast" data-order="cast" ${disabled(cooldown||game.phase!=='combat')}>${esc(actor.role)}${cooldown?` · ${cooldown} s`:''}</button>`:''}
      <button class="command-action" data-order="upgrade" ${disabled(piece.rank>=4 || player.gold<price(piece.rank,piece.tier))}>${piece.rank>=4?'Höchste Stufe':`Aufwerten · ${price(piece.rank,piece.tier)} Gold`}</button>
      <button class="command-action sell" data-order="sell">Verkaufen</button>
    </div></article>`;
}

function fieldContext(pending, piece, player, actors, game) {
  if (!pending && !piece) return '';
  const recruit = pending?.type==='deploy' && player.reserve.find(unit => unit.id===pending.id);
  const actor = actors.get(recruit?.actor ?? pending?.actor ?? piece?.actor);
  if (!pending) {
    const canMerge = actor.kind==='troop' && piece.stack===3 && piece.tier<5;
    const canCast = actor.kind==='hero' && game.phase==='combat' && game.tick>=piece.cast_ready;
    const quick = canMerge ? ['merge','Verschmelzen'] : canCast ? ['cast',actor.role]
      : actor.kind==='building' ? null : ['move','Verschieben'];
    const detail = actor.kind==='troop' ? `${rarities[piece.tier]}${piece.stack>1 ? ` · ×${piece.stack}` : ''}`
      : `${actor.kind==='hero' ? 'Held' : 'Gebäude'} · Stufe ${piece.rank}`;
    return `<div class="field-context-actions">
      <button class="field-context-open" data-pane="piece" aria-controls="command-sheet"
        aria-label="Befehle für ${esc(actor.name)}">${portrait(actor.id)}
        <span><strong>${esc(actor.name)}</strong><small>${detail}</small></span><span aria-hidden="true">›</span></button>
      ${quick ? `<button class="command-action ${quick[0]}" data-order="${quick[0]}">${esc(quick[1])}</button>` : ''}
    </div>`;
  }
  const prompts = { deploy:'Feld für die Einheit wählen', place:'Freien Bauplatz wählen', move:'Zielfeld wählen', cast:'Angriffsziel wählen' };
  return `<div class="field-context-target">${actor ? portrait(actor.id) : icon('recruit')}
    <span><strong>${prompts[pending.type]}</strong><small>${esc(actor?.name ?? 'Tippe auf das Spielfeld')}</small></span>
    ${pending.type==='cast' ? '<button class="command-action" data-order="cast-auto">Auto</button>' : ''}
    <button class="sheet-close" data-order="cancel" aria-label="Auswahl abbrechen">×</button></div>`;
}

function updatePanel(panel, markup) {
  if (sections.get(panel) === markup) return;
  sections.set(panel, markup);
  const scroll = panel.scrollTop;
  panel.innerHTML = markup;
  panel.scrollTop = scroll;
}

function battleMarkup() {
  return `<button class="command-scrim" data-order="close-sheet" aria-label="Ansicht schließen" tabindex="-1" hidden></button>
    <section class="command-sheet" id="command-sheet" aria-labelledby="command-title" hidden>
      <header class="command-sheet-head"><h2 id="command-title" tabindex="-1"></h2>
        <button class="sheet-close" data-order="close-sheet" aria-label="Ansicht schließen">×</button></header>
      <div class="command-sheet-body"></div><footer class="command-sheet-foot" hidden></footer>
    </section>
    <div class="command-dock">
      <div class="field-context" hidden></div>
      <div class="battle-quick">
        <button class="draw-button" data-order="recruit">${icon('recruit')}<strong>Rekrutieren</strong>
          <span class="draw-cost">${icon('gold')}<span></span></span></button>
        <button class="draw-many" data-order="recruit-many" aria-label="Bis zu drei Einheiten rekrutieren">×3</button>
        <button class="hero-callout" data-pane="hero" aria-controls="command-sheet">${icon('hero')}
          <strong>Helden</strong><small aria-live="polite"></small></button>
      </div>
      <nav class="battle-tabs" aria-label="Weitere Spielbefehle">${panes.map(([id,label,symbol])=>
        `<button data-pane="${id}" aria-controls="command-sheet">${icon(symbol)}<span>${label}</span>${id==='recruit'?'<b hidden></b>':''}</button>`).join('')}
        <button class="ready-quick" data-order="ready" hidden></button>
      </nav>
    </div>`;
}

export function updateCircuitOrders(orders, {room, selected, pending, menuPane, focusHero, actors, catalog, level, locked}) {
  const {game, viewer} = room;
  const player = game.players[viewer];
  const draw = drawPrice(game, player);
  const piece = game.pieces.find(p => p.id===selected);
  const report = game.rituals?.[viewer];
  const readyHeroes = report?.offers.filter(offer => !offer.blockers.length) ?? [];
  if (!orders.querySelector('.command-dock')) orders.innerHTML = battleMarkup();

  const recruit = orders.querySelector('[data-order="recruit"]');
  const unable = locked || player.gold<draw || player.reserve.length>=6;
  recruit.disabled = unable;
  setText(recruit.querySelector('.draw-cost span'), draw);
  recruit.setAttribute('aria-label', `Rekrutieren · ${draw} Gold`);
  orders.querySelector('[data-order="recruit-many"]').disabled = unable;
  const ready = orders.querySelector('[data-order="ready"]');
  ready.hidden = game.phase!=='prep';
  ready.disabled = locked || game.prepared[viewer];
  setText(ready, game.prepared[viewer] ? 'Warten …' : 'Bereit');

  const hero = orders.querySelector('.hero-callout');
  const availability = readyHeroes.length===1 ? `${actors.get(readyHeroes[0].actor).name} bereit`
    : readyHeroes.length>1 ? `${readyHeroes.length} bereit` : 'Rezepte';
  hero.dataset.ready = String(readyHeroes.length>0);
  hero.setAttribute('aria-label', `Helden · ${availability}`);
  setText(hero.querySelector('small'), availability);
  const remaining = orders.querySelector('.battle-tabs b');
  remaining.hidden = !player.reserve.length;
  setText(remaining, player.reserve.length);
  const context = orders.querySelector('.field-context');
  const selection = fieldContext(pending, piece, player, actors, game);
  context.hidden = !selection;
  updatePanel(context, selection);

  const sheet = orders.querySelector('.command-sheet');
  const pane = menuPane==='piece' && !piece ? null : menuPane;
  const title = sheetTitles[pane];
  const open = Boolean(title);
  const wasHidden = sheet.hidden;
  sheet.hidden = !open;
  orders.querySelector('.command-scrim').hidden = !open;
  for (const button of orders.querySelectorAll('[data-pane]')) button.setAttribute('aria-expanded', String(button.dataset.pane===pane));
  if (!open) return;

  const body = sheet.querySelector('.command-sheet-body');
  const footer = sheet.querySelector('.command-sheet-foot');
  if (sheet.dataset.pane !== pane) {
    sheet.dataset.pane = pane;
    body.replaceChildren();
    delete body.dataset.roster;
    sections.delete(body);
    body.scrollTop = 0;
  }
  if (wasHidden) body.scrollTop = 0;
  setText(sheet.querySelector('h2'), title);
  if (pane==='hero') {
    heroPanel(body, footer, report, player, actors, focusHero, locked);
    return;
  }
  footer.hidden = true;
  const markup = pane==='piece' ? detail(piece, game, actors)
    : pane==='oracle' ? oracle(game,player,level,catalog)
    : pane==='building' ? buildPanel(game,player,level,catalog)
    : pane==='smith' ? smith(player)
    : reservePanel(player,pending,actors);
  updatePanel(body, markup);
}
