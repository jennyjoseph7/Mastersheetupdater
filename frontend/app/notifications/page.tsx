"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Lightbulb, X } from "lucide-react"

interface CampaignIdea {
  id: string
  title: string
  description: string
  objective: string
  campaignData: {
    campaignName: string
    campaignDescription: string
    selectedObjective: string
    selectedChannels: string[]
    campaignTagline?: string
    campaignOffer?: string
    selectedTone?: string
    selectedLanguage?: string
  }
}

export default function NotificationsPage() {
  const router = useRouter()
  const [campaignIdeas, setCampaignIdeas] = useState<CampaignIdea[]>([
    {
      id: "1",
      title: "Monsoon Campaign for Brezza",
      description: "Target SUV buyers with safety-focused messaging during the monsoon season.",
      objective: "Seasonal Sale",
      campaignData: {
        campaignName: "Monsoon Campaign for Brezza",
        campaignDescription:
          "Target SUV buyers with safety-focused messaging during the monsoon season. Highlight Brezza's safety features, ground clearance, and reliability in wet conditions.",
        selectedObjective: "seasonal-sale",
        selectedChannels: ["whatsapp", "email"],
        campaignTagline: "Drive Safe This Monsoon with Brezza",
        campaignOffer: "Special monsoon service package included with every purchase",
        selectedTone: "professional",
        selectedLanguage: "english",
      },
    },
    {
      id: "2",
      title: "Year-End Clearance Sale",
      description: "Clear out 2024 inventory with attractive discounts and financing options.",
      objective: "Clearance Sale",
      campaignData: {
        campaignName: "Year-End Clearance Sale 2024",
        campaignDescription:
          "Clear out 2024 inventory with attractive discounts and financing options. Target customers looking for great deals on premium vehicles.",
        selectedObjective: "clearance-sale",
        selectedChannels: ["whatsapp", "email", "voice"],
        campaignTagline: "Biggest Savings of the Year",
        campaignOffer: "Up to ₹2 lakh off + 0% financing for 12 months",
        selectedTone: "exciting",
        selectedLanguage: "english",
      },
    },
    {
      id: "3",
      title: "Service Reminder Campaign",
      description: "Remind customers about upcoming service appointments and maintenance packages.",
      objective: "Customer Retention",
      campaignData: {
        campaignName: "Service Reminder Campaign",
        campaignDescription:
          "Remind customers about upcoming service appointments and maintenance packages. Focus on building long-term relationships and ensuring vehicle health.",
        selectedObjective: "customer-retention",
        selectedChannels: ["whatsapp", "email"],
        campaignTagline: "Keep Your Car Running Smoothly",
        campaignOffer: "20% off on service packages this month",
        selectedTone: "friendly",
        selectedLanguage: "english",
      },
    },
  ])

  const handleUseIdea = (idea: CampaignIdea) => {
    // Store the campaign data in localStorage
    localStorage.setItem("campaignFormData", JSON.stringify(idea.campaignData))

    // Navigate to campaign creation page
    router.push("/campaign/create")
  }

  const handleDismiss = (ideaId: string) => {
    setCampaignIdeas((prev) => prev.filter((idea) => idea.id !== ideaId))
  }

  return (
    <div className="container mx-auto py-8 px-4 md:px-6">
      <div className="mb-8">
        <h1 className="text-3xl font-bold tracking-tight">Notifications</h1>
        <p className="text-muted-foreground mt-2">AI-powered campaign ideas and system notifications</p>
      </div>

      <div className="space-y-6">
        {campaignIdeas.length === 0 ? (
          <Card>
            <CardContent className="flex flex-col items-center justify-center py-12">
              <Lightbulb className="h-12 w-12 text-muted-foreground mb-4" />
              <p className="text-muted-foreground text-center">
                No new campaign ideas at the moment. Check back later!
              </p>
            </CardContent>
          </Card>
        ) : (
          campaignIdeas.map((idea) => (
            <Card key={idea.id} className="relative">
              <Button
                variant="ghost"
                size="icon"
                className="absolute top-4 right-4 h-8 w-8"
                onClick={() => handleDismiss(idea.id)}
              >
                <X className="h-4 w-4" />
              </Button>

              <CardHeader>
                <div className="flex items-start gap-4">
                  <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
                    <Lightbulb className="h-5 w-5 text-primary" />
                  </div>
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-2">
                      <CardTitle className="text-xl">{idea.title}</CardTitle>
                      <Badge variant="secondary" className="bg-primary/10 text-primary hover:bg-primary/20">
                        {idea.objective}
                      </Badge>
                    </div>
                    <CardDescription className="text-base">{idea.description}</CardDescription>
                  </div>
                </div>
              </CardHeader>

              <CardContent>
                <div className="flex gap-3">
                  <Button onClick={() => handleUseIdea(idea)} className="bg-primary hover:bg-primary/90">
                    Use This Idea
                  </Button>
                  <Button variant="outline" onClick={() => handleDismiss(idea.id)}>
                    Dismiss
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))
        )}
      </div>
    </div>
  )
}
