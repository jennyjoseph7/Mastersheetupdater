"use client"

import type React from "react"

import { useState } from "react"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Button } from "@/components/ui/button"
import { Checkbox } from "@/components/ui/checkbox"
import { Badge } from "@/components/ui/badge"
import type { VoiceConnection } from "@/app/connection/page"

interface CreateNumberPoolDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  onSubmit: (data: { poolName: string; selectedNumbers: any[] }) => void
  availableNumbers: VoiceConnection[]
}

export function CreateNumberPoolDialog({
  open,
  onOpenChange,
  onSubmit,
  availableNumbers,
}: CreateNumberPoolDialogProps) {
  const [poolName, setPoolName] = useState("")
  const [selectedNumbers, setSelectedNumbers] = useState<string[]>([])

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    const selected = availableNumbers
      .filter((num) => selectedNumbers.includes(num.id))
      .map((num) => ({
        number: num.number,
        provider: num.provider,
      }))
    onSubmit({ poolName, selectedNumbers: selected })
    setPoolName("")
    setSelectedNumbers([])
  }

  const toggleNumber = (id: string) => {
    setSelectedNumbers((prev) => (prev.includes(id) ? prev.filter((n) => n !== id) : [...prev, id]))
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Create Number Pool</DialogTitle>
          <DialogDescription>Select numbers to include in your new pool and give it a name</DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-6">
          <div className="space-y-2">
            <Label htmlFor="pool-name">
              Pool Name <span className="text-red-500">*</span>
            </Label>
            <Input
              id="pool-name"
              placeholder="Enter pool name (e.g., Sales Team Pool)"
              value={poolName}
              onChange={(e) => setPoolName(e.target.value)}
              required
            />
          </div>

          <div className="space-y-3">
            <Label>Select Numbers to Include</Label>
            <div className="border rounded-lg p-4 space-y-3 max-h-80 overflow-y-auto">
              {availableNumbers.length === 0 ? (
                <p className="text-sm text-muted-foreground text-center py-4">
                  No registered numbers available. Please register numbers first.
                </p>
              ) : (
                availableNumbers.map((number) => (
                  <div
                    key={number.id}
                    className="flex items-center justify-between p-3 rounded-lg border hover:bg-accent transition-colors"
                  >
                    <div className="flex items-center gap-3">
                      <Checkbox
                        id={number.id}
                        checked={selectedNumbers.includes(number.id)}
                        onCheckedChange={() => toggleNumber(number.id)}
                      />
                      <label htmlFor={number.id} className="cursor-pointer">
                        <div className="font-medium">{number.number}</div>
                      </label>
                    </div>
                    <div className="flex items-center gap-2">
                      <Badge variant="secondary" className="bg-purple-100 text-purple-700">
                        {number.provider}
                      </Badge>
                      <Badge variant="secondary" className="bg-green-100 text-green-700">
                        {number.status}
                      </Badge>
                    </div>
                  </div>
                ))
              )}
            </div>
            <p className="text-sm text-muted-foreground">Selected: {selectedNumbers.length} numbers</p>
          </div>

          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button
              type="submit"
              className="bg-purple-600 hover:bg-purple-700"
              disabled={!poolName || selectedNumbers.length === 0}
            >
              Save Pool
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
