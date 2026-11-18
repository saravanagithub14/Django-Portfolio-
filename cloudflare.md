# Putting the portfolio behind Cloudflare

The app stays on the EC2 server, and a Cloudflare Tunnel connects it to the internet. Cloudflare provides HTTPS and serves static files and cached pages from its edge. The server needs no open web ports, so nginx and certbot are no longer needed. Replace `your-domain.com` throughout.

You need a domain whose DNS is managed by Cloudflare. The free Cloudflare plan covers everything here.

## Why not run it on Cloudflare itself

| Option | Problem |
|---|---|
| Workers / Pages | Python Workers only take pure-Python or WebAssembly-built packages. This app depends on `faiss-cpu` and `onnxruntime`, needs about 425MB of RAM, and writes to a local SQLite file. It would need a rewrite. |
| Containers | The app would run on the `basic` instance (1 GiB, 1/4 vCPU), but the disk resets every time a container sleeps or restarts, which loses admin edits and chat logs. It needs the Workers Paid plan: about $12/month if kept awake around the clock. |

## Part 1: Deploy the code

The server needs a branch that includes `portfolio/middleware.py`. Deploy it with `~/deploy.sh`, then add these to `~/portfolio/.env`, keeping the existing IP entries in `ALLOWED_HOSTS` for now:

```
ALLOWED_HOSTS=your-domain.com,www.your-domain.com,3.209.62.137,127.0.0.1,localhost
CSRF_TRUSTED_ORIGINS=https://your-domain.com,https://www.your-domain.com
SITE_URL=https://your-domain.com
```

Then run `sudo systemctl restart portfolio`.

## Part 2: Create the tunnel

1. In the Cloudflare dashboard, go to **Networking → Tunnels → Create a tunnel** and give it a name.
2. Choose Linux, then run the install command it shows on the server. `cloudflared` runs as its own service and restarts with the server.
3. Wait for the tunnel to connect, then select **Continue**.
4. On the tunnel's **Routes** tab, select **Add route → Published application**, choose your domain, and set **Service URL** to `http://localhost:8000`. Repeat for `www` if you use it.

Point the tunnel straight at gunicorn, not at nginx. nginx sets `X-Forwarded-Proto` to `http` on port 80, and the admin login would then fail its CSRF check. WhiteNoise serves the static files, so nginx isn't needed for those.

Check that `https://your-domain.com` loads and that you can log in at `/login/`.

## Part 3: Close the server to direct traffic

Do this before Part 4. `BEHIND_CLOUDFLARE` makes the chat rate limit trust `CF-Connecting-IP`, and anyone who could reach the server directly could forge that header.

1. In the EC2 security group, remove the inbound rules for ports 80 and 443. Keep SSH.
2. Stop nginx: `sudo systemctl disable --now nginx`.
3. Check that `curl -m 5 http://3.209.62.137` now times out.
4. Remove `3.209.62.137` from `ALLOWED_HOSTS` in `.env`.

## Part 4: Turn on the Cloudflare settings

Add to `.env`, then run `sudo systemctl restart portfolio`:

```
BEHIND_CLOUDFLARE=True
EDGE_CACHE_SECONDS=300
```

| Setting | What it does |
|---|---|
| `BEHIND_CLOUDFLARE` | Rate-limits chat by `CF-Connecting-IP` and marks the session and CSRF cookies as secure. |
| `EDGE_CACHE_SECONDS` | Lets Cloudflare serve public pages for this many seconds without asking Django. `0` or unset turns it off. |

**The trade-off with page caching:** admin edits can take up to `EDGE_CACHE_SECONDS` to appear on the public pages. To see one sooner, use **Purge Everything** in the dashboard's cache settings. V.E.R.A. isn't affected, because its index still updates from the save.

## Part 5: Dashboard settings

Cloudflare doesn't cache HTML by default, so `EDGE_CACHE_SECONDS` does nothing until this rule exists. Create it under **Caching → Cache Rules**:

- **Match:** Hostname equals `your-domain.com`, and URI Path doesn't start with `/admin` or `/chatbot`. Add `www` if you serve it.
- **Cache eligibility:** Eligible for cache
- **Edge TTL:** Use cache control-header if present, bypass cache if not
- **Browser TTL:** Respect origin

Browser TTL matters because Cloudflare otherwise applies the higher of its own value and the page's `max-age=0`, and browsers would keep old pages.

Other settings:

| Setting | Value | Why |
|---|---|---|
| Always Use HTTPS | On | The secure cookies only work over HTTPS. |
| Rocket Loader | Off | It delays scripts, including the one that applies the saved theme before first paint. |
| Email Address Obfuscation | Off | It's on by default and rewrites the `mailto:` links on the page. |
| Bot Fight Mode | Off if you call `/update_context` from scripts | It can challenge non-browser clients. |

## Part 6: Check it

```bash
# A public page: the second request should say cf-cache-status: HIT
curl -sI https://your-domain.com/bio/ | grep -iE 'cf-cache-status|cache-control'
curl -sI https://your-domain.com/bio/ | grep -iE 'cf-cache-status|cache-control'

# The admin must never be cached: expect no HIT and a no-cache Cache-Control
curl -sI https://your-domain.com/admin/login/ | grep -iE 'cf-cache-status|cache-control'

# The chat stream: lines should arrive one at a time, not all together at the end
curl -N -X POST https://your-domain.com/chatbot/api/chat/ -H 'Content-Type: application/json' \
  -H 'Accept: application/x-ndjson' -d '{"message":"what projects has he built?"}'
```

Then open the site, send a chat message, and check that `/health` reports `healthy`.

## Troubleshooting

| Symptom | Where to look |
|---|---|
| 400 Bad Request | The domain is missing from `ALLOWED_HOSTS`. |
| 403 CSRF on the admin login | The domain is missing from `CSRF_TRUSTED_ORIGINS`, or the tunnel points at nginx instead of `localhost:8000`. |
| Admin login loops back to the form | The site was opened over plain HTTP. Turn on Always Use HTTPS. |
| 502 or error 1033 | The tunnel can't reach the app: `sudo systemctl status portfolio cloudflared`. |
| Error 524 | The app sent nothing for 125 seconds. The widget's stream sends progress lines, so look for a stuck process: `sudo journalctl -u portfolio -n 50`. |
| `cf-cache-status: DYNAMIC` on public pages | The Cache Rule is missing or doesn't match, or `EDGE_CACHE_SECONDS` isn't set. |
| Everyone shares one chat rate limit | `BEHIND_CLOUDFLARE` isn't set. |

## Going back

Re-add ports 80 and 443 to the security group, run `sudo systemctl enable --now nginx`, remove `BEHIND_CLOUDFLARE` and `EDGE_CACHE_SECONDS` from `.env`, put the IP back in `ALLOWED_HOSTS`, and restart the service.
