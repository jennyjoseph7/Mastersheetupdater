"use client"
import { Store, User, Upload } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Textarea } from "@/components/ui/textarea"

export default function ProfilePage() {
  return (
    <div className="min-h-screen bg-background">
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Profile Settings</h1>
          <p className="text-muted-foreground mt-1">Manage your personal and business information</p>
        </div>

        <Tabs defaultValue="basics" className="space-y-6">
          <TabsList className="bg-muted/50">
            <TabsTrigger value="basics" className="gap-2">
              <Store className="h-4 w-4" />
              Dealership Basics
            </TabsTrigger>
            <TabsTrigger value="identity" className="gap-2">
              <User className="h-4 w-4" />
              Dealership Identity
            </TabsTrigger>
          </TabsList>

          <TabsContent value="basics" className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>Dealership Basics</CardTitle>
                <CardDescription>Let's start with the essential details about your dealership</CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="grid md:grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="full-name">
                      Full Name <span className="text-destructive">*</span>
                    </Label>
                    <Input id="full-name" placeholder="User" />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="dealership-name">
                      Dealership Name <span className="text-destructive">*</span>
                    </Label>
                    <Input id="dealership-name" placeholder="user Auto Sales" />
                  </div>
                </div>

                <div className="grid md:grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="email">
                      Email <span className="text-destructive">*</span>
                    </Label>
                    <Input id="email" type="email" placeholder="user@g" />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="contact-number">
                      Contact Number <span className="text-destructive">*</span>
                    </Label>
                    <Input id="contact-number" type="tel" placeholder="Business contact number" />
                  </div>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="address">
                    Address <span className="text-destructive">*</span>
                  </Label>
                  <Textarea id="address" placeholder="Complete business address" className="min-h-[80px]" />
                </div>

                <div className="space-y-2">
                  <Label>
                    Upload Logo <span className="text-destructive">*</span>
                  </Label>
                  <div className="border-2 border-dashed rounded-lg p-8 text-center hover:border-primary/50 transition-colors cursor-pointer">
                    <Upload className="h-8 w-8 mx-auto mb-2 text-muted-foreground" />
                    <p className="text-sm text-muted-foreground">Drop your logo here or click to browse</p>
                    <p className="text-xs text-muted-foreground mt-1">No file chosen</p>
                  </div>
                </div>

                <div className="flex justify-end">
                  <Button size="lg" className="bg-primary hover:bg-primary/90">
                    Save Changes
                  </Button>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="identity" className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>Dealership Identity</CardTitle>
                <CardDescription>Tell us what makes your dealership unique</CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="space-y-2">
                  <Label htmlFor="usp-tagline">
                    USP/Tagline <span className="text-destructive">*</span>
                  </Label>
                  <Input
                    id="usp-tagline"
                    placeholder="Tell customers in one line why they should choose your dealership"
                  />
                  <p className="text-xs text-muted-foreground">
                    e.g., "Trusted for quality cars and excellent service"
                  </p>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="business-timings">Business Timings</Label>
                  <Input
                    id="business-timings"
                    placeholder="e.g., Mon-Sat: 9:00 AM - 7:00 PM, Sun: 10:00 AM - 6:00 PM"
                  />
                </div>

                <div className="space-y-2">
                  <Label>Upload Documents (Optional)</Label>
                  <p className="text-sm text-muted-foreground">Brochures, certifications, product PDFs, etc.</p>
                  <div className="border-2 border-dashed rounded-lg p-8 text-center hover:border-primary/50 transition-colors cursor-pointer">
                    <Upload className="h-8 w-8 mx-auto mb-2 text-muted-foreground" />
                    <p className="text-sm text-muted-foreground">Drop documents here or click to browse</p>
                    <p className="text-xs text-muted-foreground mt-1">No files chosen</p>
                  </div>
                </div>

                <div className="flex justify-end">
                  <Button size="lg" className="bg-primary hover:bg-primary/90">
                    Save Changes
                  </Button>
                </div>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  )
}
