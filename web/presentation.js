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
export const shortNames = { aegean: 'Ägäis', rome: 'Zitadelle', japan: 'Nebelpass' };
export const colorThemes = { aegean: '#dba864', rome: '#e5785f', japan: '#8dccb3' };

export function actorCard(actor, level) {
  const locked = actor.unlock > level;
  return `<article class="actor-card ${locked ? 'locked' : ''}" style="--actor-color:${actor.color}">
    <div class="card-image">${portrait(actor.id)}<span>${locked ? `Profilstufe ${actor.unlock}` : esc(actor.role)}</span></div>
    <div class="card-body"><h3>${esc(actor.name)}</h3><p>${esc(actor.note)}</p>
      ${!locked ? `<small>${actor.damage} Schaden · ${actor.range.toLocaleString('de-DE')} Reichweite</small>` : ''}
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
    <b>+${result.xp} EP</b>
  </li>`;
}
