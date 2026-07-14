import { CalendarDays, CheckSquare, FileText, LogOut, Mail, MessageSquare, Share2, SquarePlay, UserPlus } from "lucide-react";
import { NavLink } from "react-router-dom";
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

const NAV_ITEMS = [
  { to: "/", label: "Chat", icon: MessageSquare, end: true },
  { to: "/aufgaben", label: "Aufgaben", icon: CheckSquare },
  { to: "/kalender", label: "Kalender", icon: CalendarDays },
  { to: "/mail", label: "Mail", icon: Mail },
  { to: "/dateien", label: "Dateien", icon: FileText },
  { to: "/linkedin", label: "LinkedIn", icon: Share2 },
  { to: "/youtube", label: "YouTube", icon: SquarePlay },
  { to: "/onboarding", label: "Onboarding", icon: UserPlus },
];

export function AppSidebar() {
  const { user, logout } = useAuth();

  return (
    <Sidebar>
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
                    render={
                      <NavLink
                        to={item.to}
                        end={item.end}
                        className={({ isActive }) => (isActive ? "bg-sidebar-accent text-sidebar-accent-foreground" : "")}
                      >
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
