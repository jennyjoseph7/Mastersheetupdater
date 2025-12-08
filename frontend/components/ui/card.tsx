"use client";

import * as React from "react";
import { useState, useRef, useCallback } from "react";

import { cn } from "@/lib/utils";

function Card({ className, ...props }: React.ComponentProps<"div">) {
  const cardRef = useRef<HTMLDivElement>(null);
  const [transform, setTransform] = useState({
    rotateX: 0,
    rotateY: 0,
    scale: 1,
  });
  const [isHovered, setIsHovered] = useState(false);
  const rafRef = useRef<number | null>(null);
  const lastTransformRef = useRef({ rotateX: 0, rotateY: 0 });

  const handleMouseMove = useCallback((e: React.MouseEvent<HTMLDivElement>) => {
    if (!cardRef.current) return;

    // Cancel any pending animation frame
    if (rafRef.current !== null) {
      cancelAnimationFrame(rafRef.current);
    }

    // Use requestAnimationFrame for smooth updates
    rafRef.current = requestAnimationFrame(() => {
      if (!cardRef.current) return;

      const rect = cardRef.current.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;

      const centerX = rect.width / 2;
      const centerY = rect.height / 2;

      // Calculate normalized position (-1 to 1)
      const normalizedX = (x - centerX) / centerX;
      const normalizedY = (y - centerY) / centerY;

      // Reduced tilt multipliers for subtle effect
      const maxTilt = 2.5; // Maximum tilt in degrees (reduced from 8-15)
      
      // Apply easing function for smoother movement
      const easeX = normalizedX * 0.4; // Reduce sensitivity further
      const easeY = normalizedY * 0.4;

      const targetRotateX = easeY * -maxTilt;
      const targetRotateY = easeX * maxTilt;
      
      // Smooth interpolation to prevent jittery movements
      const smoothingFactor = 0.15;
      const rotateX = lastTransformRef.current.rotateX + (targetRotateX - lastTransformRef.current.rotateX) * smoothingFactor;
      const rotateY = lastTransformRef.current.rotateY + (targetRotateY - lastTransformRef.current.rotateY) * smoothingFactor;
      
      lastTransformRef.current = { rotateX, rotateY };
      const scale = 1.01; // Very subtle scale

      setTransform({ rotateX, rotateY, scale });
    });
  }, []);

  const handleMouseLeave = useCallback(() => {
    if (rafRef.current !== null) {
      cancelAnimationFrame(rafRef.current);
      rafRef.current = null;
    }
    setIsHovered(false);
    lastTransformRef.current = { rotateX: 0, rotateY: 0 };
    setTransform({ rotateX: 0, rotateY: 0, scale: 1 });
  }, []);

  const handleMouseEnter = useCallback(() => {
    setIsHovered(true);
  }, []);

  return (
    <div
      ref={cardRef}
      data-slot="card"
      className={cn(
        "bg-card/70 dark:bg-card/60 backdrop-blur-xl text-card-foreground flex flex-col gap-6 rounded-xl border border-border/40 dark:border-border/30 py-6 shadow-lg shadow-black/5 dark:shadow-black/30",
        "before:absolute before:inset-0 before:rounded-xl before:bg-gradient-to-br before:from-white/20 before:via-white/5 before:to-transparent before:opacity-50 dark:before:opacity-30 dark:before:from-white/10 dark:before:via-white/5 before:pointer-events-none",
        "relative overflow-hidden backdrop-saturate-150",
        "transition-transform duration-300 ease-out",
        "transform-gpu will-change-transform",
        className
      )}
      onMouseMove={handleMouseMove}
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
      style={{
        transform: `perspective(1000px) rotateX(${transform.rotateX}deg) rotateY(${transform.rotateY}deg) scale(${transform.scale})`,
        transformStyle: "preserve-3d",
      }}
      {...props}
    />
  );
}

function CardHeader({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="card-header"
      className={cn(
        "@container/card-header grid auto-rows-min grid-rows-[auto_auto] items-start gap-1.5 px-6 has-data-[slot=card-action]:grid-cols-[1fr_auto] [.border-b]:pb-6",
        className
      )}
      {...props}
    />
  );
}

function CardTitle({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="card-title"
      className={cn("leading-none font-semibold", className)}
      {...props}
    />
  );
}

function CardDescription({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="card-description"
      className={cn("text-muted-foreground text-sm", className)}
      {...props}
    />
  );
}

function CardAction({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="card-action"
      className={cn(
        "col-start-2 row-span-2 row-start-1 self-start justify-self-end",
        className
      )}
      {...props}
    />
  );
}

function CardContent({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="card-content"
      className={cn("px-6", className)}
      {...props}
    />
  );
}

function CardFooter({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="card-footer"
      className={cn("flex items-center px-6 [.border-t]:pt-6", className)}
      {...props}
    />
  );
}

export {
  Card,
  CardHeader,
  CardFooter,
  CardTitle,
  CardAction,
  CardDescription,
  CardContent,
};
