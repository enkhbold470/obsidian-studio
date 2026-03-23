import { useEffect, useState } from "react";
import { Link, Navigate, useParams } from "react-router-dom";
import type { AuthUser, RenderMeta } from "../api";
import { getMe, getUserRenders } from "../api";
import { formatElapsedSeconds } from "../formatElapsed";

export const RenderDetail = () => {
  const { userId, slug } = useParams<{ userId: string; slug: string }>();
  const id = userId ? Number.parseInt(userId, 10) : NaN;
  const [me, setMe] = useState<AuthUser | null | undefined>(undefined);
  const [skipAuth, setSkipAuth] = useState(false);
  const [topic, setTopic] = useState<string | null>(null);
  const [elapsedSec, setElapsedSec] = useState<number | null>(null);
  const [renderMeta, setRenderMeta] = useState<RenderMeta | null>(null);
  const [forbidden, setForbidden] = useState(false);
  const [notFound, setNotFound] = useState(false);

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

  if (me === undefined && !skipAuth) {
    return <p className="p-6">Loading…</p>;
  }
  if (Number.isNaN(id) || !slug) {
    return <Navigate to="/" replace />;
  }
  if (forbidden) {
    return (
      <div className="max-w-3xl mx-auto p-6">
        <p className="text-red-700 font-bold">You cannot view this video (private gallery).</p>
        <Link className="underline mt-2 inline-block" to="/">
          Home
        </Link>
      </div>
    );
  }
  if (notFound) {
    return (
      <div className="max-w-3xl mx-auto p-6">
        <p>Video not found.</p>
        <Link className="underline" to={`/u/${id}/renders`}>
          Back to gallery
        </Link>
      </div>
    );
  }

  const videoSrc = `/api/output/${slug}`;

  return (
    <div className="max-w-3xl mx-auto p-4">
      <div className="mb-4 flex flex-wrap gap-3 items-center">
        <Link className="underline font-bold" to={`/u/${id}/renders`}>
          ← All renders
        </Link>
        <Link className="underline text-sm" to="/">
          Maker
        </Link>
        {me ? (
          <span className="text-sm text-gray-600">{me.email}</span>
        ) : (
          <Link className="underline text-sm" to="/login">
            Log in
          </Link>
        )}
      </div>
      <h1 className="text-xl font-bold mb-2">{topic?.trim() || "Render"}</h1>
      {elapsedSec != null ? (
        <p className="text-sm text-gray-600 mb-2">
          Render time: <span className="font-semibold">{formatElapsedSeconds(elapsedSec)}</span>
        </p>
      ) : null}
      {renderMeta ? (
        <details className="mb-4 border-2 border-black p-3 bg-gray-50">
          <summary className="cursor-pointer font-bold">Saved settings &amp; script</summary>
          <dl className="mt-3 grid grid-cols-1 sm:grid-cols-2 gap-x-4 gap-y-2 text-sm">
            {renderMeta.gpt_model ? (
              <>
                <dt className="text-gray-600">AI model</dt>
                <dd className="font-mono">{renderMeta.gpt_model}</dd>
              </>
            ) : null}
            {renderMeta.tts_model ? (
              <>
                <dt className="text-gray-600">TTS model</dt>
                <dd className="font-mono">{renderMeta.tts_model}</dd>
              </>
            ) : null}
            {renderMeta.peter_voice ? (
              <>
                <dt className="text-gray-600">Peter voice</dt>
                <dd className="font-mono break-all">{renderMeta.peter_voice}</dd>
              </>
            ) : null}
            {renderMeta.stewie_voice ? (
              <>
                <dt className="text-gray-600">Stewie voice</dt>
                <dd className="font-mono break-all">{renderMeta.stewie_voice}</dd>
              </>
            ) : null}
            {renderMeta.tts_speed != null ? (
              <>
                <dt className="text-gray-600">TTS speed</dt>
                <dd>{renderMeta.tts_speed}</dd>
              </>
            ) : null}
            {renderMeta.shake_speed != null ? (
              <>
                <dt className="text-gray-600">Shake</dt>
                <dd>{renderMeta.shake_speed}</dd>
              </>
            ) : null}
            {renderMeta.font_name ? (
              <>
                <dt className="text-gray-600">Font</dt>
                <dd>
                  {renderMeta.font_name} {renderMeta.font_size != null ? `(${renderMeta.font_size}px)` : ""}
                </dd>
              </>
            ) : null}
            {renderMeta.text_color ? (
              <>
                <dt className="text-gray-600">Colors</dt>
                <dd className="font-mono text-xs">
                  text {renderMeta.text_color} / outline {renderMeta.outline_color ?? "—"}
                </dd>
              </>
            ) : null}
            {renderMeta.dialogue_lines != null ? (
              <>
                <dt className="text-gray-600">Draft line count</dt>
                <dd>{renderMeta.dialogue_lines}</dd>
              </>
            ) : null}
            {renderMeta.bg_source ? (
              <>
                <dt className="text-gray-600">Background</dt>
                <dd className="font-mono text-xs break-all">{renderMeta.bg_source}</dd>
              </>
            ) : null}
            {renderMeta.elapsed_seconds != null ? (
              <>
                <dt className="text-gray-600">Elapsed (saved)</dt>
                <dd>{formatElapsedSeconds(renderMeta.elapsed_seconds)}</dd>
              </>
            ) : null}
          </dl>
          {renderMeta.dialogue?.length ? (
            <div className="mt-3 border-t border-gray-300 pt-2">
              <p className="font-bold text-sm mb-1">Script</p>
              <ul className="text-sm space-y-1 max-h-48 overflow-y-auto">
                {renderMeta.dialogue.map((line, i) => (
                  <li key={i}>
                    <span className="font-semibold">{line.speaker}:</span> {line.text}
                  </li>
                ))}
              </ul>
            </div>
          ) : null}
        </details>
      ) : null}
      <p className="text-sm text-gray-600 mb-4">
        Share this page:{" "}
        <code className="bg-gray-100 px-1 break-all">{typeof window !== "undefined" ? window.location.href : ""}</code>
      </p>
      <video
        key={videoSrc}
        controls
        className="w-full border-2 border-black max-h-[80vh]"
        src={videoSrc}
      />
    </div>
  );
};
