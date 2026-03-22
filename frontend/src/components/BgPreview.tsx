import { useState } from "react";
import type { BackgroundItem } from "../api";

type Props = { item: BackgroundItem };

/** Lazy JPEG thumbnail with fallback to lightweight video. */
export const BgPreview = ({ item }: Props) => {
  const [useVideoFallback, setUseVideoFallback] = useState(!item.thumbUrl);

  if (useVideoFallback) {
    return (
      <video
        className="w-full h-full object-cover pointer-events-none"
        src={item.streamUrl}
        muted
        playsInline
        preload="none"
      />
    );
  }

  return (
    <img
      src={item.thumbUrl}
      alt=""
      loading="lazy"
      decoding="async"
      className="w-full h-full object-cover"
      onError={() => setUseVideoFallback(true)}
    />
  );
};
