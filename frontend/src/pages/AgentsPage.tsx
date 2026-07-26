import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { AnimatePresence, motion, useReducedMotion } from "motion/react";
import { ChevronDown, Pencil, Plus, Terminal, Trash2 } from "lucide-react";
import { agents as agentsApi, DEV_AGENT_ID, type Agent } from "@/api/client";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Dialog,
  DialogBody,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { DropdownMenu, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Switch } from "@/components/ui/switch";
import { Textarea } from "@/components/ui/textarea";
import { AgentHistoryMenuContent } from "@/components/shared/agent-history-menu";
import { IdentityAvatar } from "@/components/shared/identity-avatar";
import { StatusPill } from "@/components/shared/status-pill";
import { cn } from "@/lib/utils";

const MODELS = [
  { id: "", label: "Wie im Chat gewählt" },
  { id: "claude-sonnet-5", label: "Sonnet" },
  { id: "claude-opus-4-8", label: "Opus" },
];

// Fähigkeits-Gruppen für Agenten-Berechtigungen - Keys/Labels müssen zu
// backend/app/services/agent_capabilities.py passen (CAPABILITY_LABELS).
// Schränkt nur ein, welche Tools der Agent nutzen darf (echte Durchsetzung
// über --allowedTools) - KEIN Ordner-Zugriffsschutz (siehe Ordner-Filter
// unten, der bleibt reine RAG-Suchbeschränkung; einen Zuständigkeitsbereich
// gibt der Agent sich selbst über den Zusatz-Prompt).
const CAPABILITY_LABELS: Record<string, string> = {
  files_read: "Dateien lesen",
  files_write: "Dateien schreiben",
  linkedin: "LinkedIn",
  youtube: "YouTube",
  email_anhaenge: "E-Mail/Anhänge",
  meetings_suche: "Meetings-Suche",
};

// Nach buzz-ai's "Advanced fields"-Reveal in AgentDefinitionDialog.tsx (motion/react).
const ADVANCED_FIELDS_TRANSITION = { duration: 0.18, ease: [0.23, 1, 0.32, 1] as const };
// Nach buzz-ai's Zeilen-Enter-Spring (AgentSessionTranscriptList.tsx).
const CARD_ENTER_SPRING = { type: "spring" as const, stiffness: 480, damping: 38 };

const GRID_CLASS = "grid grid-cols-[repeat(auto-fill,minmax(180px,200px))] justify-center gap-4 sm:justify-start";

function emptyForm(): Omit<Agent, "id"> {
  return { name: "", system_prompt_zusatz: "", ordner_filter: [], model: null, allowed_tools: null };
}

// Label über einer abgerundeten, gedämpften "Schale" statt eines eigenen Inputrahmens
// - Formsprache 1:1 aus buzz-ai (PERSONA_FIELD_SHELL_CLASS in AgentDefinitionDialog.tsx).
function FieldShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="rounded-xl border border-input bg-muted/40 transition-colors focus-within:border-ring/50">
      {children}
    </div>
  );
}

const SHELL_CONTROL_CLASS = "border-0 bg-transparent shadow-none focus-visible:ring-0";

function AgentDialog({
  agent,
  open,
  onClose,
}: {
  agent: Agent | null;
  open: boolean;
  onClose: () => void;
}) {
  const queryClient = useQueryClient();
  const shouldReduceMotion = useReducedMotion();
  const [form, setForm] = useState<Omit<Agent, "id">>(emptyForm());
  const [ordnerText, setOrdnerText] = useState("");
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [restrictTools, setRestrictTools] = useState(false);
  const [allowedTools, setAllowedTools] = useState<string[]>([]);

  useEffect(() => {
    if (agent) {
      setForm({
        name: agent.name,
        system_prompt_zusatz: agent.system_prompt_zusatz,
        ordner_filter: agent.ordner_filter,
        model: agent.model,
        allowed_tools: agent.allowed_tools,
      });
      setOrdnerText(agent.ordner_filter.join(", "));
      setShowAdvanced(agent.ordner_filter.length > 0 || agent.allowed_tools !== null);
      setRestrictTools(agent.allowed_tools !== null);
      setAllowedTools(agent.allowed_tools ?? []);
    } else {
      setForm(emptyForm());
      setOrdnerText("");
      setShowAdvanced(false);
      setRestrictTools(false);
      setAllowedTools([]);
    }
  }, [agent, open]);

  const save = useMutation({
    mutationFn: () => {
      const payload = {
        ...form,
        ordner_filter: ordnerText
          .split(",")
          .map((s) => s.trim())
          .filter(Boolean),
        allowed_tools: restrictTools ? allowedTools : null,
      };
      return agent ? agentsApi.update(agent.id, payload) : agentsApi.create(payload);
    },
    onSuccess: () => {
      toast.success(agent ? "Agent gespeichert" : "Agent angelegt");
      queryClient.invalidateQueries({ queryKey: ["agents"] });
      onClose();
    },
    onError: () => toast.error("Speichern fehlgeschlagen"),
  });

  const advancedTransition = shouldReduceMotion ? { duration: 0 } : ADVANCED_FIELDS_TRANSITION;

  return (
    <Dialog open={open} onOpenChange={(o) => !o && onClose()}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{agent ? "Agent bearbeiten" : "Neuer Agent"}</DialogTitle>
          <DialogDescription>
            Zusätzlicher, wählbarer Chat-Kontext mit eigenem Fokus-Prompt. Der normale Chat bleibt davon unberührt.
          </DialogDescription>
        </DialogHeader>
        <DialogBody className="flex flex-col gap-5">
          <div className="flex justify-center">
            <IdentityAvatar name={form.name || "?"} />
          </div>
          <div className="space-y-1.5">
            <Label>Name</Label>
            <FieldShell>
              <Input
                value={form.name}
                onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
                placeholder="z.B. Schaufler-Experte"
                className={SHELL_CONTROL_CLASS}
              />
            </FieldShell>
          </div>
          <div className="space-y-1.5">
            <Label>Zusatz-Prompt</Label>
            <FieldShell>
              <Textarea
                value={form.system_prompt_zusatz}
                onChange={(e) => setForm((f) => ({ ...f, system_prompt_zusatz: e.target.value }))}
                placeholder="Zusätzliche Anweisung, z.B. 'Antworte nur zu Schaufler-Themen, kurz und faktenbasiert.'"
                className={cn(SHELL_CONTROL_CLASS, "min-h-28")}
              />
            </FieldShell>
          </div>
          <div className="space-y-1.5">
            <Label>Modell</Label>
            <Select value={form.model ?? ""} onValueChange={(v) => setForm((f) => ({ ...f, model: v || null }))}>
              <SelectTrigger className="w-full border-input bg-muted/40">
                <SelectValue>
                  {(v: string) => MODELS.find((m) => m.id === v)?.label ?? "Wie im Chat gewählt"}
                </SelectValue>
              </SelectTrigger>
              <SelectContent>
                {MODELS.map((m) => (
                  <SelectItem key={m.id} value={m.id}>
                    {m.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div>
            <button
              type="button"
              onClick={() => setShowAdvanced((s) => !s)}
              className="flex items-center gap-1.5 text-sm font-medium text-muted-foreground transition-colors hover:text-foreground"
            >
              <ChevronDown className={cn("size-4 transition-transform duration-150 ease-out", showAdvanced && "rotate-180")} />
              Erweitert
            </button>
            <AnimatePresence initial={false}>
              {showAdvanced && (
                <motion.div
                  key="agent-advanced-fields"
                  initial={{ height: 0, opacity: 0 }}
                  animate={{ height: "auto", opacity: 1 }}
                  exit={{ height: 0, opacity: 0 }}
                  transition={advancedTransition}
                  className="overflow-hidden"
                >
                  <div className="space-y-1.5 pt-3">
                    <Label>Ordner-Filter (optional)</Label>
                    <FieldShell>
                      <Input
                        value={ordnerText}
                        onChange={(e) => setOrdnerText(e.target.value)}
                        placeholder="z.B. Kunden/Schaufler/, Produkte/Beschaffungsagent/"
                        className={SHELL_CONTROL_CLASS}
                      />
                    </FieldShell>
                    <p className="text-xs text-muted-foreground">
                      Komma-getrennt. Ohne Angabe durchsucht der Agent den gesamten Vault wie der normale Chat.
                    </p>
                  </div>
                  <div className="space-y-1.5 pt-4">
                    <div className="flex items-center justify-between">
                      <Label>Zugriff auf Tools einschränken</Label>
                      <Switch checked={restrictTools} onCheckedChange={setRestrictTools} />
                    </div>
                    {restrictTools && (
                      <div className="grid grid-cols-2 gap-2 pt-1">
                        {Object.entries(CAPABILITY_LABELS).map(([key, label]) => (
                          <label key={key} className="flex items-center gap-2 text-sm">
                            <Checkbox
                              checked={allowedTools.includes(key)}
                              onCheckedChange={(c) =>
                                setAllowedTools((prev) => (c === true ? [...prev, key] : prev.filter((k) => k !== key)))
                              }
                            />
                            {label}
                          </label>
                        ))}
                      </div>
                    )}
                    <p className="text-xs text-muted-foreground">
                      Unmarkiert = kein Zugriff auf diese Fähigkeit. Ohne Einschränkung (Standard) hat der Agent
                      Zugriff auf alle Tools wie bisher.
                    </p>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </DialogBody>
        <DialogFooter>
          <Button variant="outline" onClick={onClose}>
            Abbrechen
          </Button>
          <Button onClick={() => save.mutate()} disabled={save.isPending || !form.name.trim()}>
            {save.isPending ? "Speichere…" : "Speichern"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function AgentCard({
  agent,
  onEdit,
  onDelete,
}: {
  agent: Agent;
  onEdit: () => void;
  onDelete: () => void;
}) {
  const modelLabel = agent.model ? MODELS.find((m) => m.id === agent.model)?.label ?? agent.model : null;

  return (
    <div className="group relative aspect-[4/5] w-full overflow-hidden rounded-2xl border border-border bg-card shadow-card transition-colors hover:border-primary/40">
      <DropdownMenu>
        <DropdownMenuTrigger
          render={
            <button
              type="button"
              className="absolute inset-0 z-10 rounded-2xl focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              aria-label={`${agent.name} Chat öffnen`}
            />
          }
        />
        <AgentHistoryMenuContent agentId={agent.id} buildUrl={(id) => `/?session=${id}&agent=${agent.id}`} />
      </DropdownMenu>
      <div className="pointer-events-none flex h-full w-full flex-col items-center justify-center gap-4 px-4 pb-14">
        <IdentityAvatar name={agent.name} />
      </div>
      <div className="absolute top-2 right-2 z-20 flex items-center gap-1">
        <button
          type="button"
          onClick={onEdit}
          className="flex size-7 items-center justify-center rounded-full text-muted-foreground opacity-0 transition-opacity hover:bg-muted hover:text-foreground group-hover:opacity-100"
          aria-label={`${agent.name} bearbeiten`}
        >
          <Pencil className="size-3.5" />
        </button>
        <button
          type="button"
          onClick={onDelete}
          className="flex size-7 items-center justify-center rounded-full text-muted-foreground opacity-0 transition-opacity hover:bg-destructive/10 hover:text-destructive group-hover:opacity-100"
          aria-label={`${agent.name} löschen`}
        >
          <Trash2 className="size-3.5" />
        </button>
      </div>
      <div className="pointer-events-none absolute inset-x-3 bottom-3 z-10 flex min-w-0 flex-col gap-1 text-left">
        <span className="min-w-0 truncate text-sm font-semibold text-foreground">{agent.name}</span>
        {modelLabel && (
          <StatusPill variant="info" className="w-fit">
            {modelLabel}
          </StatusPill>
        )}
      </div>
    </div>
  );
}

// Fest eingebauter Entwickler-Agent (Umsetzungsplan 2026-07-25): kein Eintrag
// aus agents.json, sondern die isolierte Sandbox aus dev-agent/ - eigenes
// Backend, eigener Chat-Screen (DevAgentPage.tsx unter /entwicklung), daher
// weder bearbeitbar noch löschbar wie die selbst angelegten Agenten. Immer
// als erste Kachel im Grid gepinnt.
function DevAgentCard() {
  return (
    <div className="group relative aspect-[4/5] w-full overflow-hidden rounded-2xl border border-border bg-card shadow-card transition-colors hover:border-primary/40">
      <DropdownMenu>
        <DropdownMenuTrigger
          render={
            <button
              type="button"
              className="absolute inset-0 z-10 rounded-2xl focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              aria-label="Entwicklungs-Agent Chat öffnen"
            />
          }
        />
        <AgentHistoryMenuContent agentId={DEV_AGENT_ID} buildUrl={(id) => `/entwicklung?session=${id}`} />
      </DropdownMenu>
      <div className="pointer-events-none flex h-full w-full flex-col items-center justify-center gap-4 px-4 pb-14">
        <span className="flex h-24 w-24 items-center justify-center rounded-full border-[3px] border-background bg-primary/15 text-primary shadow-sm">
          <Terminal className="size-8" />
        </span>
      </div>
      <div className="pointer-events-none absolute inset-x-3 bottom-3 z-10 flex min-w-0 flex-col gap-1 text-left">
        <span className="min-w-0 truncate text-sm font-semibold text-foreground">Entwicklung</span>
        <StatusPill variant="info" className="w-fit">
          Sandbox
        </StatusPill>
      </div>
    </div>
  );
}

function NewAgentCard({ onClick }: { onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="flex aspect-[4/5] w-full flex-col items-center justify-center gap-2 rounded-2xl border border-dashed border-border text-muted-foreground transition-colors hover:border-primary/50 hover:text-foreground"
    >
      <Plus className="size-6" />
      <span className="text-sm font-medium">Neuer Agent</span>
    </button>
  );
}

export function AgentsPage() {
  const queryClient = useQueryClient();
  const shouldReduceMotion = useReducedMotion();
  const { data, isLoading } = useQuery({
    queryKey: ["agents"],
    queryFn: () => agentsApi.list(),
  });
  const [editing, setEditing] = useState<Agent | null>(null);
  const [creating, setCreating] = useState(false);

  const remove = useMutation({
    mutationFn: (id: string) => agentsApi.remove(id),
    onSuccess: () => {
      toast.success("Agent gelöscht");
      queryClient.invalidateQueries({ queryKey: ["agents"] });
    },
    onError: () => toast.error("Löschen fehlgeschlagen"),
  });

  return (
    <div className="flex flex-col gap-8">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold text-foreground">Agenten</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Zusätzliche, wählbare Chat-Kontexte mit eigenem Fokus-Prompt, optionalem Ordner-Filter und eigener
            Modellwahl.
          </p>
        </div>
        <Button onClick={() => setCreating(true)}>
          <Plus className="size-4" />
          Neuer Agent
        </Button>
      </div>

      {isLoading ? (
        <div className={GRID_CLASS}>
          <Skeleton className="aspect-[4/5] w-full rounded-2xl" />
          <Skeleton className="aspect-[4/5] w-full rounded-2xl" />
          <Skeleton className="aspect-[4/5] w-full rounded-2xl" />
        </div>
      ) : (
        <motion.div layout className={GRID_CLASS}>
          <DevAgentCard />
          <AnimatePresence mode="popLayout" initial={false}>
            {data?.map((a) => (
              <motion.div
                key={a.id}
                layout
                initial={shouldReduceMotion ? false : { opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, scale: 0.9 }}
                transition={CARD_ENTER_SPRING}
              >
                <AgentCard agent={a} onEdit={() => setEditing(a)} onDelete={() => remove.mutate(a.id)} />
              </motion.div>
            ))}
          </AnimatePresence>
          <NewAgentCard onClick={() => setCreating(true)} />
        </motion.div>
      )}

      <AgentDialog agent={editing} open={!!editing} onClose={() => setEditing(null)} />
      <AgentDialog agent={null} open={creating} onClose={() => setCreating(false)} />
    </div>
  );
}
