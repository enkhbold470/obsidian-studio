# Deploy on Dokploy

Goal: one **Dockerfile** service that builds the React app and runs Flask on a single port.

## What you need in the repo

- `peter.png` and `stewie.png` under **`assets/`** (or at the repository root). The Docker build copies `assets/` into the image.
- Optional: sample videos under `storage/public/` — large files are often **mounted** at runtime instead of baked into the image (see volumes).

## Dokploy application

1. Create a **Dockerfile** application pointing at this repository.
2. **Build context**: repository root (default).
3. **Port**: container `5001` → your public HTTPS port (Dokploy reverse proxy).
4. **Environment** (minimum):

   | Name | Value |
   |------|--------|
   | `OPENAI_API_KEY` | Your key |
   | `DATABASE_URL` | PostgreSQL URL (matches `db/schema.ts` / `db/migrations/`) |
   | `SECRET_KEY` | Long random string (session integrity) |
   | `PORT` | `5001` (or match EXPOSE) |

5. **CORS**: For a single-origin deploy (same host serves UI + API), defaults are fine. If the browser origin differs, set `CORS_ORIGINS` to your exact `https://your-domain` (comma-separated, no trailing slash issues — match browser origin).

6. **HTTPS**: Run behind Dokploy’s TLS so session cookies stay `Secure` in production if you configure Flask accordingly later.

## Persistent data (recommended mounts)

| Container path | Purpose |
|----------------|---------|
| (Postgres volume or managed DB) | Users + generation history — point `DATABASE_URL` at it |
| `/app/storage/public` | Background library (optional, if not in image) |
| `/app/storage/uploads` | Upload cache |
| S3 / MinIO | Rendered videos when `S3_ENDPOINT_URL` is set |

Without a persistent database and object storage, users and past renders are lost when containers are recreated.

## Health check

Dokploy can HTTP-check `GET /api/options` (returns JSON) on the internal port.

## Smoke test after deploy

1. Open your site → register → login (unless you intentionally use `SKIP_AUTH` — **not** for public prod).
2. Put a test `.mp4` in `storage/public` (via mount or image rebuild).
3. Draft script → generate → confirm video plays.

## Troubleshooting

- **503 “Frontend not built”**: Image was built without the frontend stage succeeding; check Docker build logs.
- **`OPENAI_API_KEY not set`**: Missing env in Dokploy service.
- **FFmpeg errors**: Base image installs distro `ffmpeg`. Brainrot may still download static macOS-focused binaries on developers’ machines only; Linux containers use apt’s FFmpeg.
