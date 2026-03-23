import { Outlet } from "react-router-dom";
import { AppFooter } from "./AppFooter";
import { AppHeader } from "./AppHeader";

export const AppLayout = () => (
  <div className="flex min-h-screen flex-col bg-background">
    <AppHeader />
    <main className="flex-1">
      <Outlet />
    </main>
    <AppFooter />
  </div>
);
