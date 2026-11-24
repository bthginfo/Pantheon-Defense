const offlineCache = 'pantheon-offline-v4';
self.addEventListener('install', event => {
  event.waitUntil(caches.open(offlineCache).then(cache => cache.add('/offline.html')).then(() => self.skipWaiting()));
});
self.addEventListener('activate', event => {
  event.waitUntil(caches.keys().then(keys => Promise.all(keys
    .filter(key=>key.startsWith('pantheon-offline-')&&key!==offlineCache)
    .map(key=>caches.delete(key)))).then(()=>self.clients.claim()));
});
self.addEventListener('fetch', event => {
  if (event.request.mode === 'navigate' && new URL(event.request.url).origin === self.location.origin) {
    event.respondWith(fetch(event.request).catch(()=>caches.match('/offline.html')));
  }
});
