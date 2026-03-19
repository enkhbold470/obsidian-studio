import { useCallback } from "react";
import type { DialogueLine } from "../api";

type DialogueEditorProps = {
  lines: DialogueLine[];
  onChange: (lines: DialogueLine[]) => void;
};

const emptyLine = (): DialogueLine => ({ speaker: "Peter", text: "" });

export const DialogueEditor = ({ lines, onChange }: DialogueEditorProps) => {
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

  return (
    <div className="space-y-2">
      <p className="text-sm text-gray-600">
        All lines are visible below — scroll the page if the script is long.
      </p>
      <div className="space-y-2 border-2 border-black p-2">
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
              className="dlg-speaker border-2 border-black p-2 shrink-0"
              aria-label={`Speaker for line ${index + 1}`}
            >
              <option value="Peter">Peter</option>
              <option value="Stewie">Stewie</option>
            </select>
            <input
              type="text"
              value={line.text}
              onChange={(e) => handleText(index, e.target.value)}
              className="dlg-text flex-1 min-w-0 border-2 border-black p-2"
              placeholder="Line…"
              aria-label={`Dialogue text line ${index + 1}`}
            />
            <button
              type="button"
              onClick={() => handleRemove(index)}
              className="shrink-0 border-2 border-black px-2 py-1 font-bold hover:bg-gray-100"
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
        className="border-2 border-black px-2 py-1 text-sm font-bold hover:bg-gray-100"
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
