"use client"

import { useEffect, useState } from "react"

interface CircularProgressProps {
  value: number
  label: string
  size?: number
  strokeWidth?: number
  color?: string
}

export function CircularProgress({
  value,
  label,
  size = 80,
  strokeWidth = 6,
  color = "hsl(190, 90%, 50%)",
}: CircularProgressProps) {
  const [progress, setProgress] = useState(0)

  useEffect(() => {
    const timer = setTimeout(() => {
      setProgress(value)
    }, 100)

    return () => clearTimeout(timer)
  }, [value])

  const radius = (size - strokeWidth) / 2
  const circumference = radius * 2 * Math.PI
  const strokeDashoffset = circumference - (progress / 100) * circumference

  return (
    <div className="flex flex-col items-center justify-center">
      <div className="relative" style={{ width: size, height: size }}>
        <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
          {/* Background circle */}
          <circle
            className="stroke-muted"
            cx={size / 2}
            cy={size / 2}
            r={radius}
            strokeWidth={strokeWidth}
            fill="none"
          />

          {/* Progress circle with animation */}
          <circle
            className="transition-all duration-1000 ease-out"
            cx={size / 2}
            cy={size / 2}
            r={radius}
            strokeWidth={strokeWidth}
            fill="none"
            stroke={color}
            strokeLinecap="round"
            strokeDasharray={circumference}
            strokeDashoffset={strokeDashoffset}
            transform={`rotate(-90 ${size / 2} ${size / 2})`}
          />

          {/* Percentage text */}
          <text x="50%" y="50%" textAnchor="middle" dy=".3em" className="fill-foreground text-xl font-bold">
            {`${progress}%`}
          </text>
        </svg>
      </div>
      <p className="mt-2 text-center text-xs font-medium whitespace-normal text-wrap max-w-[100px] mx-auto">{label}</p>
    </div>
  )
}
