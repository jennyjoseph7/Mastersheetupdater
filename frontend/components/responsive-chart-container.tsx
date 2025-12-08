import type React from "react"

interface ResponsiveChartContainerProps {
  children: React.ReactNode
  className?: string
}

export function ResponsiveChartContainer({ children, className }: ResponsiveChartContainerProps) {
  return (
    <div className={`w-full overflow-visible ${className || ""}`}>
      <div className="flex justify-center items-center w-full min-h-[280px] py-4">{children}</div>
    </div>
  )
}
