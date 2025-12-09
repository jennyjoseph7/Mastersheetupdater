"use client"

import { Label } from "@/components/ui/label"
import { Input } from "@/components/ui/input"
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group"
import { Checkbox } from "@/components/ui/checkbox"
import type { DealershipData } from "@/types/dealership"

interface BasicInfoStepProps {
  data: DealershipData
  updateData: (data: Partial<DealershipData>) => void
}

const AVAILABLE_BRANDS = [
  "Toyota",
  "Honda",
  "Maruti Suzuki",
  "Hyundai",
  "Tata Motors",
  "Mahindra",
  "Kia",
  "MG Motor",
  "Ford",
  "Volkswagen",
]

export function BasicInfoStep({ data, updateData }: BasicInfoStepProps) {
  const handleBrandToggle = (brand: string) => {
    const currentBrands = data.supported_brands
    const newBrands = currentBrands.includes(brand)
      ? currentBrands.filter((b) => b !== brand)
      : [...currentBrands, brand]
    updateData({ supported_brands: newBrands })
  }

  return (
    <div className="space-y-6">
      <div className="space-y-2">
        <Label htmlFor="dealer_name" className="text-base font-semibold">
          Dealership Name <span className="text-red-500">*</span>
        </Label>
        <Input
          id="dealer_name"
          placeholder="Enter dealership name"
          value={data.dealer_name}
          onChange={(e) => updateData({ dealer_name: e.target.value })}
          className="text-base"
        />
        <p className="text-sm text-muted-foreground">The official name of your dealership</p>
      </div>

      <div className="space-y-2">
        <Label htmlFor="dealership_legal_name" className="text-base font-semibold">
          Legal Name
        </Label>
        <Input
          id="dealership_legal_name"
          placeholder="Enter legal business name"
          value={data.dealership_legal_name}
          onChange={(e) => updateData({ dealership_legal_name: e.target.value })}
          className="text-base"
        />
        <p className="text-sm text-muted-foreground">Legal name as per registration documents</p>
      </div>

      <div className="space-y-3">
        <Label className="text-base font-semibold">
          Dealership Type <span className="text-red-500">*</span>
        </Label>
        <RadioGroup
          value={data.dealership_type}
          onValueChange={(value) => updateData({ dealership_type: value as "Single Brand" | "Multi Brand" })}
        >
          <div className="flex items-center space-x-3 p-4 border rounded-lg hover:bg-gray-50 transition-colors">
            <RadioGroupItem value="Single Brand" id="single-brand" />
            <Label htmlFor="single-brand" className="flex-1 cursor-pointer">
              <div className="font-medium">Single Brand</div>
              <div className="text-sm text-muted-foreground">Exclusive partnership with one manufacturer</div>
            </Label>
          </div>
          <div className="flex items-center space-x-3 p-4 border rounded-lg hover:bg-gray-50 transition-colors">
            <RadioGroupItem value="Multi Brand" id="multi-brand" />
            <Label htmlFor="multi-brand" className="flex-1 cursor-pointer">
              <div className="font-medium">Multi Brand</div>
              <div className="text-sm text-muted-foreground">Multiple brand partnerships</div>
            </Label>
          </div>
        </RadioGroup>
      </div>

      <div className="space-y-3">
        <Label className="text-base font-semibold">
          Supported Brands <span className="text-red-500">*</span>
        </Label>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
          {AVAILABLE_BRANDS.map((brand) => (
            <div
              key={brand}
              className="flex items-center space-x-2 p-3 border rounded-lg hover:bg-gray-50 transition-colors"
            >
              <Checkbox
                id={brand}
                checked={data.supported_brands.includes(brand)}
                onCheckedChange={() => handleBrandToggle(brand)}
              />
              <Label htmlFor={brand} className="cursor-pointer flex-1">
                {brand}
              </Label>
            </div>
          ))}
        </div>
      </div>

      <div className="space-y-2">
        <Label htmlFor="dealership_url" className="text-base font-semibold">
          Dealership Website URL
        </Label>
        <Input
          id="dealership_url"
          type="url"
          placeholder="https://www.yourdealership.com"
          value={data.dealership_url}
          onChange={(e) => updateData({ dealership_url: e.target.value })}
          className="text-base"
        />
      </div>

      <div className="space-y-2">
        <Label htmlFor="year_established" className="text-base font-semibold">
          Year Established
        </Label>
        <Input
          id="year_established"
          type="number"
          placeholder="2020"
          value={data.year_established}
          onChange={(e) => updateData({ year_established: Number.parseInt(e.target.value) })}
          className="text-base"
        />
      </div>
    </div>
  )
}
