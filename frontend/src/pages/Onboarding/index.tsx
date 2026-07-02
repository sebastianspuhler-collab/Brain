import { Check } from "lucide-react";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import { useOnboarding } from "./hooks/useOnboarding";
import { CustomerDataStep, isCustomerDataValid } from "./steps/CustomerDataStep";
import { isProjectTypeValid, ProjectTypeStep } from "./steps/ProjectTypeStep";
import { ReviewStep } from "./steps/ReviewStep";

const STEPS = [
  { number: 1, label: "Kundendaten" },
  { number: 2, label: "Projekttyp" },
  { number: 3, label: "Review" },
];

export function OnboardingPage() {
  const onboarding = useOnboarding();
  const [confirmed, setConfirmed] = useState(false);

  const canGoNext =
    onboarding.step === 1
      ? isCustomerDataValid(onboarding.customer)
      : onboarding.step === 2
        ? isProjectTypeValid(onboarding.project)
        : true;

  return (
    <Card>
      <CardContent className="flex flex-col gap-6 pt-6">
        <nav className="flex items-center gap-2">
          {STEPS.map((s, i) => (
            <div key={s.number} className="flex items-center gap-2">
              <div className="flex items-center gap-2">
                <span
                  className={cn(
                    "flex size-7 shrink-0 items-center justify-center rounded-full text-xs font-medium",
                    onboarding.step > s.number
                      ? "bg-primary text-primary-foreground"
                      : onboarding.step === s.number
                        ? "border-2 border-primary text-primary"
                        : "border border-border text-muted-foreground"
                  )}
                >
                  {onboarding.step > s.number ? <Check className="size-3.5" /> : s.number}
                </span>
                <span className={cn("text-sm", onboarding.step === s.number ? "font-medium" : "text-muted-foreground")}>
                  {s.label}
                </span>
              </div>
              {i < STEPS.length - 1 && <div className="mx-1 h-px w-8 bg-border" />}
            </div>
          ))}
        </nav>

        <div>
          {onboarding.step === 1 && <CustomerDataStep data={onboarding.customer} onChange={onboarding.updateCustomer} />}
          {onboarding.step === 2 && (
            <ProjectTypeStep
              data={onboarding.project}
              onChange={onboarding.updateProject}
              onUpdateAnalysis={onboarding.updateAnalysis}
              analyzing={onboarding.analyzing}
              analyzeError={onboarding.analyzeError}
              onAnalyze={onboarding.analyzeNewProject}
            />
          )}
          {onboarding.step === 3 && (
            <ReviewStep
              customer={onboarding.customer}
              project={onboarding.project}
              toggles={onboarding.toggles}
              onToggleChange={onboarding.setToggles}
              confirmed={confirmed}
              onConfirmChange={setConfirmed}
              running={onboarding.running}
              events={onboarding.events}
              result={onboarding.result}
              runError={onboarding.runError}
              onStart={onboarding.startOnboarding}
            />
          )}
        </div>

        {!onboarding.running && !onboarding.result && (
          <div className="flex justify-between border-t border-border pt-4">
            <Button variant="outline" disabled={onboarding.step === 1} onClick={() => onboarding.setStep(onboarding.step - 1)}>
              Zurück
            </Button>
            {onboarding.step < 3 && (
              <Button disabled={!canGoNext} onClick={() => onboarding.setStep(onboarding.step + 1)}>
                Weiter
              </Button>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
