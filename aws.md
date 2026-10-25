# Deploying the portfolio on AWS EC2

A single Ubuntu server running the Django app with gunicorn behind nginx, with HTTPS from Let's Encrypt. Replace `your-domain.com` and `<ELASTIC_IP>` with your own values throughout.

Unlike Render, EC2 keeps its disk, so edits made in `/admin/` on the live site survive deploys. That only holds if the live database lives outside the git checkout (Part 0 and Part 3).

## Part 0: Code support (done)

The settings in `portfolio_hub/settings.py` already handle EC2; you only set the values in `.env` (Part 4).

1. **`SQLITE_PATH`** sets where the database lives. On EC2 it points to `/home/ubuntu/data/db.sqlite3`, outside the git checkout, so `git pull` never overwrites admin edits with the committed `db.sqlite3`. Unset or empty means `db.sqlite3` in the project folder, as in development and on Render.
2. **`CSRF_TRUSTED_ORIGINS`** (comma-separated) adds your domain's `https://` origins, and `SECURE_PROXY_SSL_HEADER` trusts nginx's `X-Forwarded-Proto` header. Together they let the admin login work over HTTPS. Without them it fails with "403 CSRF verification failed".

`portfolio/tests/test_deploy_settings.py` covers both, including an admin login over HTTPS through a proxy.

## Part 1: Launch the instance (AWS console)

1. **EC2 → Launch instance**
   - **Name:** `portfolio`
   - **Image:** Ubuntu Server 24.04 LTS (ships Python 3.12, the version used in development).
   - **Instance type:** `t3.small` (2 GB RAM, about $15/month) is recommended. `t3.micro` (1 GB, free tier) works with swap and one gunicorn worker. The chatbot's models use about 370MB per worker.
   - **Key pair:** create one (`portfolio-key`, `.pem`) and keep the file safe; it can't be downloaded again.
   - **Storage:** 20 GB gp3. Models and Python packages take about 2 GB.
2. **Security group** (inbound rules):

   | Type | Port | Source |
   |---|---|---|
   | SSH | 22 | My IP only |
   | HTTP | 80 | Anywhere |
   | HTTPS | 443 | Anywhere |

3. **Elastic IP:** EC2 → Elastic IPs → Allocate → Associate with the instance, so the address stays fixed across reboots.
4. **DNS:** at your domain registrar, add an **A record** for `your-domain.com` (and `www`) pointing to the Elastic IP.

## Part 2: Connect and install the basics




If SSH reports that the key's permissions are too open: right-click the `.pem` file → Properties → Security, and leave only your own user with access.

On the server:

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3-venv python3-pip nginx git sqlite3

# Swap: a safety net for memory spikes (needed on t3.micro, harmless on t3.small)
sudo fallocate -l 2G /swapfile && sudo chmod 600 /swapfile
sudo mkswap /swapfile && sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

## Part 3: Get the app onto the server

```bash
cd ~
git clone https://github.com/saravanagithub14/Django-Portfolio-.git portfolio
cd portfolio
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# The live database lives outside the repo, so git never touches it
mkdir -p ~/data
cp db.sqlite3 ~/data/db.sqlite3
```

## Part 4: Production settings (`.env` on the server)

```bash
nano ~/portfolio/.env
```

```
DEBUG=False
SECRET_KEY=<generate: python3 -c "import secrets; print(secrets.token_urlsafe(50))">
ALLOWED_HOSTS=your-domain.com,www.your-domain.com
CSRF_TRUSTED_ORIGINS=https://your-domain.com,https://www.your-domain.com
SQLITE_PATH=/home/ubuntu/data/db.sqlite3

OPENAI_API_KEY=<your key>
CHATBOT_PROVIDER=openai
UPDATE_TOKEN=<another random value>
GITHUB_USERNAME=saravanagithub14
```

Then restrict it to your user: `chmod 600 ~/portfolio/.env`. The file is ignored by git, so pulls never touch it.

## Part 5: Build steps (the same ones `build.sh` runs on Render)

```bash
cd ~/portfolio && source .venv/bin/activate
python manage.py collectstatic --noinput
python manage.py migrate
python manage.py build_rag_index     # downloads the chatbot models (~150MB) the first time
python manage.py check --deploy      # Django's production checklist
```

## Part 6: Run the app as a service (gunicorn + systemd)

systemd keeps the app running and restarts it after crashes and reboots.

```bash
sudo nano /etc/systemd/system/portfolio.service
```

```ini
[Unit]
Description=Saravana portfolio (gunicorn)
After=network.target

[Service]
User=ubuntu
Group=www-data
WorkingDirectory=/home/ubuntu/portfolio
ExecStart=/home/ubuntu/portfolio/.venv/bin/gunicorn portfolio_hub.wsgi:application \
    --workers 2 --timeout 120 --bind 127.0.0.1:8000
Restart=always

[Install]
WantedBy=multi-user.target
```

- `--workers 2` suits `t3.small`; use `--workers 1` on `t3.micro`.
- `--timeout 120` gives the first chat request after a restart time to load the models.

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now portfolio
sudo systemctl status portfolio        # should say "active (running)"
curl -I http://127.0.0.1:8000/          # should say HTTP/1.1 200
```

## Part 7: nginx in front, then HTTPS

```bash
sudo nano /etc/nginx/sites-available/portfolio
```

```nginx
server {
    listen 80;
    server_name your-domain.com www.your-domain.com;
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
sudo ln -s /etc/nginx/sites-available/portfolio /etc/nginx/sites-enabled/
sudo rm /etc/nginx/sites-enabled/default
sudo chmod 755 /home/ubuntu          # lets nginx read the static files
sudo nginx -t && sudo systemctl reload nginx

# Free HTTPS certificate, renewed automatically
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com -d www.your-domain.com --redirect
```

The `X-Forwarded-For` header also matters for the chatbot: its 10-messages-per-minute limit uses it to tell visitors apart.

**Check the site:** open `https://your-domain.com`, then the 3D graph at the bottom of `/experience.html`, a chat message, `/health` (expect `"status": "healthy"` and `"active_provider": "openai"`), and `/login/`.

## Part 8: Deploying updates

Save as `~/deploy.sh` and run `chmod +x ~/deploy.sh` once:

```bash
#!/usr/bin/env bash
set -euo pipefail
cd ~/portfolio
source .venv/bin/activate
git pull origin main
pip install -r requirements.txt
python manage.py collectstatic --noinput
python manage.py migrate
python manage.py build_rag_index      # rebuilds only if the knowledge base changed
sudo systemctl restart portfolio
echo "Deployed $(git rev-parse --short HEAD)"
```

Every update after that: push to `main` on GitHub, SSH in, run `~/deploy.sh`.

## Part 9: Back up the database

On EC2 the live database is the only copy of your admin edits.

```bash
mkdir -p ~/backups
crontab -e
```

Add this line for a daily 3am backup that keeps 14 days:

```
0 3 * * * sqlite3 /home/ubuntu/data/db.sqlite3 ".backup /home/ubuntu/backups/db-$(date +\%F).sqlite3" && find /home/ubuntu/backups -mtime +14 -delete
```

For copies off the server, add an S3 upload (`aws s3 cp …`), or turn on automated EBS snapshots under EC2 → Lifecycle Manager.

## Troubleshooting

| Symptom | Where to look |
|---|---|
| 502 Bad Gateway | `sudo journalctl -u portfolio -n 50`: gunicorn crashed or hasn't started. |
| 400 Bad Request | Your domain is missing from `ALLOWED_HOSTS` in `.env`. |
| 403 CSRF on the admin login | The domain is missing from `CSRF_TRUSTED_ORIGINS`, or Part 0 isn't done. |
| Pages without styling | `collectstatic` didn't run, or nginx can't read `/home/ubuntu/portfolio/staticfiles`. |
| The chatbot only gives canned replies | `journalctl` shows "API execution error": check the API keys in `.env`. |
| Server killed or very slow | Out of memory (`free -h`): use fewer workers or a bigger instance. |

Live logs: `sudo journalctl -u portfolio -f` for the app, `/var/log/nginx/error.log` for nginx.
