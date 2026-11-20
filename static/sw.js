/**
 * Service Worker Oficial de JR ACCESORIOS - PWA (v2.1)
 * Diseñado para alta confiabilidad en Tablets, Móviles y Web.
 * 
 * Reglas clave:
 * 1. NUNCA cachear páginas dinámicas con sesión o tokens CSRF (evita "Error de conexión con el servidor").
 * 2. NUNCA cachear endpoints de API (/api/, /sales/nueva, /perfumeria/api/).
 * 3. En peticiones de API fallidas sin red, responder con JSON 503 limpio para evitar SyntaxError en cliente.
 * 4. Purgar cachés obsoletas automáticamente en cada actualización.
 */

const CACHE_VERSION = 'v2.1';
const CACHE_NAME = `jr-accesorios-pwa-${CACHE_VERSION}`;

// Recursos offline mínimos inmutables
const PRECACHE_ASSETS = [
    '/offline',
    '/static/manifest.json',
    '/static/favicon.ico',
    '/static/img/logojr.png',
    '/static/img/logojr_square.png',
    '/static/img/icons/icon-192x192.png',
    '/static/img/icons/icon-512x512.png',
    'https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600;700&family=Montserrat:wght@500;600;700;800;900&display=swap',
    'https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css',
    'https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js',
    'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css'
];

// Instalación: Precarga de recursos offline esenciales
self.addEventListener('install', (event) => {
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then((cache) => {
                return cache.addAll(PRECACHE_ASSETS).catch((err) => {
                    console.warn('[SW] Precaché parcial completado:', err);
                });
            })
            .then(() => self.skipWaiting())
    );
});

// Activación: Purga agresiva de cachés anteriores
self.addEventListener('activate', (event) => {
    event.waitUntil(
        caches.keys().then((cacheNames) => {
            return Promise.all(
                cacheNames.map((cache) => {
                    if (cache !== CACHE_NAME) {
                        console.log('[SW] Purgando caché obsoleta:', cache);
                        return caches.delete(cache);
                    }
                })
            );
        }).then(() => self.clients.claim())
    );
});

// Mensajería entre clientes y Service Worker
self.addEventListener('message', (event) => {
    if (event.data && event.data.type === 'SKIP_WAITING') {
        self.skipWaiting();
    }
    if (event.data && event.data.type === 'PURGE_CACHE') {
        caches.keys().then((names) => Promise.all(names.map(n => caches.delete(n))));
    }
});

// Estrategia de Fetch
self.addEventListener('fetch', (event) => {
    // 1. Ignorar métodos que no sean GET (como POST de cobros, arqueos, etc.)
    if (event.request.method !== 'GET') {
        return;
    }

    const url = new URL(event.request.url);

    // 2. Endpoints de API y peticiones dinámicas: NUNCA usar caché. Siempre Red directa.
    const isApiRequest = url.pathname.includes('/api/') || 
                         url.pathname.startsWith('/auth/') || 
                         url.pathname.includes('logout') || 
                         url.pathname.includes('/sales/nueva') ||
                         url.pathname.includes('/perfumeria/api/') ||
                         (event.request.headers.get('Accept') && event.request.headers.get('Accept').includes('application/json'));

    if (isApiRequest) {
        event.respondWith(
            fetch(event.request).catch(() => {
                // Si la red se cae durante una llamada fetch, retornar JSON 503 en lugar de HTML o NetworkError roto
                return new Response(JSON.stringify({
                    error: 'Sin conexión con el servidor. Por favor verifica tu red Wi-Fi o datos móviles.',
                    offline: true
                }), {
                    status: 503,
                    statusText: 'Service Unavailable',
                    headers: new Headers({ 'Content-Type': 'application/json' })
                });
            })
        );
        return;
    }

    // 3. Manejo de Navegación HTML (Páginas del POS, Catálogo, Vistas del Sistema)
    // ESTRATEGIA: Network First SIN cachear HTML con sesión o tokens CSRF vivos
    if (event.request.mode === 'navigate') {
        event.respondWith(
            fetch(event.request)
                .catch(async () => {
                    // Fallback exclusivo a pantalla offline sin servir HTML rancio con CSRF expirado
                    const offlinePage = await caches.match('/offline');
                    if (offlinePage) {
                        return offlinePage;
                    }
                    return new Response('Sin conexión con el servidor. Revisa tu conexión a internet.', {
                        status: 503,
                        statusText: 'Service Unavailable',
                        headers: new Headers({ 'Content-Type': 'text/plain; charset=utf-8' })
                    });
                })
        );
        return;
    }

    // 4. Recursos Estáticos Inmutables (/static/, fuentes, css, js, CDNs): Stale While Revalidate
    if (url.pathname.startsWith('/static/') || url.hostname.includes('cdn') || url.hostname.includes('fonts') || url.hostname.includes('cdnjs')) {
        event.respondWith(
            caches.match(event.request).then((cachedResponse) => {
                const fetchPromise = fetch(event.request)
                    .then((networkResponse) => {
                        if (networkResponse && networkResponse.status === 200) {
                            const responseClone = networkResponse.clone();
                            caches.open(CACHE_NAME).then((cache) => {
                                cache.put(event.request, responseClone);
                            });
                        }
                        return networkResponse;
                    })
                    .catch(() => {});

                return cachedResponse || fetchPromise;
            })
        );
        return;
    }
});
