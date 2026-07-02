import { Check } from "lucide-react";
import { cn } from "@/lib/utils";

interface FeatureCardProps {
  label: string;
  active: boolean;
  onToggle: () => void;
}

export function FeatureCard({ label, active, onToggle }: FeatureCardProps) {
  return (
    <button
      type="button"
      onClick={onToggle}
      className={cn(
        "flex items-center gap-2 rounded-lg border px-3 py-2.5 text-left text-sm transition",
        active
          ? "border-primary bg-primary/10 text-foreground"
          : "border-border text-muted-foreground hover:border-primary/40 hover:text-foreground"
      )}
    >
      <span
        className={cn(
          "flex size-4 shrink-0 items-center justify-center rounded-full border",
          active ? "border-primary bg-primary text-primary-foreground" : "border-border"
        )}
      >
        {active && <Check className="size-3" />}
      </span>
      {label}
    </button>
  );
}
