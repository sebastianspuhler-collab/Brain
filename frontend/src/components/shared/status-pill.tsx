import * as React from "react"

import { cn } from "@/lib/utils"

export type StatusPillVariant = "neutral" | "warning" | "success" | "info" | "danger"

const VARIANT_CLASSES: Record<StatusPillVariant, string> = {
  neutral: "bg-muted text-muted-foreground",
  warning: "bg-amber-500/15 text-amber-400",
  success: "bg-emerald-500/15 text-emerald-400",
  info: "bg-accent text-accent-foreground",
  danger: "bg-destructive/10 text-destructive",
}

export interface StatusPillProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: StatusPillVariant
}

export function StatusPill({ variant = "neutral", className, children, ...props }: StatusPillProps) {
  return (
    <span
      data-slot="status-pill"
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-xs font-medium leading-normal",
        VARIANT_CLASSES[variant],
        className
      )}
      {...props}
    >
      {children}
    </span>
  )
}
