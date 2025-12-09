"use client"

import { useState } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Button } from "@/components/ui/button"
import { CreateNumberPoolDialog } from "./create-number-pool-dialog"
import type { VoiceConnection } from "@/app/connection/page"

interface VoiceQuickConnectCardProps {
  onConnect: (data: { phoneNumber: string; provider: string; callerName: string; numberType: string }) => void
  onCreatePool: (data: { poolName: string; selectedNumbers: any[] }) => void
  existingNumbers: VoiceConnection[]
}

export function VoiceQuickConnectCard({ onConnect, onCreatePool, existingNumbers }: VoiceQuickConnectCardProps) {
  const [phoneNumber, setPhoneNumber] = useState("")
  const [provider, setProvider] = useState("")
  const [numberType, setNumberType] = useState("")
  const [selectedPool, setSelectedPool] = useState("")
  const [isCreatePoolDialogOpen, setIsCreatePoolDialogOpen] = useState(false)

  const handleConnect = () => {
    if (phoneNumber && provider && numberType) {
      onConnect({ phoneNumber, provider, callerName: "Voice Caller", numberType })
      setPhoneNumber("")
      setProvider("")
      setNumberType("")
      setSelectedPool("")
    }
  }

  const handleCreatePool = (data: { poolName: string; selectedNumbers: any[] }) => {
    onCreatePool(data)
    setIsCreatePoolDialogOpen(false)
  }

  const handlePoolSelection = (value: string) => {
    if (value === "create-new") {
      setIsCreatePoolDialogOpen(true)
      // Don't set the selectedPool value, keep it empty
    } else {
      setSelectedPool(value)
    }
  }

  return (
    <>
      <Card>
        <CardHeader>
          <CardTitle>Quick Connect</CardTitle>
          <CardDescription>Quickly connect a registered voice number or number pool</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 md:grid-cols-4">
            <div className="space-y-2">
              <Label htmlFor="voice-number">Registered Number</Label>
              <Input
                id="voice-number"
                placeholder="+91-XXXXXXXXXX"
                value={phoneNumber}
                onChange={(e) => setPhoneNumber(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="voice-provider">Provider</Label>
              <Select value={provider} onValueChange={setProvider}>
                <SelectTrigger id="voice-provider">
                  <SelectValue placeholder="Choose Provider" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="Twilio">Twilio</SelectItem>
                  <SelectItem value="Airtel IQ">Airtel IQ</SelectItem>
                  <SelectItem value="Exotel">Exotel</SelectItem>
                  <SelectItem value="Knowlarity">Knowlarity</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="number-type">Number Type</Label>
              <Select value={numberType} onValueChange={setNumberType}>
                <SelectTrigger id="number-type">
                  <SelectValue placeholder="Select Type" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="Single Number">Single Number</SelectItem>
                  <SelectItem value="Number Pool">Number Pool</SelectItem>
                </SelectContent>
              </Select>
            </div>
            {numberType === "Number Pool" && (
              <div className="space-y-2">
                <Label htmlFor="pool-select">Select Number Pool</Label>
                <Select value={selectedPool} onValueChange={handlePoolSelection}>
                  <SelectTrigger id="pool-select">
                    <SelectValue placeholder="Choose Pool" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="create-new" className="text-purple-600 font-medium">
                      + Create Number Pool
                    </SelectItem>
                    <SelectItem value="pool-1">Sales Team Pool</SelectItem>
                    <SelectItem value="pool-2">Support Team Pool</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            )}
          </div>
          <div className="mt-4">
            <Button
              onClick={handleConnect}
              disabled={!phoneNumber || !provider || !numberType || (numberType === "Number Pool" && !selectedPool)}
              className="hover:bg-purple-700 bg-primary"
            >
              Connect
            </Button>
          </div>
        </CardContent>
      </Card>

      <CreateNumberPoolDialog
        open={isCreatePoolDialogOpen}
        onOpenChange={setIsCreatePoolDialogOpen}
        onSubmit={handleCreatePool}
        availableNumbers={existingNumbers}
      />
    </>
  )
}
