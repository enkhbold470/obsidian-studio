# Deploy on Dokploy

Recommended layout: **two applications** — API (this repo’s `Dockerfile`) and **frontend** (static build from `frontend/`, no Docker required for the UI).

## Backend (Dockerfile at repo root)

1. Create a **Dockerfile** application pointing at this repository; **build context** = repository root.
2. **Port**: container `5001` → map to your public HTTP port (or internal only if the SPA talks to it via `VITE_API_BASE_URL`).
3. **Environment** (minimum):

   | Name | Value |
   |------|--------|
   | `OPENAI_API_KEY` | Your key |
   | `DATABASE_URL` | PostgreSQL URL (Alembic migrations in `alembic/versions/`) |
   | `SECRET_KEY` | Long random string (session integrity) |
   | `PORT` | `5001` (or match EXPOSE) |
   | `CORS_ORIGINS` | **Required** if the SPA is on another origin: comma-separated browser origins, e.g. `http://your-frontend-host:4173` or your public app URL. Must match what the browser sends as `Origin` (scheme + host + port). |

4. **MinIO / S3**: Set `S3_ENDPOINT_URL`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `S3_BUCKET` as in `docker-compose.yml` when using object storage.

5. Opening `/` without a baked-in SPA returns JSON `503` with a hint — that is expected when only the API is deployed.

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

Dokploy can HTTP-check `GET /api/options` (returns JSON) on the internal port.

## Smoke test after deploy

1. Open the **frontend** URL → register → login (unless `SKIP_AUTH` — not for public prod).
2. Put a test `.mp4` in `storage/public` (via mount or image rebuild) if you rely on bundled backgrounds.
3. Draft script → generate → confirm video plays (video URLs go through `/api/output/...` on the API origin).

## Troubleshooting

- **503 JSON on API root**: Normal when no SPA is bundled; use the separate frontend.
- **CORS errors**: Add the exact SPA `Origin` to `CORS_ORIGINS`; rebuild the SPA with correct `VITE_API_BASE_URL`.
- **`OPENAI_API_KEY not set`**: Missing env in Dokploy service.
- **FFmpeg errors**: Base image installs distro `ffmpeg`.
