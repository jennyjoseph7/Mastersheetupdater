"use client"

import { Check } from "lucide-react"
import { cn } from "@/lib/utils"

interface Step {
  number: number
  title: string
  completed: boolean
}

interface StepperProps {
  steps: Step[]
  currentStep: number
  onStepClick: (step: number) => void
}

export function Stepper({ steps, currentStep, onStepClick }: StepperProps) {
  return (
    <div className="w-full py-6">
      <div className="flex items-center justify-center max-w-2xl mx-auto">
        {steps.map((step, index) => (
          <div key={step.number} className="flex flex-1 items-center">
            <div className="flex flex-col items-center flex-1">
              <button
                onClick={() => step.completed && onStepClick(step.number)}
                disabled={!step.completed && step.number !== currentStep}
                className={cn(
                  "flex h-10 w-10 items-center justify-center rounded-full border transition-all duration-300",
                  step.number === currentStep &&
                    "border-primary/60 bg-primary/10 text-primary border-2 shadow-sm",
                  step.completed &&
                    step.number !== currentStep &&
                    "border-primary/40 bg-primary/5 text-primary cursor-pointer hover:bg-primary/10 hover:border-primary/60",
                  !step.completed &&
                    step.number !== currentStep &&
                    "border-border/50 bg-background/50 text-muted-foreground cursor-not-allowed",
                )}
              >
                {step.completed && step.number !== currentStep ? (
                  <Check className="h-4 w-4" />
                ) : (
                  <span className="text-sm font-medium">{step.number}</span>
                )}
              </button>
              <span
                className={cn(
                  "mt-2 text-xs font-medium text-center transition-colors",
                  step.number === currentStep 
                    ? "text-primary" 
                    : step.completed
                    ? "text-muted-foreground"
                    : "text-muted-foreground/60",
                )}
              >
                {step.title}
              </span>
            </div>
            {index < steps.length - 1 && (
              <div className="flex-1 mx-3 h-px bg-border/30 relative">
                <div
                  className={cn(
                    "absolute top-0 left-0 h-full transition-all duration-500 ease-out",
                    step.completed 
                      ? "w-full bg-primary/40" 
                      : "w-0 bg-transparent",
                  )}
                />
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
