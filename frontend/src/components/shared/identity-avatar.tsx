import { UserRound } from "lucide-react"

import { cn } from "@/lib/utils"

/* Initialen-Avatar mit deterministisch aus dem Namen abgeleiteter Farbe (Muster
   aus buzz-ai: IdentityInitialsAvatar) - feste Palette aus Theme-Tokens statt
   Hex-Werten, damit die Farbe in Hell/Dunkel automatisch passt. */
const COLOR_CLASSES = [
  "bg-muted text-muted-foreground",
  "bg-secondary text-secondary-foreground",
  "bg-accent text-accent-foreground",
  "bg-primary/15 text-primary",
  "bg-destructive/15 text-destructive",
  "bg-emerald-500/15 text-emerald-600 dark:text-emerald-400",
] as const

function getInitials(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean)
  if (parts.length === 0) return ""
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase()
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase()
}

function colorIndexFor(seed: string): number {
  let hash = 0
  for (let i = 0; i < seed.length; i++) hash = (hash * 31 + seed.charCodeAt(i)) >>> 0
  return hash % COLOR_CLASSES.length
}

export interface IdentityAvatarProps {
  name: string
  size?: "sm" | "lg"
  className?: string
}

export function IdentityAvatar({ name, size = "lg", className }: IdentityAvatarProps) {
  const initials = getInitials(name)
  const colorClass = COLOR_CLASSES[colorIndexFor(name || "?")]

  return (
    <span
      className={cn(
        "flex shrink-0 items-center justify-center rounded-full border-[3px] border-background font-semibold shadow-sm",
        size === "lg" ? "h-24 w-24 text-2xl" : "h-9 w-9 text-sm",
        colorClass,
        className
      )}
    >
      {initials || <UserRound className={size === "lg" ? "h-8 w-8" : "h-4 w-4"} />}
    </span>
  )
}
