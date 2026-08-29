"use strict";
const SHELL_CACHE = "dq7-guide-shell-v3";
const DATA_CACHE = "dq7-guide-data-v3";
const SHELL = ["/", "/index.html", "/styles.css", "/app.js", "/manifest.webmanifest", "/icons/guide-icon.svg"];
self.addEventListener("install", event => { event.waitUntil(caches.open(SHELL_CACHE).then(cache => cache.addAll(SHELL)).then(() => self.skipWaiting())); });
self.addEventListener("activate", event => { event.waitUntil(caches.keys().then(keys => Promise.all(keys.filter(key => ![SHELL_CACHE, DATA_CACHE].includes(key)).map(key => caches.delete(key)))).then(() => self.clients.claim())); });
self.addEventListener("fetch", event => {
  const request = event.request, url = new URL(request.url);
  if (request.method !== "GET" || url.origin !== self.location.origin) return;
  if (url.pathname === "/api/state-backup") return;
  if (url.pathname.startsWith("/api/")) {
    event.respondWith(fetch(request).then(response => { if (response.ok) caches.open(DATA_CACHE).then(cache => cache.put(request, response.clone())); return response; }).catch(async () => {
      const cached = await caches.match(request);
      if (!cached) return new Response(JSON.stringify({error: "Not available in offline cache"}), {status: 503, headers: {"Content-Type": "application/json"}});
      const headers = new Headers(cached.headers); headers.set("X-DQ7-Offline-Cache", "true");
      return new Response(await cached.blob(), {status: cached.status, statusText: cached.statusText, headers});
    }));
    return;
  }
  event.respondWith(fetch(request).then(response => { if (response.ok) caches.open(SHELL_CACHE).then(cache => cache.put(request, response.clone())); return response; }).catch(() => caches.match(request).then(cached => cached || caches.match("/index.html"))));
});
