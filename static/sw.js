const CACHE = 'maya-v1';
const STATIC = ['/static/style.css', '/static/app.js'];

self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(STATIC)));
  self.skipWaiting();
});

self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)))
    )
  );
  self.clients.claim();
});

// Network-first: serve live content, fall back to cache if offline
self.addEventListener('fetch', e => {
  if (e.request.method !== 'GET') return;
  e.respondWith(
    fetch(e.request)
      .then(res => {
        if (res.ok && e.request.url.includes('/static/')) {
          const copy = res.clone();
          caches.open(CACHE).then(c => c.put(e.request, copy));
        }
        return res;
      })
      .catch(() => caches.match(e.request))
  );
});

// Push notification received
self.addEventListener('push', e => {
  if (!e.data) return;
  let data = {};
  try { data = e.data.json(); } catch { data = { title: 'Maya Admin', body: e.data.text() }; }

  e.waitUntil(
    self.registration.showNotification(data.title || 'Maya Admin', {
      body:  data.body  || '',
      icon:  '/static/icons/icon-192.png',
      badge: '/static/icons/icon-192.png',
      tag:   data.tag   || 'maya-admin',
      data:  { url: data.url || '/admin/app' },
    })
  );
});

// Notification tapped — open or focus the admin app
self.addEventListener('notificationclick', e => {
  e.notification.close();
  const url = e.notification.data?.url || '/admin/app';
  e.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true }).then(list => {
      for (const c of list) {
        if (c.url.includes('/admin/app') && 'focus' in c) return c.focus();
      }
      if (clients.openWindow) return clients.openWindow(url);
    })
  );
});
