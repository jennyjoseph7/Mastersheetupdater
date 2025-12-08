"use client"

import { useState } from "react"
import { ArrowRight, ArrowLeft, CreditCard, Building2, Smartphone } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Badge } from "@/components/ui/badge"

const creditPacks = [
  { credits: 500, price: 500, label: "Starter" },
  { credits: 1000, price: 900, originalPrice: 1000, savings: 100, label: "Value Pack", popular: true },
  { credits: 5000, price: 4000, originalPrice: 5000, savings: 1000, label: "Best Value" },
]

export function BuyCreditsTab() {
  const [step, setStep] = useState(1)
  const [selectedPack, setSelectedPack] = useState<number | null>(1000)
  const [customCredits, setCustomCredits] = useState("")
  const [billingDetails, setBillingDetails] = useState({
    name: "John Doe",
    email: "john.doe@example.com",
    company: "ABC Auto Sales",
    gstin: "",
    address: "",
  })
  const [paymentMethod, setPaymentMethod] = useState("card")

  const selectedCredits = selectedPack !== null ? selectedPack : Number.parseInt(customCredits) || 0
  const selectedPackData = creditPacks.find((p) => p.credits === selectedPack)
  const pricePerCredit = selectedPack !== null ? (selectedPackData?.price || 0) / (selectedPackData?.credits || 1) : 1
  const subtotal = selectedPack !== null ? selectedPackData?.price || 0 : Number.parseInt(customCredits) || 0
  const tax = subtotal * 0.18
  const total = subtotal + tax

  return (
    <div className="space-y-6">
      {/* Step indicator */}
      <div className="text-xl font-semibold">
        Step {step} of 3: {step === 1 ? "Choose Credits" : step === 2 ? "Billing Details" : "Payment"}
      </div>

      {step === 1 && (
        <div className="grid lg:grid-cols-3 gap-6">
          {/* Main content */}
          <div className="lg:col-span-2 space-y-6">
            {/* Credit Packs */}
            <Card>
              <CardContent className="pt-6 space-y-4">
                <div>
                  <h3 className="font-semibold text-lg mb-1">Credit Packs</h3>
                  <p className="text-sm text-muted-foreground">Choose from our popular credit packages</p>
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
                      {pack.popular && (
                        <Badge className="absolute -top-2 left-1/2 -translate-x-1/2 bg-primary">Most Popular</Badge>
                      )}
                      {pack.label && !pack.popular && (
                        <Badge variant="secondary" className="absolute -top-2 left-1/2 -translate-x-1/2">
                          {pack.label}
                        </Badge>
                      )}
                      {pack.label === "Best Value" && (
                        <Badge className="absolute -top-2 left-1/2 -translate-x-1/2 bg-green-600">Best Value</Badge>
                      )}

                      <div className="text-4xl font-bold text-primary mt-2">{pack.credits.toLocaleString()}</div>
                      <div className="text-sm text-muted-foreground mb-4">Credits</div>

                      <div className="text-2xl font-bold">₹{pack.price.toLocaleString()}</div>
                      {pack.originalPrice && (
                        <div className="flex items-center gap-2 mt-1">
                          <span className="text-sm text-muted-foreground line-through">
                            ₹{pack.originalPrice.toLocaleString()}
                          </span>
                          <span className="text-sm text-green-600 font-medium">Save ₹{pack.savings}</span>
                        </div>
                      )}
                    </button>
                  ))}
                </div>
              </CardContent>
            </Card>

            {/* Custom Pack */}
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
              <Button size="lg" onClick={() => setStep(2)} disabled={!selectedCredits} className="gap-2">
                Continue
                <ArrowRight className="h-4 w-4" />
              </Button>
            </div>
          </div>

          {/* Order Summary */}
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
                  <Label htmlFor="name">
                    Full Name <span className="text-destructive">*</span>
                  </Label>
                  <Input
                    id="name"
                    value={billingDetails.name}
                    onChange={(e) => setBillingDetails({ ...billingDetails, name: e.target.value })}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="email">
                    Email <span className="text-destructive">*</span>
                  </Label>
                  <Input
                    id="email"
                    type="email"
                    value={billingDetails.email}
                    onChange={(e) => setBillingDetails({ ...billingDetails, email: e.target.value })}
                  />
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="company">
                  Company <span className="text-destructive">*</span>
                </Label>
                <Input
                  id="company"
                  value={billingDetails.company}
                  onChange={(e) => setBillingDetails({ ...billingDetails, company: e.target.value })}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="gstin">GST/Tax ID (Optional)</Label>
                <Input
                  id="gstin"
                  placeholder="e.g., 22AAAAA0000A1Z5"
                  value={billingDetails.gstin}
                  onChange={(e) => setBillingDetails({ ...billingDetails, gstin: e.target.value })}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="address">
                  Address <span className="text-destructive">*</span>
                </Label>
                <Input
                  id="address"
                  placeholder="Complete billing address"
                  value={billingDetails.address}
                  onChange={(e) => setBillingDetails({ ...billingDetails, address: e.target.value })}
                />
              </div>
            </CardContent>
          </Card>

          <div className="flex justify-between">
            <Button variant="ghost" onClick={() => setStep(1)} className="gap-2">
              <ArrowLeft className="h-4 w-4" />
              Back
            </Button>
            <Button size="lg" onClick={() => setStep(3)} className="gap-2">
              Proceed to Payment
              <ArrowRight className="h-4 w-4" />
            </Button>
          </div>
        </div>
      )}

      {step === 3 && (
        <div className="max-w-3xl space-y-6">
          <Card>
            <CardContent className="pt-6 space-y-6">
              <div>
                <h3 className="font-semibold text-lg mb-1">Payment Methods</h3>
                <p className="text-sm text-muted-foreground">Choose your preferred payment method</p>
              </div>

              {/* Payment method selection */}
              <div className="grid md:grid-cols-3 gap-4">
                <button
                  onClick={() => setPaymentMethod("upi")}
                  className={`p-6 rounded-lg border-2 transition-all text-center ${
                    paymentMethod === "upi" ? "border-primary bg-primary/5" : "border-border hover:border-primary/50"
                  }`}
                >
                  <Smartphone className="h-8 w-8 mx-auto mb-3 text-green-600" />
                  <div className="font-semibold mb-1">UPI Payment</div>
                  <div className="text-xs text-muted-foreground">Instant & Secure</div>
                </button>

                <button
                  onClick={() => setPaymentMethod("card")}
                  className={`p-6 rounded-lg border-2 transition-all text-center ${
                    paymentMethod === "card" ? "border-primary bg-primary/5" : "border-border hover:border-primary/50"
                  }`}
                >
                  <CreditCard className="h-8 w-8 mx-auto mb-3 text-primary" />
                  <div className="font-semibold mb-1">Card Payment</div>
                  <div className="text-xs text-muted-foreground">Credit/Debit Card</div>
                </button>

                <button
                  onClick={() => setPaymentMethod("netbanking")}
                  className={`p-6 rounded-lg border-2 transition-all text-center ${
                    paymentMethod === "netbanking"
                      ? "border-primary bg-primary/5"
                      : "border-border hover:border-primary/50"
                  }`}
                >
                  <Building2 className="h-8 w-8 mx-auto mb-3 text-blue-600" />
                  <div className="font-semibold mb-1">Net Banking</div>
                  <div className="text-xs text-muted-foreground">All Major Banks</div>
                </button>
              </div>

              {/* Card payment form */}
              {paymentMethod === "card" && (
                <div className="space-y-4 p-6 border-2 border-primary rounded-lg bg-primary/5">
                  <div className="space-y-2">
                    <Label htmlFor="card-number">
                      Card Number <span className="text-destructive">*</span>
                    </Label>
                    <Input id="card-number" placeholder="1234 5678 9012 3456" />
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label htmlFor="expiry">
                        Expiry Date <span className="text-destructive">*</span>
                      </Label>
                      <Input id="expiry" placeholder="MM/YY" />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="cvv">
                        CVV <span className="text-destructive">*</span>
                      </Label>
                      <Input id="cvv" placeholder="123" type="password" maxLength={3} />
                    </div>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="cardholder">
                      Cardholder Name <span className="text-destructive">*</span>
                    </Label>
                    <Input id="cardholder" placeholder="Name on card" />
                  </div>
                </div>
              )}

              {/* Total amount display */}
              <div className="flex justify-between items-center pt-4 border-t">
                <span className="font-semibold">Total Amount</span>
                <span className="text-2xl font-bold text-primary">₹{total.toFixed(2)}</span>
              </div>
            </CardContent>
          </Card>

          {/* Action buttons */}
          <div className="space-y-4">
            <Button size="lg" className="w-full hover:bg-orange-700 text-white text-lg bg-primary h-11">
              Pay ₹{total.toFixed(2)}
            </Button>

            <Button variant="ghost" onClick={() => setStep(2)} className="gap-2">
              <ArrowLeft className="h-4 w-4" />
              Back
            </Button>
          </div>
        </div>
      )}
    </div>
  )
}
