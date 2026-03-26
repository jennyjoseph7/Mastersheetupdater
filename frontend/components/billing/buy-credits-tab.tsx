"use client"

import { useState } from "react"
import { ArrowRight, ArrowLeft, CreditCard, Loader2, CheckCircle2 } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Badge } from "@/components/ui/badge"
import { createCreditPurchaseOrder } from "@/utils/api"

declare global {
  interface Window {
    Razorpay: any;
  }
}

// Updated: All prices are now 1:1 with credits (No discounts)
const creditPacks = [
  { credits: 500, price: 500, label: "Starter" },
  { credits: 1000, price: 1000, label: "Standard" },
  { credits: 5000, price: 5000, label: "Business" },
]

export function BuyCreditsTab() {
  const [step, setStep] = useState(1)
  const [selectedPack, setSelectedPack] = useState<number | null>(1000)
  const [customCredits, setCustomCredits] = useState("")
  const [isLoading, setIsLoading] = useState(false)
  const [paymentResult, setPaymentResult] = useState<any>(null)
  
  const [billingDetails, setBillingDetails] = useState({
    name: "John Doe",
    email: "john.doe@example.com",
    contact: "9999999999",
    company: "ABC Auto Sales",
    gstin: "",
    address: "",
  })

  const selectedCredits = selectedPack !== null ? selectedPack : Number.parseInt(customCredits) || 0
  const selectedPackData = creditPacks.find((p) => p.credits === selectedPack)
  
  // Logic remains consistent: Subtotal is strictly based on credit count
  const subtotal = selectedPack !== null ? selectedPackData?.price || 0 : Number.parseInt(customCredits) || 0
  const tax = subtotal * 0.18
  const total = subtotal + tax

  const loadRazorpayScript = () => {
    return new Promise((resolve) => {
      if (window.Razorpay) {
        resolve(true);
        return;
      }
      const script = document.createElement("script");
      script.src = "https://checkout.razorpay.com/v1/checkout.js";
      script.onload = () => resolve(true);
      script.onerror = () => resolve(false);
      document.body.appendChild(script);
    });
  };

  const handleRazorpayPayment = async () => {
    setIsLoading(true);
    setPaymentResult(null);

    const isScriptLoaded = await loadRazorpayScript();
    if (!isScriptLoaded) {
      alert("Failed to load Razorpay. Please check your connection.");
      setIsLoading(false);
      return;
    }

    try {
      const orderData = await createCreditPurchaseOrder(selectedCredits);

      const options = {
        key: "rzp_test_htVSSrrdDO0Mvj", 
        amount: Math.round(orderData.amount * 100), 
        currency: orderData.currency || "INR",
        name: "AutoNgage",
        description: `Purchase ${orderData.credits} Credits`,
        order_id: orderData.order_id,
        handler: function (response: any) {
          const successData = {
            status: "SUCCESS",
            payment_id: response.razorpay_payment_id,
            order_id: response.razorpay_order_id,
          };
          setPaymentResult(successData);
          setStep(4);
        },
        modal: {
          ondismiss: function () {
            setIsLoading(false);
          },
        },
        prefill: {
          name: billingDetails.name,
          email: billingDetails.email,
          contact: billingDetails.contact,
        },
        theme: {
          color: "##c6bdff",
        },
      };

      const rzp = new window.Razorpay(options);
      rzp.on("payment.failed", function (response: any) {
        setPaymentResult({ status: "FAILED", reason: response.error.description });
        setIsLoading(false);
      });
      rzp.open();
    } catch (error: any) {
      console.error("Payment flow error:", error);
      setPaymentResult({ status: "ERROR", message: error.message });
      setIsLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      {step < 4 && (
        <div className="text-xl font-semibold">
          Step {step} of 3: {step === 1 ? "Choose Credits" : step === 2 ? "Billing Details" : "Review & Pay"}
        </div>
      )}

      {step === 1 && (
        <div className="grid lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 space-y-6">
            <Card>
              <CardContent className="pt-6 space-y-4">
                <div>
                  <h3 className="font-semibold text-lg mb-1">Credit Packs</h3>
                  <p className="text-sm text-muted-foreground">Select a package to add credits to your account</p>
                </div>

                <div className="grid md:grid-cols-3 gap-4">
                  {creditPacks.map((pack) => (
                    <button
                      key={pack.credits}
                      onClick={() => {
                        setSelectedPack(pack.credits)
                        setCustomCredits("")
                      }}
                      className={`relative text-left p-6 rounded-lg border-2 transition-all ${
                        selectedPack === pack.credits
                          ? "border-primary bg-primary/5"
                          : "border-border hover:border-primary/50"
                      }`}
                    >
                      {pack.label && (
                        <Badge variant="secondary" className="absolute -top-2 left-1/2 -translate-x-1/2">
                          {pack.label}
                        </Badge>
                      )}

                      <div className="text-4xl font-bold text-primary mt-2">{pack.credits.toLocaleString()}</div>
                      <div className="text-sm text-muted-foreground mb-4">Credits</div>

                      <div className="text-2xl font-bold">₹{pack.price.toLocaleString()}</div>
                      {/* Removed originalPrice and savings display */}
                    </button>
                  ))}
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="pt-6 space-y-4">
                <div>
                  <h3 className="font-semibold text-lg mb-1">Custom Pack</h3>
                  <p className="text-sm text-muted-foreground">Enter the exact number of credits you need</p>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="custom-credits">Number of Credits</Label>
                  <Input
                    id="custom-credits"
                    type="number"
                    placeholder="Enter credits (min 100)"
                    value={customCredits}
                    onChange={(e) => {
                      setCustomCredits(e.target.value)
                      setSelectedPack(null)
                    }}
                  />
                  <p className="text-sm text-muted-foreground">₹1 per credit • Minimum 100 credits</p>
                </div>
              </CardContent>
            </Card>

            <div className="flex justify-end">
              <Button size="lg" onClick={() => setStep(2)} disabled={!selectedCredits || selectedCredits < 100} className="gap-2">
                Continue
                <ArrowRight className="h-4 w-4" />
              </Button>
            </div>
          </div>

          <div className="lg:col-span-1">
            <Card>
              <CardContent className="pt-6 space-y-4">
                <h3 className="font-semibold text-lg">Order Summary</h3>
                <div className="space-y-3">
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground">Credits</span>
                    <span className="font-medium">{selectedCredits.toLocaleString()}</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground">Subtotal</span>
                    <span className="font-medium">₹{subtotal.toLocaleString()}</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground">GST (18%)</span>
                    <span className="font-medium">₹{tax.toFixed(2)}</span>
                  </div>
                  <div className="border-t pt-3">
                    <div className="flex justify-between">
                      <span className="font-semibold">Total Amount</span>
                      <span className="font-bold text-lg">₹{total.toFixed(2)}</span>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      )}

      {/* Steps 2, 3, and 4 follow the same logic as your original code */}
      {step === 2 && (
        <div className="max-w-3xl space-y-6">
          <Card>
            <CardContent className="pt-6 space-y-6">
              <div>
                <h3 className="font-semibold text-lg mb-1">Billing Details</h3>
                <p className="text-sm text-muted-foreground">Your billing information for the invoice</p>
              </div>

              <div className="grid md:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="name">Full Name <span className="text-destructive">*</span></Label>
                  <Input id="name" value={billingDetails.name} onChange={(e) => setBillingDetails({ ...billingDetails, name: e.target.value })} />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="email">Email <span className="text-destructive">*</span></Label>
                  <Input id="email" type="email" value={billingDetails.email} onChange={(e) => setBillingDetails({ ...billingDetails, email: e.target.value })} />
                </div>
              </div>

              <div className="grid md:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="contact">Phone Number <span className="text-destructive">*</span></Label>
                  <Input id="contact" value={billingDetails.contact} onChange={(e) => setBillingDetails({ ...billingDetails, contact: e.target.value })} />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="company">Company <span className="text-destructive">*</span></Label>
                  <Input id="company" value={billingDetails.company} onChange={(e) => setBillingDetails({ ...billingDetails, company: e.target.value })} />
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="gstin">GST/Tax ID (Optional)</Label>
                <Input id="gstin" placeholder="e.g., 22AAAAA0000A1Z5" value={billingDetails.gstin} onChange={(e) => setBillingDetails({ ...billingDetails, gstin: e.target.value })} />
              </div>

              <div className="space-y-2">
                <Label htmlFor="address">Address <span className="text-destructive">*</span></Label>
                <Input id="address" placeholder="Complete billing address" value={billingDetails.address} onChange={(e) => setBillingDetails({ ...billingDetails, address: e.target.value })} />
              </div>
            </CardContent>
          </Card>

          <div className="flex justify-between">
            <Button variant="ghost" onClick={() => setStep(1)} className="gap-2">
              <ArrowLeft className="h-4 w-4" /> Back
            </Button>
            <Button size="lg" onClick={() => setStep(3)} className="gap-2">
              Review Order <ArrowRight className="h-4 w-4" />
            </Button>
          </div>
        </div>
      )}

      {step === 3 && (
        <div className="max-w-3xl space-y-6">
          <Card>
            <CardContent className="pt-6 space-y-6">
              <div>
                <h3 className="font-semibold text-lg mb-1">Review & Confirm</h3>
                <p className="text-sm text-muted-foreground">Verify your details before securely proceeding to payment.</p>
              </div>

              <div className="grid md:grid-cols-2 gap-8 border rounded-lg p-6 bg-muted/20">
                <div className="space-y-2 text-sm">
                  <h4 className="font-semibold text-base mb-3">Billing Information</h4>
                  <p><span className="text-muted-foreground">Name:</span> {billingDetails.name}</p>
                  <p><span className="text-muted-foreground">Email:</span> {billingDetails.email}</p>
                  <p><span className="text-muted-foreground">Company:</span> {billingDetails.company}</p>
                  {billingDetails.gstin && <p><span className="text-muted-foreground">GSTIN:</span> {billingDetails.gstin}</p>}
                </div>

                <div className="space-y-3 text-sm">
                   <h4 className="font-semibold text-base mb-3">Order Details</h4>
                  <div className="flex justify-between border-b pb-2">
                    <span className="text-muted-foreground">Credits Requested:</span>
                    <span className="font-medium">{selectedCredits.toLocaleString()}</span>
                  </div>
                  <div className="flex justify-between pt-2">
                    <span className="font-semibold text-base">Total Amount to Pay:</span>
                    <span className="font-bold text-lg text-primary">₹{total.toFixed(2)}</span>
                  </div>
                </div>
              </div>

              {paymentResult?.status === "ERROR" || paymentResult?.status === "FAILED" ? (
                <div className="p-3 bg-red-100 text-red-700 rounded-md text-sm border border-red-200">
                  Payment Failed: {paymentResult.reason || paymentResult.message}
                </div>
              ) : null}
            </CardContent>
          </Card>

          <div className="flex justify-between items-center">
            <Button variant="ghost" onClick={() => setStep(2)} className="gap-2" disabled={isLoading}>
              <ArrowLeft className="h-4 w-4" /> Back
            </Button>

            <Button 
              size="lg" 
              onClick={handleRazorpayPayment} 
              disabled={isLoading}
              className="gap-2 bg-green-600 hover:bg-green-700 text-white min-w-[200px]"
            >
              {isLoading ? (
                <Loader2 className="h-5 w-5 animate-spin" />
              ) : (
                <CreditCard className="h-5 w-5" />
              )}
              {isLoading ? "Connecting to secure gateway..." : `Pay ₹${total.toFixed(2)} Securely`}
            </Button>
          </div>
        </div>
      )}

      {step === 4 && (
        <Card className="max-w-xl mx-auto mt-12 border-green-200 bg-green-50/50">
          <CardContent className="pt-10 pb-10 text-center space-y-4">
            <CheckCircle2 className="h-16 w-16 text-green-500 mx-auto" />
            <h2 className="text-2xl font-bold text-green-900">Payment Successful!</h2>
            <p className="text-green-700 mb-6">
              Your account has been credited with <strong>{selectedCredits.toLocaleString()}</strong> credits.
            </p>
            <div className="text-sm text-green-800 bg-white p-4 rounded-md border border-green-100 inline-block text-left mb-6">
               <p><strong>Order ID:</strong> {paymentResult?.order_id}</p>
               <p><strong>Payment ID:</strong> {paymentResult?.payment_id}</p>
            </div>
            <div>
              <Button onClick={() => window.location.reload()} className="bg-green-600 hover:bg-green-700">
                Return to Dashboard
              </Button>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}