import { masteryPayment, materials, waveMaterials } from '../shared/progression.js';

export const $ = id => document.getElementById(id);
export const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({
  '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;',
}[c]));
export const portrait = (id, extra = '') => `<img class="portrait ${extra}" src="/assets/portraits/${id}.png" alt="" loading="lazy">`;
export const numeral = value => ['', 'I', 'II', 'III', 'IV', 'V'][value] ?? value;
export const rarities = ['', 'Common', 'Uncommon', 'Rare', 'Epic', 'Legendary'];
export const number = value => new Intl.NumberFormat('de-DE').format(value);
export const price = (rank, tier) => 55 + rank * 32 + (tier - 1) * 18;
export function pieceLabel(entry, piece, circuit) {
  const title = circuit ? ({ troop: rarities[piece.tier], hero: 'Held', building: 'Gebäude' })[entry.kind]
    : `Rang ${numeral(piece.tier)}`;
  const count = circuit && piece.stack > 1 ? `, ${piece.stack} Einheiten` : '';
  return `${entry.name}, ${title}, Stufe ${piece.rank}${count}`;
}
export const groupNames = { troop: 'Einheiten', building: 'Gebäude', hero: 'Helden' };
export const themeHeroes = { aegean: ['thekla','Thekla','Phalanx-Hauptfrau'], rome: ['marcus','Marcus','Kastellmeister'], japan: ['akari','Akari','Schreinwächterin'] };
export const colorThemes = { aegean: '#dba864', rome: '#e5785f', japan: '#8dccb3' };

export function spoilsText(spoils) {
  return waveMaterials.filter(key => spoils?.[key] > 0)
    .map(key => `+${number(spoils[key])} ${quantityLabel(key, spoils[key])}`).join(' · ');
}

export function quantityLabel(material, amount) {
  if (amount === 1 && material === 'training') return 'Trainingsmarke';
  if (amount === 1 && material === 'blueprints') return 'Bauplan';
  if (amount === 1 && material === 'cores') return 'Urkern';
  return materials[material];
}

export function signCard(sign, account) {
  const rank = account.fieldSigns?.[sign.id] ?? 0;
  const equipped = account.fieldSign === sign.id;
  const material = rank === 0 ? 'runedust' : 'cores';
  const price = rank === 0 ? sign.forge : sign.awaken;
  const effect = index => sign.gold[index] ? `+${sign.gold[index]} Startgold`
    : sign.essence[index] ? `+${sign.essence[index]} Startessenz`
      : `+${Math.round(sign.boss_damage[index] * 100)} % Schaden gegen Bosse`;
  return `<article class="sign-card ${equipped ? 'equipped' : ''}">
    <h3>${esc(sign.name)}</h3><p>${effect(rank === 2 ? 1 : 0)}
    ${rank === 1 ? `<small>Nach dem Erwecken · ${effect(1)}</small>` : ''}</p>
    <div class="sign-actions">
      ${rank < 2 ? `<button class="minibutton" data-sign="${sign.id}" data-sign-action="forge"
        ${account.materials?.[material] >= price ? '' : 'disabled'}>${rank === 0 ? 'Schmieden' : 'Erwecken'} · ${price} ${quantityLabel(material, price)}</button>` : ''}
      ${rank ? `<button class="minibutton" data-sign="${sign.id}" data-sign-action="equip"
        aria-pressed="${equipped}">${equipped ? 'Ablegen' : 'Ausrüsten'}</button>` : ''}
    </div></article>`;
}

export function actorCard(actor, level, mastery, account) {
  const locked = actor.unlock > level;
  const payment = mastery < 3 ? masteryPayment(actor.kind, mastery, account?.materials, account?.seals) : null;
  return `<article class="actor-card ${locked ? 'locked' : ''}" data-rarity="${actor.rarity??0}" style="--actor-color:${actor.color}">
    <div class="card-image">${portrait(actor.id)}<span>${locked ? `Ab Profilstufe ${actor.unlock}` : actor.kind==='troop'?rarities[actor.rarity]:esc(actor.role)}</span></div>
    <div class="card-body"><h3>${esc(actor.name)}</h3><p>${esc(actor.note)}</p>
      ${!locked ? `<small>${actor.damage} Grundschaden · ${actor.range.toLocaleString('de-DE')} Reichweite</small>` : ''}
      ${account && !locked ? `<div class="mastery-row"><span>Meisterschaft ${mastery}/3
        ${mastery ? `<small>+${mastery*7} % Schaden</small>` : ''}</span>
        <button class="minibutton" data-mastery="${actor.id}" ${payment?.affordable ? '' : 'disabled'}>
          ${payment ? `Aufwerten · ${payment.amount} ${quantityLabel(payment.material, payment.amount)}` : 'Höchste Meisterschaft'}</button></div>` : ''}
    </div>
  </article>`;
}

export function historyRow(result, catalog) {
  const theme = catalog.themes.find(item => item.id === result.theme);
  const challenge = catalog.challenges.find(item => item.id === result.challenge);
  const difficulty = catalog.difficulties.find(item => item.id === (result.difficulty ?? 'normal'));
  const loot = spoilsText(result.spoils);
  return `<li>
    <strong>${esc(theme?.map)} <small>${esc(challenge?.name)} · ${esc(difficulty?.name)}</small></strong>
    <span>${result.duo ? 'Koop' : 'Solo'}</span>
    <span>${result.won ? 'Sieg' : `Welle ${result.wave}`}</span>
    <b>+${result.xp} EP${result.seals ? `<small>+${result.seals} Siegel</small>` : ''}${loot ? `<small>${loot}</small>` : ''}</b>
  </li>`;
}
