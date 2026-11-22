# Linkly V3 custom domain setup

A custom domain requires a domain you own and a publicly reachable hosting target. The app is domain-ready, but a real domain cannot be activated until you supply the domain name and choose hosting/DNS.

1. Buy or use a domain/subdomain, e.g. `go.example.com`.
2. Deploy Linkly to a public host. Point the subdomain's DNS record (usually CNAME for a subdomain) to the hostname supplied by that host. For a VPS, use an A record to its public IPv4 address.
3. Configure HTTPS at the hosting platform or a reverse proxy such as Caddy. Do not expose the app publicly over plain HTTP for real accounts.
4. Set `BASE_URL=https://go.example.com` and `COOKIE_SECURE=true` in the deployment environment.
5. Set a unique `SESSION_SECRET` using `python -c "import secrets; print(secrets.token_urlsafe(48))"`.
6. Restart/redeploy and verify `https://go.example.com/health`, registration/login, a short link and its QR code.

Do not point public DNS at a private Wi-Fi address such as `10.x.x.x`; it is not reachable from the public internet. The current `10.62.246.48` URL is LAN-only and changes when the network address changes.

For country analytics, requests proxied through Cloudflare can populate the country field from `CF-IPCountry`. Without that trusted header, the country appears as `Unknown`. Linkly intentionally does not store visitor IP addresses.
