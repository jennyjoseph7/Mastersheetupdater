"use client";

import { useState } from "react";
import { PhoneInput } from "react-international-phone";
import "react-international-phone/style.css";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Checkbox } from "@/components/ui/checkbox";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { AlertCircle } from "lucide-react";

export interface PhysicalLocationFormData {
  // Basic Location Details (required across all types)
  locationName: string; // workshop_name, showroom_name
  contactNumber: string; // contact_number
  emailAddress: string; // email
  address: string; // address
  city: string; // city
  state: string; // state
  pincode: string; // pincode
  
  // Operating Details (required)
  openingTime: string; // operating_hours.opening_time
  closingTime: string; // operating_hours.closing_time
  daysOpen: string[]; // days_open
  
  // Location Type Selection (required)
  locationTypes: string[]; // workshop, showroom, buyback_center
}

interface PhysicalLocationFormProps {
  onSubmit?: (data: PhysicalLocationFormData) => void | Promise<void>;
  initialData?: Partial<PhysicalLocationFormData>;
  isLoading?: boolean;
}

const DAYS_OF_WEEK = [
  "Monday",
  "Tuesday",
  "Wednesday",
  "Thursday",
  "Friday",
  "Saturday",
  "Sunday",
];

const LOCATION_TYPES = [
  { id: "workshop", label: "Workshop" },
  { id: "showroom", label: "Showroom" },
  { id: "buyback_center", label: "Buyback Center" },
];

export function PhysicalLocationForm({
  onSubmit,
  initialData,
  isLoading = false,
}: PhysicalLocationFormProps) {
  const [formData, setFormData] = useState<PhysicalLocationFormData>({
    locationName: initialData?.locationName || "",
    contactNumber: initialData?.contactNumber || "",
    emailAddress: initialData?.emailAddress || "",
    address: initialData?.address || "",
    city: initialData?.city || "",
    state: initialData?.state || "",
    pincode: initialData?.pincode || "",
    openingTime: initialData?.openingTime || "09:00",
    closingTime: initialData?.closingTime || "18:00",
    daysOpen: initialData?.daysOpen || [],
    locationTypes: initialData?.locationTypes || [],
  });

  const [errors, setErrors] = useState<Record<string, string>>({});
  const [submitError, setSubmitError] = useState("");

  const validateForm = (): boolean => {
    const newErrors: Record<string, string> = {};

    // Location Name validation
    if (!formData.locationName.trim()) {
      newErrors.locationName = "Location name is required";
    }

    // Contact Number validation
    if (!formData.contactNumber.trim()) {
      newErrors.contactNumber = "Contact number is required";
    } else if (!formData.contactNumber.startsWith("+")) {
      newErrors.contactNumber =
        "Please select a country code for the phone number";
    } else if (formData.contactNumber.replace(/\D/g, "").length < 10) {
      newErrors.contactNumber = "Please enter a valid phone number";
    }

    // Email validation
    if (!formData.emailAddress.trim()) {
      newErrors.emailAddress = "Email address is required";
    } else {
      const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
      if (!emailRegex.test(formData.emailAddress)) {
        newErrors.emailAddress = "Please enter a valid email address";
      }
    }

    // Address validation
    if (!formData.address.trim()) {
      newErrors.address = "Address is required";
    }

    // City validation
    if (!formData.city.trim()) {
      newErrors.city = "City is required";
    }

    // State validation
    if (!formData.state.trim()) {
      newErrors.state = "State is required";
    }

    // Pincode validation
    if (!formData.pincode.trim()) {
      newErrors.pincode = "Pincode is required";
    } else if (!/^\d{6}$/.test(formData.pincode.trim())) {
      newErrors.pincode = "Pincode must be 6 digits";
    }

    // Days Open validation
    if (formData.daysOpen.length === 0) {
      newErrors.daysOpen = "Please select at least one day";
    }

    // Location Types validation
    if (formData.locationTypes.length === 0) {
      newErrors.locationTypes = "Please select at least one location type";
    }

    // Time validation
    if (formData.openingTime && formData.closingTime) {
      const [openHour, openMin] = formData.openingTime.split(":").map(Number);
      const [closeHour, closeMin] = formData.closingTime.split(":").map(Number);
      const openMinutes = openHour * 60 + openMin;
      const closeMinutes = closeHour * 60 + closeMin;

      if (closeMinutes <= openMinutes) {
        newErrors.closingTime = "Closing time must be after opening time";
      }
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitError("");

    if (!validateForm()) {
      setSubmitError("Please fix the errors in the form");
      return;
    }

    if (onSubmit) {
      try {
        await onSubmit(formData);
      } catch (error) {
        setSubmitError(
          error instanceof Error
            ? error.message
            : "Failed to submit form. Please try again."
        );
      }
    }
  };

  const handleFieldChange = (
    field: keyof PhysicalLocationFormData,
    value: string | string[]
  ) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
    // Clear error for this field when user starts typing
    if (errors[field]) {
      setErrors((prev) => {
        const newErrors = { ...prev };
        delete newErrors[field];
        return newErrors;
      });
    }
  };

  const toggleDay = (day: string) => {
    const newDaysOpen = formData.daysOpen.includes(day)
      ? formData.daysOpen.filter((d) => d !== day)
      : [...formData.daysOpen, day];
    handleFieldChange("daysOpen", newDaysOpen);
  };

  const toggleLocationType = (typeId: string) => {
    const newLocationTypes = formData.locationTypes.includes(typeId)
      ? formData.locationTypes.filter((t) => t !== typeId)
      : [...formData.locationTypes, typeId];
    handleFieldChange("locationTypes", newLocationTypes);
  };

  return (
    <Card className="w-full">
      <CardHeader>
        <CardTitle>Physical Location Details</CardTitle>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Error Alert */}
          {submitError && (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>{submitError}</AlertDescription>
            </Alert>
          )}

          {/* Basic Location Details */}
          <div className="space-y-4">

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* Location Name */}
              <div className="space-y-2">
                <Label htmlFor="locationName">
                  Location Name <span className="text-destructive">*</span>
                </Label>
                <Input
                  id="locationName"
                  placeholder="e.g., Main Showroom"
                  value={formData.locationName}
                  onChange={(e) =>
                    handleFieldChange("locationName", e.target.value)
                  }
                  className={errors.locationName ? "border-destructive" : ""}
                />
                {errors.locationName && (
                  <p className="text-sm text-destructive">
                    {errors.locationName}
                  </p>
                )}
              </div>

              {/* Contact Number */}
              <div className="space-y-2">
                <Label htmlFor="contactNumber">
                  Contact Number <span className="text-destructive">*</span>
                </Label>
                <PhoneInput
                  defaultCountry="in"
                  value={formData.contactNumber}
                  onChange={(value) =>
                    handleFieldChange("contactNumber", value)
                  }
                  className={
                    errors.contactNumber
                      ? "[&_.react-international-phone-input]:border-destructive"
                      : ""
                  }
                />
                {errors.contactNumber && (
                  <p className="text-sm text-destructive">
                    {errors.contactNumber}
                  </p>
                )}
              </div>
            </div>

            {/* Email Address */}
            <div className="space-y-2">
              <Label htmlFor="emailAddress">
                Email Address <span className="text-destructive">*</span>
              </Label>
              <Input
                id="emailAddress"
                type="email"
                placeholder="location@dealership.com"
                value={formData.emailAddress}
                onChange={(e) =>
                  handleFieldChange("emailAddress", e.target.value)
                }
                className={errors.emailAddress ? "border-destructive" : ""}
              />
              {errors.emailAddress && (
                <p className="text-sm text-destructive">
                  {errors.emailAddress}
                </p>
              )}
            </div>

            {/* Full Address */}
            <div className="space-y-2">
              <Label htmlFor="address">
                Full Address <span className="text-destructive">*</span>
              </Label>
              <Textarea
                id="address"
                placeholder="Street address, area, landmark..."
                value={formData.address}
                onChange={(e) => handleFieldChange("address", e.target.value)}
                rows={3}
                className={errors.address ? "border-destructive" : ""}
              />
              {errors.address && (
                <p className="text-sm text-destructive">{errors.address}</p>
              )}
            </div>

            {/* City, State, Pincode */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="space-y-2">
                <Label htmlFor="city">
                  City <span className="text-destructive">*</span>
                </Label>
                <Input
                  id="city"
                  placeholder="City"
                  value={formData.city}
                  onChange={(e) => handleFieldChange("city", e.target.value)}
                  className={errors.city ? "border-destructive" : ""}
                />
                {errors.city && (
                  <p className="text-sm text-destructive">{errors.city}</p>
                )}
              </div>

              <div className="space-y-2">
                <Label htmlFor="state">
                  State <span className="text-destructive">*</span>
                </Label>
                <Input
                  id="state"
                  placeholder="State"
                  value={formData.state}
                  onChange={(e) => handleFieldChange("state", e.target.value)}
                  className={errors.state ? "border-destructive" : ""}
                />
                {errors.state && (
                  <p className="text-sm text-destructive">{errors.state}</p>
                )}
              </div>

              <div className="space-y-2">
                <Label htmlFor="pincode">
                  Pincode <span className="text-destructive">*</span>
                </Label>
                <Input
                  id="pincode"
                  placeholder="123456"
                  value={formData.pincode}
                  onChange={(e) => handleFieldChange("pincode", e.target.value)}
                  maxLength={6}
                  className={errors.pincode ? "border-destructive" : ""}
                />
                {errors.pincode && (
                  <p className="text-sm text-destructive">{errors.pincode}</p>
                )}
              </div>
            </div>
          </div>

          {/* Operating Details */}
          <div className="space-y-4">

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* Opening Time */}
              <div className="space-y-2">
                <Label htmlFor="openingTime">Opens At</Label>
                <Input
                  id="openingTime"
                  type="time"
                  value={formData.openingTime}
                  onChange={(e) =>
                    handleFieldChange("openingTime", e.target.value)
                  }
                />
              </div>

              {/* Closing Time */}
              <div className="space-y-2">
                <Label htmlFor="closingTime">Closes At</Label>
                <Input
                  id="closingTime"
                  type="time"
                  value={formData.closingTime}
                  onChange={(e) =>
                    handleFieldChange("closingTime", e.target.value)
                  }
                  className={errors.closingTime ? "border-destructive" : ""}
                />
                {errors.closingTime && (
                  <p className="text-sm text-destructive">
                    {errors.closingTime}
                  </p>
                )}
              </div>
            </div>

            {/* Days Open */}
            <div className="space-y-2">
              <Label>
                Days Open <span className="text-destructive">*</span>
              </Label>
              <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-7 gap-3 p-3 border rounded-md">
                {DAYS_OF_WEEK.map((day) => (
                  <div key={day} className="flex items-center space-x-2">
                    <Checkbox
                      id={`day-${day}`}
                      checked={formData.daysOpen.includes(day)}
                      onCheckedChange={() => toggleDay(day)}
                    />
                    <Label
                      htmlFor={`day-${day}`}
                      className="text-sm font-normal cursor-pointer"
                    >
                      {day}
                    </Label>
                  </div>
                ))}
              </div>
              {errors.daysOpen && (
                <p className="text-sm text-destructive">{errors.daysOpen}</p>
              )}
            </div>
          </div>

          {/* Location Type */}
          <div className="space-y-2">
            <Label>
              Location Type <span className="text-destructive">*</span>
            </Label>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 p-3 border rounded-md">
              {LOCATION_TYPES.map((type) => (
                <div key={type.id} className="flex items-center space-x-2">
                  <Checkbox
                    id={`location-type-${type.id}`}
                    checked={formData.locationTypes.includes(type.id)}
                    onCheckedChange={() => toggleLocationType(type.id)}
                  />
                  <Label
                    htmlFor={`location-type-${type.id}`}
                    className="text-sm font-normal cursor-pointer"
                  >
                    {type.label}
                  </Label>
                </div>
              ))}
            </div>
            {errors.locationTypes && (
              <p className="text-sm text-destructive">
                {errors.locationTypes}
              </p>
            )}
          </div>

          {/* Submit Button */}
          <div className="flex justify-end gap-4 pt-4">
            <Button
              type="submit"
              disabled={isLoading}
              className="min-w-[120px]"
            >
              {isLoading ? "Submitting..." : "Done"}
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  );
}
