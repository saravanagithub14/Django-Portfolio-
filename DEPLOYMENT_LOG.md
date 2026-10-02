# EC2 deployment log

A record of the steps actually taken to deploy the portfolio to AWS EC2 on 2026-10-02. For the general how-to guide, see `aws.md`; this file records what was done on this particular server, including the places where it differed from that guide.

No secrets are recorded here. API keys, `SECRET_KEY`, `UPDATE_TOKEN` and the admin password live only in `~/portfolio/.env` and the database on the server.

## Result

| Item | Value |
|---|---|
| Live URL | http://3.209.62.137 |
| Admin | http://3.209.62.137/login/ (redirects to `/admin/`) |
| Health check | http://3.209.62.137/health |
| Server OS | Ubuntu 26.04 (ships Python 3.14) |
| Memory | 908 MB RAM + 2 GB swap |
| App Python | 3.12, installed with `uv` |
| Branch deployed | `cleanup-structure` |
| Process | gunicorn, 1 worker, systemd service `portfolio` |
| Web server | nginx on port 80 (no HTTPS yet) |
| Live database | `/home/ubuntu/data/db.sqlite3` |
| Backups | `/home/ubuntu/backups/`, daily at 03:00, kept 14 days |

## Step 1: Code changes for EC2 (on the laptop)

Done before touching the server (commit `568b538`, "Support EC2 deployment: SQLITE_PATH, CSRF origins, proxy HTTPS"):

1. `portfolio_hub/settings.py`
   - `SQLITE_PATH` env var chooses the database file, so the live database can sit outside the git checkout and `git pull` never overwrites admin edits. Empty or unset falls back to `db.sqlite3` in the project.
   - `CSRF_TRUSTED_ORIGINS` env var (comma-separated) is appended to the built-in list. Empty values are ignored.
   - `SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')`, so Django trusts nginx's HTTPS header once certbot is added.
2. `portfolio/tests/test_deploy_settings.py` tests all three, including an admin login over HTTPS through a proxy.
3. `.env` was untracked earlier (commit `45f19b8`), so server secrets never go to git.
4. Tests passed, then the branch was pushed to GitHub.

## Step 2: Connect to the server

The instance was launched in the AWS console with ports 22, 80 and 443 open. SSH from Windows with the key pair:

```bash
ssh -i path/to/key.pem ubuntu@3.209.62.137
```

Problem found: SSH timed out intermittently. The laptop's VPN (Cloudflare WARP style, `104.28.x.x`) keeps changing the outgoing IP, while the security group allows SSH from a single IP. Workaround used: retry the connection, and run long jobs on the server with `nohup` so a dropped connection doesn't kill them. Permanent fix: pause the VPN while using SSH, or widen the SSH rule to `104.28.0.0/16`.

## Step 3: System setup (stage 1 script)

Run on the server with `nohup bash ec2_stage1.sh`:

```bash
# Packages
sudo apt-get update -qq
sudo apt-get install -y -qq nginx git sqlite3 curl

# 2 GB swap: the chatbot models need ~375 MB and the box has only 908 MB
sudo fallocate -l 2G /swapfile && sudo chmod 600 /swapfile
sudo mkswap /swapfile && sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab

# Python 3.12 via uv (Ubuntu 26.04 only has 3.14, which some packages don't support yet)
curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="$HOME/.local/bin:$PATH"
uv python install 3.12
```

Difference from `aws.md`: the guide assumes Ubuntu 24.04 with system Python 3.12 and `python3 -m venv`. This server came with 26.04 and Python 3.14, so `uv` was used to install 3.12 and create the virtualenv.

## Step 4: Get the code (deploy key)

Problem found: cloning over HTTPS failed because the repository is private.

Fix: a read-only deploy key.

```bash
# On the server
ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519 -N "" -C "portfolio-ec2"
cat ~/.ssh/id_ed25519.pub
```

The public key was added on GitHub under the repository's **Settings → Deploy keys** (read-only, write access unchecked). Then:

```bash
ssh-keyscan github.com >> ~/.ssh/known_hosts
git clone --branch cleanup-structure git@github.com:saravanagithub14/Django-Portfolio-.git ~/portfolio
```

## Step 5: Production `.env`

The file was prepared on the laptop, copied to the server with `scp`, moved to `~/portfolio/.env` and locked down with `chmod 600`. Its values were never printed or committed.

| Key | Value |
|---|---|
| `DEBUG` | `False` |
| `SECRET_KEY` | new random value generated for the server |
| `ALLOWED_HOSTS` | `3.209.62.137,127.0.0.1,localhost` |
| `SQLITE_PATH` | `/home/ubuntu/data/db.sqlite3` |
| `OPENAI_API_KEY`, `GROQ_API_KEY`, `GROQ_MODEL` | copied from the local `.env` |
| `CHATBOT_PROVIDER` | `openai` |
| `UPDATE_TOKEN` | new random value generated for the server |
| `GITHUB_USERNAME` | `saravanagithub14` |

## Step 6: Install and build (stage 2 script)

Run on the server with `nohup bash ec2_deploy.sh`:

```bash
cd ~/portfolio

# Virtualenv and dependencies
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python -r requirements.txt

# Live database outside the repo (copied once, never overwritten afterwards)
mkdir -p ~/data ~/backups
[ -f ~/data/db.sqlite3 ] || cp db.sqlite3 ~/data/db.sqlite3

# Build steps (same as build.sh)
.venv/bin/python manage.py collectstatic --noinput
.venv/bin/python manage.py migrate --noinput
.venv/bin/python manage.py build_rag_index     # downloads the ONNX models, builds faiss_index/
.venv/bin/python manage.py check --deploy
```

## Step 7: gunicorn as a systemd service

`/etc/systemd/system/portfolio.service`:

```ini
[Unit]
Description=Saravana portfolio (gunicorn)
After=network.target

[Service]
User=ubuntu
Group=www-data
WorkingDirectory=/home/ubuntu/portfolio
ExecStart=/home/ubuntu/portfolio/.venv/bin/gunicorn portfolio_hub.wsgi:application --workers 1 --timeout 120 --bind 127.0.0.1:8000
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable portfolio
sudo systemctl restart portfolio
```

One worker because of the 908 MB of RAM. `--timeout 120` covers the first chat request after a restart, which loads the models.

## Step 8: nginx

`/etc/nginx/sites-available/portfolio`:

```nginx
server {
    listen 80 default_server;
    server_name 3.209.62.137 _;
    client_max_body_size 10M;

    location /static/ {
        alias /home/ubuntu/portfolio/staticfiles/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 120s;
    }
}
```

```bash
sudo ln -sf /etc/nginx/sites-available/portfolio /etc/nginx/sites-enabled/portfolio
sudo rm -f /etc/nginx/sites-enabled/default      # removes the "Welcome to nginx" page
sudo chmod 755 /home/ubuntu                      # lets nginx read staticfiles/
sudo nginx -t && sudo systemctl reload nginx
```

## Step 9: Update script

`~/deploy.sh` on the server:

```bash
#!/usr/bin/env bash
# Pull the latest code and redeploy. Usage: ~/deploy.sh
set -euo pipefail
export PATH="$HOME/.local/bin:$PATH"
cd ~/portfolio
git pull --ff-only
uv pip install -q --python .venv/bin/python -r requirements.txt
.venv/bin/python manage.py collectstatic --noinput | tail -1
.venv/bin/python manage.py migrate --noinput | tail -1
.venv/bin/python manage.py build_rag_index 2>&1 | grep -v "it/s" | tail -1
sudo systemctl restart portfolio
echo "Deployed $(git rev-parse --short HEAD)"
```

## Step 10: Daily database backup

Problem found: the deploy script stopped at `crontab -l`, which exits with an error when the user has no crontab yet (`set -e` aborts). A second attempt to add the cron line inline from PowerShell failed because PowerShell stripped the quotes.

Fix: put the backup in its own script, `~/backup_db.sh`:

```bash
#!/usr/bin/env bash
# Daily SQLite backup of the live database; keeps 14 days. Run by cron at 03:00.
set -euo pipefail
mkdir -p /home/ubuntu/backups
sqlite3 /home/ubuntu/data/db.sqlite3 ".backup /home/ubuntu/backups/db-$(date +%F).sqlite3"
find /home/ubuntu/backups -name 'db-*.sqlite3' -mtime +14 -delete
```

```bash
chmod +x ~/backup_db.sh
echo '0 3 * * * /home/ubuntu/backup_db.sh' | crontab -
~/backup_db.sh && ls ~/backups      # tested once by hand
```

## Step 11: Verification

On the server:

- `/`, `/experience.html` and `/projects/` returned 200, `/login/` returned 302 (redirect to `/admin/`), `/health` returned 200.
- `systemctl is-active portfolio` reported `active`.

From the internet:

| Check | Result |
|---|---|
| All pages | 200, in 0.6 to 1.1 s |
| Static CSS | `/static/css/style.63b116414c2b.css` returned 200 with `Cache-Control: max-age=31536000` |
| Chatbot (`POST /chatbot/api/chat/`) | Correct answer from OpenAI ("I currently work as a Gen AI Engineer at Blackbox Learning in Trivandrum…") |
| `/health` | `healthy`, provider `openai`, 136 chunks, index fresh, 424 MB RSS |
| Admin login form | A deliberately wrong password returned "Please enter the correct username and password" (so no CSRF error) |
| Backup | Ran by hand and produced a file in `~/backups/` |

## Day-to-day operations

| Task | Command |
|---|---|
| Deploy an update | Push to GitHub, SSH in, run `~/deploy.sh` |
| App logs | `sudo journalctl -u portfolio -f` |
| nginx errors | `sudo tail -f /var/log/nginx/error.log` |
| Restart the app | `sudo systemctl restart portfolio` |
| Change a key | Edit `~/portfolio/.env`, then `sudo systemctl restart portfolio` |
| Restore a backup | `sudo systemctl stop portfolio && cp ~/backups/db-YYYY-MM-DD.sqlite3 ~/data/db.sqlite3 && sudo systemctl start portfolio` |

The live content is now the server's database. Edit it through `/admin/`; changes to the local `db.sqlite3` don't reach the live site.

## Still to do

1. **HTTPS.** Point a domain's A record at the IP, add the domain to `ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS` (`https://your-domain.com`) in `.env`, then run certbot (`aws.md` Part 7). Until then the admin password travels over plain HTTP.
2. **Elastic IP.** Make sure `3.209.62.137` is an Elastic IP, or the address changes when the instance is stopped and started.
3. **Switch to `main`.** After merging `update-site-content-and-admin-password` and `cleanup-structure`, run `cd ~/portfolio && git checkout main` once on the server.
4. **Rotate leaked keys.** The old Groq key and GitHub token are in the git history. Revoke them, then put the new Groq key in `~/portfolio/.env` and restart the service.
5. **SSH access.** Widen the SSH rule to `104.28.0.0/16` or pause the VPN when connecting.
