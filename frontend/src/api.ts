const jsonHeaders = { "Content-Type": "application/json" };

export const apiFetch = (path: string, init?: RequestInit) =>
  fetch(path, { ...init, credentials: "include" });

export const getMe = () => apiFetch("/api/auth/me").then((r) => r.json());

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

export const getOptions = () => apiFetch("/api/options").then((r) => r.json());

export const getBackgrounds = () => apiFetch("/api/backgrounds").then((r) => r.json());

export type DialogueLine = { speaker: "Peter" | "Stewie"; text: string };

export const postScript = (body: {
  topic: string;
  dialogue_lines: number;
  gpt_model: string;
}) =>
  apiFetch("/api/script", {
    method: "POST",
    headers: jsonHeaders,
    body: JSON.stringify(body),
  }).then((r) => r.json());

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
