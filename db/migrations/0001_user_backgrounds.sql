ALTER TABLE users ADD COLUMN IF NOT EXISTS gallery_public BOOLEAN NOT NULL DEFAULT false;

CREATE TABLE IF NOT EXISTS user_backgrounds (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
  user_id integer NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  storage_key text NOT NULL,
  original_filename text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS user_backgrounds_user_id_idx ON user_backgrounds (user_id);
