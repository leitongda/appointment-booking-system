// 最小化 Service Worker -- 仅满足 Chrome PWA 安装条件
// 不进行离线缓存，所有请求直接透传
self.addEventListener('fetch', (event) => {
  event.respondWith(fetch(event.request));
});

self.addEventListener('install', () => {
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(self.clients.claim());
});
