import type { ReactNode } from "react";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { cn } from "@/lib/utils";

const WEEKDAYS = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"];

export function toDayKey(d: Date): string {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

/** Montag-first Rasterkalender: volle Wochen, inkl. Rand-Tage aus Vor-/Folgemonat.
 * Extrahiert aus CalendarPage.tsx (Umsetzungsplan 2026-07-26), damit auch die
 * Aufgaben- und Meetings-Kalenderansicht dasselbe Raster nutzen können. */
export function buildMonthGrid(year: number, month: number): Date[] {
  const first = new Date(year, month, 1);
  const startOffset = (first.getDay() + 6) % 7;
  const gridStart = new Date(year, month, 1 - startOffset);
  const days: Date[] = [];
  for (let i = 0; i < 42; i++) {
    days.push(new Date(gridStart.getFullYear(), gridStart.getMonth(), gridStart.getDate() + i));
  }
  return days;
}

export interface MonthGridProps<T> {
  cursor: Date;
  itemsByDay: Map<string, T[]>;
  renderPill: (item: T, index: number) => ReactNode;
  /** Inhalt des Tages-Popups, z.B. <DayEventsPopoverContent date={date} items={items} .../>. */
  renderPopoverContent: (date: Date, items: T[]) => ReactNode;
  maxVisible?: number;
}

/** Generisches Monatsraster mit anklickbaren Tagen (Umsetzungsplan 2026-07-26):
 * jede Zelle ist ein eigener, unabhängig steuerbarer Popover-Trigger - Klick auf
 * den Tag ODER auf "+N weitere" öffnet dasselbe Tages-Popup, da beides Teil
 * desselben Trigger-Elements ist. Wird von CalendarPage.tsx sowie den
 * Kalenderansichten von TasksPage.tsx/MeetingsPage.tsx genutzt. */
export function MonthGrid<T>({ cursor, itemsByDay, renderPill, renderPopoverContent, maxVisible = 3 }: MonthGridProps<T>) {
  const grid = buildMonthGrid(cursor.getFullYear(), cursor.getMonth());
  const todayKey = toDayKey(new Date());

  return (
    <div className="overflow-hidden rounded-2xl border border-border">
      <div className="grid grid-cols-7 border-b border-border bg-muted/40">
        {WEEKDAYS.map((d) => (
          <div key={d} className="px-2 py-2 text-center text-xs font-medium text-muted-foreground">
            {d}
          </div>
        ))}
      </div>
      <div className="grid grid-cols-7">
        {grid.map((date, i) => {
          const key = toDayKey(date);
          const dayItems = itemsByDay.get(key) ?? [];
          const isCurrentMonth = date.getMonth() === cursor.getMonth();
          const isToday = key === todayKey;
          const isLastRow = i >= grid.length - 7;
          const visible = dayItems.slice(0, maxVisible);
          const overflow = dayItems.length - visible.length;

          return (
            <Popover key={key}>
              <PopoverTrigger
                render={
                  <div
                    role="button"
                    tabIndex={0}
                    className={cn(
                      "min-h-24 cursor-pointer border-r border-border p-1.5 text-left transition-colors hover:bg-muted/40 [&:nth-child(7n)]:border-r-0",
                      !isLastRow && "border-b",
                      !isCurrentMonth && "bg-muted/20"
                    )}
                  >
                    <div
                      className={cn(
                        "mb-1 flex size-6 items-center justify-center rounded-full text-xs",
                        isToday
                          ? "bg-primary font-medium text-primary-foreground"
                          : isCurrentMonth
                            ? "text-foreground"
                            : "text-muted-foreground/50"
                      )}
                    >
                      {date.getDate()}
                    </div>
                    <div className="flex flex-col gap-1">
                      {visible.map((item, idx) => renderPill(item, idx))}
                      {overflow > 0 && (
                        <div className="px-1.5 text-[10px] text-muted-foreground">+{overflow} weitere</div>
                      )}
                    </div>
                  </div>
                }
              />
              <PopoverContent align="start" side="bottom">
                {renderPopoverContent(date, dayItems)}
              </PopoverContent>
            </Popover>
          );
        })}
      </div>
    </div>
  );
}
