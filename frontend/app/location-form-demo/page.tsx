"use client";

import { PhysicalLocationForm, type PhysicalLocationFormData } from "@/components/location/physical-location-form";
import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { CheckCircle2 } from "lucide-react";

export default function LocationFormDemoPage() {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submittedData, setSubmittedData] = useState<PhysicalLocationFormData | null>(null);

  const handleSubmit = async (data: PhysicalLocationFormData) => {
    setIsSubmitting(true);
    
    // Simulate API call
    await new Promise((resolve) => setTimeout(resolve, 1500));
    
    console.log("Form submitted with data:", data);
    setSubmittedData(data);
    setIsSubmitting(false);
    
    // You can integrate with your API here
    // Example:
    // await createPhysicalLocation(data);
  };

  return (
    <div className="container mx-auto py-8 px-4 max-w-4xl">
      <div className="mb-6">
        <h1 className="text-3xl font-bold mb-2">Physical Location Details Form</h1>
        <p className="text-muted-foreground">
          Complete form for collecting dealership physical location information
        </p>
      </div>

      {submittedData && (
        <Alert className="mb-6 bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-800">
          <CheckCircle2 className="h-4 w-4 text-green-600 dark:text-green-400" />
          <AlertDescription className="text-green-800 dark:text-green-200">
            Form submitted successfully! Check the console for the submitted data.
          </AlertDescription>
        </Alert>
      )}

      <PhysicalLocationForm
        onSubmit={handleSubmit}
        isLoading={isSubmitting}
      />

      {submittedData && (
        <Card className="mt-6">
          <CardHeader>
            <CardTitle>Submitted Data Preview</CardTitle>
          </CardHeader>
          <CardContent>
            <pre className="bg-muted p-4 rounded-md overflow-auto text-sm">
              {JSON.stringify(submittedData, null, 2)}
            </pre>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
