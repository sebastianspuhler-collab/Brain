import { AlertTriangle, Check, ExternalLink, Loader2, X } from "lucide-react";
import type { OnboardingEvent } from "@/api/client";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { STEP_LABELS, type AutomationToggles } from "../types";

interface StatusChecklistProps {
  toggles: AutomationToggles;
  events: Record<string, OnboardingEvent>;
}

const STATUS_ICON: Record<string, React.ReactNode> = {
  pending: <span className="size-4 rounded-full border border-border" />,
  running: <Loader2 className="size-4 animate-spin text-primary" />,
  done: <Check className="size-4 text-emerald-500" />,
  error: <X className="size-4 text-destructive" />,
  warning: <AlertTriangle className="size-4 text-amber-500" />,
};

export function StatusChecklist({ toggles, events }: StatusChecklistProps) {
  const keys = (Object.keys(STEP_LABELS) as (keyof AutomationToggles)[]).filter((key) => toggles[key]);

  return (
    <ul className="flex flex-col gap-2">
      {keys.map((key) => {
        const event = events[key];
        const status = event?.status ?? "pending";
        return (
          <li
            key={key}
            className={cn(
              "flex items-center justify-between gap-3 rounded-lg border border-border px-3 py-2.5",
              status === "running" && "border-primary/40 bg-primary/5"
            )}
          >
            <div className="flex items-center gap-3">
              {STATUS_ICON[status]}
              <span className="text-sm">{event?.message ?? STEP_LABELS[key]}</span>
            </div>
            {event?.link && (
              <Button
                variant="ghost"
                size="sm"
                render={
                  <a href={event.link} target="_blank" rel="noreferrer">
                    Öffnen <ExternalLink className="size-3.5" />
                  </a>
                }
              />
            )}
          </li>
        );
      })}
    </ul>
  );
}
