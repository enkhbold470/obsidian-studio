import { LayoutGrid, LogOut, Sparkles } from "lucide-react";
import { useEffect, useState } from "react";
import { Link, NavLink, useLocation } from "react-router-dom";
import type { AuthUser } from "../../api";
import { getMe, logout } from "../../api";

const navLinkClass = ({ isActive }: { isActive: boolean }) =>
  [
    "text-sm font-medium transition-colors",
    isActive
      ? "border-b-2 border-primary pb-1 text-primary"
      : "text-on-surface-variant hover:text-on-surface",
  ].join(" ");

export const AppHeader = () => {
  const location = useLocation();
  const [me, setMe] = useState<AuthUser | null | undefined>(undefined);
  const [skipAuth, setSkipAuth] = useState(false);

  useEffect(() => {
    let cancelled = false;
    getMe().then((j) => {
      if (cancelled) {
        return;
      }
      if (j.skipAuth) {
        setSkipAuth(true);
        setMe(null);
      } else {
        setMe(j.user ?? null);
      }
    });
    return () => {
      cancelled = true;
    };
  }, [location.pathname]);

  const dashboardHref = me ? `/u/${me.id}/renders` : "/login";

  const handleLogout = async () => {
    await logout();
    setMe(null);
    window.location.href = "/login";
  };

  return (
    <header className="sticky top-0 z-50 border-b border-outline-variant/15 bg-surface/95 backdrop-blur-md">
      <div className="mx-auto flex max-w-7xl items-center justify-between gap-4 px-4 py-4 sm:px-6">
        <div className="flex min-w-0 flex-1 items-center gap-6 md:gap-8">
          <Link
            to="/"
            className="shrink-0 font-headline text-xl font-bold tracking-tight text-primary sm:text-2xl"
          >
            ReelMaker
          </Link>
          <nav className="hidden items-center gap-5 md:flex" aria-label="Primary">
            <NavLink to="/" end className={navLinkClass} title="Editor">
              <span className="inline-flex items-center gap-1.5">
                <Sparkles className="h-4 w-4 opacity-80" aria-hidden />
                Editor
              </span>
            </NavLink>
            <NavLink to={dashboardHref} className={navLinkClass} title="Dashboard">
              <span className="inline-flex items-center gap-1.5">
                <LayoutGrid className="h-4 w-4 opacity-80" aria-hidden />
                Dashboard
              </span>
            </NavLink>
          </nav>
        </div>
        <div className="flex shrink-0 items-center gap-2 sm:gap-3">
          {me === undefined ? (
            <span className="text-xs text-on-surface-variant" aria-live="polite">
              …
            </span>
          ) : skipAuth ? (
            <span className="rounded-full bg-tertiary/15 px-3 py-1 text-xs font-semibold text-tertiary">
              Dev: auth off
            </span>
          ) : me ? (
            <>
              <div className="flex max-w-[min(100%,16rem)] items-center gap-2 rounded-xl border border-outline-variant/10 bg-surface-container px-3 py-1.5 sm:max-w-xs">
                <span
                  className="h-2 w-2 shrink-0 animate-pulse rounded-full bg-secondary"
                  aria-hidden
                />
                <span className="truncate text-xs font-medium text-on-surface-variant">{me.email}</span>
              </div>
              <button
                type="button"
                onClick={handleLogout}
                className="inline-flex items-center gap-1.5 rounded-xl border border-outline-variant/20 bg-surface-container-highest px-3 py-1.5 text-xs font-bold text-on-surface transition hover:bg-surface-bright sm:text-sm"
              >
                <LogOut className="h-4 w-4 shrink-0" aria-hidden />
                <span className="hidden sm:inline">Log out</span>
              </button>
            </>
          ) : (
            <Link
              to="/login"
              className="rounded-xl border border-outline-variant/30 px-3 py-1.5 text-sm font-semibold text-primary hover:bg-surface-container-highest"
            >
              Log in
            </Link>
          )}
        </div>
      </div>
      <nav
        className="flex gap-4 overflow-x-auto border-t border-outline-variant/10 px-4 py-2 sm:px-6 md:hidden"
        aria-label="Primary mobile"
      >
        <NavLink to="/" end className={navLinkClass} title="Editor">
          <span className="inline-flex shrink-0 items-center gap-1.5">
            <Sparkles className="h-4 w-4 opacity-80" aria-hidden />
            Editor
          </span>
        </NavLink>
        <NavLink to={dashboardHref} className={navLinkClass} title="Dashboard">
          <span className="inline-flex shrink-0 items-center gap-1.5">
            <LayoutGrid className="h-4 w-4 opacity-80" aria-hidden />
            Dashboard
          </span>
        </NavLink>
      </nav>
    </header>
  );
};
