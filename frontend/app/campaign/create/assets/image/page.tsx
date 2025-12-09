"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import { Card, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Badge } from "@/components/ui/badge"
import { ScrollArea } from "@/components/ui/scroll-area"
import { ImageIcon, Upload, Sparkles, Download, Trash2, Search, ArrowLeft, Save } from "lucide-react"

const carCategories = ["EV", "Sedan", "Hatchback", "SUV", "Other"]

const sampleImages = [
  { id: 1, category: "Sedan", name: "Luxury Sedan", url: "/luxury-sedan.png" },
  { id: 2, category: "SUV", name: "Family SUV", url: "/family-suv.png" },
  { id: 3, category: "EV", name: "Electric Car", url: "/modern-electric-car.png" },
  { id: 4, category: "Hatchback", name: "City Hatchback", url: "/city-hatchback.jpg" },
]

const aspectRatios = [
  { id: "1:1", label: "1:1 (Square)", width: "300px", height: "300px" },
  { id: "16:9", label: "16:9 (Landscape)", width: "400px", height: "225px" },
  { id: "9:16", label: "9:16 (Portrait)", width: "225px", height: "400px" },
]

export default function ImageEditorPage() {
  const router = useRouter()
  const [selectedAspectRatio, setSelectedAspectRatio] = useState("16:9")
  const [selectedCategory, setSelectedCategory] = useState("All")
  const [searchQuery, setSearchQuery] = useState("")
  const [canvasImage, setCanvasImage] = useState<string | null>(null)
  const [taglineText, setTaglineText] = useState("")
  const [taglineStyle, setTaglineStyle] = useState("")
  const [aiPrompt, setAiPrompt] = useState("")
  const [generatedOptions, setGeneratedOptions] = useState<string[]>([])
  const [isGenerating, setIsGenerating] = useState(false)

  const currentRatio = aspectRatios.find((r) => r.id === selectedAspectRatio) || aspectRatios[1]

  const filteredImages = sampleImages.filter((img) => {
    const matchesCategory = selectedCategory === "All" || img.category === selectedCategory
    const matchesSearch = img.name.toLowerCase().includes(searchQuery.toLowerCase())
    return matchesCategory && matchesSearch
  })

  const handleGenerateAI = () => {
    if (!aiPrompt.trim()) return

    setIsGenerating(true)
    // Simulate AI generation
    setTimeout(() => {
      setGeneratedOptions([
        "/modern-car-background-option-1.jpg",
        "/modern-car-background-option-2.jpg",
        "/modern-car-background-option-3.jpg",
        "/modern-car-background-option-4.jpg",
      ])
      setIsGenerating(false)
    }, 2000)
  }

  const handleSaveAsset = () => {
    if (!canvasImage) return

    const asset = {
      id: `image-${Date.now()}`,
      type: "image",
      url: canvasImage,
      name: `Image Asset ${new Date().toLocaleTimeString()}`,
    }

    // Encode asset data and pass via URL params
    const assetParam = encodeURIComponent(JSON.stringify(asset))
    router.push(`/campaign/create?step=3&savedAsset=${assetParam}`)
  }

  return (
    <div className="min-h-screen flex flex-col">
      {/* Header with back button */}
      <div className="border-b bg-background/95 backdrop-blur">
        <div className="w-full px-4 py-4 md:px-6 lg:px-8">
          <div className="flex items-center gap-4">
            <Button variant="ghost" size="icon" onClick={() => router.push("/campaign/create?step=3")}>
              <ArrowLeft className="h-5 w-5" />
            </Button>
            <div>
              <h1 className="text-2xl font-bold">Image Creative Editor</h1>
              <p className="text-sm text-muted-foreground">Design your campaign creative</p>
            </div>
          </div>
        </div>
      </div>

      <div className="flex-1 p-6 md:p-8 w-full">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Left Panel - Editor Tabs */}
          <div className="space-y-4">
            <Tabs defaultValue="browse" className="w-full">
              <TabsList className="grid w-full grid-cols-4">
                <TabsTrigger value="browse">Browse</TabsTrigger>
                <TabsTrigger value="upload">Upload</TabsTrigger>
                <TabsTrigger value="tagline">Tagline</TabsTrigger>
                <TabsTrigger value="ai">AI Generate</TabsTrigger>
              </TabsList>

              {/* Browse Tab */}
              <TabsContent value="browse" className="space-y-4">
                <div className="space-y-3">
                  <div className="flex gap-2 flex-wrap">
                    <Badge
                      variant={selectedCategory === "All" ? "default" : "outline"}
                      className="cursor-pointer"
                      onClick={() => setSelectedCategory("All")}
                    >
                      All
                    </Badge>
                    {carCategories.map((category) => (
                      <Badge
                        key={category}
                        variant={selectedCategory === category ? "default" : "outline"}
                        className="cursor-pointer"
                        onClick={() => setSelectedCategory(category)}
                      >
                        {category}
                      </Badge>
                    ))}
                  </div>

                  <div className="relative">
                    <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                    <Input
                      placeholder="Search models..."
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                      className="pl-9"
                    />
                  </div>
                </div>

                <ScrollArea className="h-[400px] pr-4">
                  <div className="grid grid-cols-2 gap-3">
                    {filteredImages.map((image) => (
                      <Card
                        key={image.id}
                        className="cursor-pointer transition-all hover:shadow-md hover:border-primary"
                        onClick={() => setCanvasImage(image.url)}
                      >
                        <CardContent className="p-2">
                          <img
                            src={image.url || "/placeholder.svg"}
                            alt={image.name}
                            className="w-full h-32 object-cover rounded mb-2"
                          />
                          <p className="text-xs font-medium truncate">{image.name}</p>
                          <Badge variant="outline" className="text-xs mt-1">
                            {image.category}
                          </Badge>
                        </CardContent>
                      </Card>
                    ))}
                  </div>
                </ScrollArea>
              </TabsContent>

              {/* Upload Tab */}
              <TabsContent value="upload" className="space-y-4">
                <Card className="border-dashed border-2">
                  <CardContent className="flex flex-col items-center justify-center p-12">
                    <Upload className="h-12 w-12 text-muted-foreground mb-4" />
                    <p className="text-sm text-muted-foreground mb-4">
                      Drag and drop your image here, or click to browse
                    </p>
                    <Button variant="outline">
                      <Upload className="mr-2 h-4 w-4" />
                      Choose File
                    </Button>
                  </CardContent>
                </Card>
                <p className="text-xs text-muted-foreground">Supported formats: JPG, PNG, GIF (Max 5MB)</p>
              </TabsContent>

              {/* Tagline Tab */}
              <TabsContent value="tagline" className="space-y-4">
                <div className="space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="tagline-text">Tagline Text</Label>
                    <Textarea
                      id="tagline-text"
                      placeholder="Enter your tagline..."
                      rows={3}
                      value={taglineText}
                      onChange={(e) => setTaglineText(e.target.value)}
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="tagline-style">AI Edit Styling Prompt</Label>
                    <Input
                      id="tagline-style"
                      placeholder="e.g., Make it bold red at the top center"
                      value={taglineStyle}
                      onChange={(e) => setTaglineStyle(e.target.value)}
                    />
                    <Button variant="outline" size="sm" className="w-full gap-2 mt-2 bg-transparent">
                      <Sparkles className="h-4 w-4" />
                      Apply AI Styling
                    </Button>
                  </div>

                  <div className="p-4 border rounded-lg bg-muted/50">
                    <p className="text-sm text-muted-foreground mb-2">Preview:</p>
                    {taglineText ? (
                      <p className="text-lg font-semibold text-center">{taglineText}</p>
                    ) : (
                      <p className="text-sm text-muted-foreground text-center">Your tagline will appear here</p>
                    )}
                  </div>
                </div>
              </TabsContent>

              {/* AI Generate Tab */}
              <TabsContent value="ai" className="space-y-4">
                <div className="space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="ai-prompt">AI Background Prompt</Label>
                    <Textarea
                      id="ai-prompt"
                      placeholder="Describe the background you want to generate..."
                      rows={4}
                      value={aiPrompt}
                      onChange={(e) => setAiPrompt(e.target.value)}
                    />
                  </div>

                  <Button
                    className="w-full gap-2"
                    onClick={handleGenerateAI}
                    disabled={!aiPrompt.trim() || isGenerating}
                  >
                    <Sparkles className="h-4 w-4" />
                    {isGenerating ? "Generating..." : "Generate Options (3-4 variations)"}
                  </Button>

                  {generatedOptions.length > 0 && (
                    <>
                      <div className="space-y-2">
                        <Label>Generated Options</Label>
                        <div className="grid grid-cols-2 gap-3">
                          {generatedOptions.map((url, i) => (
                            <Card
                              key={i}
                              className="cursor-pointer hover:border-primary transition-all"
                              onClick={() => setCanvasImage(url)}
                            >
                              <CardContent className="p-2">
                                <div className="w-full h-24 bg-muted rounded flex items-center justify-center overflow-hidden">
                                  <img
                                    src={url || "/placeholder.svg"}
                                    alt={`Option ${i + 1}`}
                                    className="w-full h-full object-cover"
                                  />
                                </div>
                                <p className="text-xs text-center mt-2">Option {i + 1}</p>
                              </CardContent>
                            </Card>
                          ))}
                        </div>
                      </div>

                      <Button variant="outline" className="w-full gap-2 bg-transparent" onClick={handleGenerateAI}>
                        <Sparkles className="h-4 w-4" />
                        Regenerate
                      </Button>
                    </>
                  )}
                </div>
              </TabsContent>
            </Tabs>
          </div>

          {/* Right Panel - Canvas */}
          <div className="space-y-4">
            <div className="space-y-2">
              <Label>Aspect Ratio</Label>
              <div className="flex gap-2">
                {aspectRatios.map((ratio) => (
                  <Badge
                    key={ratio.id}
                    variant={selectedAspectRatio === ratio.id ? "default" : "outline"}
                    className="cursor-pointer"
                    onClick={() => setSelectedAspectRatio(ratio.id)}
                  >
                    {ratio.label}
                  </Badge>
                ))}
              </div>
            </div>

            <Card className="shadow">
              <CardContent className="p-6">
                <div className="flex items-center justify-center bg-muted/30 rounded-lg p-4">
                  <div
                    style={{
                      width: currentRatio.width,
                      height: currentRatio.height,
                      maxWidth: "100%",
                    }}
                    className="border-2 border-dashed border-muted-foreground/30 rounded-lg flex items-center justify-center bg-background relative overflow-hidden"
                  >
                    {canvasImage ? (
                      <img
                        src={canvasImage || "/placeholder.svg"}
                        alt="Canvas"
                        className="w-full h-full object-cover"
                      />
                    ) : (
                      <div className="text-center p-4">
                        <ImageIcon className="h-12 w-12 text-muted-foreground mx-auto mb-2" />
                        <p className="text-sm text-muted-foreground">Select an image or generate with AI</p>
                      </div>
                    )}
                    {taglineText && canvasImage && (
                      <div className="absolute inset-0 flex items-center justify-center">
                        <div className="bg-black/50 text-white px-4 py-2 rounded">
                          <p className="font-bold text-lg">{taglineText}</p>
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              </CardContent>
            </Card>

            <div className="flex gap-2">
              <Button variant="outline" className="flex-1 gap-2 bg-transparent">
                <Download className="h-4 w-4" />
                Download
              </Button>
              <Button variant="outline" className="flex-1 gap-2 bg-transparent">
                <Trash2 className="h-4 w-4" />
                Clear
              </Button>
              <Button className="flex-1 gap-2" onClick={handleSaveAsset} disabled={!canvasImage}>
                <Save className="h-4 w-4" />
                Save
              </Button>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
