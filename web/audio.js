let muted = localStorage.getItem('pantheon-sound') === 'off';
let theme = '';
let context;
let output;
let soundtrack;
let preparing = '';
let musicError = false;
let lastImpact = -Infinity;
let lastRecruit = -Infinity;
const buffers = new Map();

function soundChanged() {
  window.dispatchEvent(new Event('pantheon-sound'));
}

function buffer(id) {
  if (!buffers.has(id)) {
    buffers.set(id, (async () => {
      const response = await fetch(`/assets/audio/${id}.mp3`);
      if (!response.ok) throw new Error(`Audio ${id} returned ${response.status}`);
      return context.decodeAudioData(await response.arrayBuffer());
    })().catch(error => {
      buffers.delete(id);
      throw error;
    }));
  }
  return buffers.get(id);
}

function start(buffer, volume, loop = false) {
  const level = context.createGain();
  const source = context.createBufferSource();
  source.buffer = buffer;
  source.loop = loop;
  level.gain.value = volume;
  source.connect(level);
  level.connect(output);
  source.onended = () => { source.disconnect(); level.disconnect(); };
  source.start();
  return source;
}

async function startScore() {
  if (!theme || muted || context?.state !== 'running' || soundtrack || preparing === theme) return;
  const requested = theme;
  preparing = requested;
  musicError = false;
  soundChanged();
  try {
    const track = await buffer(requested);
    if (theme !== requested || muted || context.state !== 'running' || soundtrack) return;
    soundtrack = start(track, 0.58, true);
  } catch (error) {
    if (theme === requested) musicError = true;
    console.warn('Pantheon music:', error.message);
  } finally {
    if (preparing === requested) preparing = '';
    soundChanged();
  }
}

async function play(id, volume) {
  if (muted || context?.state !== 'running') return;
  const playingTheme = theme;
  try {
    const clip = await buffer(id);
    if (!muted && context.state === 'running' && theme === playingTheme) start(clip, volume);
  } catch (error) {
    console.warn('Pantheon sound:', error.message);
  }
}

export function soundState() {
  if (muted) return 'off';
  if (!theme) return 'on';
  if (soundtrack && context?.state === 'running') return 'playing';
  if (musicError) return 'retry';
  if (context?.state === 'running') return 'loading';
  return 'tap';
}

// Call directly from a user interaction, before requests or fullscreen consume the gesture.
export function unlockSound() {
  if (muted) return;
  try {
    if (!context) {
      const AudioEngine = window.AudioContext ?? window.webkitAudioContext;
      context = new AudioEngine();
      output = context.createGain();
      output.connect(context.destination);
      context.addEventListener('statechange', () => {
        soundChanged();
        void startScore();
      });
    }
    if (context.state === 'running') void startScore();
    else void context.resume().then(startScore, () => { musicError = true; soundChanged(); });
  } catch (error) {
    musicError = true;
    soundChanged();
  }
}

export function toggleSound() {
  const needsGesture = ['tap', 'retry'].includes(soundState());
  if (!needsGesture) {
    muted = !muted;
    localStorage.setItem('pantheon-sound', muted ? 'off' : 'on');
    if (output) output.gain.value = muted ? 0 : 1;
  }
  if (muted) {
    soundtrack?.stop();
    soundtrack = null;
  } else {
    unlockSound();
    if (!theme) void play('place', 0.36);
  }
  soundChanged();
}

export function score(next) {
  if (theme === next) return;
  soundtrack?.stop();
  soundtrack = null;
  theme = next;
  musicError = false;
  soundChanged();
  void startScore();
}

export function battleSound(event) {
  if (['draw', 'reserve', 'stack'].includes(event.kind)) {
    const now = performance.now();
    if (now - lastRecruit < 100) return;
    lastRecruit = now;
    void play(event.kind === 'draw' ? 'place' : event.kind, 0.38);
    return;
  }
  if (event.kind === 'impact') {
    const now = performance.now();
    if (now - lastImpact < 125) return;
    lastImpact = now;
    void play(['sun', 'frost', 'rally'].includes(event.actor) ? 'magic' : 'impact', 0.22);
    return;
  }
  const audio = {place:'place',oracle_hit:'oracle',bounty:'wave',
    ritual:'ritual',merge:'merge',upgrade:'merge',cast:'cast',boss:'boss',boss_windup:'wave',
    boss_impact:'boss',wave:'wave',victory:'victory',leak:'impact'}[event.kind];
  if (audio) void play(audio, audio === 'boss' ? 0.52 : 0.38);
}
