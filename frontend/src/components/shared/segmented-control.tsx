import * as React from "react"
import { Check } from "lucide-react"

import { cn } from "@/lib/utils"

export interface SegmentedControlOption<T extends string> {
  value: T
  label: string
  icon?: React.ReactNode
}

export interface SegmentedControlProps<T extends string> {
  options: SegmentedControlOption<T>[]
  value: T
  onChange: (value: T) => void
  showCheck?: boolean
  className?: string
}

export function SegmentedControl<T extends string>({
  options,
  value,
  onChange,
  showCheck,
  className,
}: SegmentedControlProps<T>) {
  return (
    <div className={cn("inline-flex flex-wrap gap-2", className)}>
      {options.map((option) => {
        const selected = option.value === value
        return (
          <button
            key={option.value}
            type="button"
            onClick={() => onChange(option.value)}
            className={cn(
              "flex items-center gap-2 rounded-2xl border px-4 py-2 text-sm transition-colors",
              selected
                ? "border-primary bg-accent text-foreground font-medium"
                : "border-border text-muted-foreground hover:border-muted-foreground"
            )}
          >
            {option.icon}
            {option.label}
            {showCheck && selected && <Check className="h-3.5 w-3.5 text-accent-foreground" />}
          </button>
        )
      })}
    </div>
  )
}
