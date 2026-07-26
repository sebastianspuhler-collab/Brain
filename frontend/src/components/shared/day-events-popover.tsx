import type { ReactNode } from "react";

const DATE_FORMAT = new Intl.DateTimeFormat("de-DE", {
  weekday: "long",
  day: "numeric",
  month: "long",
});

export interface DayEventsPopoverContentProps<T> {
  date: Date;
  items: T[];
  renderItem: (item: T, index: number) => ReactNode;
  emptyLabel?: string;
}

/** Inhalt für das Tages-Popup im Kalender/Aufgaben-Kalender/Meetings-Kalender
 * (Umsetzungsplan 2026-07-26) - rendert selbst nur Kopf+Liste, der Rahmen kommt
 * vom aufrufenden <PopoverContent> (components/ui/popover.tsx). Rein anzeigend,
 * der Aufrufer entscheidet über renderItem, was pro Zeile passiert (Termin,
 * Aufgabe mit Checkbox, Meeting mit Link). */
export function DayEventsPopoverContent<T>({
  date,
  items,
  renderItem,
  emptyLabel = "Keine Einträge an diesem Tag.",
}: DayEventsPopoverContentProps<T>) {
  return (
    <div className="flex flex-col gap-2">
      <div className="text-sm font-medium text-foreground capitalize">{DATE_FORMAT.format(date)}</div>
      {items.length === 0 ? (
        <p className="text-xs text-muted-foreground">{emptyLabel}</p>
      ) : (
        <div className="flex max-h-80 flex-col gap-1 overflow-y-auto">
          {items.map((item, i) => (
            <div key={i}>{renderItem(item, i)}</div>
          ))}
        </div>
      )}
    </div>
  );
}
