import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Trash2 } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";
import { api } from "@/api/client";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { SegmentedControl } from "@/components/shared/segmented-control";

type Assignee = "Amin" | "Sebastian" | "Beide";

interface Task {
  text: string;
  urgency: "urgent" | "soon" | "normal" | "done";
  done?: boolean;
  assignee: Assignee;
  due: string | null;
}

const ASSIGNEES: Assignee[] = ["Amin", "Sebastian", "Beide"];

const URGENCY_LABEL: Record<Task["urgency"], string> = {
  urgent: "Dringend",
  soon: "Bald",
  normal: "Normal",
  done: "Erledigt",
};

const URGENCY_VARIANT: Record<Task["urgency"], "destructive" | "secondary" | "outline"> = {
  urgent: "destructive",
  soon: "secondary",
  normal: "outline",
  done: "outline",
};

export function TasksPage() {
  const queryClient = useQueryClient();
  const [newTask, setNewTask] = useState("");
  const [newAssignee, setNewAssignee] = useState<Assignee>("Beide");
  const [newDue, setNewDue] = useState("");
  const [filter, setFilter] = useState<Assignee | "Alle">("Alle");

  const { data, isLoading } = useQuery({
    queryKey: ["tasks"],
    queryFn: () => api.get<Task[]>("/api/tasks"),
    refetchInterval: 5 * 60 * 1000,
  });

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ["tasks"] });

  const addTask = useMutation({
    mutationFn: ({ text, assignee, due }: { text: string; assignee: Assignee; due: string | null }) =>
      api.post("/api/tasks", { text, assignee, due }),
    onSuccess: () => {
      setNewTask("");
      setNewDue("");
      invalidate();
    },
    onError: () => toast.error("Aufgabe konnte nicht hinzugefügt werden"),
  });

  const toggleTask = useMutation({
    mutationFn: ({ text, done }: { text: string; done: boolean }) =>
      api.post("/api/tasks/toggle", { text, done }),
    onSuccess: invalidate,
    onError: () => toast.error("Aufgabe konnte nicht aktualisiert werden"),
  });

  const deleteTask = useMutation({
    mutationFn: (text: string) => api.post("/api/tasks/delete", { text }),
    onSuccess: invalidate,
    onError: () => toast.error("Aufgabe konnte nicht gelöscht werden"),
  });

  const setAssignee = useMutation({
    mutationFn: ({ text, assignee }: { text: string; assignee: Assignee }) =>
      api.post("/api/tasks/assignee", { text, assignee }),
    onSuccess: invalidate,
    onError: () => toast.error("Zuständigkeit konnte nicht geändert werden"),
  });

  const setDue = useMutation({
    mutationFn: ({ text, due }: { text: string; due: string | null }) => api.post("/api/tasks/due", { text, due }),
    onSuccess: invalidate,
    onError: () => toast.error("Datum konnte nicht gespeichert werden"),
  });

  const open = (data?.filter((t) => !t.done) ?? []).filter((t) => filter === "Alle" || t.assignee === filter);

  const submitNewTask = () => {
    const text = newTask.trim();
    if (!text || addTask.isPending) return;
    addTask.mutate({ text, assignee: newAssignee, due: newDue || null });
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Aufgaben</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex items-center gap-2">
          <Input
            placeholder="Neue Aufgabe…"
            value={newTask}
            onChange={(e) => setNewTask(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && submitNewTask()}
          />
          <Select value={newAssignee} onValueChange={(v) => v && setNewAssignee(v as Assignee)}>
            <SelectTrigger className="w-32 shrink-0">
              <SelectValue>{(v: string) => v}</SelectValue>
            </SelectTrigger>
            <SelectContent>
              {ASSIGNEES.map((a) => (
                <SelectItem key={a} value={a}>
                  {a}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Input
            type="date"
            value={newDue}
            onChange={(e) => setNewDue(e.target.value)}
            className="w-36 shrink-0"
          />
          <Button size="sm" onClick={submitNewTask} disabled={addTask.isPending || !newTask.trim()}>
            {addTask.isPending ? "…" : "Hinzufügen"}
          </Button>
        </div>

        <SegmentedControl
          options={(["Alle", ...ASSIGNEES] as const).map((a) => ({ value: a, label: a }))}
          value={filter}
          onChange={setFilter}
        />

        {isLoading ? (
          <div className="space-y-2">
            <Skeleton className="h-8 w-full" />
            <Skeleton className="h-8 w-full" />
            <Skeleton className="h-8 w-full" />
          </div>
        ) : open.length === 0 ? (
          <p className="text-sm text-muted-foreground">Keine offenen Aufgaben.</p>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-8" />
                <TableHead>Aufgabe</TableHead>
                <TableHead className="w-28">Priorität</TableHead>
                <TableHead className="w-32">Zuständig</TableHead>
                <TableHead className="w-36">Fällig</TableHead>
                <TableHead className="w-8" />
              </TableRow>
            </TableHeader>
            <TableBody>
              {open.map((t, i) => (
                <TableRow key={`${i}-${t.text}`}>
                  <TableCell>
                    <Checkbox
                      disabled={toggleTask.isPending}
                      onCheckedChange={(checked) => toggleTask.mutate({ text: t.text, done: checked === true })}
                    />
                  </TableCell>
                  <TableCell>{t.text}</TableCell>
                  <TableCell>
                    <Badge variant={URGENCY_VARIANT[t.urgency]}>{URGENCY_LABEL[t.urgency]}</Badge>
                  </TableCell>
                  <TableCell>
                    <Select
                      value={t.assignee}
                      onValueChange={(v) => v && setAssignee.mutate({ text: t.text, assignee: v as Assignee })}
                      disabled={setAssignee.isPending}
                    >
                      <SelectTrigger size="sm" className="h-7 w-28 text-xs">
                        <SelectValue>{(v: string) => v}</SelectValue>
                      </SelectTrigger>
                      <SelectContent>
                        {ASSIGNEES.map((a) => (
                          <SelectItem key={a} value={a}>
                            {a}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </TableCell>
                  <TableCell>
                    <Input
                      type="date"
                      value={t.due ?? ""}
                      disabled={setDue.isPending}
                      onChange={(e) => setDue.mutate({ text: t.text, due: e.target.value || null })}
                      className="h-7 w-full text-xs"
                    />
                  </TableCell>
                  <TableCell>
                    <Button
                      variant="ghost"
                      size="icon-sm"
                      disabled={deleteTask.isPending}
                      onClick={() => deleteTask.mutate(t.text)}
                    >
                      <Trash2 />
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </CardContent>
    </Card>
  );
}
