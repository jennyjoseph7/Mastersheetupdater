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
      <div className="flex items-start max-w-4xl mx-auto relative">
        {steps.map((step, index) => {
          const isLastStep = index === steps.length - 1
          const isActive = step.number === currentStep
          const isCompleted = step.completed && !isActive
          const isClickable = step.completed || isActive

          return (
            <div key={step.number} className="flex-1 flex items-center relative">
              {/* Connector Line */}
              {!isLastStep && (
                <div className="absolute top-5 left-[50%] right-[-50%] h-1 bg-secondary -z-10">
                  <div
                    className={cn(
                      "h-full bg-primary transition-all duration-500 ease-out origin-left",
                      step.completed ? "w-full scale-x-100" : "w-0 scale-x-0"
                    )}
                  />
                </div>
              )}

              <div className="flex flex-col items-center w-full group">
                {/* Step Circle */}
                <button
                  onClick={() => isClickable && onStepClick(step.number)}
                  disabled={!isClickable}
                  className={cn(
                    "relative flex h-10 w-10 items-center justify-center rounded-full border-2 transition-all duration-300 ease-in-out z-10",
                    // Active State
                    isActive &&
                      "border-primary bg-primary text-primary-foreground shadow-lg shadow-primary/25 scale-110 ring-4 ring-primary/20",
                    // Completed State
                    isCompleted &&
                      "border-primary bg-primary text-primary-foreground hover:bg-primary/90 cursor-pointer",
                    // Pending State
                    !isActive &&
                      !isCompleted &&
                      "border-muted-foreground/20 bg-background text-muted-foreground/40 cursor-not-allowed"
                  )}
                >
                  <span className="relative z-10 flex items-center justify-center">
                    {isCompleted ? (
                      <Check className="h-5 w-5 animate-in fade-in zoom-in duration-300" />
                    ) : (
                      <span className="text-sm font-bold">{step.number}</span>
                    )}
                  </span>
                </button>

                {/* Step Title */}
                <div
                  className={cn(
                    "mt-3 flex flex-col items-center text-center transition-all duration-300",
                    isActive ? "-translate-y-1" : ""
                  )}
                >
                  <span
                    className={cn(
                      "text-sm font-semibold tracking-tight transition-colors duration-300",
                      isActive ? "text-primary" : "text-muted-foreground",
                      !isActive && !isCompleted && "text-muted-foreground/50"
                    )}
                  >
                    {step.title}
                  </span>
                  
                  {/* Optional: Add a status label below */}
                  <span className="text-[10px] font-medium text-muted-foreground/60 h-4">
                    {isActive ? "In Progress" : isCompleted ? "Completed" : "Pending"}
                  </span>
                </div>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}