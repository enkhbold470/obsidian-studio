import { Film } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { Link, Navigate, useParams } from "react-router-dom";
import type { AuthUser } from "../api";
import { getMe, getUserRenders, patchMe, type HistoryItem } from "../api";
import { formatElapsedSeconds } from "../formatElapsed";
import { panelClass } from "../lib/obsidianStyles";

export const RendersGallery = () => {
  const { userId } = useParams<{ userId: string }>();
  const id = userId ? Number.parseInt(userId, 10) : NaN;
  const [me, setMe] = useState<AuthUser | null | undefined>(undefined);
  const [skipAuth, setSkipAuth] = useState(false);
  const [items, setItems] = useState<HistoryItem[]>([]);
  const [galleryPublic, setGalleryPublic] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [toggleLoading, setToggleLoading] = useState(false);

  const load = useCallback(() => {
    if (Number.isNaN(id)) {
      return;
    }
    getUserRenders(id)
      .then((d) => {
        setItems(d.items ?? []);
        setGalleryPublic(Boolean(d.galleryPublic));
        setErr(null);
      })
      .catch((e: Error) => setErr(e.message));
  }, [id]);

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
    load();
  }, [load]);

  const handleTogglePublic = async () => {
    if (!me || me.id !== id) {
      return;
    }
    setToggleLoading(true);
    try {
      const next = !galleryPublic;
      await patchMe({ galleryPublic: next });
      setGalleryPublic(next);
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Toggle failed");
    } finally {
      setToggleLoading(false);
    }
  };

  if (me === undefined && !skipAuth) {
    return (
      <div className="px-6 py-16 text-center text-on-surface-variant" aria-live="polite">
        Loading…
      </div>
    );
  }
  if (Number.isNaN(id)) {
    return <Navigate to="/" replace />;
  }
  if (err === "Forbidden") {
    return (
      <div className="mx-auto max-w-lg px-6 py-16 text-center">
        <p className="font-headline text-lg font-bold text-error">Gallery unavailable</p>
        <p className="mt-2 text-sm text-on-surface-variant">This gallery is private or does not exist.</p>
        <Link
          className="mt-6 inline-block rounded-xl bg-primary px-5 py-2.5 text-sm font-bold text-on-primary transition hover:brightness-110"
          to="/"
        >
          Back to maker
        </Link>
      </div>
    );
  }

  const isOwner = Boolean(me && me.id === id);

  return (
    <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6">
      <div className="mb-10 flex flex-col gap-6 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <h1 className="font-headline text-3xl font-extrabold tracking-tight text-on-surface md:text-4xl">
            {isOwner ? "Your renders" : "Gallery"}
          </h1>
          <p className="mt-1 text-sm text-on-surface-variant">User #{id}</p>
        </div>
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:flex-wrap">
          {isOwner ? (
            <label
              className={`flex cursor-pointer items-start gap-3 rounded-xl border border-outline-variant/10 bg-surface-container px-4 py-3 transition ${toggleLoading ? "opacity-60" : ""}`}
            >
              <input
                type="checkbox"
                checked={galleryPublic}
                disabled={toggleLoading}
                onChange={handleTogglePublic}
                className="mt-0.5 h-4 w-4 shrink-0 rounded border-outline-variant text-primary focus:ring-primary"
                aria-label="Public gallery"
              />
              <span className="text-sm text-on-surface-variant">
                Public gallery — anyone with the link can view videos
              </span>
            </label>
          ) : null}
        </div>
      </div>

      {err && err !== "Forbidden" ? (
        <p className="mb-6 rounded-xl border border-error/30 bg-error/10 px-4 py-3 text-sm text-error" role="alert">
          {err}
        </p>
      ) : null}

      {items.length === 0 ? (
        <div className={panelClass}>
          <div className="flex flex-col items-center gap-3 py-12 text-center">
            <Film className="h-12 w-12 text-on-surface-variant/40" aria-hidden />
            <p className="text-on-surface-variant">No renders yet.</p>
            {isOwner ? (
              <Link
                to="/"
                className="mt-2 rounded-xl bg-primary px-5 py-2.5 text-sm font-bold text-on-primary transition hover:brightness-110"
              >
                Open editor
              </Link>
            ) : null}
          </div>
        </div>
      ) : (
        <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {items.map((h) => (
            <Link
              key={h.jobUid}
              to={`/u/${id}/renders/${h.jobUid}`}
              className="group overflow-hidden rounded-xl border border-outline-variant/10 bg-surface-container-low shadow-primaryGlow transition hover:border-primary/30 hover:bg-surface-container"
            >
              <div className="aspect-video bg-surface-container-lowest">
                <video
                  className="h-full w-full object-cover pointer-events-none transition group-hover:brightness-110"
                  src={`/api/output/${h.jobUid}`}
                  muted
                  playsInline
                  preload="metadata"
                />
              </div>
              <div className="space-y-1 p-4">
                <p className="truncate font-headline font-bold text-on-surface">
                  {h.topic?.trim() || "Untitled"}
                </p>
                <p className="text-xs text-on-surface-variant">
                  {new Date(h.createdAt).toLocaleString()}
                </p>
                {h.elapsedSeconds != null && Number.isFinite(h.elapsedSeconds) ? (
                  <p className="text-xs text-on-surface-variant">
                    Render:{" "}
                    <span className="font-semibold text-secondary">
                      {formatElapsedSeconds(h.elapsedSeconds)}
                    </span>
                  </p>
                ) : null}
                {h.renderMeta?.gpt_model || h.renderMeta?.tts_model ? (
                  <p
                    className="truncate font-mono text-[10px] text-outline"
                    title={[h.renderMeta?.gpt_model, h.renderMeta?.tts_model].filter(Boolean).join(" · ")}
                  >
                    {[h.renderMeta?.gpt_model, h.renderMeta?.tts_model].filter(Boolean).join(" · ")}
                  </p>
                ) : null}
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
};
