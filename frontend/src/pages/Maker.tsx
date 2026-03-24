import { FormEvent, useCallback, useEffect, useRef, useState } from "react";
import { Link, Navigate } from "react-router-dom";
import { toast } from "sonner";

const SCRIPT_READY_KEY = "reelmaker-script-ready";
import type { AuthUser, BackgroundItem, DialogueLine } from "../api";
import {
  apiUrl,
  deleteBackground,
  getBackgrounds,
  getMe,
  getOptions,
  postGenerate,
  postGenerateWithProgress,
  postScript,
  uploadBackgroundWithProgress,
} from "../api";
import { BgPreview } from "../components/BgPreview";
import {
  DialogueEditor,
  isValidDialogue,
  toPayloadLines,
} from "../components/DialogueEditor";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { formatElapsedSeconds } from "../formatElapsed";
import { inputClass, panelClass, panelMutedClass, selectClass } from "../lib/obsidianStyles";

type OptionsPayload = {
  tts_voices: string[];
  tts_models: string[];
  gpt_models: string[];
  fonts: string[];
};

const LUCKY_TOPICS = [
  "pineapple on pizza",
  "crypto",
  "AI taking over",
  "the best programming language",
  "why we exist",
  "coffee vs tea",
  "aliens",
  "time travel",
];

const Spinner = () => (
  <span
    className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent"
    aria-hidden
  />
);

export const Maker = () => {
  const [authLoading, setAuthLoading] = useState(true);
  const [skipAuth, setSkipAuth] = useState(false);
  const [user, setUser] = useState<AuthUser | null>(null);

  const [topic, setTopic] = useState("");
  const [dialogueLines, setDialogueLines] = useState(8);
  const [ttsSpeed, setTtsSpeed] = useState(1.2);
  const [shakeSpeed, setShakeSpeed] = useState(10);
  const [outputFormat, setOutputFormat] = useState("mp4");
  const [fontName, setFontName] = useState("Arial Black");
  const [fontSize, setFontSize] = useState(100);
  const [textColor, setTextColor] = useState("#FDE047");
  const [outlineColor, setOutlineColor] = useState("#000000");
  const [peterVoice, setPeterVoice] = useState("am_michael");
  const [stewieVoice, setStewieVoice] = useState("bm_george*0.7+af_bella*0.3");
  const [gptModel, setGptModel] = useState("gpt-4o");
  const [ttsModel, setTtsModel] = useState("kokoro");

  const [options, setOptions] = useState<OptionsPayload | null>(null);
  const [bgItems, setBgItems] = useState<BackgroundItem[]>([]);
  const [savedBgId, setSavedBgId] = useState("");
  const [bgFile, setBgFile] = useState<File | null>(null);
  const [bgLoadErr, setBgLoadErr] = useState<string | null>(null);

  const [lines, setLines] = useState<DialogueLine[]>([{ speaker: "Peter", text: "" }]);

  const [videoSrc, setVideoSrc] = useState<string | null>(null);
  const [lastGenElapsedSec, setLastGenElapsedSec] = useState<number | null>(null);
  const [draftLoading, setDraftLoading] = useState(false);
  const [genLoading, setGenLoading] = useState(false);
  const [genProgress, setGenProgress] = useState(0);
  const [libraryUploadPct, setLibraryUploadPct] = useState<number | null>(null);
  const [genUploadPct, setGenUploadPct] = useState<number | null>(null);
  /** After first successful AI draft (or user skips), show dialogue / background / advanced / generate. */
  const [scriptReady, setScriptReady] = useState(false);
  const genTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const refreshBackgrounds = useCallback(() => {
    if (skipAuth || !user) {
      setBgItems([]);
      return;
    }
    getBackgrounds()
      .then((items) => {
        setBgItems(items);
        setBgLoadErr(null);
      })
      .catch((e: Error) => {
        setBgItems([]);
        setBgLoadErr(e.message);
      });
  }, [skipAuth, user]);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const me = await getMe();
        if (cancelled) {
          return;
        }
        if (me.skipAuth) {
          setSkipAuth(true);
          setUser(null);
        } else if (me.user) {
          setUser(me.user);
        } else {
          setUser(null);
        }
      } finally {
        if (!cancelled) {
          setAuthLoading(false);
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    getOptions().then((o: OptionsPayload) => {
      setOptions(o);
      if (o.gpt_models?.length && !o.gpt_models.includes(gptModel)) {
        setGptModel(o.gpt_models[0]);
      }
      if (o.tts_models?.length && !o.tts_models.includes(ttsModel)) {
        setTtsModel(o.tts_models[0]);
      }
      if (o.tts_voices?.length) {
        if (!o.tts_voices.includes(peterVoice)) {
          setPeterVoice(o.tts_voices[0]);
        }
        if (!o.tts_voices.includes(stewieVoice)) {
          setStewieVoice(o.tts_voices[Math.min(1, o.tts_voices.length - 1)]);
        }
      }
    });
  }, []);

  useEffect(() => {
    refreshBackgrounds();
  }, [refreshBackgrounds]);

  useEffect(() => {
    try {
      if (sessionStorage.getItem(SCRIPT_READY_KEY) === "1") {
        setScriptReady(true);
      }
    } catch {
      /* ignore */
    }
  }, []);

  const persistScriptReady = useCallback(() => {
    setScriptReady(true);
    try {
      sessionStorage.setItem(SCRIPT_READY_KEY, "1");
    } catch {
      /* ignore */
    }
  }, []);

  useEffect(() => {
    if (!genLoading) {
      if (genTimerRef.current) {
        clearInterval(genTimerRef.current);
        genTimerRef.current = null;
      }
      return;
    }
    if (genUploadPct !== null && genUploadPct < 100) {
      setGenProgress(0);
      if (genTimerRef.current) {
        clearInterval(genTimerRef.current);
        genTimerRef.current = null;
      }
      return;
    }
    const start = Date.now();
    genTimerRef.current = setInterval(() => {
      const elapsed = (Date.now() - start) / 1000;
      if (elapsed < 30) {
        setGenProgress(Math.min(90, (elapsed / 30) * 90));
      } else {
        setGenProgress(90);
      }
    }, 120);
    return () => {
      if (genTimerRef.current) {
        clearInterval(genTimerRef.current);
        genTimerRef.current = null;
      }
    };
  }, [genLoading, genUploadPct]);

  const handleDraftScript = async () => {
    let t = topic.trim();
    if (t.length < 10) {
      const pick = LUCKY_TOPICS[Math.floor(Math.random() * LUCKY_TOPICS.length)];
      t = pick.length >= 10 ? pick : `${pick} — brainrot debate, unhinged`;
      setTopic(t);
    } else {
      t = topic.trim();
    }
    setDraftLoading(true);
    try {
      const data = await postScript({
        topic: t,
        dialogue_lines: dialogueLines,
        gpt_model: gptModel,
      });
      if (data.error) {
        throw new Error(String(data.error));
      }
      const d = data.dialogue as DialogueLine[];
      setLines(d.length ? d : [{ speaker: "Peter", text: "" }]);
      persistScriptReady();
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Draft failed");
    } finally {
      setDraftLoading(false);
    }
  };

  const handleBgUploadChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0] ?? null;
    setBgFile(f);
    if (f) {
      setSavedBgId("");
    }
  };

  const handlePickSaved = (id: string) => {
    setSavedBgId(id);
    setBgFile(null);
    const input = document.getElementById("bg-upload") as HTMLInputElement | null;
    if (input) {
      input.value = "";
    }
  };

  const handleDeleteBg = async (id: string, name: string) => {
    if (!window.confirm(`Delete “${name}” from your library?`)) {
      return;
    }
    try {
      await deleteBackground(id);
      refreshBackgrounds();
      if (savedBgId === id) {
        setSavedBgId("");
      }
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Delete failed");
    }
  };

  const handleUploadToLibrary = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    if (!f) {
      return;
    }
    setLibraryUploadPct(0);
    try {
      await uploadBackgroundWithProgress(f, (loaded, total) => {
        setLibraryUploadPct(Math.min(100, Math.round((loaded / total) * 100)));
      });
      refreshBackgrounds();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setLibraryUploadPct(null);
    }
    e.target.value = "";
  };

  const buildFormData = useCallback(
    (e: FormEvent<HTMLFormElement>) => {
      e.preventDefault();
      const payload = toPayloadLines(lines);
      if (!isValidDialogue(payload)) {
        toast.error("Add at least one dialogue line with text (or draft with AI).");
        return null;
      }
      const hasUpload = Boolean(bgFile);
      const hasSaved = Boolean(savedBgId.trim());
      if (!hasUpload && !hasSaved) {
        toast.error("Select a saved background or upload a video file.");
        return null;
      }
      if (hasUpload && hasSaved) {
        toast.error("Use either a saved background or a new file, not both.");
        return null;
      }
      const fd = new FormData(e.currentTarget);
      fd.set("dialogue", JSON.stringify(payload));
      if (hasUpload && bgFile) {
        fd.set("bg", bgFile);
        fd.delete("bg_saved_id");
      } else {
        fd.set("bg_saved_id", savedBgId);
        fd.delete("bg");
      }
      return fd;
    },
    [lines, bgFile, savedBgId]
  );

  const handleFormSubmit = (e: FormEvent<HTMLFormElement>) => {
    if (!scriptReady) {
      e.preventDefault();
      return;
    }
    void handleGenerate(e);
  };

  const handleGenerate = async (e: FormEvent<HTMLFormElement>) => {
    const fd = buildFormData(e);
    if (!fd) {
      return;
    }
    const bgPart = fd.get("bg");
    const useUploadProgress = bgPart instanceof File;
    setGenLoading(true);
    setGenProgress(0);
    setGenUploadPct(useUploadProgress ? 0 : null);
    setVideoSrc(null);
    setLastGenElapsedSec(null);
    try {
      const bgMeta =
        bgPart instanceof File
          ? { name: bgPart.name, size: bgPart.size, type: bgPart.type }
          : { savedId: String(fd.get("bg_saved_id") || "") };
      console.info("[Maker] generate submit", {
        ...bgMeta,
        t: new Date().toISOString(),
      });
      const data = useUploadProgress
        ? await postGenerateWithProgress(fd, (loaded, total) => {
            setGenUploadPct(Math.min(100, Math.round((loaded / total) * 100)));
          })
        : await postGenerate(fd);
      if (data.error) {
        throw new Error(String(data.error));
      }
      setGenProgress(100);
      const path = data.file as string;
      setVideoSrc(apiUrl(path.startsWith("/") ? path : `/api/output/${path}`));
      if (typeof data.elapsedSeconds === "number" && Number.isFinite(data.elapsedSeconds)) {
        setLastGenElapsedSec(data.elapsedSeconds);
      }
      persistScriptReady();
      refreshBackgrounds();
      toast.success("Video ready");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "failed");
    } finally {
      setGenLoading(false);
      setGenUploadPct(null);
      setTimeout(() => setGenProgress(0), 400);
    }
  };

  if (authLoading) {
    return (
      <div className="px-6 py-16 text-center text-muted-foreground" aria-live="polite">
        Loading…
      </div>
    );
  }
  if (!skipAuth && !user) {
    return <Navigate to="/login" replace />;
  }

  return (
    <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:py-4">
      <div className="mb-6 lg:mb-4">
        <h1 className="font-headline text-3xl font-extrabold tracking-tight text-foreground md:text-4xl">
          Editor
        </h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Start with a topic, then draft your script. More steps unlock after your first successful draft.
        </p>
        {skipAuth ? (
          <p className="mt-2 text-xs font-semibold text-tertiary">
            Auth disabled (dev) —{" "}
            <Link className="underline" to="/login">
              Login anyway
            </Link>
          </p>
        ) : null}
      </div>

      <form className="divide-y divide-border" onSubmit={handleFormSubmit}>
        <section aria-label="Topic and draft" className="space-y-4 py-6">
          <div className="flex flex-col gap-6 lg:grid lg:grid-cols-12 lg:items-start lg:gap-6">
            <div className="space-y-2 lg:col-span-4">
              <Label className="font-label text-xs font-bold uppercase tracking-wider text-muted-foreground">
                AI model (draft script)
              </Label>
              <select
                name="gpt_model"
                value={gptModel}
                onChange={(e) => setGptModel(e.target.value)}
                className={selectClass}
              >
                {(options?.gpt_models ?? [gptModel]).map((m) => (
                  <option key={m} value={m}>
                    {m}
                  </option>
                ))}
              </select>
              <p className="text-xs text-muted-foreground">Used for “Draft script with AI” only.</p>
            </div>
            <div className="space-y-2 lg:col-span-5">
              <Label htmlFor="topic-field" className="font-label text-xs font-bold uppercase tracking-wider text-muted-foreground">
                Topic (for AI script draft)
              </Label>
              <Textarea
                id="topic-field"
                name="topic"
                rows={3}
                value={topic}
                onChange={(e) => setTopic(e.target.value)}
                placeholder="Paste a paragraph / dump for the debate topic…"
                className="min-h-20 resize-y"
              />
              <p className="text-xs text-muted-foreground">
                <strong className="text-foreground">Draft</strong> uses line count; <strong className="text-foreground">Generate</strong> runs TTS + subs + mux.
              </p>
            </div>
            <div className="flex flex-col gap-3 border-border lg:col-span-3 lg:border-l lg:pl-6">
              <div className="flex flex-wrap items-center gap-2">
                <Label htmlFor="dialogue_lines" className="font-label text-sm font-bold">
                  Lines (AI draft)
                </Label>
                <Input
                  id="dialogue_lines"
                  name="dialogue_lines"
                  type="number"
                  value={dialogueLines}
                  min={2}
                  max={20}
                  onChange={(e) => setDialogueLines(Number(e.target.value))}
                  className="w-16 text-center"
                />
              </div>
              <Button
                type="button"
                variant="secondary"
                onClick={handleDraftScript}
                disabled={draftLoading}
                className="w-full lg:w-auto"
              >
                {draftLoading ? <Spinner /> : null}
                Draft script with AI
              </Button>
            </div>
          </div>
        </section>

        {!scriptReady ? (
          <div className="space-y-3 py-6">
            <p className="text-sm text-muted-foreground">
              Run <strong className="text-foreground">Draft script with AI</strong> to unlock dialogue, background, and
              render. Or continue without a draft if you already know your lines.
            </p>
            <Button
              type="button"
              variant="outline"
              onClick={() => {
                persistScriptReady();
              }}
              className="border-secondary/50 text-secondary hover:bg-secondary/10"
            >
              Continue without draft — show dialogue &amp; background
            </Button>
          </div>
        ) : null}

        {scriptReady ? (
          <>
        <section aria-label="Dialogue" className="space-y-3 py-6">
          <h2 className="font-label text-xs font-bold uppercase tracking-wider text-muted-foreground">
            Dialogue
          </h2>
          <div className={panelClass}>
            <DialogueEditor lines={lines} onChange={setLines} />
          </div>
        </section>

        <section aria-label="Background video" className="space-y-4 py-6">
          <h2 className="font-label text-xs font-bold uppercase tracking-wider text-muted-foreground">
            Background video
          </h2>
          <p className="text-sm text-muted-foreground">
            Uploads go to your library; generating from a new file also saves a copy.
          </p>
          {bgLoadErr ? (
            <p className="rounded-lg border border-tertiary/40 bg-tertiary/10 px-3 py-2 text-sm text-tertiary">
              {bgLoadErr}
            </p>
          ) : null}
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
            {bgItems.map((b) => (
              <div
                key={b.id}
                className={`relative overflow-hidden rounded-xl border p-1 transition ${
                  savedBgId === b.id
                    ? "border-secondary ring-2 ring-secondary/40"
                    : "border-border/60 hover:border-border"
                }`}
              >
                <button
                  type="button"
                  onClick={() => handlePickSaved(b.id)}
                  className="block w-full text-left"
                >
                  <div className="aspect-video overflow-hidden rounded-lg bg-muted/30">
                    <BgPreview item={b} />
                  </div>
                  <p className="truncate p-2 font-mono text-xs text-muted-foreground">{b.filename}</p>
                </button>
                <button
                  type="button"
                  onClick={() => handleDeleteBg(b.id, b.filename)}
                  className="absolute right-2 top-2 rounded-md border border-border bg-card px-2 py-0.5 text-xs font-bold text-destructive hover:bg-destructive/10"
                  aria-label={`Delete ${b.filename}`}
                >
                  ×
                </button>
              </div>
            ))}
          </div>
          <div className="space-y-2">
            <label className="block text-sm font-bold text-foreground" htmlFor="bg-upload">
              Upload for this render (saved to library after generate)
            </label>
            <input
              id="bg-upload"
              name="bg"
              type="file"
              accept="video/*"
              onChange={handleBgUploadChange}
              className={`${inputClass} file:mr-3 file:rounded-lg file:border-0 file:bg-primary/20 file:px-3 file:py-1.5 file:text-sm file:font-semibold file:text-primary`}
            />
          </div>
          <input type="hidden" name="bg_saved_id" value={savedBgId} readOnly />
        </section>

        <details className="group py-6">
          <summary className="cursor-pointer list-none font-label text-xs font-bold uppercase tracking-wider text-muted-foreground transition hover:text-foreground [&::-webkit-details-marker]:hidden">
            <span className="inline-flex items-center gap-2 rounded-lg border border-border/60 bg-muted/40 px-4 py-2">
              Advanced options
            </span>
          </summary>
          <p className="mt-4 text-xs text-muted-foreground">
            Library upload, timing, output, look, and voices — defaults apply when collapsed.
          </p>
          <div className={`${panelMutedClass} mt-4 space-y-4`}>
            <div>
              <label className="mb-2 block text-sm font-bold text-foreground" htmlFor="lib-upload">
                Add to library only
              </label>
              {libraryUploadPct !== null ? (
                <div
                  className="mb-2 h-2 w-full overflow-hidden rounded-full bg-muted"
                  role="progressbar"
                  aria-valuenow={libraryUploadPct}
                  aria-valuemin={0}
                  aria-valuemax={100}
                  aria-label="Library upload progress"
                >
                  <div
                    className="h-full bg-primary transition-[width] duration-150"
                    style={{ width: `${libraryUploadPct}%` }}
                  />
                </div>
              ) : null}
              <input
                id="lib-upload"
                type="file"
                accept="video/*"
                onChange={handleUploadToLibrary}
                disabled={libraryUploadPct !== null}
                className={`${inputClass} border-dashed file:mr-3 file:rounded-lg file:border-0 file:bg-primary/20 file:px-3 file:py-1.5 file:text-sm file:font-semibold file:text-primary`}
              />
            </div>

            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
              <div>
                <label className="mb-1 block font-bold text-foreground">TTS speed</label>
                <input
                  name="tts_speed"
                  type="number"
                  step={0.1}
                  value={ttsSpeed}
                  min={0.5}
                  max={2}
                  onChange={(e) => setTtsSpeed(Number(e.target.value))}
                  className={inputClass}
                />
              </div>
              <div>
                <label className="mb-1 block font-bold text-foreground">Shake speed</label>
                <input
                  name="shake_speed"
                  type="number"
                  value={shakeSpeed}
                  min={5}
                  max={50}
                  onChange={(e) => setShakeSpeed(Number(e.target.value))}
                  className={inputClass}
                />
              </div>
              <div>
                <label className="mb-1 block font-bold text-foreground">Output</label>
                <select
                  name="output_format"
                  value={outputFormat}
                  onChange={(e) => setOutputFormat(e.target.value)}
                  className={selectClass}
                >
                  <option value="mp4">MP4</option>
                  <option value="mkv">MKV</option>
                </select>
              </div>
              <div>
                <label className="mb-1 block font-bold text-foreground">TTS model</label>
                <select
                  name="tts_model"
                  value={ttsModel}
                  onChange={(e) => setTtsModel(e.target.value)}
                  className={selectClass}
                >
                  {(options?.tts_models ?? [ttsModel]).map((m) => (
                    <option key={m} value={m}>
                      {m}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="mb-1 block font-bold text-foreground">Font</label>
                <select
                  name="font_name"
                  value={fontName}
                  onChange={(e) => setFontName(e.target.value)}
                  className={selectClass}
                >
                  {(options?.fonts ?? ["Arial"]).map((f) => (
                    <option key={f} value={f}>
                      {f}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="mb-1 block font-bold text-foreground">Font size</label>
                <input
                  name="font_size"
                  type="number"
                  value={fontSize}
                  min={40}
                  max={200}
                  onChange={(e) => setFontSize(Number(e.target.value))}
                  className={inputClass}
                />
              </div>
              <div>
                <label className="mb-1 block font-bold text-foreground">Text color</label>
                <input
                  name="text_color"
                  type="color"
                  value={textColor}
                  onChange={(e) => setTextColor(e.target.value)}
                  className="h-11 w-full cursor-pointer rounded-xl border border-border bg-muted/30"
                />
              </div>
              <div>
                <label className="mb-1 block font-bold text-foreground">Outline color</label>
                <input
                  name="outline_color"
                  type="color"
                  value={outlineColor}
                  onChange={(e) => setOutlineColor(e.target.value)}
                  className="h-11 w-full cursor-pointer rounded-xl border border-border bg-muted/30"
                />
              </div>
              <div className="sm:col-span-2 lg:col-span-1">
                <label className="mb-1 block font-bold text-foreground">Peter voice</label>
                <select
                  name="peter_voice"
                  value={peterVoice}
                  onChange={(e) => setPeterVoice(e.target.value)}
                  className={selectClass}
                >
                  {(options?.tts_voices ?? ["am_michael", "bm_george", "bm_george*0.7+af_bella*0.3"]).map((v) => (
                    <option key={v} value={v}>
                      {v}
                    </option>
                  ))}
                </select>
              </div>
              <div className="sm:col-span-2 lg:col-span-1">
                <label className="mb-1 block font-bold text-foreground">Stewie voice</label>
                <select
                  name="stewie_voice"
                  value={stewieVoice}
                  onChange={(e) => setStewieVoice(e.target.value)}
                  className={selectClass}
                >
                  {(options?.tts_voices ?? ["am_michael", "bm_george", "bm_george*0.7+af_bella*0.3"]).map((v) => (
                    <option key={`s-${v}`} value={v}>
                      {v}
                    </option>
                  ))}
                </select>
              </div>
            </div>
          </div>
        </details>

        <section aria-label="Generate" className="space-y-4 py-6">
          {genUploadPct !== null ? (
            <div>
              <p className="text-xs font-bold text-muted-foreground">
                {genUploadPct < 100
                  ? `Uploading background… ${genUploadPct}%`
                  : "Upload complete — rendering on server…"}
              </p>
              <div
                className="mt-1 h-2 w-full overflow-hidden rounded-full bg-muted"
                role="progressbar"
                aria-valuenow={genUploadPct}
                aria-valuemin={0}
                aria-valuemax={100}
                aria-label="Generate upload progress"
              >
                <div
                  className="h-full bg-secondary transition-[width] duration-150"
                  style={{ width: `${genUploadPct}%` }}
                />
              </div>
            </div>
          ) : null}

          <div className="flex flex-col gap-4 lg:grid lg:grid-cols-12 lg:gap-6 lg:items-start">
            <div className={videoSrc ? "space-y-4 lg:col-span-5" : "space-y-4 lg:col-span-12"}>
              <div className="relative overflow-hidden rounded-xl border border-border shadow-primaryGlow">
                <Button
                  type="submit"
                  disabled={genLoading}
                  className="relative z-10 h-auto w-full rounded-xl bg-gradient-to-r from-primary to-primary-dim px-4 py-4 font-headline text-base font-bold text-primary-foreground shadow-lg shadow-primary/25 hover:brightness-110 disabled:opacity-70"
                  aria-busy={genLoading}
                >
                  {genLoading ? (
                    <span className="flex items-center justify-center gap-2">
                      <Spinner /> Generating…
                    </span>
                  ) : (
                    "Generate video"
                  )}
                </Button>
                {genLoading && (genUploadPct === null || genUploadPct >= 100) ? (
                  <div
                    className="absolute left-0 top-0 h-full bg-foreground/10 transition-[width] duration-150"
                    style={{ width: `${genProgress}%` }}
                  />
                ) : null}
              </div>
            </div>
            {videoSrc ? (
              <div className="overflow-hidden rounded-xl border border-border/50 bg-card pt-2 shadow-primaryGlow lg:col-span-7">
                {lastGenElapsedSec != null ? (
                  <p className="mb-3 px-2 text-sm text-muted-foreground" aria-live="polite">
                    Render time:{" "}
                    <span className="font-bold text-secondary">{formatElapsedSeconds(lastGenElapsedSec)}</span>
                  </p>
                ) : null}
                <video
                  key={videoSrc}
                  controls
                  className="mx-auto max-h-editor-preview-sm w-full max-w-3xl object-contain"
                  src={videoSrc}
                />
              </div>
            ) : null}
          </div>
        </section>
          </>
        ) : null}
      </form>
    </div>
  );
};
