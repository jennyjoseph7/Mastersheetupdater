"use client"

import { Sparkles } from "lucide-react"
import { useState, useEffect } from "react"

interface AILoaderProps {
  quotes?: string[]
  facts?: string[]
  className?: string
}

const defaultQuotes = [
  "AI is the new electricity.",
  "Machine learning is programming computers to optimize a performance criterion using example data or past experience.",
  "The key to artificial intelligence has always been the representation.",
  "AI will probably most likely lead to the end of the world, but in the meantime, there'll be great companies.",
  "Artificial intelligence would be the ultimate version of Google.",
  "AI is neither good nor evil. It's a tool. It's a technology for us to use.",
]

const defaultFacts = [
  "Did you know? The first AI program was written in 1951.",
  "Fun fact: AI can now generate human-like text and images.",
  "Interesting: Machine learning algorithms improve with more data.",
  "Cool fact: AI has beaten humans at chess, Go, and Jeopardy!",
  "Amazing: Natural language processing helps AI understand human speech.",
  "Neat fact: Computer vision allows AI to interpret and understand visual data.",
]

export function AILoader({ quotes = defaultQuotes, facts = defaultFacts, className = "" }: AILoaderProps) {
  const [currentQuote, setCurrentQuote] = useState(0)
  const [currentFact, setCurrentFact] = useState(0)
  const [showQuote, setShowQuote] = useState(true)

  useEffect(() => {
    const quoteInterval = setInterval(() => {
      setShowQuote(false)
      setTimeout(() => {
        setCurrentQuote((prev) => (prev + 1) % quotes.length)
        setShowQuote(true)
      }, 300)
    }, 4000)

    return () => clearInterval(quoteInterval)
  }, [quotes.length])

  useEffect(() => {
    const factInterval = setInterval(() => {
      setCurrentFact((prev) => (prev + 1) % facts.length)
    }, 5000)

    return () => clearInterval(factInterval)
  }, [facts.length])

  return (
    <div className={`flex flex-col items-center justify-center space-y-8 ${className}`}>
      <div className="relative">
        <div className="absolute inset-0 animate-ping rounded-full bg-primary/20 blur-xl" />
        <div className="absolute inset-0 animate-pulse rounded-full bg-primary/10 blur-lg" />
        <div className="relative flex h-28 w-28 items-center justify-center rounded-full bg-gradient-to-br from-primary/20 via-primary/10 to-primary/5 border-2 border-primary/30 shadow-xl">
          <Sparkles className="h-14 w-14 text-primary animate-pulse" />
        </div>
      </div>

      <div className="flex gap-3">
        {[0, 1, 2, 3, 4].map((i) => (
          <div
            key={i}
            className="h-2.5 w-2.5 rounded-full bg-primary animate-bounce shadow-md"
            style={{ animationDelay: `${i * 0.12}s` }}
          />
        ))}
      </div>

      <div className="max-w-2xl text-center space-y-2 px-4">
        <div
          className={`transition-all duration-500 ${showQuote ? "opacity-100 translate-y-0" : "opacity-0 -translate-y-4"}`}
        >
          <p className="text-base md:text-lg font-semibold text-foreground italic leading-relaxed">
            "{quotes[currentQuote]}"
          </p>
        </div>
      </div>

      <div className="max-w-lg text-center px-4">
        <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-primary/5 border border-primary/20">
          <Sparkles className="h-4 w-4 text-primary flex-shrink-0" />
          <p className="text-sm text-muted-foreground transition-opacity duration-500 font-medium">
            {facts[currentFact]}
          </p>
        </div>
      </div>
    </div>
  )
}
