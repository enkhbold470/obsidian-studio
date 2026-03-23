import { useCallback, useEffect, useState } from "react";
import { Link, Navigate, useParams } from "react-router-dom";
import type { AuthUser } from "../api";
import { getMe, getUserRenders, logout, patchMe, type HistoryItem } from "../api";
import { formatElapsedSeconds } from "../formatElapsed";

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
    return <p className="p-6">Loading…</p>;
  }
  if (Number.isNaN(id)) {
    return <Navigate to="/" replace />;
  }
  if (err === "Forbidden") {
    return (
      <div className="max-w-3xl mx-auto p-6">
        <p className="text-red-700 font-bold">This gallery is private or does not exist.</p>
        <Link className="underline mt-2 inline-block" to="/">
          Back to maker
        </Link>
      </div>
    );
  }

  const isOwner = Boolean(me && me.id === id);

  return (
    <div className="max-w-5xl mx-auto p-4">
      <header className="flex flex-wrap items-center justify-between gap-2 border-b-2 border-black pb-3 mb-6">
        <div>
          <h1 className="text-2xl font-bold">{isOwner ? "Your renders" : "Gallery"}</h1>
          <p className="text-sm text-gray-600">User #{id}</p>
        </div>
        <div className="flex items-center gap-3 flex-wrap">
          {isOwner ? (
            <label className="flex items-center gap-2 text-sm cursor-pointer">
              <input
                type="checkbox"
                checked={galleryPublic}
                disabled={toggleLoading}
                onChange={handleTogglePublic}
                className="h-4 w-4"
              />
              <span>Public gallery (anyone with the link can view videos)</span>
            </label>
          ) : null}
          <Link className="underline font-bold" to="/">
            Maker
          </Link>
          {me && !skipAuth ? (
            <button
              type="button"
              onClick={() => {
                logout().then(() => {
                  window.location.href = "/login";
                });
              }}
              className="border-2 border-black px-2 py-1 text-sm font-bold"
            >
              Log out
            </button>
          ) : null}
        </div>
      </header>

      {err && err !== "Forbidden" ? <p className="text-red-700 mb-4">{err}</p> : null}

      {items.length === 0 ? (
        <p className="text-gray-600">No renders yet.</p>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {items.map((h) => (
            <Link
              key={h.jobUid}
              to={`/u/${id}/renders/${h.jobUid}`}
              className="border-2 border-black block hover:bg-gray-50 overflow-hidden"
            >
              <div className="aspect-video bg-black">
                <video
                  className="w-full h-full object-cover pointer-events-none"
                  src={`/api/output/${h.jobUid}`}
                  muted
                  playsInline
                  preload="metadata"
                />
              </div>
              <div className="p-2 text-sm">
                <p className="font-bold truncate">{h.topic?.trim() || "Untitled"}</p>
                <p className="text-gray-600 text-xs">{new Date(h.createdAt).toLocaleString()}</p>
                {h.elapsedSeconds != null && Number.isFinite(h.elapsedSeconds) ? (
                  <p className="text-gray-600 text-xs mt-0.5">
                    Render: <span className="font-semibold">{formatElapsedSeconds(h.elapsedSeconds)}</span>
                  </p>
                ) : null}
                {h.renderMeta?.gpt_model || h.renderMeta?.tts_model ? (
                  <p className="text-gray-500 text-xs mt-0.5 font-mono truncate" title={[h.renderMeta?.gpt_model, h.renderMeta?.tts_model].filter(Boolean).join(" · ")}>
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
