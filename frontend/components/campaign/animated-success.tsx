"use client"

import { CheckCircle2 } from "lucide-react"
import { motion } from "framer-motion"

interface AnimatedSuccessProps {
  message: string
}

export function AnimatedSuccess({ message }: AnimatedSuccessProps) {
  return (
    <motion.div
      initial={{ scale: 0, opacity: 0 }}
      animate={{ scale: 1, opacity: 1 }}
      transition={{ type: "spring", duration: 0.5 }}
      className="flex items-center gap-2 text-emerald-600"
    >
      <CheckCircle2 className="h-5 w-5" />
      <span className="text-sm font-medium">{message}</span>
    </motion.div>
  )
}
