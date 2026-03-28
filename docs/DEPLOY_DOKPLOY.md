# Deploy on Dokploy

Recommended layout: **two applications** — API (this repo’s `Dockerfile`) and **frontend** (static build from `frontend/`, no Docker required for the UI).

## Backend (Dockerfile at repo root)

1. Create a **Dockerfile** application pointing at this repository; **build context** = repository root.
2. **Port**: container `5001` → map to your public HTTP port (or internal only if the SPA talks to it via `VITE_API_BASE_URL`).
3. **Environment** (minimum):

   | Name | Value |
   |------|--------|
   | `OPENAI_API_KEY` | Your key |
   | `DATABASE_URL` | PostgreSQL URL (Alembic migrations in `backend/alembic/versions/`) |
   | `SECRET_KEY` | Long random string (session integrity) |
   | `PORT` | `5001` (or match EXPOSE) |
   | `CORS_ORIGINS` | **Required** if the SPA is on another origin: comma-separated browser origins, e.g. `http://your-frontend-host:4173` or your public app URL. Must match what the browser sends as `Origin` (scheme + host + port). |

4. **MinIO / S3**: Set `S3_ENDPOINT_URL`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `S3_BUCKET` as in `docker-compose.yml` when using object storage.

5. **`GET /`** returns a welcome JSON payload; **`GET /health`** is for load balancers. Routes like `/login` without a built SPA still return `503` JSON (use the separate frontend app).

## Frontend (separate Dokploy app or static host)

1. Build locally or in CI: `cd frontend && bun install && bun run build`.
2. Deploy the `frontend/dist` folder as a static site (or Node static server).
3. Set **`VITE_API_BASE_URL`** at **build time** to the public base URL of the API (no trailing slash), e.g. `http://api.internal:5001` or your reverse-proxied URL. See `frontend/.env.example`.
4. Ensure that URL is listed in **`CORS_ORIGINS`** on the backend.

## CORS and cookies

- The browser sends `credentials: "include"` for `/api/*`. Allowed origins must be listed explicitly in `CORS_ORIGINS` (wildcards are not used with credentials).
- Cross-site cookies need `SameSite=None; Secure` in browsers; on plain HTTP / split hostnames, session login may require same-site deployment or TLS — plan accordingly.

## Persistent data (recommended mounts)

| Container path | Purpose |
|----------------|---------|
| (Postgres volume or managed DB) | Users + generation history — point `DATABASE_URL` at it |
| `/app/storage/public` | Background library (optional, if not in image) |
| `/app/storage/uploads` | Upload cache |
| S3 / MinIO | Rendered videos when `S3_ENDPOINT_URL` is set |

## Health check

Use **`GET /health`**: returns `{"status":"healthy","checks":{...}}` with HTTP 200 when Postgres responds; **503** if the database is unreachable. `GET /` returns a small welcome JSON (service name and links).

## Smoke test after deploy

1. Open the **frontend** URL → register → login (unless `SKIP_AUTH` — not for public prod).
2. Put a test `.mp4` in `storage/public` (via mount or image rebuild) if you rely on bundled backgrounds.
3. Draft script → generate → confirm video plays (video URLs go through `/api/output/...` on the API origin).

## Rate limiting & scans

The API uses **Flask-Limiter** (per-IP, in-memory by default): `/api/*` ~120/min; login/register ~12/min. Obvious scanner paths (`.env`, `wp-admin`, etc.) return **404** without running heavy handlers. Disable with `RATELIMIT_ENABLED=0` if needed. For serious abuse, add **Traefik / firewall** rules or a WAF — app-level limits are a light baseline.

## Troubleshooting

- **503 JSON on `/login` etc.**: Normal when no SPA is bundled; open the separate frontend URL instead.
- **CORS errors**: Add the exact SPA `Origin` to `CORS_ORIGINS`; rebuild the SPA with correct `VITE_API_BASE_URL`.
- **`OPENAI_API_KEY not set`**: Missing env in Dokploy service.
- **FFmpeg errors**: Base image installs distro `ffmpeg`.
