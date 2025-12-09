"use client"

import { Download, Mail } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Badge } from "@/components/ui/badge"

const billingHistory = [
  {
    date: "15/08/2025",
    credits: 1000,
    amount: 900,
    paymentMethod: "UPI",
    status: "Completed",
  },
  {
    date: "20/07/2025",
    credits: 500,
    amount: 500,
    paymentMethod: "Credit Card",
    status: "Completed",
  },
  {
    date: "28/06/2025",
    credits: 5000,
    amount: 4000,
    paymentMethod: "Net Banking",
    status: "Completed",
  },
]

export function BillingHistoryTab() {
  return (
    <Card>
      <CardContent className="pt-6 space-y-4">
        <div>
          <h3 className="font-semibold text-lg">Billing History</h3>
          <p className="text-sm text-muted-foreground">View and manage your past purchases</p>
        </div>

        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Date</TableHead>
              <TableHead>Credits Purchased</TableHead>
              <TableHead>Amount</TableHead>
              <TableHead>Payment Method</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {billingHistory.map((transaction, index) => (
              <TableRow key={index}>
                <TableCell>{transaction.date}</TableCell>
                <TableCell>{transaction.credits.toLocaleString()}</TableCell>
                <TableCell>₹{transaction.amount.toLocaleString()}</TableCell>
                <TableCell>{transaction.paymentMethod}</TableCell>
                <TableCell>
                  <Badge className="bg-green-600">{transaction.status}</Badge>
                </TableCell>
                <TableCell>
                  <div className="flex gap-2">
                    <Button variant="ghost" size="sm" className="gap-1 h-8">
                      <Download className="h-3 w-3" />
                      PDF
                    </Button>
                    <Button variant="ghost" size="sm" className="gap-1 h-8">
                      <Mail className="h-3 w-3" />
                      Email
                    </Button>
                  </div>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  )
}
