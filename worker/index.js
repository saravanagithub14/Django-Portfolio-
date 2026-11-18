import { Container, getContainer } from '@cloudflare/containers';

// Worker vars and secrets the Django app reads (wrangler.jsonc, `wrangler secret put`)
const CONTAINER_ENV = [
  'SECRET_KEY', 'OPENAI_API_KEY', 'UPDATE_TOKEN', 'GITHUB_TOKEN',
  'BEHIND_CLOUDFLARE', 'EDGE_CACHE_SECONDS', 'SITE_URL', 'CHATBOT_PROVIDER',
  'R2_BUCKET', 'R2_ENDPOINT', 'R2_ACCESS_KEY_ID', 'R2_SECRET_ACCESS_KEY',
];

// Only what Django marks as shared: public pages (s-maxage) and hashed static files (immutable)
const EDGE_CACHEABLE = /\b(s-maxage|immutable)\b/;

export class Portfolio extends Container {
  defaultPort = 8080;
  sleepAfter = '15m';

  constructor(ctx, env) {
    super(ctx, env);
    this.envVars = Object.fromEntries(CONTAINER_ENV.filter((name) => env[name]).map((name) => [name, env[name]]));
  }
}

export default {
  async fetch(request, env, ctx) {
    // A Worker runs in front of Cloudflare's cache, so it has to use the cache itself. A hit never wakes the container.
    const cache = caches.default;
    if (request.method === 'GET') {
      const hit = await cache.match(request);
      if (hit) return hit;
    }

    const forwarded = new Request(request);
    forwarded.headers.set('X-Forwarded-Proto', new URL(request.url).protocol.replace(':', ''));
    const visitor = request.headers.get('CF-Connecting-IP');
    if (visitor) forwarded.headers.set('CF-Connecting-IP', visitor);

    // One named instance: it holds the models and the only writer of the SQLite file
    const response = await getContainer(env.PORTFOLIO).fetch(forwarded);

    if (request.method === 'GET' && response.ok && EDGE_CACHEABLE.test(response.headers.get('Cache-Control') ?? '')) {
      ctx.waitUntil(cache.put(request, response.clone()));
    }
    return response;
  },
};
