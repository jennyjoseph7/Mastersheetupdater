"use client";

import { useState } from "react";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Users,
  TrendingUp,
  TrendingDown,
  Activity,
  ArrowRight,
} from "lucide-react";
import { cn } from "@/lib/utils";

// --- Types ---
interface FunnelStage {
  id: string;
  stage: string;
  count: number;
  percentage: number;
}

// --- Data ---
const defaultFunnelData = {
  all: [
    { id: "1", stage: "Queued", count: 37, percentage: 100 },
    { id: "2", stage: "Attempted", count: 33, percentage: 89 },
    { id: "3", stage: "Contacted", count: 31, percentage: 84 },
    { id: "4", stage: "Reached", count: 22, percentage: 59 },
    { id: "5", stage: "Engaged", count: 0, percentage: 0 },
    { id: "6", stage: "Converted", count: 0, percentage: 0 },
  ],
  whatsapp: [
    { id: "w1", stage: "Sent", count: 120, percentage: 100 },
    { id: "w2", stage: "Delivered", count: 110, percentage: 92 },
    { id: "w3", stage: "Read", count: 85, percentage: 71 },
    { id: "w4", stage: "Replied", count: 40, percentage: 33 },
    { id: "w5", stage: "Converted", count: 10, percentage: 8 },
  ],
};

// --- Helper: Color Generator ---
function getStageColor(dropoffRate: number, index: number) {
  // Base Hues
  const healthyHue = 245; // Indigo (Good retention)
  const warningHue = 270; // Purple
  const dangerHue = 330;  // Pink/Red (High dropoff)

  // Logic: 
  // If dropoff is low (<10%), use Healthy Indigo.
  // If dropoff is high (>20%), shift towards Danger Pink.
  // Otherwise, standard Purple.
  
  if (dropoffRate > 25) {
     return {
        top: `hsl(${dangerHue}, 85%, 55%)`,
        bottom: `hsl(${dangerHue}, 90%, 45%)`,
        border: `hsl(${dangerHue}, 90%, 75%)`
     };
  }
  
  if (dropoffRate > 10) {
     // Standard Purple Gradient
     return {
        top: `hsl(${warningHue}, 75%, ${60 - index * 3}%)`,
        bottom: `hsl(${warningHue}, 85%, ${50 - index * 3}%)`,
        border: `hsl(${warningHue}, 85%, 70%)`
     };
  }

  // Healthy (Blue-ish)
  return {
     top: `hsl(${healthyHue}, 80%, ${60 - index * 2}%)`,
     bottom: `hsl(${healthyHue}, 90%, ${50 - index * 2}%)`,
     border: `hsl(${healthyHue}, 90%, 70%)`
  };
}

// --- Hover Details Card ---
function HoverDetails({
  stage,
  prevStage,
  index,
  totalStages,
  isVisible,
  widthOffset,
}: {
  stage: FunnelStage;
  prevStage: FunnelStage | null;
  index: number;
  totalStages: number;
  isVisible: boolean;
  widthOffset: number;
}) {
  const dropoffCount = prevStage ? prevStage.count - stage.count : 0;
  
  const conversionRate = prevStage && prevStage.count > 0
    ? ((stage.count / prevStage.count) * 100).toFixed(1)
    : "0.0";

  const dropoffRate = prevStage && prevStage.count > 0
    ? ((dropoffCount / prevStage.count) * 100).toFixed(0)
    : "0";

  // Position Logic
  const isBottomHalf = index > totalStages - 3; 

  const alignmentClass = isBottomHalf 
    ? "bottom-0 origin-bottom-left" 
    : "top-0 origin-top-left";
    
  const arrowPosition = isBottomHalf 
    ? "bottom-6" 
    : "top-6";

  return (
    <div
      className={cn(
        "absolute z-50 w-[280px] pl-8 transition-all duration-300 cubic-bezier(0.16, 1, 0.3, 1) cursor-default",
        isVisible
          ? "opacity-100 translate-x-0 scale-100"
          : "opacity-0 -translate-x-4 scale-95 pointer-events-none",
        alignmentClass 
      )}
      style={{
        left: `calc(50% + ${widthOffset / 2}%)`, 
      }}
    >
      <div className="bg-white/95 backdrop-blur-xl rounded-xl shadow-[0_20px_60px_-15px_rgba(0,0,0,0.3)] border border-slate-100 p-5 relative overflow-hidden">
        
        {/* Decorative Top Line */}
        <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-indigo-500 via-purple-500 to-pink-500 opacity-80" />

        {/* Header */}
        <div className="flex items-center justify-between mb-4 border-b border-slate-100 pb-3">
          <h4 className="font-bold text-slate-800 text-sm">{stage.stage}</h4>
          <span className="text-[10px] font-bold bg-slate-100 text-slate-600 px-2 py-1 rounded-full tracking-wide uppercase">
            Step {index + 1}
          </span>
        </div>

        {/* Stats */}
        <div className="space-y-4">
          <div className="bg-slate-50 p-3 rounded-lg border border-slate-100">
            <div className="flex items-center gap-2 text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-1">
              <Users className="w-3 h-3" /> Active Users
            </div>
            <div className="text-3xl font-bold text-slate-900 tabular-nums tracking-tight">{stage.count}</div>
          </div>

          {prevStage && (
            <div className="space-y-3 pt-2">
              <div className="flex justify-between items-end">
                 <div>
                    <div className="text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-0.5">Conversion</div>
                    <div className="text-lg font-bold text-emerald-600 flex items-center gap-1">
                       <TrendingUp className="w-4 h-4" /> {conversionRate}%
                    </div>
                 </div>
                 <span className="text-[10px] font-medium text-emerald-600/70">from prev. step</span>
              </div>

              <div className="h-px bg-slate-100 w-full" />

              <div className="flex justify-between items-end">
                 <div>
                    <div className="text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-0.5">Drop-off</div>
                    <div className="text-lg font-bold text-slate-700 flex items-center gap-1">
                       <TrendingDown className="w-4 h-4" /> {dropoffRate}%
                    </div>
                 </div>
                 <span className="text-xs font-medium text-red-600 bg-red-50 px-2 py-0.5 rounded-full border border-red-100">
                   -{dropoffCount} users
                 </span>
              </div>
            </div>
          )}
        </div>
        
        {/* Triangle Pointer */}
        {/* <div 
           className={cn(
             "absolute left-6 w-4 h-4 bg-white border-l border-b border-slate-100 transform rotate-45",
             arrowPosition
           )} 
        /> */}
      </div>
    </div>
  );
}

// --- Funnel Row Component ---
function FunnelRow({
  stage,
  prevStage,
  index,
  totalStages,
  topWidth,
  bottomWidth,
}: {
  stage: FunnelStage;
  prevStage: FunnelStage | null;
  index: number;
  totalStages: number;
  topWidth: number;
  bottomWidth: number;
}) {
  const [isHovered, setIsHovered] = useState(false);

  // 1. Math for Layout
  const avgWidth = (topWidth + bottomWidth) / 2;
  const leftEdgePercent = (100 - avgWidth) / 2;

  // 2. Math for Shape
  const insetTop = (100 - topWidth) / 2;
  const insetBottom = (100 - bottomWidth) / 2;
  const clipPath = `polygon(${insetTop}% 0%, ${100 - insetTop}% 0%, ${100 - insetBottom}% 100%, ${insetBottom}% 100%)`;

  // 3. Logic for Color & Dropoff
  const dropoffCount = prevStage ? prevStage.count - stage.count : 0;
  const dropoffRate = prevStage && prevStage.count > 0 
    ? (dropoffCount / prevStage.count) * 100 
    : 0;

  // Get dynamic color based on health
  const colors = getStageColor(dropoffRate, index);
  const gradient = `linear-gradient(to bottom, ${colors.top}, ${colors.bottom})`;

  // 4. Stacking Logic
  const zIndexValue = isHovered ? 50 : totalStages - index;

  return (
    <div 
      className="relative w-[600px] h-[64px] group flex items-center justify-center transition-all duration-200"
      style={{ 
        zIndex: zIndexValue, 
        marginBottom: '-6px' 
      }} 
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      {/* LEFT LABEL */}
      <div 
        className="absolute top-1/2 -translate-y-1/2 flex flex-col items-end pr-6 transition-all duration-300"
        style={{ 
           left: 0, 
           width: `${leftEdgePercent}%`, 
           opacity: isHovered ? 1 : 0.6
        }}
      >
         <span className="text-xs font-semibold text-slate-400 whitespace-nowrap">{stage.stage}</span>
         <span className={cn(
            "text-lg font-bold tabular-nums leading-none",
            isHovered ? "text-indigo-600" : "text-slate-700"
         )}>
            {stage.count}
         </span>
      </div>

      {/* CENTER: Funnel Slice */}
      <div className="relative w-full h-full">
        {/* Shadow */}
        <div 
          className="absolute inset-0 bg-slate-900/10 blur-md translate-y-2 scale-[0.95]"
          style={{ clipPath, zIndex: -1 }}
        />
        
        {/* Main Body */}
        <div
          className="relative w-full h-full transition-all duration-300 group-hover:scale-[1.01] group-hover:-translate-y-0.5 cursor-pointer shadow-inner"
          style={{ clipPath, background: gradient }}
        >
          {/* Top Highlight (Glass effect) */}
          <div className="absolute top-0 left-0 right-0 h-[1px] bg-white/40" />
          
          {/* Percentage Text */}
          <div className="absolute inset-0 flex items-center justify-center">
             <span className="text-white font-bold text-sm drop-shadow-md tracking-wide">
                {stage.percentage}
             </span>
          </div>
        </div>
      </div>

      {/* RIGHT: Drop-off Arrow & Hover Card */}
      <div 
         className="absolute h-full pointer-events-none"
         style={{
            left: `calc(50% + ${avgWidth / 2}%)`,
         }}
      >
          {/* THE DROP-OFF ARROW INDICATOR */}
          {dropoffCount > 0 && (
             <div className="absolute top-1/2 -translate-y-1/2 left-2 flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity duration-300">
                <div className={cn(
                   "h-px w-6", 
                   dropoffRate > 20 ? "bg-red-300" : "bg-slate-300"
                )} />
                <div className={cn(
                   "flex items-center text-xs font-bold bg-white/80 backdrop-blur px-2 py-0.5 rounded-full border shadow-sm",
                   dropoffRate > 20 ? "text-red-600 border-red-100" : "text-slate-500 border-slate-100"
                )}>
                   <ArrowRight className="w-3 h-3 mr-1" />
                   {dropoffRate.toFixed(0)}%
                </div>
             </div>
          )}

          {/* Hover Details Popup (Inside this div to share relative positioning) */}
          <div className="pointer-events-auto">
             <HoverDetails 
               stage={stage} 
               prevStage={prevStage} 
               index={index}
               totalStages={totalStages}
               isVisible={isHovered}
               widthOffset={0} // We are already positioned at the edge
             />
          </div>
      </div>
    </div>
  );
}

// --- Main Export ---
export function ProfessionalFunnel({
  customData,
  availableChannels,
}: {
  customData?: any;
  availableChannels?: string[];
} = {}) {
  const funnelData = customData || defaultFunnelData;
  const channels = availableChannels || ["all", "whatsapp"];
  const [activeTab, setActiveTab] = useState(channels[0]);

  // @ts-ignore
  const currentData: FunnelStage[] = funnelData[activeTab] || funnelData.all;

  const MAX_WIDTH = 100;
  const MIN_WIDTH = 25; 
  const stepSize = currentData.length > 1 
    ? (MAX_WIDTH - MIN_WIDTH) / (currentData.length - 1)
    : 0;

  if (!currentData || currentData.length === 0) {
    return <div className="p-8 text-center text-slate-400">No Data Available</div>;
  }

  return (
    <div className="w-full max-w-5xl mx-auto bg-white rounded-3xl border border-slate-100 shadow-sm p-8 pb-12 overflow-visible">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-12">
        <div>
          <h2 className="text-xl font-bold text-slate-900">Conversion Flow</h2>
          <p className="text-sm text-slate-500 mt-1">
            Real-time stage analysis and drop-off metrics
          </p>
        </div>
        
        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <TabsList className="bg-slate-100/80 p-1 h-auto">
            {channels.map((c) => (
              <TabsTrigger 
                key={c} 
                value={c} 
                className="capitalize px-4 py-1.5 data-[state=active]:bg-white data-[state=active]:shadow-sm data-[state=active]:text-indigo-600 font-medium"
              >
                {c === 'all' ? 'All Channels' : c}
              </TabsTrigger>
            ))}
          </TabsList>
        </Tabs>
      </div>

      {/* Chart Area */}
      <div className="relative flex flex-col items-center py-6 isolate">
        {/* Dashed Center Line */}
        <div className="absolute top-0 bottom-12 left-1/2 w-px border-l border-dashed border-slate-200 -z-10" />

        {currentData.map((stage, index) => {
          const topW = MAX_WIDTH - (index * stepSize);
          const bottomW = MAX_WIDTH - ((index + 1) * stepSize);
          const safeTop = Math.max(topW, 15);
          const safeBottom = Math.max(bottomW, 15 * 0.8);

          return (
            <FunnelRow
              key={stage.id}
              stage={stage}
              prevStage={index > 0 ? currentData[index - 1] : null}
              index={index}
              totalStages={currentData.length}
              topWidth={safeTop}
              bottomWidth={safeBottom}
            />
          );
        })}

        {/* Bottom Badge */}
        <div className="mt-8 z-20">
           <div className="inline-flex items-center gap-2 px-6 py-2.5 bg-emerald-50 text-emerald-700 rounded-full border border-emerald-100 shadow-sm hover:shadow-md transition-shadow cursor-default">
              <Activity className="w-4 h-4" />
              <span className="font-bold tabular-nums">
                {currentData[currentData.length - 1].count}
              </span>
              <span className="text-sm font-medium">Converted Users</span>
           </div>
        </div>
      </div>
    </div>
  );
}