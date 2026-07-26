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
  size?: "xs" | "sm" | "lg"
  className?: string
}

export function IdentityAvatar({ name, size = "lg", className }: IdentityAvatarProps) {
  const initials = getInitials(name)
  const colorClass = COLOR_CLASSES[colorIndexFor(name || "?")]

  return (
    <span
      className={cn(
        "flex shrink-0 items-center justify-center rounded-full font-semibold shadow-sm",
        size === "lg" && "h-24 w-24 border-[3px] border-background text-2xl",
        size === "sm" && "h-9 w-9 border-[3px] border-background text-sm",
        // Kompakte Variante für enge Zeilen wie den Sidebar-Verlauf
        // (Umsetzungsplan 2026-07-26) - dünnerer Rand statt 3px, sonst wirkt
        // er bei 20px Gesamtgröße wie ein dicker Ring statt ein Avatar.
        size === "xs" && "h-5 w-5 border border-background text-[10px]",
        colorClass,
        className
      )}
    >
      {initials || <UserRound className={size === "lg" ? "h-8 w-8" : size === "sm" ? "h-4 w-4" : "h-3 w-3"} />}
    </span>
  )
}
