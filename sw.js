const STORE_NAME = 'lottery-stats-v27';
const FILES = [
  './',
  './index.html',
  './draws.json',
  './manifest.json',
  './icons/icon-192.png',
  './icons/icon-512.png',
  './icons/icon-maskable.png'
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(STORE_NAME)
      .then((store) => store.addAll(FILES))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(
        keys.filter((key) => key !== STORE_NAME).map((key) => caches.delete(key))
      ))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (event) => {
  if (event.request.method !== 'GET') return;

  const address = new URL(event.request.url);

  // Requests to other websites (for example the GoatCounter script and its count)
  // go straight to the internet: a saved count would never be counted.
  if (address.origin !== self.location.origin) return;

  // draws.json changes often -- ask the internet first, so a start with a live
  // connection always shows today's data instead of waiting for the next
  // start (iOS can not get new data in the background).
  // Use the saved copy when the request fails or gives an error.
  if (address.pathname.endsWith('/draws.json')) {
    event.respondWith(
      fetch(event.request)
        .then((answer) => {
          if (!answer.ok) throw new Error(`HTTP ${answer.status}`);
          const copy = answer.clone();
          caches.open(STORE_NAME).then((store) => store.put(event.request, copy));
          return answer;
        })
        .catch(() => caches.match(event.request))
    );
    return;
  }

  // Everything else: show the saved copy at once,
  // and get a new copy in the background for next time.
  event.respondWith(
    caches.match(event.request).then((saved) => {
      const online = fetch(event.request)
        .then((answer) => {
          if (answer && answer.ok) {
            const copy = answer.clone();
            caches.open(STORE_NAME).then((store) => store.put(event.request, copy));
          }
          return answer;
        })
        .catch(() => saved);
      return saved || online;
    })
  );
});
