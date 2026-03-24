import { useCallback } from "react";
import type { DialogueLine } from "../api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { selectClass } from "../lib/obsidianStyles";
import { cn } from "@/lib/utils";

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
      ? "dlg-scroll custom-scrollbar min-h-dialogue-panel-min flex-1 space-y-2 overflow-auto rounded-xl border border-border bg-card p-3 lg:min-h-0"
      : "dlg-scroll custom-scrollbar max-h-dialogue-panel min-h-dialogue-panel-min space-y-2 rounded-xl border border-border bg-card p-3";

  return (
    <div
      className={
        layout === "fill"
          ? "flex min-h-0 flex-1 flex-col gap-3 lg:min-h-64"
          : "space-y-3"
      }
    >
      <p className="shrink-0 text-sm text-muted-foreground">
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
            <Input
              type="text"
              value={line.text}
              onChange={(e) => handleText(index, e.target.value)}
              className={cn("dlg-text min-w-0 flex-1")}
              placeholder="Line…"
              aria-label={`Dialogue text line ${index + 1}`}
            />
            <Button
              type="button"
              variant="outline"
              size="icon"
              onClick={() => handleRemove(index)}
              className="shrink-0 border-destructive/30 text-muted-foreground hover:border-destructive/50 hover:bg-destructive/10 hover:text-destructive"
              aria-label={`Remove line ${index + 1}`}
            >
              ×
            </Button>
          </div>
        ))}
      </div>
      <Button type="button" variant="secondary" onClick={handleAddLine} className="shrink-0">
        + Add line
      </Button>
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
