// MHF Diario - guarda el ultimo diario para poder leerlo sin cobertura
const CACHE = "mhf-diario-v1";
const BASE = self.registration.scope;

self.addEventListener("install", e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll([BASE, BASE + "index.html"])
    .catch(() => null)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", e => {
  e.waitUntil(caches.keys().then(ks =>
    Promise.all(ks.filter(k => k !== CACHE).map(k => caches.delete(k)))
  ).then(() => self.clients.claim()));
});

// Primero la red (para tener el diario de hoy); si no hay, lo guardado.
self.addEventListener("fetch", e => {
  if (e.request.method !== "GET") return;
  e.respondWith(
    fetch(e.request).then(r => {
      const copia = r.clone();
      caches.open(CACHE).then(c => c.put(e.request, copia)).catch(() => {});
      return r;
    }).catch(() => caches.match(e.request).then(r => r || caches.match(BASE)))
  );
});
