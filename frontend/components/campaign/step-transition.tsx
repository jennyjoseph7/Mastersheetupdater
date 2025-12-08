"use client"

import { motion, AnimatePresence } from "framer-motion"
import type React from "react"

interface StepTransitionProps {
  children: React.ReactNode
  step: number
}

export function StepTransition({ children, step }: StepTransitionProps) {
  return (
    <AnimatePresence mode="wait">
      <motion.div
        key={step}
        initial={{ opacity: 0, x: 20 }}
        animate={{ opacity: 1, x: 0 }}
        exit={{ opacity: 0, x: -20 }}
        transition={{ duration: 0.3 }}
      >
        {children}
      </motion.div>
    </AnimatePresence>
  )
}
