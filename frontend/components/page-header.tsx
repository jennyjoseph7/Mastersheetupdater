"use client"

import type { ReactNode } from "react"

interface PageHeaderProps {
  title: string
  description?: string
  actions?: ReactNode
}

export default function PageHeader({ title, description, actions }: PageHeaderProps) {
  return (
    <div className="border-b bg-background/95 backdrop-blur mb-8">
      <div className="flex h-16 items-center justify-between px-6 md:px-8">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">{title}</h1>
          {description && <p className="text-sm text-muted-foreground mt-1">{description}</p>}
        </div>
        {actions && <div className="flex items-center">{actions}</div>}
      </div>
    </div>
  )
}
