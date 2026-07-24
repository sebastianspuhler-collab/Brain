import { useEffect, useState } from "react";
import {
  Bot,
  CalendarDays,
  CheckSquare,
  FileText,
  LayoutDashboard,
  LogOut,
  Mail,
  MessageSquare,
  MessageSquarePlus,
  Share2,
  SquarePlay,
  Trash2,
  UserPlus,
  Users,
} from "lucide-react";
import { NavLink, useLocation, useNavigate, useSearchParams } from "react-router-dom";
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
} from "@/components/ui/sidebar";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/context/AuthContext";
import { chatSessions, type ChatSessionSummary } from "@/api/client";

const NAV_ITEMS = [
  { to: "/", label: "Chat", icon: MessageSquare, end: true },
  { to: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { to: "/aufgaben", label: "Aufgaben", icon: CheckSquare },
  { to: "/kalender", label: "Kalender", icon: CalendarDays },
  { to: "/mail", label: "Mail", icon: Mail },
  { to: "/dateien", label: "Dateien", icon: FileText },
  { to: "/meetings", label: "Meetings", icon: Users },
  { to: "/agenten", label: "Agenten", icon: Bot },
  { to: "/linkedin", label: "LinkedIn", icon: Share2 },
  { to: "/youtube", label: "YouTube", icon: SquarePlay },
  { to: "/onboarding", label: "Onboarding", icon: UserPlus },
];

function isRouteActive(pathname: string, to: string, end?: boolean): boolean {
  if (end) return pathname === to;
  return pathname === to || pathname.startsWith(`${to}/`);
}

function timeAgo(iso: string): string {
  if (!iso) return "";
  const diffMs = Date.now() - new Date(iso).getTime();
  const minutes = Math.round(diffMs / 60000);
  if (minutes < 1) return "jetzt";
  if (minutes < 60) return `vor ${minutes} Min.`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `vor ${hours} Std.`;
  const days = Math.round(hours / 24);
  return `vor ${days} Tg.`;
}

export function AppSidebar() {
  const { user, logout } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const activeSessionId = location.pathname === "/" ? searchParams.get("session") : null;
  const [sessions, setSessions] = useState<ChatSessionSummary[]>([]);

  useEffect(() => {
    function refresh() {
      chatSessions.list().then(setSessions).catch(() => {});
    }
    refresh();
    window.addEventListener("brain:sessions-changed", refresh);
    return () => window.removeEventListener("brain:sessions-changed", refresh);
  }, [location.pathname]);

  async function handleDelete(e: React.MouseEvent, id: string) {
    e.preventDefault();
    e.stopPropagation();
    try {
      await chatSessions.remove(id);
      setSessions((prev) => prev.filter((s) => s.id !== id));
      if (activeSessionId === id) navigate("/");
    } catch {
      // still fine, UI hat gar keinen Zwang das anzuzeigen - Liste wird beim nächsten Refresh korrigiert
    }
  }

  return (
    <Sidebar variant="floating">
      <SidebarHeader className="px-3 py-4">
        <div className="flex flex-col gap-0.5">
          <span className="font-display text-lg text-foreground" style={{ fontFamily: "var(--font-display)" }}>
            Prozessia Brain
          </span>
          <span className="text-xs text-muted-foreground">Second Brain</span>
        </div>
      </SidebarHeader>
      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupLabel>Bereiche</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              {NAV_ITEMS.map((item) => (
                <SidebarMenuItem key={item.to}>
                  <SidebarMenuButton
                    isActive={isRouteActive(location.pathname, item.to, item.end)}
                    render={
                      <NavLink to={item.to} end={item.end}>
                        <item.icon />
                        <span>{item.label}</span>
                      </NavLink>
                    }
                  />
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
        <SidebarGroup>
          <SidebarGroupLabel>Verlauf</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              <SidebarMenuItem>
                <SidebarMenuButton
                  render={
                    <NavLink to="/" end>
                      <MessageSquarePlus />
                      <span>Neuer Chat</span>
                    </NavLink>
                  }
                />
              </SidebarMenuItem>
              {sessions.map((s) => (
                <SidebarMenuItem key={s.id}>
                  <SidebarMenuButton
                    isActive={s.id === activeSessionId}
                    render={
                      <NavLink to={`/?session=${s.id}`}>
                        <span className="min-w-0 flex-1 truncate">{s.title}</span>
                        <span className="shrink-0 text-[10px] text-muted-foreground">{timeAgo(s.updated_at)}</span>
                        <button
                          onClick={(e) => handleDelete(e, s.id)}
                          className="ml-1 shrink-0 rounded p-0.5 text-muted-foreground opacity-0 transition hover:text-destructive group-hover/menu-item:opacity-100"
                          title="Chat löschen"
                        >
                          <Trash2 className="size-3" />
                        </button>
                      </NavLink>
                    }
                  />
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>
      <SidebarFooter className="px-3 py-3">
        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-2 min-w-0">
            <Avatar className="h-7 w-7">
              <AvatarFallback className="bg-primary text-primary-foreground text-xs">
                {user?.slice(0, 2).toUpperCase()}
              </AvatarFallback>
            </Avatar>
            <span className="text-sm truncate">{user}</span>
          </div>
          <Button variant="ghost" size="icon" onClick={() => logout()} title="Abmelden">
            <LogOut className="h-4 w-4" />
          </Button>
        </div>
      </SidebarFooter>
    </Sidebar>
  );
}
