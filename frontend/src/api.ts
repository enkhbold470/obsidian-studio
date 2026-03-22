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

export const deleteBackground = async (id: string) => {
  const r = await apiFetch(`/api/backgrounds/${id}`, { method: "DELETE" });
  const data = (await r.json()) as { ok?: boolean; error?: string };
  if (!r.ok) {
    throw new Error(data.error ?? `Delete failed (${r.status})`);
  }
};

export type HistoryItem = {
  id: string;
  jobUid: string;
  topic: string | null;
  outputFormat: string;
  bgSource: string | null;
  createdAt: string;
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

export const postGenerate = async (form: FormData) => {
  const r = await apiFetch("/api/generate", { method: "POST", body: form });
  const raw = await r.text();
  let data: { error?: string; file?: string; ok?: boolean };
  try {
    data = JSON.parse(raw) as typeof data;
  } catch {
    throw new Error(
      r.status === 413
        ? "Upload too large or blocked (413). Raise MAX_UPLOAD_MB / reverse-proxy body size, or use a smaller file."
        : r.status === 401
          ? "Unauthorized."
          : `Bad response (${r.status}) — not JSON.`
    );
  }
  if (!r.ok) {
    throw new Error(data.error ?? `Request failed (${r.status})`);
  }
  return data;
};
