# What else you might add later

The current stack is intentionally minimal. When you outgrow it, consider:

| Area | Idea |
|------|------|
| **Secrets** | Managed secrets in Dokploy / your host instead of plain env vars where teams share access. |
| **Database** | SQLite + single container is fine at small scale; move to Postgres if you need HA or multi-instance. |
| **File storage** | Mount S3-compatible object storage or NFS if `storage/` grows beyond one machine. |
| **Auth** | OAuth (GitHub/Google), email verification, password reset, rate limits on `/api/auth/*`. |
| **API safety** per user | Per-IP or per-user quotas on `/api/generate` and `/api/script` to cap OpenAI spend. |
| **Observability** | Structured logs, request IDs, error tracking (e.g. OpenTelemetry or a hosted APM). |
| **Jobs** | Long FFmpeg runs in a queue (Redis + worker) so HTTP requests return a job id instead of blocking. |
| **TLS / cookies** | In production, serve only HTTPS and tighten `SESSION_COOKIE_SECURE` when appropriate. |
| **Backups** | If SQLite is mounted on a volume, snapshot or copy `backend/instance/app.sqlite` on a schedule. |

None of this is required for a personal or low-traffic deployment.
