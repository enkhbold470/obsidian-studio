const jsonHeaders = { "Content-Type": "application/json" };

export const apiFetch = (path: string, init?: RequestInit) =>
  fetch(path, { ...init, credentials: "include" });

export type AuthUser = {
  id: number;
  email: string;
  galleryPublic?: boolean;
};

export const getMe = () =>
  apiFetch("/api/auth/me").then((r) => r.json()) as Promise<{
    user: AuthUser | null;
    skipAuth?: boolean;
  }>;

export const login = (email: string, password: string) =>
  apiFetch("/api/auth/login", {
    method: "POST",
    headers: jsonHeaders,
    body: JSON.stringify({ email, password }),
  }).then((r) => r.json());

export const register = (email: string, password: string) =>
  apiFetch("/api/auth/register", {
    method: "POST",
    headers: jsonHeaders,
    body: JSON.stringify({ email, password }),
  }).then((r) => r.json());

export const logout = () =>
  apiFetch("/api/auth/logout", { method: "POST" }).then((r) => r.json());

export const patchMe = (body: { galleryPublic?: boolean }) =>
  apiFetch("/api/me", {
    method: "PATCH",
    headers: jsonHeaders,
    body: JSON.stringify(body),
  }).then(async (r) => {
    const data = (await r.json()) as { user?: AuthUser; error?: string };
    if (!r.ok) {
      throw new Error(data.error ?? `Request failed (${r.status})`);
    }
    return data;
  });

export const getOptions = () => apiFetch("/api/options").then((r) => r.json());

export type BackgroundItem = {
  id: string;
  filename: string;
  createdAt: string;
  streamUrl: string;
  /** JPEG preview; may be missing for legacy uploads. */
  thumbUrl?: string;
};

export const getBackgrounds = async () => {
  const r = await apiFetch("/api/backgrounds");
  const data = (await r.json()) as { items?: BackgroundItem[]; error?: string };
  if (!r.ok) {
    throw new Error(data.error ?? `Backgrounds failed (${r.status})`);
  }
  return data.items ?? [];
};

export const uploadBackground = async (file: File) => {
  const fd = new FormData();
  fd.set("file", file);
  const r = await apiFetch("/api/backgrounds", { method: "POST", body: fd });
  const data = (await r.json()) as { item?: BackgroundItem; error?: string };
  if (!r.ok) {
    throw new Error(data.error ?? `Upload failed (${r.status})`);
  }
  return data.item!;
};

/** XMLHttpRequest so upload progress is visible (library upload). */
export const uploadBackgroundWithProgress = async (
  file: File,
  onProgress?: (loaded: number, total: number) => void,
) => {
  const fd = new FormData();
  fd.set("file", file);
  return new Promise<BackgroundItem>((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", "/api/backgrounds");
    xhr.withCredentials = true;
    xhr.upload.onprogress = (e) => {
      if (e.lengthComputable && onProgress) {
        onProgress(e.loaded, e.total);
      }
    };
    xhr.onload = () => {
      let data: { item?: BackgroundItem; error?: string };
      try {
        data = JSON.parse(xhr.responseText) as typeof data;
      } catch {
        reject(new Error(`Upload failed (${xhr.status}) — not JSON.`));
        return;
      }
      if (xhr.status < 200 || xhr.status >= 300) {
        reject(new Error(data.error ?? `Upload failed (${xhr.status})`));
        return;
      }
      if (!data.item) {
        reject(new Error("Upload failed: missing item."));
        return;
      }
      resolve(data.item);
    };
    xhr.onerror = () => reject(new Error("Network error during upload."));
    xhr.send(fd);
  });
};

export const deleteBackground = async (id: string) => {
  const r = await apiFetch(`/api/backgrounds/${id}`, { method: "DELETE" });
  const data = (await r.json()) as { ok?: boolean; error?: string };
  if (!r.ok) {
    throw new Error(data.error ?? `Delete failed (${r.status})`);
  }
};

/** Snapshot saved with each generation (settings + script + timing). */
export type RenderMeta = {
  topic?: string;
  dialogue_lines?: number;
  tts_speed?: number;
  shake_speed?: number;
  font_name?: string;
  font_size?: number;
  text_color?: string;
  outline_color?: string;
  peter_voice?: string;
  stewie_voice?: string;
  tts_model?: string;
  gpt_model?: string;
  output_format?: string;
  bg_source?: string;
  dialogue?: { speaker: string; text: string }[];
  elapsed_seconds?: number;
};

export type HistoryItem = {
  id: string;
  jobUid: string;
  topic: string | null;
  outputFormat: string;
  bgSource: string | null;
  createdAt: string;
  /** Server-side seconds from upload through render + upload (null for legacy rows). */
  elapsedSeconds?: number | null;
  renderMeta?: RenderMeta | null;
  watchUrl: string;
};

export const getHistory = async () => {
  const r = await apiFetch("/api/history");
  const data = (await r.json()) as { items?: HistoryItem[]; error?: string };
  if (!r.ok) {
    throw new Error(data.error ?? `History failed (${r.status})`);
  }
  return data.items ?? [];
};

export const getUserRenders = async (userId: number) => {
  const r = await apiFetch(`/api/users/${userId}/renders`);
  const data = (await r.json()) as {
    items?: HistoryItem[];
    galleryPublic?: boolean;
    error?: string;
  };
  if (r.status === 403) {
    throw new Error("Forbidden");
  }
  if (!r.ok) {
    throw new Error(data.error ?? `Renders failed (${r.status})`);
  }
  return data;
};

export type DialogueLine = { speaker: "Peter" | "Stewie"; text: string };

export const postScript = async (body: {
  topic: string;
  dialogue_lines: number;
  gpt_model: string;
}) => {
  const r = await apiFetch("/api/script", {
    method: "POST",
    headers: jsonHeaders,
    body: JSON.stringify(body),
  });
  const data = (await r.json()) as { dialogue?: unknown; error?: string };
  if (!r.ok) {
    throw new Error(data.error ?? `Script failed (${r.status})`);
  }
  return data;
};

const parseGenerateError = (status: number, raw: string): Error => {
  try {
    const data = JSON.parse(raw) as { error?: string };
    if (data.error) {
      return new Error(data.error);
    }
  } catch {
    /* not JSON */
  }
  const proxyTimeoutHint =
    status === 502 || status === 504
      ? " Proxy timeout or bad gateway: (1) Large multipart uploads (e.g. 100MB+ bg) can take minutes — increase proxy read/body timeouts. (2) Long ffmpeg/TTS after upload — increase response timeouts (often 300–600s+). Check app container logs to see how far [generate] got."
      : "";
  return new Error(
    status === 413
      ? "Upload too large or blocked (413). Raise MAX_UPLOAD_MB / reverse-proxy body size, or use a smaller file."
      : status === 401
        ? "Unauthorized."
        : `Bad response (${status}) — not JSON (proxy returned HTML).${proxyTimeoutHint}`
  );
};

export const postGenerate = async (form: FormData) => {
  const t0 = performance.now();
  console.info("[generate] POST /api/generate starting …");
  const r = await apiFetch("/api/generate", { method: "POST", body: form });
  const elapsedMs = Math.round(performance.now() - t0);
  console.info(
    `[generate] response status=${r.status} ok=${r.ok} elapsed_ms=${elapsedMs} content_type=${r.headers.get("content-type")}`
  );
  const raw = await r.text();
  if (raw.length < 500) {
    console.info("[generate] body preview:", raw.slice(0, 400));
  } else {
    console.info(`[generate] body length=${raw.length} (truncated log)`);
  }
  let data: { error?: string; file?: string; ok?: boolean; elapsedSeconds?: number };
  try {
    data = JSON.parse(raw) as typeof data;
  } catch {
    throw parseGenerateError(r.status, raw);
  }
  if (!r.ok) {
    throw parseGenerateError(r.status, raw);
  }
  return data;
};

/** Multipart generate with upload progress (XHR). Use when sending a large background file. */
export const postGenerateWithProgress = async (
  form: FormData,
  onUploadProgress?: (loaded: number, total: number) => void,
) => {
  const t0 = performance.now();
  console.info("[generate] POST /api/generate (XHR) starting …");
  return new Promise<{ error?: string; file?: string; ok?: boolean; elapsedSeconds?: number }>(
    (resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", "/api/generate");
    xhr.withCredentials = true;
    xhr.upload.onprogress = (e) => {
      if (e.lengthComputable && onUploadProgress) {
        onUploadProgress(e.loaded, e.total);
      }
    };
    xhr.onload = () => {
      const elapsedMs = Math.round(performance.now() - t0);
      console.info(
        `[generate] XHR done status=${xhr.status} elapsed_ms=${elapsedMs}`
      );
      const raw = xhr.responseText;
      if (raw.length < 500) {
        console.info("[generate] body preview:", raw.slice(0, 400));
      }
      let data: { error?: string; file?: string; ok?: boolean; elapsedSeconds?: number };
      try {
        data = JSON.parse(raw) as typeof data;
      } catch {
        reject(parseGenerateError(xhr.status, raw));
        return;
      }
      if (xhr.status < 200 || xhr.status >= 300) {
        reject(parseGenerateError(xhr.status, raw));
        return;
      }
      resolve(data);
    };
    xhr.onerror = () => reject(new Error("Network error during generate."));
    xhr.send(form);
  });
};
