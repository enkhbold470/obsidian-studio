import { useEffect, useState } from "react";
import { Link, Navigate, useParams } from "react-router-dom";
import type { AuthUser } from "../api";
import { getMe, getUserRenders } from "../api";

export const RenderDetail = () => {
  const { userId, slug } = useParams<{ userId: string; slug: string }>();
  const id = userId ? Number.parseInt(userId, 10) : NaN;
  const [me, setMe] = useState<AuthUser | null | undefined>(undefined);
  const [skipAuth, setSkipAuth] = useState(false);
  const [topic, setTopic] = useState<string | null>(null);
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
