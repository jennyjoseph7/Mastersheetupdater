"use client";

import type React from "react";

import { Card, CardContent } from "@/components/ui/card";
import { Check } from "lucide-react";
import { cn } from "@/lib/utils";

interface ObjectiveCardProps {
  icon: React.ReactNode;
  title: string;
  campaignSubType?: string;
  selected: boolean;
  onSelect: () => void;
}

export function ObjectiveCard({
  icon,
  title,
  campaignSubType,
  selected,
  onSelect,
}: ObjectiveCardProps) {
  return (
    <Card
      className={cn(
        "cursor-pointer transition-all duration-300 hover:shadow-lg hover:scale-[1.03] hover:border-primary/50",
        selected &&
          "border-primary ring-2 ring-primary ring-offset-2 shadow-lg bg-primary/5"
      )}
      onClick={onSelect}
    >
      <CardContent className="flex flex-col items-center justify-center p-6 relative">
        {selected && (
          <div className="absolute top-2 right-2 flex h-7 w-7 items-center justify-center rounded-full bg-primary text-primary-foreground shadow-md">
            <Check className="h-5 w-5" />
          </div>
        )}
        <div className="mb-3 text-muted-foreground">{icon}</div>
        {campaignSubType && (
          <p className="text-xs text-muted-foreground mb-1 text-center font-normal">
            {campaignSubType}
          </p>
        )}
        <h3 className="font-semibold text-sm text-center text-foreground">
          {title}
        </h3>
      </CardContent>
    </Card>
  );
}
