import { cn } from "@/lib/utils";

/** Shared class strings — aligned with shadcn input/card tokens. */
export const inputClass = cn(
  "flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background",
  "file:mr-3 file:rounded-md file:border-0 file:bg-primary/20 file:px-3 file:py-1.5 file:text-sm file:font-semibold file:text-primary",
  "placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2",
  "disabled:cursor-not-allowed disabled:opacity-50"
);

export const selectClass = cn(
  "flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background",
  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2",
  "disabled:cursor-not-allowed disabled:opacity-50"
);

export const panelClass = cn("rounded-xl border border-border bg-card p-4 text-card-foreground shadow-sm");

export const panelMutedClass = cn("rounded-xl border border-border bg-muted/40 p-4");
