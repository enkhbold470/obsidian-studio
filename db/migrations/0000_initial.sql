CREATE TABLE IF NOT EXISTS "users" (
  "id" serial PRIMARY KEY NOT NULL,
  "email" text NOT NULL,
  "password_hash" text NOT NULL,
  "created_at" timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT "users_email_unique" UNIQUE("email")
);

CREATE TABLE IF NOT EXISTS "generations" (
  "id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
  "user_id" integer REFERENCES users(id) ON DELETE SET NULL,
  "job_uid" text NOT NULL,
  "output_key" text NOT NULL,
  "output_format" text NOT NULL,
  "topic" text,
  "dialogue" jsonb NOT NULL,
  "bg_source" text,
  "created_at" timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT "generations_job_uid_unique" UNIQUE("job_uid")
);

CREATE INDEX IF NOT EXISTS "generations_user_id_idx" ON "generations" ("user_id");
