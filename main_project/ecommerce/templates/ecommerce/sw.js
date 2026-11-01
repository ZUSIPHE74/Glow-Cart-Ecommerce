{% load static %}// GlowCart service worker: makes the site installable and keeps recently viewed
// pages and the shop's own assets available offline. Carts, checkout, payment and
// account pages always go to the network and are never cached.
const CACHE = 'glowcart-v1';
const OFFLINE_URL = '{% url "ecommerce:offline" %}';
const PRECACHE = [
    OFFLINE_URL,
    '{% static "ecommerce/icons/icon-192.png" %}',
];
const NEVER_CACHE = ['/cart', '/checkout', '/order', '/orders', '/payfast', '/login', '/logout',
    '/register', '/vendor', '/admin', '/messages', '/currency', '/invoice', '/api'];

self.addEventListener('install', (event) => {
    event.waitUntil(caches.open(CACHE).then((cache) => cache.addAll(PRECACHE)).then(() => self.skipWaiting()));
});

self.addEventListener('activate', (event) => {
    event.waitUntil(
        caches.keys()
            .then((keys) => Promise.all(keys.filter((key) => key !== CACHE).map((key) => caches.delete(key))))
            .then(() => self.clients.claim())
    );
});

self.addEventListener('fetch', (event) => {
    const request = event.request;
    const url = new URL(request.url);
    if (request.method !== 'GET' || url.origin !== location.origin) return;
    if (url.pathname.startsWith('/logout')) {
        // Forget pages cached while signed in, so a shared device shows nothing personal.
        event.waitUntil(caches.open(CACHE).then((cache) => cache.keys().then((requests) => Promise.all(
            requests.filter((cached) => {
                const path = new URL(cached.url).pathname;
                return !path.startsWith('/static/') && path !== OFFLINE_URL;
            }).map((cached) => cache.delete(cached))
        ))));
        return;
    }
    if (NEVER_CACHE.some((path) => url.pathname.startsWith(path))) return;

    if (request.mode === 'navigate') {
        // Pages: fresh from the network, the last copy when offline.
        event.respondWith(
            fetch(request)
                .then((response) => {
                    const copy = response.clone();
                    if (response.ok) caches.open(CACHE).then((cache) => cache.put(request, copy));
                    return response;
                })
                .catch(() => caches.match(request).then((cached) => cached || caches.match(OFFLINE_URL)))
        );
        return;
    }

    if (url.pathname.startsWith('/static/')) {
        // Static files have versioned names, so a cached copy is always right.
        event.respondWith(
            caches.match(request).then((cached) => cached || fetch(request).then((response) => {
                const copy = response.clone();
                if (response.ok) caches.open(CACHE).then((cache) => cache.put(request, copy));
                return response;
            }))
        );
    }
});
