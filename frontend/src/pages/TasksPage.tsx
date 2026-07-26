import { DndContext, DragOverlay, PointerSensor, useDraggable, useDroppable, useSensor, useSensors } from "@dnd-kit/core";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Calendar as CalendarIcon, ChevronDown, ChevronLeft, ChevronRight, Kanban as KanbanIcon, List, Trash2 } from "lucide-react";
import { useMemo, useState } from "react";
import { toast } from "sonner";
import { api } from "@/api/client";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { DayEventsPopoverContent } from "@/components/shared/day-events-popover";
import { MonthGrid, toDayKey } from "@/components/shared/month-grid";
import { SegmentedControl } from "@/components/shared/segmented-control";
import { cn } from "@/lib/utils";

type Assignee = "Amin" | "Sebastian" | "Beide";
type View = "list" | "calendar" | "kanban";
type Bucket = "overdue" | "today" | "week" | "later" | "none";
type KanbanStatus = "todo" | "in_progress" | "done";

interface Task {
  text: string;
  urgency: "urgent" | "soon" | "normal" | "done";
  done?: boolean;
  assignee: Assignee;
  due: string | null;
  status: KanbanStatus;
}

const ASSIGNEES: Assignee[] = ["Amin", "Sebastian", "Beide"];
const MONTHS = [
  "Januar", "Februar", "März", "April", "Mai", "Juni",
  "Juli", "August", "September", "Oktober", "November", "Dezember",
];

// Fälligkeits-Pille statt Prioritäts-Badge (Umsetzungsplan 2026-07-26,
// Microsoft-To-Do/Google-Tasks-Vorbild) - die Buckets unten sagen schon, wie
// dringend etwas ist, die Farbe hier ist nur noch ein leiser Zusatzhinweis.
const URGENCY_DOT: Record<Task["urgency"], string> = {
  urgent: "bg-destructive/15 text-destructive",
  soon: "bg-amber-500/15 text-amber-600 dark:text-amber-400",
  normal: "bg-muted text-muted-foreground",
  done: "bg-muted text-muted-foreground",
};

const BUCKET_LABEL: Record<Bucket, string> = {
  overdue: "Überfällig",
  today: "Heute",
  week: "Diese Woche",
  later: "Später",
  none: "Kein Datum",
};
const BUCKET_ORDER: Bucket[] = ["overdue", "today", "week", "later", "none"];

function formatDue(due: string): string {
  const [, m, d] = due.split("-");
  return `${d}.${m}.`;
}

function bucketFor(due: string | null, todayStr: string, weekAheadStr: string): Bucket {
  if (!due) return "none";
  if (due < todayStr) return "overdue";
  if (due === todayStr) return "today";
  if (due <= weekAheadStr) return "week";
  return "later";
}

// Kanban-Board wie bei Jira (Umsetzungsplan 2026-07-27): drei Spalten nach
// Bearbeitungsstatus statt Fälligkeit. "Erledigt" bleibt weiterhin die echte
// Checkbox (siehe tasks_service.py::set_task_status) - ein Kartenzug aus
// "Erledigt" heraus öffnet die Aufgabe wieder, wie in Jira üblich.
const KANBAN_COLUMNS: { key: KanbanStatus; label: string }[] = [
  { key: "todo", label: "Zu erledigen" },
  { key: "in_progress", label: "In Arbeit" },
  { key: "done", label: "Erledigt" },
];

function KanbanCard({ t }: { t: Task }) {
  const { attributes, listeners, setNodeRef, transform, isDragging } = useDraggable({ id: t.text });
  const style = transform ? { transform: `translate3d(${transform.x}px, ${transform.y}px, 0)` } : undefined;
  return (
    <div
      ref={setNodeRef}
      style={style}
      {...listeners}
      {...attributes}
      className={cn(
        "cursor-grab touch-none rounded-xl border border-border bg-card p-2.5 shadow-sm select-none active:cursor-grabbing",
        isDragging && "opacity-40"
      )}
    >
      <div className={cn("text-sm text-foreground", t.done && "text-muted-foreground line-through")}>{t.text}</div>
      <div className="mt-1.5 flex items-center gap-1.5">
        {t.due && (
          <span className={cn("rounded-full px-1.5 py-0.5 text-[10px] font-medium", URGENCY_DOT[t.urgency])}>
            {formatDue(t.due)}
          </span>
        )}
        <span className="rounded-full bg-muted px-1.5 py-0.5 text-[10px] text-muted-foreground">{t.assignee}</span>
      </div>
    </div>
  );
}

function KanbanColumn({ status, label, tasks }: { status: KanbanStatus; label: string; tasks: Task[] }) {
  const { setNodeRef, isOver } = useDroppable({ id: status });
  return (
    <div
      ref={setNodeRef}
      className={cn(
        "flex min-h-40 flex-1 flex-col gap-2 rounded-2xl border border-border bg-muted/20 p-2.5 transition-colors",
        isOver && "border-primary/50 bg-primary/5"
      )}
    >
      <div className="flex items-center justify-between px-0.5">
        <span className="text-xs font-semibold text-muted-foreground">{label}</span>
        <span className="text-xs text-muted-foreground">{tasks.length}</span>
      </div>
      <div className="flex flex-col gap-2">
        {tasks.map((t, i) => (
          <KanbanCard key={`${status}-${i}-${t.text}`} t={t} />
        ))}
      </div>
    </div>
  );
}

function KanbanBoard({ tasks, onMove }: { tasks: Task[]; onMove: (text: string, status: KanbanStatus) => void }) {
  const sensors = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 8 } }));
  const [activeText, setActiveText] = useState<string | null>(null);

  const byStatus: Record<KanbanStatus, Task[]> = { todo: [], in_progress: [], done: [] };
  for (const t of tasks) byStatus[t.status].push(t);
  const activeTask = tasks.find((t) => t.text === activeText) ?? null;

  return (
    <DndContext
      sensors={sensors}
      onDragStart={(e) => setActiveText(String(e.active.id))}
      onDragEnd={(e) => {
        setActiveText(null);
        const target = e.over?.id as KanbanStatus | undefined;
        if (!target) return;
        const task = tasks.find((t) => t.text === e.active.id);
        if (task && task.status !== target) onMove(task.text, target);
      }}
      onDragCancel={() => setActiveText(null)}
    >
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        {KANBAN_COLUMNS.map((c) => (
          <KanbanColumn key={c.key} status={c.key} label={c.label} tasks={byStatus[c.key]} />
        ))}
      </div>
      <DragOverlay>{activeTask && <KanbanCard t={activeTask} />}</DragOverlay>
    </DndContext>
  );
}

export function TasksPage() {
  const queryClient = useQueryClient();
  const [newTask, setNewTask] = useState("");
  const [newAssignee, setNewAssignee] = useState<Assignee>("Beide");
  const [newDue, setNewDue] = useState("");
  const [filter, setFilter] = useState<Assignee | "Alle">("Alle");
  const [view, setView] = useState<View>("list");
  const [showDone, setShowDone] = useState(false);
  const [cursor, setCursor] = useState(() => {
    const now = new Date();
    return new Date(now.getFullYear(), now.getMonth(), 1);
  });

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

  const setStatus = useMutation({
    mutationFn: ({ text, status }: { text: string; status: KanbanStatus }) =>
      api.post("/api/tasks/status", { text, status }),
    onSuccess: invalidate,
    onError: () => toast.error("Status konnte nicht geändert werden"),
  });

  function moveKanbanCard(text: string, status: KanbanStatus) {
    if (status === "done") toggleTask.mutate({ text, done: true });
    else setStatus.mutate({ text, status });
  }

  const filtered = (data ?? []).filter((t) => filter === "Alle" || t.assignee === filter);
  const openTasks = filtered.filter((t) => !t.done);
  const doneTasks = filtered.filter((t) => t.done);

  const buckets = useMemo(() => {
    const todayStr = toDayKey(new Date());
    const weekAhead = new Date();
    weekAhead.setDate(weekAhead.getDate() + 7);
    const weekAheadStr = toDayKey(weekAhead);
    const map: Record<Bucket, Task[]> = { overdue: [], today: [], week: [], later: [], none: [] };
    for (const t of openTasks) {
      map[bucketFor(t.due, todayStr, weekAheadStr)].push(t);
    }
    for (const b of BUCKET_ORDER) {
      map[b].sort((a, c) => (a.due ?? "").localeCompare(c.due ?? ""));
    }
    return map;
  }, [openTasks]);

  const tasksByDue = useMemo(() => {
    const map = new Map<string, Task[]>();
    for (const t of openTasks) {
      if (!t.due) continue;
      if (!map.has(t.due)) map.set(t.due, []);
      map.get(t.due)!.push(t);
    }
    return map;
  }, [openTasks]);

  const submitNewTask = () => {
    const text = newTask.trim();
    if (!text || addTask.isPending) return;
    addTask.mutate({ text, assignee: newAssignee, due: newDue || null });
  };

  function TaskRow({ t }: { t: Task }) {
    return (
      <div className="group flex items-center gap-2.5 rounded-xl px-2 py-2 transition-colors hover:bg-muted/40">
        <Checkbox
          checked={!!t.done}
          disabled={toggleTask.isPending}
          onCheckedChange={(checked) => toggleTask.mutate({ text: t.text, done: checked === true })}
        />
        <span className={cn("min-w-0 flex-1 truncate text-sm", t.done && "text-muted-foreground line-through")}>
          {t.text}
        </span>
        {t.due && (
          <span className={cn("shrink-0 rounded-full px-2 py-0.5 text-[11px] font-medium", URGENCY_DOT[t.urgency])}>
            {formatDue(t.due)}
          </span>
        )}
        <Select
          value={t.assignee}
          onValueChange={(v) => v && setAssignee.mutate({ text: t.text, assignee: v as Assignee })}
          disabled={setAssignee.isPending}
        >
          <SelectTrigger size="sm" className="h-7 w-24 shrink-0 border-none bg-transparent text-xs shadow-none">
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
        <Button
          variant="ghost"
          size="icon-sm"
          className="shrink-0 opacity-0 group-hover:opacity-100"
          disabled={deleteTask.isPending}
          onClick={() => deleteTask.mutate(t.text)}
        >
          <Trash2 className="size-4" />
        </Button>
      </div>
    );
  }

  return (
    <Card>
      <CardHeader className="flex-row items-center justify-between gap-2 space-y-0">
        <CardTitle>Aufgaben</CardTitle>
        <SegmentedControl
          options={[
            { value: "list", label: "Liste", icon: <List className="size-3.5" /> },
            { value: "kanban", label: "Kanban", icon: <KanbanIcon className="size-3.5" /> },
            { value: "calendar", label: "Kalender", icon: <CalendarIcon className="size-3.5" /> },
          ]}
          value={view}
          onChange={setView}
        />
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
          <Input type="date" value={newDue} onChange={(e) => setNewDue(e.target.value)} className="w-36 shrink-0" />
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
        ) : view === "kanban" ? (
          <KanbanBoard tasks={filtered} onMove={moveKanbanCard} />
        ) : view === "calendar" ? (
          <div className="flex flex-col gap-2">
            <div className="flex items-center justify-between gap-2">
              <span className="text-sm font-medium text-foreground">
                {MONTHS[cursor.getMonth()]} {cursor.getFullYear()}
              </span>
              <div className="flex items-center gap-1">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => {
                    const now = new Date();
                    setCursor(new Date(now.getFullYear(), now.getMonth(), 1));
                  }}
                >
                  Heute
                </Button>
                <Button
                  variant="ghost"
                  size="icon-sm"
                  aria-label="Vorheriger Monat"
                  onClick={() => setCursor((c) => new Date(c.getFullYear(), c.getMonth() - 1, 1))}
                >
                  <ChevronLeft className="size-4" />
                </Button>
                <Button
                  variant="ghost"
                  size="icon-sm"
                  aria-label="Nächster Monat"
                  onClick={() => setCursor((c) => new Date(c.getFullYear(), c.getMonth() + 1, 1))}
                >
                  <ChevronRight className="size-4" />
                </Button>
              </div>
            </div>
            <MonthGrid
              cursor={cursor}
              itemsByDay={tasksByDue}
              renderPill={(t, idx) => (
                <div
                  key={idx}
                  className={cn("truncate rounded-md px-1.5 py-0.5 text-[11px] leading-tight", URGENCY_DOT[t.urgency])}
                >
                  {t.text}
                </div>
              )}
              renderPopoverContent={(date, dayTasks) => (
                <DayEventsPopoverContent
                  date={date}
                  items={dayTasks}
                  emptyLabel="Keine Aufgaben an diesem Tag."
                  renderItem={(t) => (
                    <div className="flex items-center gap-2 rounded-lg px-2 py-1.5 hover:bg-muted/50">
                      <Checkbox
                        checked={!!t.done}
                        disabled={toggleTask.isPending}
                        onCheckedChange={(checked) => toggleTask.mutate({ text: t.text, done: checked === true })}
                      />
                      <span className="min-w-0 flex-1 truncate text-sm text-foreground">{t.text}</span>
                    </div>
                  )}
                />
              )}
            />
          </div>
        ) : openTasks.length === 0 && doneTasks.length === 0 ? (
          <p className="text-sm text-muted-foreground">Keine Aufgaben.</p>
        ) : (
          <div className="flex flex-col gap-4">
            {openTasks.length === 0 ? (
              <p className="text-sm text-muted-foreground">Keine offenen Aufgaben.</p>
            ) : (
              BUCKET_ORDER.filter((b) => buckets[b].length > 0).map((b) => (
                <div key={b}>
                  <div className="mb-1 px-2 text-xs font-medium text-muted-foreground">{BUCKET_LABEL[b]}</div>
                  <div className="flex flex-col">
                    {buckets[b].map((t, i) => (
                      <TaskRow key={`${b}-${i}-${t.text}`} t={t} />
                    ))}
                  </div>
                </div>
              ))
            )}

            {doneTasks.length > 0 && (
              <div>
                <button
                  type="button"
                  onClick={() => setShowDone((v) => !v)}
                  className="flex items-center gap-1 px-2 text-xs font-medium text-muted-foreground hover:text-foreground"
                >
                  {showDone ? <ChevronDown className="size-3.5" /> : <ChevronRight className="size-3.5" />}
                  Erledigt ({doneTasks.length})
                </button>
                {showDone && (
                  <div className="mt-1 flex flex-col">
                    {doneTasks.map((t, i) => (
                      <TaskRow key={`done-${i}-${t.text}`} t={t} />
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
