import { Switch } from "@/components/ui/switch";
import { STEP_DESCRIPTIONS, STEP_LABELS, type AutomationToggles as TogglesType } from "../types";

interface AutomationTogglesProps {
  toggles: TogglesType;
  onChange: (toggles: TogglesType) => void;
  hasFiles: boolean;
}

export function AutomationToggles({ toggles, onChange, hasFiles }: AutomationTogglesProps) {
  const keys = Object.keys(STEP_LABELS) as (keyof TogglesType)[];

  return (
    <div className="flex flex-col divide-y divide-border rounded-2xl border border-border">
      {keys.map((key) => {
        const disabled = key === "file_upload" && !hasFiles;
        return (
          <div key={key} className="flex items-start justify-between gap-4 px-4 py-3">
            <div>
              <div className="text-sm font-medium">{STEP_LABELS[key]}</div>
              <div className="text-xs text-muted-foreground">
                {disabled ? "Deaktiviert - keine Dateien hochgeladen" : STEP_DESCRIPTIONS[key]}
              </div>
            </div>
            <Switch
              checked={disabled ? false : toggles[key]}
              disabled={disabled}
              onCheckedChange={(checked) => onChange({ ...toggles, [key]: checked === true })}
            />
          </div>
        );
      })}
    </div>
  );
}
