"use client"

import { useEffect, useCallback, useMemo } from "react"
import { Switch } from "@/components/ui/switch"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Button } from "@/components/ui/button"
import { CheckCircle2, AlertTriangle, Sparkles, Zap } from "lucide-react"
import type { DataSourceFormData, FieldMapping } from "../add-data-source-dialog"

interface MapFieldsProps {
  formData: DataSourceFormData
  updateFormData: (updates: Partial<DataSourceFormData>) => void
}

export function MapFields({ formData, updateFormData }: MapFieldsProps) {
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

  // Helper to clean strings of \n, \r, and whitespace
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
      // Clean the source field itself to remove \n from the payload keys
      const sanitizedSource = cleanString(mapping.sourceField);
      const match = findBestMatch(sanitizedSource);
      
      return { 
        ...mapping, 
        sourceField: sanitizedSource, // FIX: Sanitize the key
        targetField: cleanString(match), // FIX: Sanitize the value
        enabled: match !== "" 
      };
    });
    updateFormData({ fieldMappings: mappedResult });
  }, [formData.fieldMappings, findBestMatch, updateFormData]);

  useEffect(() => {
    if (formData.fieldMappings.length > 0) {
      // Check if any fields contain newlines
      const needsCleaning = formData.fieldMappings.some(m => m.sourceField.includes('\n') || m.sourceField.includes('\\n'));
      if (needsCleaning) {
        handleAutoMapAll();
      }
    }
  }, [formData.fieldMappings.length, handleAutoMapAll]);

  const updateFieldMapping = (id: string, updates: Partial<FieldMapping>) => {
    // Ensure any manual updates are also cleaned
    if (updates.targetField) updates.targetField = cleanString(updates.targetField);
    
    updateFormData({
      fieldMappings: formData.fieldMappings.map((m) => (m.id === id ? { ...m, ...updates } : m)),
    });
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between p-4 bg-slate-900 rounded-xl shadow-lg border-b-4 border-indigo-500">
        <div className="flex items-center gap-3">
          <Zap className="h-5 w-5 text-yellow-400 fill-yellow-400" />
          <p className="text-sm font-bold text-white tracking-tight">Data Sync Ready</p>
        </div>
        <Button size="sm" onClick={handleAutoMapAll} variant="secondary" className="font-bold text-xs">
          <Sparkles className="h-3.5 w-3.5 mr-2" />
          Clean & Auto-map
        </Button>
      </div>

      <div className="border rounded-xl bg-white shadow-sm overflow-hidden">
        <div className="grid grid-cols-12 gap-4 px-6 py-3 bg-slate-50 border-b text-[10px] font-black uppercase tracking-widest text-slate-400">
          <div className="col-span-1 text-center">Import</div>
          <div className="col-span-5">CSV Source</div>
          <div className="col-span-6">System Target</div>
        </div>

        <div className="max-h-[480px] overflow-y-auto divide-y divide-slate-100">
          {formData.fieldMappings.map((mapping) => {
            const isUnmapped = !mapping.targetField && mapping.enabled;
            
            return (
              <div 
                key={mapping.id} 
                className={`grid grid-cols-12 gap-4 items-center px-6 py-4 transition-all ${
                  isUnmapped ? "bg-amber-50/50" : "bg-white"
                } ${!mapping.enabled ? "opacity-40" : ""}`}
              >
                <div className="col-span-1 flex justify-center">
                  <Switch
                    checked={mapping.enabled}
                    onCheckedChange={(enabled) => updateFieldMapping(mapping.id, { enabled })}
                  />
                </div>

                <div className="col-span-5 flex flex-col">
                  <span className="text-sm font-bold text-slate-700 truncate">
                    {cleanString(mapping.sourceField)}
                  </span>
                  <span className="text-[10px] text-slate-400 font-medium">Header</span>
                </div>

                <div className="col-span-6 flex flex-col gap-1">
                  <Select
                    disabled={!mapping.enabled}
                    value={mapping.targetField || ""} 
                    onValueChange={(val) => updateFieldMapping(mapping.id, { targetField: val, enabled: true })}
                  >
                    <SelectTrigger className={`h-11 border-slate-200 ${isUnmapped ? 'border-amber-300 ring-2 ring-amber-100' : ''}`}>
                      <SelectValue placeholder="Select Destination..." />
                    </SelectTrigger>
                    <SelectContent>
                      {systemTargets.map((field) => (
                        <SelectItem key={field} value={field} className="text-xs">
                          {field.replace(/_/g, " ").toUpperCase()}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  {isUnmapped && (
                    <span className="text-[9px] font-bold text-amber-600 flex items-center gap-1">
                      <AlertTriangle className="h-2.5 w-2.5" /> MANUAL ACTION NEEDED
                    </span>
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