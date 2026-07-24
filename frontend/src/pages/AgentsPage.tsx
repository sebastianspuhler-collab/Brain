import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Pencil, Plus, Trash2 } from "lucide-react";
import { agents as agentsApi, type Agent } from "@/api/client";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import { StatusPill } from "@/components/shared/status-pill";

const MODELS = [
  { id: "", label: "Wie im Chat gewählt" },
  { id: "claude-sonnet-5", label: "Sonnet" },
  { id: "claude-opus-4-8", label: "Opus" },
];

function emptyForm(): Omit<Agent, "id"> {
  return { name: "", system_prompt_zusatz: "", ordner_filter: [], model: null };
}

function AgentSheet({
  agent,
  open,
  onClose,
}: {
  agent: Agent | null;
  open: boolean;
  onClose: () => void;
}) {
  const queryClient = useQueryClient();
  const [form, setForm] = useState<Omit<Agent, "id">>(emptyForm());
  const [ordnerText, setOrdnerText] = useState("");

  useEffect(() => {
    if (agent) {
      setForm({
        name: agent.name,
        system_prompt_zusatz: agent.system_prompt_zusatz,
        ordner_filter: agent.ordner_filter,
        model: agent.model,
      });
      setOrdnerText(agent.ordner_filter.join(", "));
    } else {
      setForm(emptyForm());
      setOrdnerText("");
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

  return (
    <Sheet open={open} onOpenChange={(o) => !o && onClose()}>
      <SheetContent className="flex flex-col gap-4 p-4 sm:max-w-lg">
        <SheetHeader className="p-0">
          <SheetTitle>{agent ? "Agent bearbeiten" : "Neuer Agent"}</SheetTitle>
        </SheetHeader>
        <div className="flex flex-col gap-1.5">
          <Label>Name</Label>
          <Input
            value={form.name}
            onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
            placeholder="z.B. Schaufler-Experte"
          />
        </div>
        <div className="flex flex-col gap-1.5">
          <Label>Zusatz-Prompt</Label>
          <Textarea
            value={form.system_prompt_zusatz}
            onChange={(e) => setForm((f) => ({ ...f, system_prompt_zusatz: e.target.value }))}
            placeholder="Zusätzliche Anweisung, z.B. 'Antworte nur zu Schaufler-Themen, kurz und faktenbasiert.'"
            className="min-h-28"
          />
        </div>
        <div className="flex flex-col gap-1.5">
          <Label>Ordner-Filter (optional)</Label>
          <Input
            value={ordnerText}
            onChange={(e) => setOrdnerText(e.target.value)}
            placeholder="z.B. Kunden/Schaufler/, Produkte/Beschaffungsagent/"
          />
          <p className="text-xs text-muted-foreground">
            Komma-getrennt. Ohne Angabe durchsucht der Agent den gesamten Vault wie der normale Chat.
          </p>
        </div>
        <div className="flex flex-col gap-1.5">
          <Label>Modell</Label>
          <Select
            value={form.model ?? ""}
            onValueChange={(v) => setForm((f) => ({ ...f, model: v || null }))}
          >
            <SelectTrigger>
              <SelectValue>{(v: string) => MODELS.find((m) => m.id === v)?.label ?? "Wie im Chat gewählt"}</SelectValue>
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
        <Button onClick={() => save.mutate()} disabled={save.isPending || !form.name.trim()}>
          {save.isPending ? "Speichere…" : "Speichern"}
        </Button>
      </SheetContent>
    </Sheet>
  );
}

export function AgentsPage() {
  const queryClient = useQueryClient();
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
    <Card>
      <CardHeader className="flex-row items-center justify-between gap-2 space-y-0">
        <CardTitle>Eigene Agenten</CardTitle>
        <Button size="sm" onClick={() => setCreating(true)}>
          <Plus className="size-4" />
          Neuer Agent
        </Button>
      </CardHeader>
      <CardContent>
        <p className="mb-4 text-sm text-muted-foreground">
          Zusätzliche, wählbare Chat-Kontexte mit eigenem Fokus-Prompt, optionalem Ordner-Filter und
          eigener Modellwahl. Der normale Chat bleibt davon unberührt.
        </p>
        {isLoading ? (
          <div className="space-y-2">
            <Skeleton className="h-14 w-full" />
            <Skeleton className="h-14 w-full" />
          </div>
        ) : !data?.length ? (
          <p className="text-sm text-muted-foreground">Noch keine eigenen Agenten angelegt.</p>
        ) : (
          <div className="flex flex-col divide-y divide-border">
            {data.map((a) => (
              <div key={a.id} className="flex items-center justify-between gap-3 py-3 first:pt-0 last:pb-0">
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <span className="font-medium text-foreground">{a.name}</span>
                    {a.model && (
                      <StatusPill variant="info">
                        {MODELS.find((m) => m.id === a.model)?.label ?? a.model}
                      </StatusPill>
                    )}
                  </div>
                  {a.system_prompt_zusatz && (
                    <p className="line-clamp-1 text-xs text-muted-foreground">{a.system_prompt_zusatz}</p>
                  )}
                  {a.ordner_filter.length > 0 && (
                    <p className="text-xs text-muted-foreground">Ordner: {a.ordner_filter.join(", ")}</p>
                  )}
                </div>
                <div className="flex shrink-0 items-center gap-1">
                  <Button variant="ghost" size="icon-sm" onClick={() => setEditing(a)} title="Bearbeiten">
                    <Pencil className="size-4" />
                  </Button>
                  <Button
                    variant="ghost"
                    size="icon-sm"
                    onClick={() => remove.mutate(a.id)}
                    title="Löschen"
                    className="text-destructive hover:text-destructive"
                  >
                    <Trash2 className="size-4" />
                  </Button>
                </div>
              </div>
            ))}
          </div>
        )}
      </CardContent>
      <AgentSheet agent={editing} open={!!editing} onClose={() => setEditing(null)} />
      <AgentSheet agent={null} open={creating} onClose={() => setCreating(false)} />
    </Card>
  );
}
