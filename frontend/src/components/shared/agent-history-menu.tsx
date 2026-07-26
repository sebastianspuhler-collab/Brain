import { Loader2, MessageSquarePlus, Trash2 } from "lucide-react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { agents as agentsApi, chatSessions } from "@/api/client";
import { DropdownMenuContent, DropdownMenuItem, DropdownMenuSeparator } from "@/components/ui/dropdown-menu";
import { cn } from "@/lib/utils";

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

export interface AgentHistoryMenuContentProps {
  agentId: string;
  /** Baut die Ziel-URL für eine (bestehende oder frisch erzeugte) Session -
   * unterscheidet sich zwischen normalen Agenten (/?session=X&agent=Y) und
   * dem Entwicklungs-Agenten (/entwicklung?session=X). */
  buildUrl: (sessionId: string) => string;
}

/** Verlauf-Dropdown-Inhalt für einen Agenten (Umsetzungsplan 2026-07-26):
 * "+ Neuer Chat" plus alle bisherigen Chats mit diesem Agenten, mit
 * Löschen/Fortsetzen - funktioniert unverändert auch für den reservierten
 * Entwicklungs-Agenten (agentId="dev-agent"), da beide über dieselbe
 * chat_sessions.py-Persistenz laufen. Rendert nur den <DropdownMenuContent>-
 * Teil, der Trigger (die Karte selbst) lebt beim Aufrufer. */
export function AgentHistoryMenuContent({ agentId, buildUrl }: AgentHistoryMenuContentProps) {
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const { data: sessions, isLoading } = useQuery({
    queryKey: ["agent-sessions", agentId],
    queryFn: () => agentsApi.sessions(agentId),
  });

  async function handleDelete(e: React.MouseEvent, id: string) {
    e.preventDefault();
    e.stopPropagation();
    try {
      await chatSessions.remove(id);
      queryClient.invalidateQueries({ queryKey: ["agent-sessions", agentId] });
      window.dispatchEvent(new CustomEvent("brain:sessions-changed"));
    } catch {
      // Liste korrigiert sich beim nächsten Öffnen von selbst
    }
  }

  return (
    <DropdownMenuContent align="start" className="w-64">
      <DropdownMenuItem onClick={() => navigate(buildUrl(crypto.randomUUID()))}>
        <MessageSquarePlus className="size-4" />
        Neuer Chat
      </DropdownMenuItem>
      {(isLoading || !!sessions?.length) && <DropdownMenuSeparator />}
      {isLoading && (
        <div className="flex items-center justify-center py-3 text-muted-foreground">
          <Loader2 className="size-4 animate-spin" />
        </div>
      )}
      {sessions?.map((s) => (
        <DropdownMenuItem
          key={s.id}
          onClick={() => navigate(buildUrl(s.id))}
          className={cn("group/history-item justify-between gap-2")}
        >
          <span className="min-w-0 flex-1 truncate">{s.title}</span>
          <span className="shrink-0 text-[10px] text-muted-foreground">{timeAgo(s.updated_at)}</span>
          <button
            type="button"
            onClick={(e) => handleDelete(e, s.id)}
            className="shrink-0 rounded p-0.5 text-muted-foreground opacity-0 transition hover:text-destructive group-hover/history-item:opacity-100"
            title="Chat löschen"
          >
            <Trash2 className="size-3" />
          </button>
        </DropdownMenuItem>
      ))}
    </DropdownMenuContent>
  );
}
