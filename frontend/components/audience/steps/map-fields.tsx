"use client"

import { useEffect, useCallback, useMemo, useRef } from "react"
import { Switch } from "@/components/ui/switch"
import { Button } from "@/components/ui/button"
import { 
  CheckCircle2, 
  AlertTriangle, 
  Sparkles, 
  Check, 
  ChevronsUpDown,
  UserCircle,
  Car,
  Zap
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
  const hasAutoTrigged = useRef(false);

  // 1. Identify the mode robustly (Handling "PRE-SALES", "Sales", "presales", etc.)
  const isPresales = useMemo(() => {
    const cat = formData.category?.toLowerCase() || "";
    // Checks if the string contains "pre" or "sales" but is NOT "post-sales"
    return (cat.includes("pre") || cat === "sales") && !cat.includes("post");
  }, [formData.category]);

  // 2. Strict Field Lists
  const fieldLists = useMemo(() => ({
 presales: [
    "phone_number",
    "email",
    "person_name",
    "last_contacted_whatsapp_number",
    "last_contacted_email",
    "last_contacted_phone_number",
    "city",
    "pincode",
    "budget_range",
    "feature_preferences",
    "seating_capacity_preference",
    "segment_preference",
    "lead_source",
    "existing_vehicle_brand",
    "existing_vehicle_model",
    "subdivision_name",
    "alt_phone_number_2",
    "alt_phone_number_3",
    "alt_phone_number_4",
    "showroom_code",

    "brand_preference",
    "model_preference",
    "variant_preference",
    "color_preference",
    "engine_type_preference",
    "transmission_preference",
    "range_preference",
    "feature_preferences",
    "segment_preference",

    "competitor_brands",
    "competitor_models",
    "interested_vehicle_competitor_vehicles",
    "interested_vehicle_name",
    "interested_vehicle_brand_name",


    "emotions",
    "engagement_events",
    "previous_interaction_ids",
    "lead_code_for_dealership"
  ],
     postsales: [
"lead_code_for_dealership",
    // VEHICLE INFO
    "reg_number",
    "vehicle_brand",
    "vehicle_model",
    "vehicle_model_year",
    "vehicle_variant",
    "vehicle_color",
    "vehicle_category",
    "vehicle_type",
    "transmission",
    "engine_type",
    "engine_capacity_cc",
    "drivetrain",
    "vehicle_variant",

    // VEHICLE IDENTIFIERS
    "vin_number",
    "engine_number",
    "chassis_number",

    // PURCHASE & REGISTRATION
    "purchase_date",
    "registration_date",
    "original_delivery_date",
    "vehicle_age_months",

    // ACCESSORIES
    "accessories",

    // SERVICE HISTORY
    "last_service_type",
    "last_service_date",
    "service_history",
    "service_advisor",
    "service_plan_type",
    "service_plan_expiry_date",
    "next_service_due",
    "service_feedback",
    "feedback_rating",
    "feedback_sentiment_score",

    // SERVICE / MAINTENANCE EVENTS
    "oil_change_date",
    "oil_filter_replacement_date",
    "tyre_change_date",
    "brake_pad_change_date",
    "brake_oil_change_date",
    "suspension_check_date",
    "coolant_radiator_service_date",
    "ac_vent_cleaning_date",
    "polishing_and_waxing_date",
    "car_wash_date",
    "underbody_coating_date",
    "wheel_alignment",

    // BATTERY
    "battery_health",
    "battery_change_date",
    "battery_service_date",
    "battery_warranty_expiry_date",

    // TYRE
    "tyre_change_details",
    "tyre_health",

    // WARRANTY
    "extended_warranty_purchased",
    "warranty_expiry_date",
    "extended_warranty_expiry_date",

    // INSURANCE
    "insurance",
    "insurance_expiry_date",
    "puc",

    // VEHICLE USAGE
    "odometer_reading",
    "odometer_reading_date",
    "avg_monthly_mileage",
    "vehicle_usage_category",

    // SERVICE ANALYTICS
    "avg_service_cost",
    "service_frequency",
    "repair_notes",
    "purpose_of_visit",

    // FINANCE
    "finance_loan_status",
    "loan_provider",
    "loan_account_number",
    "loan_amount",
    "emi_amount",
    "emi_due_date",
    "loan_end_date",

    // OWNERSHIP
    "first_owner_name",
    "ownership_status",
    "person_name",

    // CUSTOMER ANALYTICS
    "customer_score",

    // CONTACT
    "phone_number",
    "email",
    "alt_phone_number_2",
    "alt_phone_number_3",
    "alt_phone_number_4",
    "workshop_pincode",
    "workshop_city",
    "workshop_code",

    // REGION
    "region_name"
  ]
  }), []);

  // 3. Select active target list
  const systemTargets = useMemo(() => {
    return isPresales ? fieldLists.presales : fieldLists.postsales;
  }, [isPresales, fieldLists]);

  const cleanString = (str: string) => str ? str.replace(/\\n|\n|\r/g, "").trim() : "";

  // 4. Intelligent Matching Logic
  const findBestMatch = useCallback((source: string) => {
    const s = cleanString(source).toLowerCase();
    const cleanS = s.replace(/[^a-z0-9]/g, "");

    const exact = systemTargets.find(t => t.toLowerCase() === s || t.replace(/_/g, "") === cleanS);
    if (exact) return exact;

    if (isPresales) {
      if (cleanS.includes("name")) return "name";
      if (cleanS.includes("mobile") || cleanS.includes("phone")) return "phone_number";
      if (cleanS.includes("mail")) return "email";
    } else {
      if (cleanS.includes("reg")) return "reg_number";
      if (cleanS.includes("vin") || cleanS.includes("chassis")) return "vin_number";
      if (cleanS.includes("model")) return "vehicle_model_name";
    }
    
    return systemTargets.find(t => t.replace(/_/g, "").includes(cleanS)) || "";
  }, [systemTargets, isPresales]);

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
      {/* Dynamic Header */}
      <div className={cn(
        "flex items-center justify-between p-4 rounded-xl shadow-lg border-b-4 transition-all duration-300",
        isPresales ? "bg-slate-900 border-sky-500" : "bg-slate-900 border-indigo-500"
      )}>
        <div className="flex items-center gap-3">
          <div className={cn("p-2 rounded-lg", isPresales ? "bg-sky-500/20" : "bg-indigo-500/20")}>
            {isPresales ? (
              <UserCircle className="h-5 w-5 text-sky-400" />
            ) : (
              <Car className="h-5 w-5 text-indigo-400" />
            )}
          </div>
          <div>
            <p className="text-sm font-bold text-white leading-tight">
              {isPresales ? "Presales Matcher" : "Post-sales Matcher"}
            </p>
            <p className="text-[10px] text-slate-400 uppercase font-black tracking-widest">
              Category: {formData.category}
            </p>
          </div>
        </div>
        <Button size="sm" onClick={handleAutoMapAll} variant="secondary" className="font-bold text-xs h-9">
          <Sparkles className="h-3.5 w-3.5 mr-2" />
          Auto-Map
        </Button>
      </div>

      {/* Mapping Table */}
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
                    {mapping.sourceField}
                  </span>
                  <span className="text-[10px] text-slate-400 font-medium uppercase">Source Data</span>
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
                            : "Select System Field..."}
                        </span>
                        <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
                      </Button>
                    </PopoverTrigger>
                    <PopoverContent className="w-[320px] p-0" align="start">
                      <Command>
                        <CommandInput placeholder={`Search ${isPresales ? 'Lead' : 'Vehicle'} fields...`} className="h-10" />
                        <CommandList className="max-h-[300px]">
                          <CommandEmpty>No matches found.</CommandEmpty>
                          <CommandGroup heading={isPresales ? "Presales Attributes" : "Service & Vehicle Details"}>
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
                      <span className="text-[9px] font-black uppercase">Field Unmapped</span>
                    </div>
                  )}
                  {isMapped && (
                    <div className="flex items-center gap-1.5 text-emerald-600">
                      <CheckCircle2 className="h-3 w-3" />
                      <span className="text-[9px] font-black uppercase">Ready for Import</span>
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