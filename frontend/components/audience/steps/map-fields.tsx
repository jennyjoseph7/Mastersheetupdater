"use client"

import { useEffect, useCallback, useMemo, useState, useRef } from "react"
import { Switch } from "@/components/ui/switch"
import { Button } from "@/components/ui/button"
import { 
  CheckCircle2, 
  AlertTriangle, 
  Sparkles, 
  Zap, 
  Check, 
  ChevronsUpDown 
} from "lucide-react"
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/command"
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover"
import { cn } from "@/lib/utils"
import type { DataSourceFormData, FieldMapping } from "../add-data-source-dialog"

interface MapFieldsProps {
  formData: DataSourceFormData
  updateFormData: (updates: Partial<DataSourceFormData>) => void
}

export function MapFields({ formData, updateFormData }: MapFieldsProps) {
  // Ref to ensure we only auto-trigger once on open
  const hasAutoTrigged = useRef(false);

  const systemTargets = useMemo(() => [
    "reg_number", "vehicle_brand_name", "vehicle_model_name", "vehicle_model_year",
    "variant_name", "vehicle_color_name", "vehicle_category", "vehicle_type",
    "transmission", "engine_type", "engine_capacity_cc", "drivetrain",
    "vin_number", "engine_number", "chassis_number", "accessories",
    "registration_date", "vehicle_age_months", "last_service_type", "service_history",
    "service_advisor", "service_plan_type", "service_plan_expiry_date", "next_service_due",
    "service_feedback", "feedback_rating", "feedback_sentiment_score", "extended_warranty_purchased",
    "avg_service_cost", "service_frequency", "loan_end_date", "odometer_reading",
    "avg_monthly_mileage", "vehicle_usage_category", "battery_health", "tyre_change_details",
    "tyre_health", "wheel_alignment", "repair_notes", "first_owner_name", "ownership_status",
    "finance_loan_status", "loan_provider", "loan_account_number", "loan_amount",
    "emi_amount", "insurance", "puc","region_name","phone_number","email","alt_phone_number_2","alt_phone_number_3","alt_phone_number_4"
  ], []);

  const cleanString = (str: string) => {
    return str ? str.replace(/\\n|\n|\r/g, "").trim() : "";
  };

  const findBestMatch = useCallback((source: string) => {
    const s = cleanString(source).toLowerCase();
    const cleanS = s.replace(/[^a-z0-9]/g, "");

    const exact = systemTargets.find(t => t.toLowerCase() === s || t.replace(/_/g, "") === cleanS);
    if (exact) return exact;

    if (cleanS.includes("model") || cleanS.includes("vehiclename")) return "vehicle_model_name";
    if (cleanS.includes("reg") || cleanS === "number") return "reg_number";
    if (cleanS.includes("vin") || cleanS.includes("chassis")) return "vin_number";
    if (cleanS.includes("person") && cleanS.includes("name")) return "first_owner_name";
    
    return systemTargets.find(t => t.replace(/_/g, "").includes(cleanS)) || "";
  }, [systemTargets]);

  const handleAutoMapAll = useCallback(() => {
    const mappedResult = formData.fieldMappings.map(mapping => {
      const sanitizedSource = cleanString(mapping.sourceField);
      const match = findBestMatch(sanitizedSource);
      return { 
        ...mapping, 
        sourceField: sanitizedSource,
        targetField: cleanString(match),
        enabled: match !== "" 
      };
    });
    updateFormData({ fieldMappings: mappedResult });
  }, [formData.fieldMappings, findBestMatch, updateFormData]);

  // --- AUTO-TRIGGER ON OPEN ---
  useEffect(() => {
    if (formData.fieldMappings.length > 0 && !hasAutoTrigged.current) {
      handleAutoMapAll();
      hasAutoTrigged.current = true;
    }
  }, [formData.fieldMappings.length, handleAutoMapAll]);

  const updateFieldMapping = (id: string, updates: Partial<FieldMapping>) => {
    if (updates.targetField) updates.targetField = cleanString(updates.targetField);
    updateFormData({
      fieldMappings: formData.fieldMappings.map((m) => (m.id === id ? { ...m, ...updates } : m)),
    });
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between p-4 bg-slate-900 rounded-xl shadow-lg border-b-4 border-indigo-500">
        <div className="flex items-center gap-3">
          <div className="bg-indigo-500/20 p-2 rounded-lg">
            <Zap className="h-5 w-5 text-yellow-400 fill-yellow-400" />
          </div>
          <div>
            <p className="text-sm font-bold text-white leading-tight">Instant Auto-Map</p>
            <p className="text-[10px] text-indigo-200 uppercase font-bold tracking-widest">Payload Sanitized</p>
          </div>
        </div>
        <Button size="sm" onClick={handleAutoMapAll} variant="secondary" className="font-bold text-xs h-9">
          <Sparkles className="h-3.5 w-3.5 mr-2" />
          Re-run Matcher
        </Button>
      </div>

      <div className="border rounded-xl bg-white shadow-sm overflow-hidden">
        <div className="grid grid-cols-12 gap-4 px-6 py-3 bg-slate-50 border-b text-[10px] font-black uppercase tracking-widest text-slate-400">
          <div className="col-span-1 text-center">Import</div>
          <div className="col-span-5">CSV Source Column</div>
          <div className="col-span-6">System Destination</div>
        </div>

        <div className="max-h-[500px] overflow-y-auto divide-y divide-slate-100">
          {formData.fieldMappings.map((mapping) => {
            const isUnmapped = !mapping.targetField && mapping.enabled;
            const isMapped = mapping.targetField && mapping.enabled;

            return (
              <div 
                key={mapping.id} 
                className={cn(
                  "grid grid-cols-12 gap-4 items-center px-6 py-4 transition-all duration-200",
                  isUnmapped ? "bg-amber-50/40 border-l-4 border-l-amber-400" : "border-l-4 border-l-transparent",
                  !mapping.enabled && "opacity-40 grayscale-[0.5]"
                )}
              >
                <div className="col-span-1 flex justify-center">
                  <Switch
                    checked={mapping.enabled}
                    onCheckedChange={(enabled) => updateFieldMapping(mapping.id, { enabled })}
                    className="data-[state=checked]:bg-indigo-600"
                  />
                </div>

                <div className="col-span-5 flex flex-col min-w-0">
                  <span className="text-sm font-bold text-slate-700 truncate">
                    {cleanString(mapping.sourceField)}
                  </span>
                  <span className="text-[10px] text-slate-400 font-medium">CSV Header</span>
                </div>

                <div className="col-span-6 flex flex-col gap-1.5">
                  <Popover>
                    <PopoverTrigger asChild>
                      <Button
                        variant="outline"
                        role="combobox"
                        disabled={!mapping.enabled}
                        className={cn(
                          "h-11 justify-between text-left font-semibold border-slate-200",
                          isUnmapped && "border-amber-300 ring-2 ring-amber-100",
                          isMapped && "border-emerald-200 bg-emerald-50/20 text-emerald-900"
                        )}
                      >
                        <span className="truncate">
                          {mapping.targetField 
                            ? mapping.targetField.replace(/_/g, " ").toUpperCase() 
                            : "Select CRM Field..."}
                        </span>
                        <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
                      </Button>
                    </PopoverTrigger>
                    <PopoverContent className="w-[320px] p-0" align="start">
                      <Command>
                        <CommandInput placeholder="Search system fields..." className="h-10" />
                        <CommandList className="max-h-[300px]">
                          <CommandEmpty>No results found.</CommandEmpty>
                          <CommandGroup heading="System Targets">
                            {systemTargets.map((field) => (
                              <CommandItem
                                key={field}
                                value={field}
                                onSelect={() => {
                                  updateFieldMapping(mapping.id, { targetField: field, enabled: true });
                                }}
                                className="flex items-center gap-2 py-2.5"
                              >
                                <Check
                                  className={cn(
                                    "h-4 w-4 text-indigo-600",
                                    mapping.targetField === field ? "opacity-100" : "opacity-0"
                                  )}
                                />
                                <span className="text-xs font-medium uppercase tracking-tight">
                                    {field.replace(/_/g, " ")}
                                </span>
                              </CommandItem>
                            ))}
                          </CommandGroup>
                        </CommandList>
                      </Command>
                    </PopoverContent>
                  </Popover>

                  {isUnmapped && (
                    <div className="flex items-center gap-1.5 text-amber-600">
                      <AlertTriangle className="h-3 w-3" />
                      <span className="text-[9px] font-black uppercase tracking-tighter">Requires Manual Mapping</span>
                    </div>
                  )}
                  {isMapped && (
                    <div className="flex items-center gap-1.5 text-emerald-600">
                      <CheckCircle2 className="h-3 w-3" />
                      <span className="text-[9px] font-black uppercase tracking-tighter">Auto-Matched</span>
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  )
}