import { Film } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { Link, Navigate, useParams } from "react-router-dom";
import { toast } from "sonner";
import type { AuthUser } from "../api";
import { apiUrl, getMe, getUserRenders, patchMe, type HistoryItem } from "../api";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";
import { formatElapsedSeconds } from "../formatElapsed";
import { panelClass } from "../lib/obsidianStyles";

const outputThumbPath = (jobUid: string, thumbUrl?: string) =>
  thumbUrl?.startsWith("/") ? thumbUrl : `/api/output/${jobUid}/thumb`;

const RenderCardThumb = ({ jobUid, thumbUrl }: { jobUid: string; thumbUrl?: string }) => {
  const [failed, setFailed] = useState(false);
  const src = apiUrl(outputThumbPath(jobUid, thumbUrl));

  if (failed) {
    return (
      <div className="flex h-full min-h-[8rem] w-full items-center justify-center bg-muted/50" aria-hidden>
        <Film className="h-14 w-14 text-muted-foreground/35" />
      </div>
    );
  }

  return (
    <img
      src={src}
      alt=""
      loading="lazy"
      decoding="async"
      className="h-full w-full object-cover transition group-hover:brightness-110"
      onError={() => setFailed(true)}
    />
  );
};

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
      .catch((e: Error) => {
        if (e.message === "Forbidden") {
          setErr("Forbidden");
        } else {
          toast.error(e.message || "Failed to load gallery");
          setErr(null);
        }
      });
  }, [id]);

  useEffect(() => {
    getMe()
      .then((j) => {
        if (j.skipAuth) {
          setSkipAuth(true);
          setMe(null);
        } else {
          setMe(j.user);
        }
      })
      .catch(() => {
        setMe(null);
      });
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const handleTogglePublic = async (checked: boolean) => {
    if (!me || me.id !== id) {
      return;
    }
    setToggleLoading(true);
    try {
      await patchMe({ galleryPublic: checked });
      setGalleryPublic(checked);
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Toggle failed");
    } finally {
      setToggleLoading(false);
    }
  };

  if (me === undefined && !skipAuth) {
    return (
      <div className="px-6 py-16 text-center text-muted-foreground" aria-live="polite">
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
        <p className="font-headline text-lg font-bold text-destructive">Gallery unavailable</p>
        <p className="mt-2 text-sm text-muted-foreground">This gallery is private or does not exist.</p>
        <Button asChild className="mt-6">
          <Link to="/">Back to maker</Link>
        </Button>
      </div>
    );
  }

  const isOwner = Boolean(me && me.id === id);

  return (
    <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6">
      <div className="mb-10 flex flex-col gap-6 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <h1 className="font-headline text-3xl font-extrabold tracking-tight text-foreground md:text-4xl">
            {isOwner ? "Your renders" : "Gallery"}
          </h1>
          <p className="mt-1 text-sm text-muted-foreground">User #{id}</p>
        </div>
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:flex-wrap">
          {isOwner ? (
            <div
              className={`flex max-w-md cursor-pointer items-start gap-3 rounded-xl border border-border bg-card px-4 py-3 text-card-foreground shadow-sm transition ${toggleLoading ? "opacity-60" : ""}`}
            >
              <Checkbox
                id="gallery-public"
                checked={galleryPublic}
                disabled={toggleLoading}
                onCheckedChange={(v) => {
                  if (v === "indeterminate") {
                    return;
                  }
                  void handleTogglePublic(v);
                }}
                className="mt-0.5"
                aria-label="Public gallery"
              />
              <Label htmlFor="gallery-public" className="cursor-pointer text-sm font-normal leading-snug text-muted-foreground">
                Public gallery — anyone with the link can view videos
              </Label>
            </div>
          ) : null}
        </div>
      </div>

      {items.length === 0 ? (
        <div className={panelClass}>
          <div className="flex flex-col items-center gap-3 py-12 text-center">
            <Film className="h-12 w-12 text-muted-foreground/40" aria-hidden />
            <p className="text-muted-foreground">No renders yet.</p>
            {isOwner ? (
              <Button asChild className="mt-2">
                <Link to="/">Open editor</Link>
              </Button>
            ) : null}
          </div>
        </div>
      ) : (
        <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {items.map((h) => (
            <Link
              key={h.jobUid}
              to={`/u/${id}/renders/${h.jobUid}`}
              className="group overflow-hidden rounded-xl border border-border/50 bg-card shadow-primaryGlow transition hover:border-primary/30 hover:bg-muted/50"
            >
              <div className="relative aspect-video overflow-hidden bg-muted/30">
                <RenderCardThumb jobUid={h.jobUid} thumbUrl={h.thumbUrl} />
              </div>
              <div className="space-y-1 p-4">
                <p className="truncate font-headline font-bold text-foreground">
                  {h.topic?.trim() || "Untitled"}
                </p>
                <p className="text-xs text-muted-foreground">
                  {new Date(h.createdAt).toLocaleString()}
                </p>
                {h.elapsedSeconds != null && Number.isFinite(h.elapsedSeconds) ? (
                  <p className="text-xs text-muted-foreground">
                    Render:{" "}
                    <span className="font-semibold text-secondary">
                      {formatElapsedSeconds(h.elapsedSeconds)}
                    </span>
                  </p>
                ) : null}
                {h.renderMeta?.gpt_model || h.renderMeta?.tts_model ? (
                  <p
                    className="truncate font-mono text-[10px] text-muted-foreground/80"
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
