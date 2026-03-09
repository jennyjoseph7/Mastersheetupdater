"use client";

import { useState, useMemo } from "react";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Users,
  TrendingUp,
  TrendingDown,
  Activity,
  ArrowRight,
  AlertCircle,
  Target,
  Layers,
} from "lucide-react";
import { cn } from "@/lib/utils";

// --- Types ---

interface EngagementStat {
  total: number;
  channel: string;
  converted?: number;
  // Channel specific & Combined keys
  sent?: number;
  called?: number;
  sent_called?: number;
  delivered?: number;
  ringing?: number;
  delivered_ringing?: number;
  read?: number;
  answered?: number;
  read_answered?: number;
  interacted?: number;
  engaged?: number;
  interacted_engaged?: number;
  [key: string]: any; // Fallback for dynamic keys
}

interface CampaignData {
  campaign_id: string;
  campaign_name: string;
  engagement_stats: EngagementStat[];
}

interface ApiResponse {
  data: CampaignData[];
}

interface FunnelStage {
  id: string;
  stage: string;
  count: number;
  percentage: number;
}

// --- Configuration ---

// We check these keys in order of preference depending on the channel
const STAGE_MAPPINGS = [
  { id: "attempted", keys: ["sent_called", "called", "sent"], fallbackLabel: "Attempted" },
  { id: "reached", keys: ["delivered_ringing", "ringing", "delivered"], fallbackLabel: "Reached" },
  { id: "contacted", keys: ["read_answered", "answered", "read"], fallbackLabel: "Contacted" },
  { id: "engaged", keys: ["interacted_engaged", "engaged", "interacted"], fallbackLabel: "Engaged" },
  // Added final 'Converted' stage to be rendered as a row
  { id: "converted", keys: ["converted"], fallbackLabel: "Converted" },
] as const;

// --- Helper: Color Generator ---
function getStageColor(dropoffRate: number, index: number) {
  const healthyHue = 245; // Indigo
  const warningHue = 270; // Purple
  const dangerHue = 330;  // Pink/Red

  if (dropoffRate > 30) {
    return {
      top: `hsl(${dangerHue}, 85%, 55%)`,
      bottom: `hsl(${dangerHue}, 90%, 45%)`,
      bgClass: "bg-pink-500",
    };
  }
  if (dropoffRate > 15) {
    return {
      top: `hsl(${warningHue}, 75%, ${60 - index * 3}%)`,
      bottom: `hsl(${warningHue}, 85%, ${50 - index * 3}%)`,
      bgClass: "bg-purple-500",
    };
  }
  return {
    top: `hsl(${healthyHue}, 80%, ${60 - index * 2}%)`,
    bottom: `hsl(${healthyHue}, 90%, ${50 - index * 2}%)`,
    bgClass: "bg-indigo-500",
  };
}

// --- Helper: Format Label ---
function formatStageLabel(key: string): string {
  return key
    .split("_")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" / ");
}

// --- Sub-Component: Legend ---
function FunnelLegend() {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-10">
      <div className="flex flex-col gap-3 p-4 bg-slate-50/50 rounded-2xl border border-slate-100">
        <div className="flex items-center gap-2 mb-1">
          <Target className="w-4 h-4 text-indigo-600" />
          <span className="text-[11px] font-black text-slate-500 uppercase tracking-widest">Retention Health</span>
        </div>
        <div className="flex flex-wrap gap-4">
          <div className="flex items-center gap-2">
            <div className="w-2.5 h-2.5 rounded-full bg-indigo-500 shadow-[0_0_8px_rgba(99,102,241,0.4)]" />
            <span className="text-xs font-bold text-slate-600">Healthy (&gt;85%)</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-2.5 h-2.5 rounded-full bg-purple-500 shadow-[0_0_8px_rgba(168,85,247,0.4)]" />
            <span className="text-xs font-bold text-slate-600">Warning (70-85%)</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-2.5 h-2.5 rounded-full bg-pink-500 shadow-[0_0_8px_rgba(236,72,153,0.4)]" />
            <span className="text-xs font-bold text-slate-600">Critical (&lt;70%)</span>
          </div>
        </div>
      </div>

      <div className="flex flex-col gap-3 p-4 bg-slate-50/50 rounded-2xl border border-slate-100">
        <div className="flex items-center gap-2 mb-1">
          <Layers className="w-4 h-4 text-slate-400" />
          <span className="text-[11px] font-black text-slate-500 uppercase tracking-widest">Calculation Logic</span>
        </div>
        <div className="flex gap-6">
          <div className="flex items-center gap-2">
            <div className="px-1.5 py-0.5 rounded bg-slate-200 text-[10px] font-black text-slate-600">%</div>
            <span className="text-xs font-medium text-slate-500 italic">Vs. Total Leads</span>
          </div>
          <div className="flex items-center gap-2">
            <ArrowRight className="w-3.5 h-3.5 text-slate-300" />
            <span className="text-xs font-medium text-slate-500 italic">Step-over-step Drop</span>
          </div>
        </div>
      </div>
    </div>
  );
}

// --- Sub-Component: Hover Details ---
function HoverDetails({
  stage,
  prevStage,
  index,
  totalStages,
  isVisible,
}: {
  stage: FunnelStage;
  prevStage: FunnelStage | null;
  index: number;
  totalStages: number;
  isVisible: boolean;
}) {
  const dropoffCount = prevStage ? prevStage.count - stage.count : 0;
  const conversionRate = prevStage && prevStage.count > 0
    ? ((stage.count / prevStage.count) * 100).toFixed(1)
    : "0.0";
  const dropoffRate = prevStage && prevStage.count > 0
    ? ((dropoffCount / prevStage.count) * 100).toFixed(0)
    : "0";

  const isBottomHalf = index > totalStages - 3;
  const alignmentClass = isBottomHalf ? "bottom-0 origin-bottom-left" : "top-0 origin-top-left";

  return (
    <div
      className={cn(
        "absolute z-50 w-[280px] pl-8 transition-all duration-300 cubic-bezier(0.16, 1, 0.3, 1) cursor-default",
        isVisible ? "opacity-100 translate-x-0 scale-100" : "opacity-0 -translate-x-4 scale-95 pointer-events-none",
        alignmentClass
      )}
      style={{ left: "50%" }}
    >
      <div className="bg-white/95 backdrop-blur-xl rounded-xl shadow-[0_20px_60px_-15px_rgba(0,0,0,0.3)] border border-slate-100 p-5 relative overflow-hidden">
        <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-indigo-500 via-purple-500 to-pink-500 opacity-80" />
        <div className="flex items-center justify-between mb-4 border-b border-slate-100 pb-3">
          <h4 className="font-bold text-slate-800 text-sm">{stage.stage}</h4>
          <span className="text-[10px] font-bold bg-slate-100 text-slate-600 px-2 py-1 rounded-full tracking-wide uppercase">
            Step {index + 1}
          </span>
        </div>
        <div className="space-y-4">
          <div className="bg-slate-50 p-3 rounded-lg border border-slate-100">
            <div className="flex items-center gap-2 text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-1">
              <Users className="w-3 h-3" /> Volume
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
                  {dropoffCount > 0 ? `-${dropoffCount}` : "0"} users
                </span>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// --- Sub-Component: Funnel Row ---
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

  const avgWidth = (topWidth + bottomWidth) / 2;
  const leftEdgePercent = (100 - avgWidth) / 2;
  const insetTop = (100 - topWidth) / 2;
  const insetBottom = (100 - bottomWidth) / 2;
  const clipPath = `polygon(${insetTop}% 0%, ${100 - insetTop}% 0%, ${100 - insetBottom}% 100%, ${insetBottom}% 100%)`;

  const dropoffCount = prevStage ? prevStage.count - stage.count : 0;
  const dropoffRate = prevStage && prevStage.count > 0 ? (dropoffCount / prevStage.count) * 100 : 0;
  const colors = getStageColor(dropoffRate, index);
  const zIndexValue = isHovered ? 50 : totalStages - index;

  return (
    <div
      className="relative w-full max-w-[600px] h-[64px] group flex items-center justify-center transition-all duration-200 mx-auto"
      style={{ zIndex: zIndexValue, marginBottom: "-6px" }}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      <div
        className="absolute top-1/2 -translate-y-1/2 flex flex-col items-end pr-6 transition-all duration-300 pointer-events-none"
        style={{ left: 0, width: `${leftEdgePercent}%`, opacity: isHovered ? 1 : 0.6 }}
      >
        <span className="text-xs font-semibold text-slate-400 whitespace-nowrap hidden sm:block">{stage.stage}</span>
        <span className={cn("text-lg font-bold tabular-nums leading-none", isHovered ? "text-indigo-600" : "text-slate-700")}>
          {stage.count}
        </span>
      </div>

      <div className="relative w-full h-full">
        <div className="absolute inset-0 bg-slate-900/10 blur-md translate-y-2 scale-[0.95]" style={{ clipPath, zIndex: -1 }} />
        <div
          className="relative w-full h-full transition-all duration-300 group-hover:scale-[1.01] group-hover:-translate-y-0.5 cursor-pointer shadow-inner"
          style={{ clipPath, background: `linear-gradient(to bottom, ${colors.top}, ${colors.bottom})` }}
        >
          <div className="absolute top-0 left-0 right-0 h-[1px] bg-white/40" />
          <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
            <span className="text-white font-bold text-sm drop-shadow-md tracking-wide">{stage.percentage}%</span>
          </div>
        </div>
      </div>

      <div className="absolute h-full pointer-events-none" style={{ left: `calc(50% + ${avgWidth / 2}%)` }}>
        {dropoffCount > 0 && (
          <div className="absolute top-1/2 -translate-y-1/2 left-2 flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity duration-300">
            <div className={cn("h-px w-6", dropoffRate > 20 ? "bg-red-300" : "bg-slate-300")} />
            <div
              className={cn(
                "flex items-center text-xs font-bold bg-white/80 backdrop-blur px-2 py-0.5 rounded-full border shadow-sm",
                dropoffRate > 20 ? "text-red-600 border-red-100" : "text-slate-500 border-slate-100"
              )}
            >
              <ArrowRight className="w-3 h-3 mr-1" />
              {dropoffRate.toFixed(0)}%
            </div>
          </div>
        )}
        <div className="pointer-events-auto">
          <HoverDetails stage={stage} prevStage={prevStage} index={index} totalStages={totalStages} isVisible={isHovered} />
        </div>
      </div>
    </div>
  );
}

// --- Main Export ---
export function ProfessionalFunnel({ apiResponse }: { apiResponse?: ApiResponse }) {
  const campaign = apiResponse?.data?.[0];
  const stats = campaign?.engagement_stats || [];
  const channels = useMemo(() => stats.map((s) => s.channel), [stats]);
  const [activeTab, setActiveTab] = useState(channels[0] || "");

  useMemo(() => {
    if (!activeTab && channels.length > 0) setActiveTab(channels[0]);
  }, [channels, activeTab]);

  // Dynamic Funnel Generation
  const funnelData = useMemo<FunnelStage[]>(() => {
    if (!activeTab) return [];
    const currentStat = stats.find((s) => s.channel === activeTab);
    if (!currentStat) return [];
    
    const totalValue = currentStat.total || 0;
    
    // Always start with Total
    const stages: FunnelStage[] = [
      { id: "total", stage: "Total Leads", count: totalValue, percentage: 100 }
    ];

    // Loop through dynamic stages
    STAGE_MAPPINGS.forEach((mapping) => {
      // Find the first matching key in our stat payload (e.g., 'sent_called', then 'called', then 'sent')
      const activeKey = mapping.keys.find((k) => currentStat[k] !== undefined);
      
      if (activeKey) {
        const count = currentStat[activeKey] ?? 0;
        stages.push({
          id: mapping.id,
          stage: formatStageLabel(activeKey), // Formats 'sent_called' into 'Sent / Called'
          count: count,
          percentage: totalValue > 0 ? Math.round((count / totalValue) * 100) : 0,
        });
      } else {
        // Fallback if no matching step is found so the funnel doesn't break visually
        stages.push({
          id: mapping.id,
          stage: mapping.fallbackLabel,
          count: 0,
          percentage: 0,
        });
      }
    });

    return stages;
  }, [stats, activeTab]);

  const MAX_WIDTH = 100;
  const MIN_WIDTH = 25;
  const stepSize = funnelData.length > 1 ? (MAX_WIDTH - MIN_WIDTH) / (funnelData.length - 1) : 0;

  if (!campaign || stats.length === 0) {
    return (
      <div className="w-full max-w-5xl mx-auto p-12 text-center border border-dashed border-slate-200 rounded-3xl bg-slate-50">
        <AlertCircle className="w-10 h-10 text-slate-300 mx-auto mb-4" />
        <h3 className="text-lg font-medium text-slate-900">No Campaign Data</h3>
        <p className="text-slate-500">Waiting for engagement statistics...</p>
      </div>
    );
  }

  return (
    <div className="w-full max-w-5xl mx-auto bg-white rounded-3xl p-8 pb-12 overflow-visible">
      {/* Header Section */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 mb-8">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <h2 className="text-xl font-bold text-slate-900">{campaign.campaign_name}</h2>
            <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-indigo-50 text-indigo-600 border border-indigo-100 uppercase tracking-wide">
              Funnel
            </span>
          </div>
          <p className="text-sm text-slate-500">Conversion metrics by channel</p>
        </div>

        {channels.length > 0 && (
          <Tabs value={activeTab} onValueChange={setActiveTab}>
            <TabsList className="bg-slate-100/80 p-1 h-auto">
              {channels.map((c) => (
                <TabsTrigger
                  key={c}
                  value={c}
                  className="capitalize px-4 py-1.5 text-sm data-[state=active]:bg-white data-[state=active]:shadow-sm data-[state=active]:text-indigo-600 font-medium"
                >
                  {c ? c.replace(/_/g, " ") : "No Data"}
                </TabsTrigger>
              ))}
            </TabsList>
          </Tabs>
        )}
      </div>

      <FunnelLegend />

      {/* The Funnel Visualization */}
      <div className="relative flex flex-col items-center py-6 isolate">
        <div className="absolute top-0 bottom-12 left-1/2 w-px border-l border-dashed border-slate-200 -z-10" />

        {funnelData.map((stage, index) => {
          const topW = MAX_WIDTH - index * stepSize;
          const bottomW = MAX_WIDTH - (index + 1) * stepSize;

          return (
            <FunnelRow
              key={stage.id}
              stage={stage}
              prevStage={index > 0 ? funnelData[index - 1] : null}
              index={index}
              totalStages={funnelData.length} // Correct total count now includes Converted
              topWidth={Math.max(topW, 15)}
              bottomWidth={Math.max(bottomW, 15 * 0.8)}
            />
          );
        })}

        {/* Bottom "Converted" Badge */}
        {funnelData.length > 0 && (
          <div className="mt-8 z-20">
            <div className="inline-flex items-center gap-2 px-6 py-2.5 bg-emerald-50 text-emerald-700 rounded-full border border-emerald-100 shadow-sm hover:shadow-md transition-shadow cursor-default">
              <Activity className="w-4 h-4" />
              <span className="font-bold tabular-nums text-lg">{funnelData[funnelData.length - 1].count}</span>
              <span className="text-sm font-medium">{funnelData[funnelData.length - 1].stage}</span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}