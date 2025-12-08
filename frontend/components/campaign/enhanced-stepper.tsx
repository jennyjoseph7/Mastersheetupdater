"use client"

import { Check, Circle } from "lucide-react"
import { cn } from "@/lib/utils"
import { motion } from "framer-motion"

interface Step {
  number: number
  title: string
  description: string
  completed: boolean
}

interface EnhancedStepperProps {
  steps: Step[]
  currentStep: number
  onStepClick: (step: number) => void
}

export function EnhancedStepper({ steps, currentStep, onStepClick }: EnhancedStepperProps) {
  return (
    <div className="w-full py-6">
      <div className="flex items-start justify-between">
        {steps.map((step, index) => (
          <div key={step.number} className="flex flex-1 items-start">
            <div className="flex flex-col items-center flex-1">
              <button
                onClick={() => step.completed && onStepClick(step.number)}
                disabled={!step.completed && step.number !== currentStep}
                className={cn(
                  "relative flex h-12 w-12 items-center justify-center rounded-full border-2 transition-all duration-300",
                  "focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2",
                  step.number === currentStep &&
                    "border-primary bg-primary text-primary-foreground shadow-lg shadow-primary/25 scale-110",
                  step.completed &&
                    step.number !== currentStep &&
                    "border-emerald-500 bg-emerald-500 text-white cursor-pointer hover:scale-105",
                  !step.completed &&
                    step.number !== currentStep &&
                    "border-muted bg-muted/50 text-muted-foreground cursor-not-allowed",
                )}
              >
                {step.completed && step.number !== currentStep ? (
                  <motion.div
                    initial={{ scale: 0 }}
                    animate={{ scale: 1 }}
                    transition={{ type: "spring", duration: 0.5 }}
                  >
                    <Check className="h-6 w-6" />
                  </motion.div>
                ) : step.number === currentStep ? (
                  <motion.span initial={{ scale: 0.8 }} animate={{ scale: 1 }} className="text-base font-bold">
                    {step.number}
                  </motion.span>
                ) : (
                  <Circle className="h-5 w-5" />
                )}
              </button>
              <div className="mt-3 text-center max-w-[140px]">
                <span
                  className={cn(
                    "block text-sm font-semibold transition-colors",
                    step.number === currentStep ? "text-foreground" : "text-muted-foreground",
                  )}
                >
                  {step.title}
                </span>
                <span className="block text-xs text-muted-foreground mt-1">{step.description}</span>
              </div>
            </div>
            {index < steps.length - 1 && (
              <div className="flex-1 pt-6 px-2">
                <div className="relative h-0.5 w-full bg-muted overflow-hidden">
                  <motion.div
                    className="absolute inset-y-0 left-0 bg-primary"
                    initial={{ width: "0%" }}
                    animate={{ width: step.completed ? "100%" : "0%" }}
                    transition={{ duration: 0.5, ease: "easeInOut" }}
                  />
                </div>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
