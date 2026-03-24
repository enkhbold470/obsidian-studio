/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** API origin without trailing slash (e.g. `http://api:5001`). Empty = same-origin / Vite proxy. */
  readonly VITE_API_BASE_URL?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
