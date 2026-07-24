import { Outlet } from "react-router-dom";
import { AppSidebar } from "./AppSidebar";
import { SidebarProvider, SidebarTrigger } from "@/components/ui/sidebar";
import { Separator } from "@/components/ui/separator";

export function DashboardLayout() {
  return (
    <SidebarProvider className="h-screen gap-4 bg-background p-4">
      <AppSidebar />
      <div className="flex min-w-0 flex-1 flex-col overflow-hidden rounded-3xl border border-border bg-background shadow-card">
        <header className="flex h-14 shrink-0 items-center gap-2 border-b border-border px-4">
          <SidebarTrigger className="lg:hidden" />
          <Separator orientation="vertical" className="h-5 lg:hidden" />
          <span className="text-sm text-muted-foreground">Prozessia GbR &middot; Saarbrücken</span>
        </header>
        <main className="flex-1 overflow-y-auto p-6">
          <Outlet />
        </main>
      </div>
    </SidebarProvider>
  );
}
