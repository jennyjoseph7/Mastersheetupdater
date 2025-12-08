import { Skeleton } from "@/components/ui/skeleton"
import { Card, CardContent, CardHeader } from "@/components/ui/card"

export function CampaignFormSkeleton() {
  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <Skeleton className="h-6 w-48" />
          <Skeleton className="h-4 w-72 mt-2" />
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Skeleton className="h-4 w-24" />
            <Skeleton className="h-10 w-full" />
          </div>
          <div className="space-y-2">
            <Skeleton className="h-4 w-32" />
            <Skeleton className="h-10 w-full" />
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

export function ChannelCardSkeleton() {
  return (
    <Card>
      <CardContent className="flex flex-col items-center justify-center p-6">
        <Skeleton className="h-12 w-12 rounded-full mb-3" />
        <Skeleton className="h-4 w-20 mb-2" />
        <Skeleton className="h-5 w-24" />
      </CardContent>
    </Card>
  )
}
