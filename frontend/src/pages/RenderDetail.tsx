import {
  ArrowLeft,
  Calendar,
  Copy,
  Download,
  Film,
  Mic,
  Music,
  Timer,
} from "lucide-react";
import { useEffect, useState } from "react";
import { Link, Navigate, useParams } from "react-router-dom";
import type { AuthUser, RenderMeta } from "../api";
import { getMe, getUserRenders } from "../api";
import { formatElapsedSeconds } from "../formatElapsed";
import { panelClass } from "../lib/obsidianStyles";

export const RenderDetail = () => {
  const { userId, slug } = useParams<{ userId: string; slug: string }>();
  const id = userId ? Number.parseInt(userId, 10) : NaN;
  const [me, setMe] = useState<AuthUser | null | undefined>(undefined);
  const [skipAuth, setSkipAuth] = useState(false);
  const [topic, setTopic] = useState<string | null>(null);
  const [createdAt, setCreatedAt] = useState<string | null>(null);
  const [elapsedSec, setElapsedSec] = useState<number | null>(null);
  const [outputFormat, setOutputFormat] = useState<string | null>(null);
  const [renderMeta, setRenderMeta] = useState<RenderMeta | null>(null);
  const [forbidden, setForbidden] = useState(false);
  const [notFound, setNotFound] = useState(false);
  const [copyOk, setCopyOk] = useState(false);

  useEffect(() => {
    getMe().then((j) => {
      if (j.skipAuth) {
        setSkipAuth(true);
        setMe(null);
      } else {
        setMe(j.user);
      }
    });
  }, []);

  useEffect(() => {
    if (Number.isNaN(id) || !slug) {
      return;
    }
    getUserRenders(id)
      .then((d) => {
        const hit = (d.items ?? []).find((x) => x.jobUid === slug);
        if (!hit) {
          setNotFound(true);
          return;
        }
        setTopic(hit.topic);
        setCreatedAt(hit.createdAt ?? null);
        setOutputFormat(hit.outputFormat ?? null);
        const es = hit.elapsedSeconds;
        setElapsedSec(typeof es === "number" && Number.isFinite(es) ? es : null);
        setRenderMeta(hit.renderMeta ?? null);
        setNotFound(false);
        setForbidden(false);
      })
      .catch((e: Error) => {
        if (e.message === "Forbidden") {
          setForbidden(true);
        }
      });
  }, [id, slug]);

  const handleCopyLink = async () => {
    const url = typeof window !== "undefined" ? window.location.href : "";
    try {
      await navigator.clipboard.writeText(url);
      setCopyOk(true);
      setTimeout(() => setCopyOk(false), 2000);
    } catch {
      setCopyOk(false);
    }
  };

  if (me === undefined && !skipAuth) {
    return (
      <div className="px-6 py-16 text-center text-on-surface-variant" aria-live="polite">
        Loading…
      </div>
    );
  }
  if (Number.isNaN(id) || !slug) {
    return <Navigate to="/" replace />;
  }
  if (forbidden) {
    return (
      <div className="mx-auto max-w-lg px-6 py-16 text-center">
        <p className="font-headline text-lg font-bold text-error">Private gallery</p>
        <p className="mt-2 text-sm text-on-surface-variant">You cannot view this video.</p>
        <Link
          className="mt-6 inline-block rounded-xl bg-primary px-5 py-2.5 text-sm font-bold text-on-primary transition hover:brightness-110"
          to="/"
        >
          Home
        </Link>
      </div>
    );
  }
  if (notFound) {
    return (
      <div className="mx-auto max-w-lg px-6 py-16 text-center">
        <p className="font-headline text-lg font-bold text-on-surface">Video not found</p>
        <Link
          className="mt-6 inline-block text-sm font-semibold text-secondary hover:underline"
          to={`/u/${id}/renders`}
        >
          ← All renders
        </Link>
      </div>
    );
  }

  const videoSrc = `/api/output/${slug}`;
  const shareUrl = typeof window !== "undefined" ? window.location.href : "";
  const dateLabel = createdAt
    ? new Date(createdAt).toLocaleDateString(undefined, {
        year: "numeric",
        month: "short",
        day: "numeric",
      })
    : null;

  return (
    <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6">
      <div className="mb-8 flex flex-col justify-between gap-4 md:flex-row md:items-center">
        <div className="flex flex-wrap items-center gap-3">
          <Link
            className="group inline-flex items-center gap-2 text-sm font-medium text-on-surface-variant transition-colors hover:text-on-surface"
            to={`/u/${id}/renders`}
          >
            <ArrowLeft className="h-4 w-4" aria-hidden />
            <span>All renders</span>
          </Link>
          <span className="text-outline-variant/40" aria-hidden>
            |
          </span>
          <Link
            className="font-headline text-sm font-extrabold uppercase tracking-widest text-secondary transition hover:brightness-110"
            to="/"
          >
            Maker
          </Link>
        </div>
        {me ? (
          <div className="flex items-center gap-2 rounded-xl border border-outline-variant/10 bg-surface-container px-4 py-2">
            <span className="h-2 w-2 shrink-0 rounded-full bg-secondary" aria-hidden />
            <span className="text-xs font-medium text-on-surface-variant">{me.email}</span>
          </div>
        ) : (
          <Link
            className="text-sm font-semibold text-primary hover:underline"
            to="/login"
          >
            Log in
          </Link>
        )}
      </div>

      <div className="mb-10">
        <h1 className="font-headline text-3xl font-extrabold tracking-tight text-on-surface md:text-4xl lg:text-5xl">
          {topic?.trim() || "Render"}
        </h1>
        <div className="mt-3 flex flex-wrap items-center gap-4 text-sm text-on-surface-variant">
          {dateLabel ? (
            <span className="inline-flex items-center gap-1.5">
              <Calendar className="h-4 w-4" aria-hidden />
              {dateLabel}
            </span>
          ) : null}
          {elapsedSec != null ? (
            <span className="inline-flex items-center gap-1.5">
              <Timer className="h-4 w-4" aria-hidden />
              {formatElapsedSeconds(elapsedSec)}
            </span>
          ) : null}
          {outputFormat ? (
            <span className="rounded bg-surface-container-highest px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider text-primary">
              {outputFormat} render
            </span>
          ) : null}
        </div>
      </div>

      <div className="grid grid-cols-1 gap-8 lg:grid-cols-12">
        <div className="space-y-6 lg:col-span-9">
          <div className="relative overflow-hidden rounded-xl border border-outline-variant/10 bg-surface-container-low shadow-2xl">
            <video
              key={videoSrc}
              controls
              className="aspect-video max-h-[80vh] w-full object-contain"
              src={videoSrc}
            />
            <div
              className="pointer-events-none absolute inset-x-0 bottom-0 h-24 bg-gradient-to-t from-black/60 to-transparent"
              aria-hidden
            />
          </div>

          <div className="flex flex-wrap items-center justify-between gap-4 p-1">
            <a
              href={videoSrc}
              download
              className="inline-flex items-center gap-2 rounded-xl bg-primary px-6 py-3 font-label text-sm font-bold text-on-primary shadow-lg shadow-primary/20 transition hover:brightness-110 active:scale-[0.98]"
            >
              <Download className="h-5 w-5" aria-hidden />
              Download
            </a>
            <Link
              to="/"
              className="inline-flex items-center gap-2 rounded-xl border border-outline-variant/20 bg-surface-container-highest px-6 py-3 font-label text-sm font-bold text-on-surface transition hover:bg-surface-bright active:scale-[0.98]"
            >
              Open in Editor
            </Link>
          </div>
        </div>

        <aside className="space-y-8 lg:col-span-3">
          <div className={panelClass}>
            <h3 className="mb-4 font-label text-xs font-bold uppercase tracking-widest text-on-surface-variant">
              Share this page
            </h3>
            <div className="relative">
              <input
                readOnly
                type="text"
                value={shareUrl}
                className="w-full rounded-lg border border-outline-variant/20 bg-surface-container-lowest py-3 pl-3 pr-11 font-mono text-xs text-on-surface-variant focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
                aria-label="Share link"
              />
              <button
                type="button"
                onClick={handleCopyLink}
                className="absolute right-2 top-1/2 -translate-y-1/2 rounded-lg p-1.5 text-primary transition hover:bg-surface-container-highest hover:text-on-surface"
                aria-label={copyOk ? "Copied" : "Copy link"}
              >
                <Copy className="h-5 w-5" aria-hidden />
              </button>
            </div>
            {copyOk ? (
              <p className="mt-2 text-xs font-medium text-secondary" role="status">
                Copied to clipboard
              </p>
            ) : null}
          </div>

          {renderMeta ? (
            <div className={panelClass}>
              <h3 className="mb-6 font-label text-xs font-bold uppercase tracking-widest text-on-surface-variant">
                Render details
              </h3>
              <div className="space-y-5">
                <div className="flex gap-4">
                  <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
                    <Film className="h-5 w-5" aria-hidden />
                  </div>
                  <div className="min-w-0">
                    <p className="text-[10px] font-bold uppercase tracking-wider text-outline">AI model</p>
                    <p className="truncate text-sm font-medium text-on-surface">
                      {renderMeta.gpt_model ?? "—"}
                    </p>
                  </div>
                </div>
                <div className="flex gap-4">
                  <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-secondary/10 text-secondary">
                    <Mic className="h-5 w-5" aria-hidden />
                  </div>
                  <div className="min-w-0">
                    <p className="text-[10px] font-bold uppercase tracking-wider text-outline">TTS</p>
                    <p className="truncate font-mono text-sm text-on-surface">
                      {renderMeta.tts_model ?? "—"}
                    </p>
                  </div>
                </div>
                <div className="flex gap-4">
                  <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-tertiary/10 text-tertiary">
                    <Music className="h-5 w-5" aria-hidden />
                  </div>
                  <div className="min-w-0">
                    <p className="text-[10px] font-bold uppercase tracking-wider text-outline">Voices</p>
                    <p className="break-all text-xs text-on-surface">
                      Peter: {renderMeta.peter_voice ?? "—"}
                    </p>
                    <p className="break-all text-xs text-on-surface-variant">
                      Stewie: {renderMeta.stewie_voice ?? "—"}
                    </p>
                  </div>
                </div>
              </div>

              <details className="mt-6 border-t border-outline-variant/10 pt-4">
                <summary className="cursor-pointer font-label text-xs font-bold uppercase tracking-wider text-primary">
                  Full settings &amp; script
                </summary>
                <dl className="mt-4 grid grid-cols-1 gap-3 text-sm">
                  {renderMeta.tts_speed != null ? (
                    <>
                      <dt className="text-on-surface-variant">TTS speed</dt>
                      <dd>{renderMeta.tts_speed}</dd>
                    </>
                  ) : null}
                  {renderMeta.shake_speed != null ? (
                    <>
                      <dt className="text-on-surface-variant">Shake</dt>
                      <dd>{renderMeta.shake_speed}</dd>
                    </>
                  ) : null}
                  {renderMeta.font_name ? (
                    <>
                      <dt className="text-on-surface-variant">Font</dt>
                      <dd>
                        {renderMeta.font_name}{" "}
                        {renderMeta.font_size != null ? `(${renderMeta.font_size}px)` : ""}
                      </dd>
                    </>
                  ) : null}
                  {renderMeta.text_color ? (
                    <>
                      <dt className="text-on-surface-variant">Colors</dt>
                      <dd className="font-mono text-xs">
                        text {renderMeta.text_color} / outline {renderMeta.outline_color ?? "—"}
                      </dd>
                    </>
                  ) : null}
                  {renderMeta.dialogue_lines != null ? (
                    <>
                      <dt className="text-on-surface-variant">Draft line count</dt>
                      <dd>{renderMeta.dialogue_lines}</dd>
                    </>
                  ) : null}
                  {renderMeta.bg_source ? (
                    <>
                      <dt className="text-on-surface-variant">Background</dt>
                      <dd className="break-all font-mono text-xs">{renderMeta.bg_source}</dd>
                    </>
                  ) : null}
                  {renderMeta.elapsed_seconds != null ? (
                    <>
                      <dt className="text-on-surface-variant">Elapsed (saved)</dt>
                      <dd>{formatElapsedSeconds(renderMeta.elapsed_seconds)}</dd>
                    </>
                  ) : null}
                </dl>
                {renderMeta.dialogue?.length ? (
                  <div className="mt-4 max-h-48 overflow-y-auto rounded-lg border border-outline-variant/10 bg-surface-container-low p-3 custom-scrollbar">
                    <p className="mb-2 font-label text-xs font-bold text-on-surface-variant">Script</p>
                    <ul className="space-y-2 text-sm">
                      {renderMeta.dialogue.map((line, i) => (
                        <li key={i}>
                          <span className="font-semibold text-secondary">{line.speaker}:</span>{" "}
                          <span className="text-on-surface-variant">{line.text}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                ) : null}
              </details>
            </div>
          ) : null}
        </aside>
      </div>
    </div>
  );
};
