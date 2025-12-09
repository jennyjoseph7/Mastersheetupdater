"use client"

import { useState } from "react"
import PageHeader from "@/components/page-header"
import { UnansweredQueryList, type UnansweredQuery } from "@/components/unanswered-query-list"
import { EnhancedTakeActionModal } from "@/components/enhanced-take-action-modal"

// Mock Data for Unanswered Queries with new statuses
const mockUnansweredQueries: UnansweredQuery[] = [
  {
    id: "uq_001",
    queryText: "My policy number is not recognized, what should I do?",
    timestamp: "2025-07-19T14:20:00Z",
    sessionId: "sess_005",
    status: "pending",
  },
  {
    id: "uq_002",
    queryText: "I need to speak to a human, the bot is not understanding me.",
    timestamp: "2025-07-19T15:05:00Z",
    sessionId: "sess_006",
    status: "pending",
  },
  {
    id: "uq_003",
    queryText: "How do I get a refund for an overpayment?",
    timestamp: "2025-07-20T09:30:00Z",
    sessionId: "sess_007",
    status: "pending",
  },
  {
    id: "uq_004",
    queryText: "Can I add a new driver to my policy online?",
    timestamp: "2025-07-20T11:45:00Z",
    sessionId: "sess_008",
    status: "faq-added",
  },
  {
    id: "uq_005",
    queryText: "What is the process for changing my coverage limits?",
    timestamp: "2025-07-21T10:00:00Z",
    sessionId: "sess_009",
    status: "pending",
  },
  {
    id: "uq_006",
    queryText: "asdfghjkl random text spam",
    timestamp: "2025-07-21T11:30:00Z",
    sessionId: "sess_010",
    status: "garbage",
  },
  {
    id: "uq_007",
    queryText: "Can I get cryptocurrency insurance?",
    timestamp: "2025-07-21T12:15:00Z",
    sessionId: "sess_011",
    status: "not-supported",
  },
  {
    id: "uq_008",
    queryText: "My claim was denied but I think it should be approved",
    timestamp: "2025-07-21T13:45:00Z",
    sessionId: "sess_012",
    status: "incorrect-answer",
  },
]

export default function UnansweredQueriesPage() {
  const [queries, setQueries] = useState<UnansweredQuery[]>(mockUnansweredQueries)
  const [selectedQueryForAction, setSelectedQueryForAction] = useState<UnansweredQuery | null>(null)
  const [isModalOpen, setIsModalOpen] = useState(false)

  const handleTakeActionClick = (queryId: string) => {
    const query = queries.find((q) => q.id === queryId)
    if (query) {
      setSelectedQueryForAction(query)
      setIsModalOpen(true)
    }
  }

  const handleActionSubmit = (queryId: string, actionType: string, actionData: any) => {
    // In a real application, you would send this to your backend
    console.log(`Query ${queryId} action: ${actionType}`, actionData)

    // Update the status in the local state
    setQueries((prevQueries) =>
      prevQueries.map((q) => (q.id === queryId ? { ...q, status: actionType as UnansweredQuery["status"] } : q)),
    )
    setSelectedQueryForAction(null)
    setIsModalOpen(false)
  }

  return (
    <div className="flex min-h-screen flex-col">
      <PageHeader
        title="Unanswered Queries"
        description="Review and take action on queries the chatbot couldn't resolve."
      />
      <main className="flex-1 space-y-6 p-6 md:p-8 w-full">
        <UnansweredQueryList queries={queries} onTakeAction={handleTakeActionClick} />
      </main>

      <EnhancedTakeActionModal
        query={selectedQueryForAction}
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onAction={handleActionSubmit}
      />
    </div>
  )
}
