"use client"

import { useState } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Button } from "@/components/ui/button"

interface QuickConnectCardProps {
  onConnect: (data: { number: string; provider: string; senderName: string }) => void
}

export function QuickConnectCard({ onConnect }: QuickConnectCardProps) {
  const [number, setNumber] = useState("")
  const [provider, setProvider] = useState("")
  const [senderName, setSenderName] = useState("")

  const handleConnect = () => {
    if (number && provider && senderName) {
      onConnect({ number, provider, senderName })
      setNumber("")
      setProvider("")
      setSenderName("")
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Quick Connect</CardTitle>
        <CardDescription>Quickly connect a registered WhatsApp Business number</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="grid gap-4 md:grid-cols-3">
          <div className="space-y-2">
            <Label htmlFor="number">Registered Mobile Number</Label>
            <Input
              id="number"
              placeholder="+91-XXXXXXXXXX"
              value={number}
              onChange={(e) => setNumber(e.target.value)}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="provider">WhatsApp Provider</Label>
            <Select value={provider} onValueChange={setProvider}>
              <SelectTrigger id="provider">
                <SelectValue placeholder="Choose your Provider" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="Meta">Meta</SelectItem>
                <SelectItem value="Twilio">Twilio</SelectItem>
                <SelectItem value="Airtel">Airtel</SelectItem>
                <SelectItem value="Gupshup">Gupshup</SelectItem>
                <SelectItem value="Kaleyra">Kaleyra</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-2">
            <Label htmlFor="senderName">Sender Name</Label>
            <Input
              id="senderName"
              placeholder="Business Name"
              value={senderName}
              onChange={(e) => setSenderName(e.target.value)}
            />
          </div>
        </div>
        <div className="mt-4">
          <Button
            onClick={handleConnect}
            disabled={!number || !provider || !senderName}
            className="hover:bg-purple-700 bg-primary"
          >
            Connect
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}
