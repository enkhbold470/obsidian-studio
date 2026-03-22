import { FormEvent, useCallback, useEffect, useRef, useState } from "react";
import { Link, Navigate } from "react-router-dom";
import type { AuthUser, BackgroundItem, DialogueLine } from "../api";
import {
  deleteBackground,
  getBackgrounds,
  getMe,
  getOptions,
  logout,
  postGenerate,
  postScript,
  uploadBackground,
} from "../api";
import {
  DialogueEditor,
  isValidDialogue,
  toPayloadLines,
} from "../components/DialogueEditor";

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
  const [peterVoice, setPeterVoice] = useState("echo");
  const [stewieVoice, setStewieVoice] = useState("alloy");
  const [gptModel, setGptModel] = useState("gpt-5.4");
  const [ttsModel, setTtsModel] = useState("tts-1");

  const [options, setOptions] = useState<OptionsPayload | null>(null);
  const [bgItems, setBgItems] = useState<BackgroundItem[]>([]);
  const [savedBgId, setSavedBgId] = useState("");
  const [bgFile, setBgFile] = useState<File | null>(null);
  const [bgLoadErr, setBgLoadErr] = useState<string | null>(null);

  const [lines, setLines] = useState<DialogueLine[]>([{ speaker: "Peter", text: "" }]);

  const [formError, setFormError] = useState("");
  const [videoSrc, setVideoSrc] = useState<string | null>(null);
  const [draftLoading, setDraftLoading] = useState(false);
  const [genLoading, setGenLoading] = useState(false);
  const [genProgress, setGenProgress] = useState(0);
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
    });
  }, []);

  useEffect(() => {
    refreshBackgrounds();
  }, [refreshBackgrounds]);

  useEffect(() => {
    if (!genLoading) {
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
  }, [genLoading]);

  const handleLogout = async () => {
    await logout();
    setUser(null);
    window.location.href = "/login";
  };

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
    setFormError("");
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
    } catch (e) {
      setFormError(e instanceof Error ? e.message : "Draft failed");
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
      setFormError(e instanceof Error ? e.message : "Delete failed");
    }
  };

  const handleUploadToLibrary = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    if (!f) {
      return;
    }
    setFormError("");
    try {
      await uploadBackground(f);
      refreshBackgrounds();
    } catch (err) {
      setFormError(err instanceof Error ? err.message : "Upload failed");
    }
    e.target.value = "";
  };

  const buildFormData = useCallback(
    (e: FormEvent<HTMLFormElement>) => {
      e.preventDefault();
      const payload = toPayloadLines(lines);
      if (!isValidDialogue(payload)) {
        setFormError("Add at least one dialogue line with text (or draft with AI).");
        return null;
      }
      const hasUpload = Boolean(bgFile);
      const hasSaved = Boolean(savedBgId.trim());
      if (!hasUpload && !hasSaved) {
        setFormError("Select a saved background or upload a video file.");
        return null;
      }
      if (hasUpload && hasSaved) {
        setFormError("Use either a saved background or a new file, not both.");
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

  const handleGenerate = async (e: FormEvent<HTMLFormElement>) => {
    const fd = buildFormData(e);
    if (!fd) {
      return;
    }
    setGenLoading(true);
    setGenProgress(0);
    setFormError("");
    setVideoSrc(null);
    try {
      const data = await postGenerate(fd);
      if (data.error) {
        throw new Error(String(data.error));
      }
      setGenProgress(100);
      const path = data.file as string;
      setVideoSrc(path.startsWith("/") ? path : `/api/output/${path}`);
      refreshBackgrounds();
    } catch (err) {
      setFormError(err instanceof Error ? err.message : "failed");
    } finally {
      setGenLoading(false);
      setTimeout(() => setGenProgress(0), 400);
    }
  };

  if (authLoading) {
    return <p className="p-6">Loading…</p>;
  }
  if (!skipAuth && !user) {
    return <Navigate to="/login" replace />;
  }

  return (
    <div className="max-w-3xl mx-auto p-4">
      <header className="flex flex-wrap items-center justify-between gap-2 border-b-2 border-black pb-2 mb-6">
        <h1 className="text-2xl font-bold">Brainrot Maker</h1>
        <div className="flex items-center gap-3 text-sm">
          {user ? (
            <>
              <span className="text-gray-700">{user.email}</span>
              <Link className="underline font-bold" to={`/u/${user.id}/renders`}>
                Your renders
              </Link>
            </>
          ) : null}
          {skipAuth ? (
            <span className="text-amber-800 font-bold">Auth disabled (dev)</span>
          ) : null}
          {!skipAuth ? (
            <button
              type="button"
              onClick={handleLogout}
              className="border-2 border-black px-2 py-1 font-bold hover:bg-gray-100"
            >
              Log out
            </button>
          ) : (
            <Link className="underline font-bold" to="/login">
              Login anyway
            </Link>
          )}
        </div>
      </header>

      <form className="space-y-6" onSubmit={handleGenerate}>
        <div>
          <label className="block font-bold">Topic (for AI script draft)</label>
          <textarea
            name="topic"
            rows={3}
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
            placeholder="Paste a paragraph / dump for the debate topic…"
            className="mt-1 w-full border-2 border-black p-2 resize-y min-h-[5rem]"
          />
          <p className="text-sm text-gray-600 mt-1">
            <strong>Draft script with AI</strong> uses the line count below. <strong>Generate video</strong> runs TTS +
            subs + mux.
          </p>
        </div>

        <div>
          <label className="block font-bold">Dialogue lines (AI draft)</label>
          <input
            name="dialogue_lines"
            type="number"
            value={dialogueLines}
            min={2}
            max={20}
            onChange={(e) => setDialogueLines(Number(e.target.value))}
            className="mt-1 w-full max-w-xs border-2 border-black p-2"
          />
          <p className="text-sm text-gray-600 mt-1">Used when you click “Draft script with AI”.</p>
        </div>

        <div>
          <button
            type="button"
            onClick={handleDraftScript}
            disabled={draftLoading}
            className="inline-flex items-center gap-2 border-2 border-black px-4 py-2 font-bold hover:bg-gray-100 disabled:opacity-50"
          >
            {draftLoading ? <Spinner /> : null}
            Draft script with AI
          </button>
        </div>

        <div>
          <label className="block font-bold">Dialogue</label>
          <DialogueEditor lines={lines} onChange={setLines} />
        </div>

        <div>
          <label className="block font-bold">Background video</label>
          <p className="text-sm text-gray-600 mb-2">
            Videos are stored in your account (S3/MinIO). Upload adds to your library; each generate from a new file
            also saves a copy to the library.
          </p>
          {bgLoadErr ? (
            <p className="text-amber-800 text-sm mb-2 border border-amber-600 p-2">{bgLoadErr}</p>
          ) : null}
          <div className="grid gap-3 sm:grid-cols-2">
            {bgItems.map((b) => (
              <div
                key={b.id}
                className={`relative border-2 p-1 ${savedBgId === b.id ? "border-black ring-2 ring-black" : "border-gray-300"}`}
              >
                <button
                  type="button"
                  onClick={() => handlePickSaved(b.id)}
                  className="block w-full text-left"
                >
                  <div className="aspect-video bg-black">
                    <video
                      className="w-full h-full object-cover pointer-events-none"
                      src={b.streamUrl}
                      muted
                      playsInline
                      preload="metadata"
                    />
                  </div>
                  <p className="text-xs p-1 truncate font-mono">{b.filename}</p>
                </button>
                <button
                  type="button"
                  onClick={() => handleDeleteBg(b.id, b.filename)}
                  className="absolute top-1 right-1 bg-white border border-black text-xs px-1 font-bold hover:bg-red-50"
                  aria-label={`Delete ${b.filename}`}
                >
                  ×
                </button>
              </div>
            ))}
          </div>
          <div className="mt-3 space-y-2">
            <label className="block text-sm font-bold" htmlFor="bg-upload">
              Upload for this render (not saved until generate completes — then copied to library)
            </label>
            <input
              id="bg-upload"
              name="bg"
              type="file"
              accept="video/*"
              onChange={handleBgUploadChange}
              className="w-full border-2 border-black p-2"
            />
            <label className="block text-sm font-bold" htmlFor="lib-upload">
              Add to library only
            </label>
            <input
              id="lib-upload"
              type="file"
              accept="video/*"
              onChange={handleUploadToLibrary}
              className="w-full border-2 border-dashed border-gray-400 p-2 text-sm"
            />
          </div>
          <input type="hidden" name="bg_saved_id" value={savedBgId} readOnly />
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block font-bold">TTS speed</label>
            <input
              name="tts_speed"
              type="number"
              step={0.1}
              value={ttsSpeed}
              min={0.5}
              max={2}
              onChange={(e) => setTtsSpeed(Number(e.target.value))}
              className="w-full border-2 border-black p-2"
            />
          </div>
          <div>
            <label className="block font-bold">Shake speed (lower=slower)</label>
            <input
              name="shake_speed"
              type="number"
              value={shakeSpeed}
              min={5}
              max={50}
              onChange={(e) => setShakeSpeed(Number(e.target.value))}
              className="w-full border-2 border-black p-2"
            />
          </div>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block font-bold">Output</label>
            <select
              name="output_format"
              value={outputFormat}
              onChange={(e) => setOutputFormat(e.target.value)}
              className="w-full border-2 border-black p-2"
            >
              <option value="mp4">MP4</option>
              <option value="mkv">MKV</option>
            </select>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block font-bold">Font</label>
            <select
              name="font_name"
              value={fontName}
              onChange={(e) => setFontName(e.target.value)}
              className="w-full border-2 border-black p-2"
            >
              {(options?.fonts ?? ["Arial"]).map((f) => (
                <option key={f} value={f}>
                  {f}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="block font-bold">Font size</label>
            <input
              name="font_size"
              type="number"
              value={fontSize}
              min={40}
              max={200}
              onChange={(e) => setFontSize(Number(e.target.value))}
              className="w-full border-2 border-black p-2"
            />
          </div>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block font-bold">Text color</label>
            <input
              name="text_color"
              type="color"
              value={textColor}
              onChange={(e) => setTextColor(e.target.value)}
              className="w-full h-10 border-2 border-black cursor-pointer"
            />
          </div>
          <div>
            <label className="block font-bold">Outline color</label>
            <input
              name="outline_color"
              type="color"
              value={outlineColor}
              onChange={(e) => setOutlineColor(e.target.value)}
              className="w-full h-10 border-2 border-black cursor-pointer"
            />
          </div>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block font-bold">Peter voice</label>
            <select
              name="peter_voice"
              value={peterVoice}
              onChange={(e) => setPeterVoice(e.target.value)}
              className="w-full border-2 border-black p-2"
            >
              {(options?.tts_voices ?? ["echo"]).map((v) => (
                <option key={v} value={v}>
                  {v}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="block font-bold">Stewie voice</label>
            <select
              name="stewie_voice"
              value={stewieVoice}
              onChange={(e) => setStewieVoice(e.target.value)}
              className="w-full border-2 border-black p-2"
            >
              {(options?.tts_voices ?? ["alloy"]).map((v) => (
                <option key={`s-${v}`} value={v}>
                  {v}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block font-bold">GPT model</label>
            <select
              name="gpt_model"
              value={gptModel}
              onChange={(e) => setGptModel(e.target.value)}
              className="w-full border-2 border-black p-2"
            >
              {(options?.gpt_models ?? [gptModel]).map((m) => (
                <option key={m} value={m}>
                  {m}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="block font-bold">TTS model</label>
            <select
              name="tts_model"
              value={ttsModel}
              onChange={(e) => setTtsModel(e.target.value)}
              className="w-full border-2 border-black p-2"
            >
              {(options?.tts_models ?? [ttsModel]).map((m) => (
                <option key={m} value={m}>
                  {m}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div className="relative overflow-hidden border-2 border-black">
          <button
            type="submit"
            disabled={genLoading}
            className="relative z-10 w-full bg-black text-white p-3 font-bold hover:bg-gray-800 disabled:opacity-70"
          >
            {genLoading ? (
              <span className="flex items-center justify-center gap-2">
                <Spinner /> Generating…
              </span>
            ) : (
              "Generate video"
            )}
          </button>
          {genLoading ? (
            <div
              className="absolute left-0 top-0 h-full bg-white/25 transition-[width] duration-150"
              style={{ width: `${genProgress}%` }}
            />
          ) : null}
        </div>
        {formError ? (
          <p className="text-sm text-red-700 border border-red-300 p-2" role="alert">
            {formError}
          </p>
        ) : null}

        {videoSrc ? (
          <div className="pt-2">
            <video key={videoSrc} controls className="w-full border-2 border-black max-h-[70vh]" src={videoSrc} />
          </div>
        ) : null}
      </form>
    </div>
  );
};
