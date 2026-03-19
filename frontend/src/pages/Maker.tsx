import { FormEvent, useCallback, useEffect, useState } from "react";
import { Link, Navigate } from "react-router-dom";
import type { DialogueLine } from "../api";
import {
  getBackgrounds,
  getMe,
  getOptions,
  logout,
  postGenerate,
  postScript,
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

export const Maker = () => {
  const [authLoading, setAuthLoading] = useState(true);
  const [skipAuth, setSkipAuth] = useState(false);
  const [userEmail, setUserEmail] = useState<string | null>(null);

  const [topic, setTopic] = useState("");
  const [dialogueLines, setDialogueLines] = useState(8);
  const [ttsSpeed, setTtsSpeed] = useState(1.2);
  const [shakeSpeed, setShakeSpeed] = useState(15);
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
  const [bgFiles, setBgFiles] = useState<string[]>([]);
  const [bgBundled, setBgBundled] = useState("");
  const [bgFile, setBgFile] = useState<File | null>(null);

  const [lines, setLines] = useState<DialogueLine[]>([{ speaker: "Peter", text: "" }]);

  const [status, setStatus] = useState("");
  const [videoSrc, setVideoSrc] = useState<string | null>(null);
  const [draftLoading, setDraftLoading] = useState(false);
  const [genLoading, setGenLoading] = useState(false);

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
          setUserEmail(null);
        } else if (me.user) {
          setUserEmail(me.user.email);
        } else {
          setUserEmail(null);
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
    getBackgrounds().then((j: { files: string[] }) => {
      const files = j.files || [];
      setBgFiles(files);
      if (files.length && !bgBundled) {
        setBgBundled(files[0]);
      }
    });
  }, []);

  const handleLogout = async () => {
    await logout();
    setUserEmail(null);
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
    setStatus("Drafting script…");
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
      setStatus("Script ready — edit lines, pick background, then Generate video.");
    } catch (e) {
      setStatus(`Error: ${e instanceof Error ? e.message : "failed"}`);
    } finally {
      setDraftLoading(false);
    }
  };

  const handleBgUploadChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0] ?? null;
    setBgFile(f);
    if (f) {
      setBgBundled("");
    }
  };

  const handleBundledChange = (name: string) => {
    setBgBundled(name);
    setBgFile(null);
    const input = document.getElementById("bg-upload") as HTMLInputElement | null;
    if (input) {
      input.value = "";
    }
  };

  const buildFormData = useCallback(
    (e: FormEvent<HTMLFormElement>) => {
      e.preventDefault();
      const payload = toPayloadLines(lines);
      if (!isValidDialogue(payload)) {
        setStatus("Error: Add at least one dialogue line with text (or draft with AI).");
        return null;
      }
      const hasUpload = Boolean(bgFile);
      const hasBundled = !hasUpload && Boolean(bgBundled.trim());
      if (!hasUpload && !hasBundled) {
        setStatus("Error: Pick a storage/public video or upload a file.");
        return null;
      }
      const fd = new FormData(e.currentTarget);
      fd.set("dialogue", JSON.stringify(payload));
      if (hasUpload && bgFile) {
        fd.set("bg", bgFile);
        fd.delete("bg_bundled");
      } else {
        fd.set("bg_bundled", bgBundled);
      }
      return fd;
    },
    [lines, bgFile, bgBundled]
  );

  const handleGenerate = async (e: FormEvent<HTMLFormElement>) => {
    const fd = buildFormData(e);
    if (!fd) {
      return;
    }
    setGenLoading(true);
    setStatus("Generating…");
    setVideoSrc(null);
    const t = window.setTimeout(() => {
      setStatus((s) => (s.startsWith("Generating") ? "Still generating…" : s));
    }, 30000);
    try {
      const data = await postGenerate(fd);
      if (data.error) {
        throw new Error(String(data.error));
      }
      setStatus("Done");
      const path = data.file as string;
      setVideoSrc(path.startsWith("/") ? path : `/api/output/${path}`);
    } catch (err) {
      setStatus(`Error: ${err instanceof Error ? err.message : "failed"}`);
    } finally {
      window.clearTimeout(t);
      setGenLoading(false);
    }
  };

  if (authLoading) {
    return <p className="p-6">Loading…</p>;
  }
  if (!skipAuth && !userEmail) {
    return <Navigate to="/login" replace />;
  }

  return (
    <div className="max-w-4xl mx-auto p-4">
      <header className="flex flex-wrap items-center justify-between gap-2 border-b-2 border-black pb-2 mb-4">
        <h1 className="text-2xl font-bold">Brainrot Maker</h1>
        <div className="flex items-center gap-3 text-sm">
          {userEmail ? <span className="text-gray-700">{userEmail}</span> : null}
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

      <div className="grid gap-4 md:grid-cols-2 md:items-start">
        <form className="space-y-4" onSubmit={handleGenerate}>
          <div>
            <label className="block font-bold">Topic (for AI script draft)</label>
            <div className="flex gap-2">
              <textarea
                name="topic"
                rows={3}
                value={topic}
                onChange={(e) => setTopic(e.target.value)}
                placeholder="Paste a paragraph / dump for the debate topic…"
                className="flex-1 border-2 border-black p-2 resize-y min-h-[5rem]"
              />
              <button
                type="button"
                onClick={handleDraftScript}
                disabled={draftLoading}
                className="border-2 border-black px-3 font-bold hover:bg-gray-100 whitespace-nowrap text-sm leading-tight disabled:opacity-50"
              >
                Draft script
                <br />
                <span className="font-normal">with AI</span>
              </button>
            </div>
            <p className="text-sm text-gray-600 mt-1">
              <strong>Draft script with AI</strong> fills dialogue below. <strong>Generate video</strong> runs
              TTS + subs + mux only.
            </p>
          </div>

          <div>
            <label className="block font-bold">Dialogue</label>
            <DialogueEditor lines={lines} onChange={setLines} />
          </div>

          <div>
            <label className="block font-bold">Background video (9:16)</label>
            <p className="text-sm text-gray-600 mb-1">
              Bundled list from <code className="bg-gray-100 px-1">storage/public</code>
            </p>
            <div className="space-y-1 border-2 border-black p-2 text-sm">
              {bgFiles.length === 0 ? (
                <p className="text-gray-600">No videos — add .mp4 files under storage/public</p>
              ) : (
                bgFiles.map((name) => (
                  <label key={name} className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="radio"
                      name="bg_pick"
                      checked={bgBundled === name && !bgFile}
                      onChange={() => handleBundledChange(name)}
                      className="bg-pick"
                    />
                    <span className="font-mono text-xs break-all">{name}</span>
                  </label>
                ))
              )}
            </div>
            <label className="block font-bold mt-2" htmlFor="bg-upload">
              Or upload
            </label>
            <input
              id="bg-upload"
              name="bg"
              type="file"
              accept="video/*"
              onChange={handleBgUploadChange}
              className="w-full border-2 border-black p-2"
            />
            <input type="hidden" name="bg_bundled" value={bgBundled} readOnly />
            <p className="text-sm text-gray-600 mt-1">
              Pick a listed file <em>or</em> upload. Upload overrides.
            </p>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block font-bold">Dialogue lines (AI draft)</label>
              <input
                name="dialogue_lines"
                type="number"
                value={dialogueLines}
                min={2}
                max={20}
                onChange={(e) => setDialogueLines(Number(e.target.value))}
                className="w-full border-2 border-black p-2"
              />
            </div>
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
          </div>

          <div className="grid grid-cols-2 gap-4">
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

          <button
            type="submit"
            disabled={genLoading}
            className="w-full border-2 border-black bg-black text-white p-3 font-bold hover:bg-gray-800 disabled:opacity-50"
          >
            {genLoading ? "Generating… (~30s)" : "Generate video"}
          </button>
        </form>

        <div>
          {status ? (
            <div className="p-3 border-2 border-black whitespace-pre-wrap text-sm">{status}</div>
          ) : null}
          {videoSrc ? (
            <div className="mt-4">
              <video key={videoSrc} controls className="w-full border-2 border-black" src={videoSrc} />
            </div>
          ) : null}
        </div>
      </div>
    </div>
  );
};
