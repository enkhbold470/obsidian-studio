import { Link } from "react-router-dom";
import { cn } from "@/lib/utils";

export const AppFooter = () => (
  <footer className={cn("mt-auto border-t border-border/50 py-8")}>
    <div className="mx-auto flex max-w-7xl flex-col items-center justify-between gap-4 px-4 text-center sm:flex-row sm:text-left sm:px-6">
      <div className="flex flex-wrap items-center justify-center gap-2 sm:justify-start">
        <span className="font-headline text-sm font-bold text-foreground">Obsidian Studio</span>
        <span className="rounded-full bg-primary/20 px-2 py-0.5 text-[10px] font-bold uppercase text-primary">
          ReelMaker
        </span>
      </div>
      <div className="flex flex-wrap justify-center gap-6">
        <Link
          className="text-xs font-bold uppercase tracking-wide text-muted-foreground transition-colors hover:text-foreground"
          to="/"
        >
          Home
        </Link>
      </div>
      <p className="text-xs text-muted-foreground">© {new Date().getFullYear()} ReelMaker</p>
    </div>
  </footer>
);
