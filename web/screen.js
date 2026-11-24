import { $ } from './presentation.js';

export const handheld = () => matchMedia('(pointer:coarse), (max-width: 810px)').matches;
let requested = false;
let installPrompt = null;

function standalone() {
  return navigator.standalone || matchMedia('(display-mode: fullscreen), (display-mode: standalone)').matches;
}

export function fullscreenText() {
  const button = $('fullscreen-button');
  const element = document.fullscreenElement || document.webkitFullscreenElement;
  button?.setAttribute('aria-pressed', String(Boolean(element || standalone())));
  button?.setAttribute('aria-label', element ? 'Vollbild verlassen' : 'Vollbild öffnen');
  button?.setAttribute('title', element ? 'Vollbild verlassen' : 'Vollbild öffnen');
}

export function enterFullscreen(force = false) {
  if ((!force && !handheld()) || standalone() || document.fullscreenElement || document.webkitFullscreenElement) return;
  const root = document.documentElement;
  const enter = root.requestFullscreen ?? root.webkitRequestFullscreen;
  if (!enter) {
    if (force) $('install-dialog').showModal();
    return;
  }
  try {
    const result = enter.call(root,{navigationUI:'hide'});
    Promise.resolve(result).then(() => { requested = true; fullscreenText(); })
      .catch(() => { if (force) $('install-dialog').showModal(); });
  } catch { if (force) $('install-dialog').showModal(); }
}

export function leaveFullscreen() {
  if (!requested) return;
  requested=false;
  const exit=document.exitFullscreen??document.webkitExitFullscreen;
  if (exit && (document.fullscreenElement || document.webkitFullscreenElement)) void Promise.resolve(exit.call(document)).catch(()=>{});
}

export function bindScreen() {
  document.addEventListener('fullscreenchange',fullscreenText);
  document.addEventListener('webkitfullscreenchange',fullscreenText);
  $('fullscreen-button').addEventListener('click',()=>{
    if (document.fullscreenElement || document.webkitFullscreenElement) {
      requested=true;
      leaveFullscreen();
    } else enterFullscreen(true);
  });
  window.addEventListener('beforeinstallprompt',event=>{
    event.preventDefault();
    installPrompt=event;
    $('install-app').hidden=false;
  });
  $('install-app').addEventListener('click',async ()=>{
    if (!installPrompt) return;
    await installPrompt.prompt();
    installPrompt=null;
    $('install-app').hidden=true;
    $('install-dialog').close();
  });
  if ('serviceWorker' in navigator && location.protocol==='https:') {
    void navigator.serviceWorker.register('/sw.js').catch(()=>{});
  }
  fullscreenText();
}
