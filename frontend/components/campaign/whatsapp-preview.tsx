"use client"

import { Card, CardContent } from "@/components/ui/card"
import { ChevronLeft, ChevronRight } from "lucide-react"
import { useState } from "react"

interface WhatsAppPreviewProps {
  businessName: string
  messageText: string
  images?: string[]
}

export function WhatsAppPreview({ businessName, messageText, images = [] }: WhatsAppPreviewProps) {
  const [currentImageIndex, setCurrentImageIndex] = useState(0)

  const handlePrevImage = () => {
    setCurrentImageIndex((prev) => (prev > 0 ? prev - 1 : images.length - 1))
  }

  const handleNextImage = () => {
    setCurrentImageIndex((prev) => (prev < images.length - 1 ? prev + 1 : 0))
  }

  return (
    <Card className="shadow-lg max-w-sm mx-auto">
      <CardContent className="p-0">
        {/* WhatsApp Header */}
        <div className="bg-[#075E54] text-white p-3 flex items-center gap-3">
          <div className="h-10 w-10 rounded-full bg-white/20 flex items-center justify-center text-sm font-semibold">
            {businessName.charAt(0)}
          </div>
          <div>
            <p className="font-semibold text-sm">{businessName}</p>
            <p className="text-xs opacity-80">Business Account</p>
          </div>
        </div>

        {/* Message Bubble */}
        <div className="bg-[#ECE5DD] p-4 min-h-[300px]">
          <div className="bg-white rounded-lg shadow-sm p-3 max-w-[85%]">
            {/* Images */}
            {images.length > 0 && (
              <div className="mb-2 relative">
                <img
                  src={images[currentImageIndex] || "/placeholder.svg"}
                  alt="Campaign creative"
                  className="w-full rounded-lg"
                />
                {images.length > 1 && (
                  <>
                    <button
                      onClick={handlePrevImage}
                      className="absolute left-2 top-1/2 -translate-y-1/2 bg-black/50 text-white rounded-full p-1 hover:bg-black/70"
                    >
                      <ChevronLeft className="h-4 w-4" />
                    </button>
                    <button
                      onClick={handleNextImage}
                      className="absolute right-2 top-1/2 -translate-y-1/2 bg-black/50 text-white rounded-full p-1 hover:bg-black/70"
                    >
                      <ChevronRight className="h-4 w-4" />
                    </button>
                    <div className="absolute bottom-2 left-1/2 -translate-x-1/2 flex gap-1">
                      {images.map((_, index) => (
                        <div
                          key={index}
                          className={`h-1.5 w-1.5 rounded-full ${
                            index === currentImageIndex ? "bg-white" : "bg-white/50"
                          }`}
                        />
                      ))}
                    </div>
                  </>
                )}
              </div>
            )}

            {/* Message Text */}
            <p className="text-sm leading-relaxed whitespace-pre-wrap">{messageText}</p>

            {/* Timestamp */}
            <div className="flex items-center justify-end gap-1 mt-1">
              <span className="text-[10px] text-gray-500">12:30 PM</span>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
