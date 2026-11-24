export const $ = id => document.getElementById(id);
export const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({
  '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;',
}[c]));
export const portrait = (id, extra = '') => `<img class="portrait ${extra}" src="/assets/portraits/${id}.png" alt="" loading="lazy">`;
export const numeral = value => ['', 'I', 'II', 'III', 'IV'][value] ?? value;
export const number = value => new Intl.NumberFormat('de-DE').format(value);
export const price = (rank, tier) => 55 + rank * 32 + (tier - 1) * 18;
export const pieceLabel = (entry, piece) => `${entry.name}, Rang ${numeral(piece.tier)}, Stufe ${piece.rank}`;
export const groupNames = { troop: 'Truppen', building: 'Gebäude', hero: 'Helden' };
export const themeHeroes = { aegean: ['thekla','Thekla','Phalanx-Hauptfrau'], rome: ['marcus','Marcus','Kastellmeister'], japan: ['akari','Akari','Schreinwächterin'] };
export const colorThemes = { aegean: '#dba864', rome: '#e5785f', japan: '#8dccb3' };

export function actorCard(actor, level, mastery, seals, signedIn) {
  const locked = actor.unlock > level;
  return `<article class="actor-card ${locked ? 'locked' : ''}" style="--actor-color:${actor.color}">
    <div class="card-image">${portrait(actor.id)}<span>${locked ? `Profilstufe ${actor.unlock}` : esc(actor.role)}</span></div>
    <div class="card-body"><h3>${esc(actor.name)}</h3><p>${esc(actor.note)}</p>
      ${!locked ? `<small>${actor.damage} Schaden · ${actor.range.toLocaleString('de-DE')} Reichweite</small>` : ''}
      ${signedIn && !locked ? `<div class="mastery-row"><span>Meisterschaft ${mastery}/3
        ${mastery ? `<small>+${mastery*7} % Schaden</small>` : ''}</span>
        <button class="minibutton" data-mastery="${actor.id}" ${mastery===3 || seals < mastery+1 ? 'disabled' : ''}>
          ${mastery===3 ? 'Vollendet' : `${mastery+1} Siegel einsetzen`}</button></div>` : ''}
    </div>
  </article>`;
}

export function historyRow(result, catalog) {
  const theme = catalog.themes.find(item => item.id === result.theme);
  const challenge = catalog.challenges.find(item => item.id === result.challenge);
  return `<li>
    <strong>${esc(theme?.map)} <small>${esc(challenge?.name)}</small></strong>
    <span>${result.duo ? 'Koop' : 'Solo'}</span>
    <span>${result.won ? 'Sieg' : `Welle ${result.wave}`}</span>
    <b>+${result.xp} EP${result.seals ? `<small>+${result.seals} Siegel</small>` : ''}</b>
  </li>`;
}
