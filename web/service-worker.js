"use strict";
const SHELL_CACHE = "dq7-guide-shell-v5";
const DATA_CACHE = "dq7-guide-data-v5";
const SHELL = ["/", "/index.html", "/styles.css", "/app.js", "/manifest.webmanifest", "/icons/guide-icon.svg"];
self.addEventListener("install", event => { event.waitUntil(caches.open(SHELL_CACHE).then(cache => cache.addAll(SHELL)).then(() => self.skipWaiting())); });
self.addEventListener("activate", event => { event.waitUntil(caches.keys().then(keys => Promise.all(keys.filter(key => ![SHELL_CACHE, DATA_CACHE].includes(key)).map(key => caches.delete(key)))).then(() => self.clients.claim())); });
self.addEventListener("fetch", event => {
  const request = event.request, url = new URL(request.url);
  if (request.method !== "GET" || url.origin !== self.location.origin) return;
  if (url.pathname === "/api/state-backup") return;
  if (url.pathname.startsWith("/api/")) {
    // Pairing is an authorization boundary. Cache matching does not partition on
    // the private header, so paired responses must never enter or leave a cache.
    if (request.headers.has("X-DQ7-Pair")) {
      event.respondWith(fetch(request));
      return;
    }
    event.respondWith(fetch(request).then(async response => {
      if (response.headers.get("X-DQ7-Pairing-Required") === "true") {
        await caches.delete(DATA_CACHE);
        return response;
      }
      if (response.ok) await caches.open(DATA_CACHE).then(cache => cache.put(request, response.clone()));
      return response;
    }).catch(async () => {
      const cached = await caches.match(request);
      if (!cached) return new Response(JSON.stringify({error: "Not available in offline cache"}), {status: 503, headers: {"Content-Type": "application/json"}});
      const headers = new Headers(cached.headers); headers.set("X-DQ7-Offline-Cache", "true");
      return new Response(await cached.blob(), {status: cached.status, statusText: cached.statusText, headers});
    }));
    return;
  }
  event.respondWith(fetch(request).then(response => { if (response.ok) caches.open(SHELL_CACHE).then(cache => cache.put(request, response.clone())); return response; }).catch(() => caches.match(request).then(cached => cached || caches.match("/index.html"))));
});
