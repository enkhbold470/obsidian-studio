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

export const postGenerate = (form: FormData) =>
  apiFetch("/api/generate", { method: "POST", body: form }).then((r) => r.json());
