# Linkly V3

FastAPI URL shortener with authenticated workspaces, custom aliases, QR codes, 30-day analytics, custom-domain configuration and Docker Compose deployment.

## Included
- Registration, login and logout using signed HTTP-only session cookies.
- Passwords hashed with Python's `scrypt`; no plaintext passwords stored.
- Per-user link ownership and deletion authorization.
- SQLite schema migration from V2: existing short codes and click totals remain intact. The first registered account claims pre-existing unowned V2 links.
- QR SVG generation and short-link redirects.
- 30-day click history, referrers, browser/device breakdowns, and country breakdown when a trusted Cloudflare country header is present.
- Dockerfile, Compose file and persistent SQLite volume.
- Custom domain instructions in `CUSTOM_DOMAIN.md`.

## Run locally in Ubuntu WSL
```bash
cd /mnt/d/linkly-v3
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export BASE_URL="http://YOUR-WINDOWS-LAN-IP:8000"
export SESSION_SECRET="$(python -c 'import secrets; print(secrets.token_urlsafe(48))')"
uvicorn main:app --host 0.0.0.0 --port 8000
```
Open `http://YOUR-WINDOWS-LAN-IP:8000`. Keep the terminal running. The URL must be reachable from your phone and laptop. Do not use `0.0.0.0` in a browser.

## Docker
```bash
cp .env.example .env
# Edit .env: set BASE_URL and a unique SESSION_SECRET
docker compose up --build -d
docker compose logs -f linkly
```
Open `http://localhost:8000`. SQLite persists in the named `linkly_data` volume. Back up this volume before upgrades.

## Migrate V2 data
Stop V2 first. Copy your existing `links.db` into the V3 project as `links.db` before the first run, or set `DB_PATH` to the existing database path. V3 performs additive schema migrations. Keep a backup of the database before migrating. Existing links and aggregate click counts remain; detailed historical events are only available for events already stored in V2.

## Production security
- Set a unique, persistent `SESSION_SECRET` and `COOKIE_SECURE=true` behind HTTPS.
- Use a publicly reachable host and HTTPS reverse proxy/platform TLS for a custom domain.
- Do not expose the development server directly to the internet.
- Country data is based on Cloudflare's `CF-IPCountry` header; otherwise it is Unknown. Visitor IP addresses are not retained.
- This starter does not include email verification, password reset, rate limiting, MFA or abuse detection. Add these before offering public self-service registration at scale.

See `CUSTOM_DOMAIN.md` for DNS and HTTPS setup.

## API
- `POST /api/auth/register` `{ "username": "...", "password": "10+ characters" }`
- `POST /api/auth/login` and `POST /api/auth/logout`
- `GET /api/auth/me`
- `POST /api/links` `{ "url": "https://...", "custom_code": "optional" }`
- `GET /api/links`
- `GET /api/links/{code}/qr`
- `GET /api/links/{code}/stats`
- `DELETE /api/links/{code}`
- `GET /health`
