const music = new Audio();
music.loop = true;
music.preload = 'none';
music.volume = 0.27;
let muted = localStorage.getItem('pantheon-sound') !== 'on';
let currentTheme = '';
let lastImpact = 0;
const clips = new Map();

function play(id, volume) {
  if (muted) return;
  if (!clips.has(id)) clips.set(id, Array.from({length: 3}, () => new Audio(`/assets/audio/${id}.ogg`)));
  const voices = clips.get(id);
  const audio = voices.find(item => item.paused || item.ended) ?? voices.shift();
  if (!voices.includes(audio)) voices.push(audio);
  audio.volume = volume;
  audio.currentTime = 0;
  void audio.play().catch(() => {});
}

export function isMuted() { return muted; }

export function toggleSound() {
  muted = !muted;
  localStorage.setItem('pantheon-sound', muted ? 'off' : 'on');
  if (muted) {
    music.pause();
    for (const voices of clips.values()) for (const voice of voices) voice.pause();
  } else {
    play('place', 0.3);
    if (currentTheme) void music.play().catch(() => {});
  }
  return muted;
}

export function score(theme) {
  if (!theme) {
    music.pause();
    currentTheme = '';
    return;
  }
  if (currentTheme !== theme) {
    currentTheme = theme;
    music.src = `/assets/audio/${theme}.ogg`;
  }
  if (!muted) void music.play().catch(() => {});
}

export function battleSound(event) {
  if (event.kind === 'impact') {
    const now = performance.now();
    if (now - lastImpact < 125) return;
    lastImpact = now;
    play(['sun','frost','rally'].includes(event.actor) ? 'magic' : 'impact', 0.22);
  } else {
    const audio = {place:'place',merge:'merge',upgrade:'merge',cast:'cast',boss:'boss',wave:'wave',victory:'victory',leak:'impact'}[event.kind];
    if (audio) play(audio, audio === 'boss' ? 0.52 : 0.38);
  }
}
