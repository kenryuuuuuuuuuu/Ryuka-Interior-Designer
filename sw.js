const CACHE = 'ryuka-interior-pwa-20260814-pinchzoom';
const ASSETS = ['./', './index.html', './interior-white-model.html', './manifest.webmanifest', './icon.svg', './vendor/three.min.js', './generated/house-data.js'];

self.addEventListener('install', event => {
  event.waitUntil(caches.open(CACHE).then(cache => cache.addAll(ASSETS)));
  self.skipWaiting();
});
self.addEventListener('activate', event => {
  event.waitUntil(caches.keys().then(keys => Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)))));
  self.clients.claim();
});
self.addEventListener('fetch', event => {
  if (event.request.method !== 'GET') return;
  const url = new URL(event.request.url);
  const isAppSource = url.origin === self.location.origin
    && (event.request.mode === 'navigate' || url.pathname.endsWith('.html') || url.pathname.endsWith('.js'));

  if (isAppSource) {
    // アプリ本体（HTML/JS）はネットワーク優先。取れなければキャッシュ、それも無ければ内装白模型へフォールバック。
    event.respondWith(fetch(event.request).then(response => {
      if (response.ok) {
        const copy = response.clone();
        caches.open(CACHE).then(cache => cache.put(event.request, copy));
      }
      return response;
    }).catch(() => (
      caches.match(event.request)
        .then(hit => hit || (event.request.mode === 'navigate' ? caches.match('./interior-white-model.html') : Response.error()))
    )));
    return;
  }

  // それ以外（ベンダーJS等）はキャッシュ優先。
  event.respondWith(caches.match(event.request).then(hit => hit || fetch(event.request).then(response => {
    if (response.ok && new URL(event.request.url).origin === self.location.origin) {
      const copy = response.clone();
      caches.open(CACHE).then(cache => cache.put(event.request, copy));
    }
    return response;
  }).catch(() => event.request.mode === 'navigate' ? caches.match('./interior-white-model.html') : Response.error())));
});
