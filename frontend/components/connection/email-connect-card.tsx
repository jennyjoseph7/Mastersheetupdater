"use client"

import { useState } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Mail, Settings } from "lucide-react"
import { SmtpConfigDialog } from "@/components/connection/smtp-config-dialog"

interface EmailConnectCardProps {
  onConnect: (data: any) => void
}

export function EmailConnectCard({ onConnect }: EmailConnectCardProps) {
  const [isSmtpDialogOpen, setIsSmtpDialogOpen] = useState(false)

  const handleOAuthConnect = () => {
    // TODO: Implement OAuth flow
    console.log("OAuth connection initiated")
  }

  const handleSmtpSubmit = (data: any) => {
    onConnect(data)
    setIsSmtpDialogOpen(false)
  }

  return (
    <>
      <Card>
        <CardHeader>
          <CardTitle>Connect Email Account</CardTitle>
          <CardDescription>
            Choose between OAuth (recommended) for easy setup or SMTP for custom configurations
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 md:grid-cols-2">
            {/* OAuth Connection Card */}
            <button
              onClick={handleOAuthConnect}
              className="group relative flex flex-col items-start gap-3 rounded-lg border border-border bg-background p-6 text-left transition-all hover:border-purple-600 hover:shadow-md"
            >
              <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-purple-100 text-purple-600 transition-colors group-hover:bg-purple-600 group-hover:text-white">
                <Mail className="h-6 w-6" />
              </div>
              <div className="space-y-1">
                <h3 className="font-semibold">OAuth Connection</h3>
                <p className="text-sm text-muted-foreground">Connect with Google, Outlook, etc.</p>
              </div>
            </button>

            {/* SMTP Setup Card */}
            <button
              onClick={() => setIsSmtpDialogOpen(true)}
              className="group relative flex flex-col items-start gap-3 rounded-lg border border-border bg-background p-6 text-left transition-all hover:border-purple-600 hover:shadow-md"
            >
              <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-purple-100 text-purple-600 transition-colors group-hover:bg-purple-600 group-hover:text-white">
                <Settings className="h-6 w-6" />
              </div>
              <div className="space-y-1">
                <h3 className="font-semibold">SMTP Setup</h3>
                <p className="text-sm text-muted-foreground">Manual SMTP configuration</p>
              </div>
            </button>
          </div>
        </CardContent>
      </Card>

      <SmtpConfigDialog open={isSmtpDialogOpen} onOpenChange={setIsSmtpDialogOpen} onSubmit={handleSmtpSubmit} />
    </>
  )
}
