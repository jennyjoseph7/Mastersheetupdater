"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import { Card, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Video, Upload, ArrowLeft, Save, Trash2 } from "lucide-react"

export default function VideoEditorPage() {
  const router = useRouter()
  const [uploadedVideo, setUploadedVideo] = useState<string | null>(null)

  const handleSaveAsset = () => {
    if (!uploadedVideo) return

    const asset = {
      id: `video-${Date.now()}`,
      type: "video",
      url: uploadedVideo,
      name: `Video Asset ${new Date().toLocaleTimeString()}`,
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
              <h1 className="text-2xl font-bold">Video Creative Editor</h1>
              <p className="text-sm text-muted-foreground">Upload your video creative</p>
            </div>
          </div>
        </div>
      </div>

      <div className="flex-1 p-6 md:p-8 w-full">
        <div className="max-w-4xl mx-auto space-y-6">
          <Card className="shadow">
            <CardContent className="p-12">
              <div className="border-2 border-dashed rounded-lg p-12 text-center">
                <Video className="h-16 w-16 text-muted-foreground mx-auto mb-4" />
                <p className="text-lg font-medium mb-2">Upload Your Video</p>
                <p className="text-sm text-muted-foreground mb-6">Drag and drop your video here, or click to browse</p>
                <Button variant="outline" className="gap-2 bg-transparent">
                  <Upload className="h-4 w-4" />
                  Choose Video File
                </Button>
                <p className="text-xs text-muted-foreground mt-4">Supported formats: MP4, MOV, AVI (Max 50MB)</p>
              </div>
            </CardContent>
          </Card>

          {uploadedVideo && (
            <Card className="shadow">
              <CardContent className="p-6">
                <div className="aspect-video bg-muted rounded-lg flex items-center justify-center">
                  <Video className="h-16 w-16 text-muted-foreground" />
                </div>
              </CardContent>
            </Card>
          )}

          <div className="flex gap-3">
            <Button variant="outline" className="flex-1 gap-2 bg-transparent">
              <Trash2 className="h-4 w-4" />
              Clear
            </Button>
            <Button className="flex-1 gap-2" onClick={handleSaveAsset} disabled={!uploadedVideo}>
              <Save className="h-4 w-4" />
              Save Video
            </Button>
          </div>
        </div>
      </div>
    </div>
  )
}
