/** Format server-side generation duration for display. */
export const formatElapsedSeconds = (sec: number): string => {
  if (!Number.isFinite(sec) || sec < 0) {
    return "—";
  }
  if (sec < 60) {
    return sec < 10 ? `${sec.toFixed(1)} s` : `${Math.round(sec)} s`;
  }
  const m = Math.floor(sec / 60);
  const s = Math.round(sec % 60);
  return `${m}m ${s}s`;
};
