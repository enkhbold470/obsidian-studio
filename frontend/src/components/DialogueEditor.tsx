import { useCallback } from "react";
import type { DialogueLine } from "../api";
import { inputClass, selectClass } from "../lib/obsidianStyles";

type DialogueEditorProps = {
  lines: DialogueLine[];
  onChange: (lines: DialogueLine[]) => void;
  /** Fills parent on large screens (parent should be flex column with min-h-0). */
  layout?: "default" | "fill";
};

const emptyLine = (): DialogueLine => ({ speaker: "Peter", text: "" });

const lineSelectClass = `${selectClass} dlg-speaker max-w-[8rem] shrink-0`;

export const DialogueEditor = ({ lines, onChange, layout = "default" }: DialogueEditorProps) => {
  const handleAddLine = useCallback(() => {
    onChange([...lines, emptyLine()]);
  }, [lines, onChange]);

  const handleRemove = useCallback(
    (index: number) => {
      const next = lines.filter((_, i) => i !== index);
      onChange(next.length ? next : [emptyLine()]);
    },
    [lines, onChange]
  );

  const handleSpeaker = useCallback(
    (index: number, speaker: DialogueLine["speaker"]) => {
      const next = lines.map((l, i) => (i === index ? { ...l, speaker } : l));
      onChange(next);
    },
    [lines, onChange]
  );

  const handleText = useCallback(
    (index: number, text: string) => {
      const next = lines.map((l, i) => (i === index ? { ...l, text } : l));
      onChange(next);
    },
    [lines, onChange]
  );

  const scrollBoxClass =
    layout === "fill"
      ? "dlg-scroll custom-scrollbar min-h-dialogue-panel-min flex-1 space-y-2 overflow-auto rounded-xl border border-outline-variant/10 bg-surface-container-lowest p-3 lg:min-h-0"
      : "dlg-scroll custom-scrollbar max-h-dialogue-panel min-h-dialogue-panel-min space-y-2 rounded-xl border border-outline-variant/10 bg-surface-container-lowest p-3";

  return (
    <div
      className={
        layout === "fill"
          ? "flex min-h-0 flex-1 flex-col gap-3 lg:min-h-64"
          : "space-y-3"
      }
    >
      <p className="shrink-0 text-sm text-on-surface-variant">
        Scroll inside the box — horizontal and vertical scrollbars stay visible when content overflows.
      </p>
      <div className={scrollBoxClass}>
        {lines.map((line, index) => (
          <div key={index} className="flex gap-2 items-start">
            <label className="sr-only" htmlFor={`sp-${index}`}>
              Speaker line {index + 1}
            </label>
            <select
              id={`sp-${index}`}
              value={line.speaker}
              onChange={(e) =>
                handleSpeaker(index, e.target.value as DialogueLine["speaker"])
              }
              className={lineSelectClass}
              aria-label={`Speaker for line ${index + 1}`}
            >
              <option value="Peter">Peter</option>
              <option value="Stewie">Stewie</option>
            </select>
            <input
              type="text"
              value={line.text}
              onChange={(e) => handleText(index, e.target.value)}
              className={`dlg-text flex-1 min-w-0 ${inputClass}`}
              placeholder="Line…"
              aria-label={`Dialogue text line ${index + 1}`}
            />
            <button
              type="button"
              onClick={() => handleRemove(index)}
              className="shrink-0 rounded-lg border border-outline-variant/20 bg-surface-container-highest px-3 py-2 text-sm font-bold text-on-surface-variant transition hover:border-error/40 hover:bg-error/10 hover:text-error"
              aria-label={`Remove line ${index + 1}`}
            >
              ×
            </button>
          </div>
        ))}
      </div>
      <button
        type="button"
        onClick={handleAddLine}
        className="shrink-0 rounded-xl border border-outline-variant/20 bg-surface-container-highest px-4 py-2 text-sm font-bold text-on-surface transition hover:bg-surface-bright"
      >
        + Add line
      </button>
    </div>
  );
};

export const isValidDialogue = (d: DialogueLine[]): boolean => {
  if (!Array.isArray(d) || d.length < 1) {
    return false;
  }
  for (const x of d) {
    if (!x || (x.speaker !== "Peter" && x.speaker !== "Stewie")) {
      return false;
    }
    if (!String(x.text || "").trim()) {
      return false;
    }
  }
  return true;
};

export const toPayloadLines = (lines: DialogueLine[]): DialogueLine[] =>
  lines
    .map((l) => ({
      speaker: l.speaker,
      text: (l.text || "").trim(),
    }))
    .filter((l) => l.text.length > 0);
