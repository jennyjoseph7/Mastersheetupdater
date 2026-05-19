# Executive Storytelling Dashboard — Implementation Plan

## 1. Core Problem

The current dashboard has analysis functions and panels, but **nowhere does it read or quote from the SUMMARY column**. The SUMMARY contains the actual customer voice — what customers said, why they didn't book, what language they requested, where they went instead, when they'll come back. This is the richest data source and it's completely unused for storytelling.

## 2. What Must Change

Every section of the dashboard must derive its narrative from **actual SUMMARY text**, not just counts. The experience should read like an analyst briefing management.

---

## 3. New Summary Mining Engine

### 3.1 `mineCustomerThemes(rows, colMap)`

Scans all SUMMARY texts and groups rows by detected customer themes. Returns:

```javascript
{
  themes: [
    {
      id: 'already_serviced',
      label: 'Already Serviced Elsewhere',
      count: 15,
      pct: '15.6',
      excerpts: [
        '...informed the agent that the service had already been completed at Shady Island Motor...',
        '...stated the bike had already been serviced last month at a different service center...',
        '...the service had already been completed by another service provider named Miles...'
      ],
      competitorNames: ['Shady Island Motor', 'Miles', 'General Electric'],
      sentiment: 'negative'
    },
    {
      id: 'language_barrier',
      label: 'Language Barrier',
      count: 5,
      pct: '5.2',
      excerpts: [
        '...the user immediately stated they do not speak English, only Hindi and Kannada...',
        '...user requested Hindi but agent only supports Kannada or English...'
      ],
      sentiment: 'neutral'
    },
    {
      id: 'voicemail',
      label: 'Voicemail / Unreachable',
      count: 22,
      pct: '22.9',
      excerpts: [
        '...call was answered by an automated voicemail system...',
        '...generic voicemail message was detected...',
        '...At the tone, please record your message...'
      ],
      sentiment: 'neutral'
    },
    {
      id: 'callback_requested',
      label: 'Requested Callback',
      count: 6,
      pct: '6.3',
      excerpts: [
        '...requested a callback for a later date and time...',
        '...user stated they would call back later...',
        '...requested to call back in half an hour...'
      ],
      callbackTimes: ['half an hour', 'after 7 PM', 'tomorrow morning'],
      sentiment: 'positive'
    },
    {
      id: 'deferred',
      label: 'Deferred / Will Decide Later',
      count: 14,
      pct: '14.6',
      excerpts: [
        '...initially deferred booking, stating they would do so next month...',
        '...user is currently out of town and will book after May 11th...',
        '...user requested appointment for next week...'
      ],
      timeframes: ['next month', 'after May 11th', 'next week', 'Monday'],
      sentiment: 'neutral'
    },
    {
      id: 'not_interested',
      label: 'Not Interested / Declined',
      count: 9,
      pct: '9.4',
      excerpts: [
        '...user declined the service appointment...',
        '...user repeatedly declined, stating it was not currently required...',
        '...user declined to book, stating they would visit a nearby service station...'
      ],
      sentiment: 'negative'
    },
    {
      id: 'customer_busy',
      label: 'Customer Busy / Unavailable',
      count: 8,
      pct: '8.3',
      excerpts: [
        '...user was driving and unable to speak...',
        '...user stated they were in a meeting and requested a callback...',
        '...user indicated they were riding and unable to speak at that moment...'
      ],
      sentiment: 'neutral'
    },
    {
      id: 'wrong_person',
      label: 'Wrong Person / Not Decision Maker',
      count: 4,
      pct: '4.2',
      excerpts: [
        '...user stated the bike belongs to their son...',
        '...user clarified the bike belongs to their son and is no longer with them...'
      ],
      sentiment: 'negative'
    }
  ],
  total: 96,
  topTheme: { id: 'already_serviced', count: 15 }
}
```

### 3.2 Theme Detection Logic

For each row's SUMMARY text, scan for these signal phrases and classify:

| Theme | Detection Pattern (from SUMMARY) |
|---|---|
| Already Serviced | `already serviced`, `already completed`, `already done`, `serviced elsewhere`, `bike was recently serviced` |
| Language Barrier | `do not speak english`, `only hindi`, `requested hindi`, `language barrier`, `only kannada` |
| Voicemail | `voicemail`, `automated voicemail`, `at the tone`, `record your message`, `hang up after` |
| Callback Requested | `requested a callback`, `call back later`, `will call back`, `asked to call back` |
| Deferred | `deferred`, `will decide`, `out of station`, `out of town`, `next week`, `next month` |
| Not Interested | `declined`, `not interested`, `not required`, `refused`, `repeatedly declined` |
| Customer Busy | `driving`, `in a meeting`, `at work`, `was riding`, `busy`, `unavailable` |
| Wrong Person | `belongs to`, `not the right person`, `not the decision maker` |
| Audio Issue | `audio issue`, `unclear audio`, `could not hear`, `difficulty hearing` |
| Sold Vehicle | `sold the bike`, `no longer own`, `given away` |
| Service Booked | `appointment was successfully booked`, `service confirmed`, `booking confirmed` |
| Dissatisfied | `dissatisfied`, `complaint`, `unhappy`, `negative feedback`, `poor service` |

For each theme, store **actual excerpt** (first 120 chars of the SUMMARY as evidence).

### 3.3 `generateStoryHeadline(themes, funnel, healthScore)`

Generates the top headline based on strongest signal in data:

- If conversion is strong: `"This campaign connected 68% of leads — here's why customers are booking"`
- If competitive loss is high: `"15 customers went to competitors — Shady Island Motor leads the list"`
- If language barriers exist: `"Language gaps blocked 5 calls — customers requested Hindi but only Kannada/English supported"`
- If deferrals dominate: `"37 customers are in the decision pipeline — most will decide within 7 days"`

### 3.4 `generateExecutiveNarrative(themes, funnel, trends, healthScore)`

Builds multi-paragraph narrative:

> *"This post-sales campaign reached **96** customers over 14 days. **65** answered (68% connect rate), and **12** booked service appointments — a 18% conversion from connected calls.*
>
> *"The most significant pattern: **15 customers were already serviced elsewhere** — including 3 at Shady Island Motor, 2 at Miles, and others at General Electric and Yellanka Newton. This represents 23% of all connected calls and is the #1 blocker to conversion.*
>
> *"Language barriers affected **5 calls** where customers requested Hindi but only Kannada and English are supported. **14 customers deferred** their decision — most indicating 'next week' or 'next month' — keeping 37 active opportunities in the pipeline.*
>
> *"Call quality: 22% of calls went to voicemail. 8% found customers driving or in meetings. Agent Lakshmi handled 78 calls with 68% connect rate and 15% booking rate, leading the team."*

---

## 4. New Dashboard Layout (Section Order)

The dashboard tells a story from top to bottom:

### Section 1: Executive Story Banner (REPLACE current exec summary)
- Strong headline from `generateStoryHeadline()`
- 2-3 paragraph narrative from `generateExecutiveNarrative()`
- Health score ring (existing)
- Anomaly chips at bottom (existing insight strip, redesigned)
- **Visual**: Full-width hero card with gradient accent

### Section 2: What Customers Are Saying (NEW — most important addition)
- Title: "What Customers Are Saying"
- Theme cards in a 3 or 4-column grid
- Each card shows:
  - Theme icon/emoji
  - Theme name + count + percentage
  - 1-2 actual transcript excerpts in quote style
  - For "Already Serviced": competitor names listed
  - For "Callback Requested": callback times listed
  - For "Deferred": timeframe list
- **Visual**: Cards with left accent border colored by sentiment (green/amber/red)
- Only shows themes with > 2 occurrences

### Section 3: Campaign Health at a Glance
- Insight chips (existing, enhanced with narrative text)
- Each chip shows: label, value, and a one-line "why" derived from themes

### Section 4: The Conversion Story
- Funnel (existing): Total → Connected → Booked
- Below funnel: "Why connected leads didn't book" — uses actual blocker data linked to customer themes
- Narrative: *"Of 53 connected but not booked: 15 already serviced, 14 deferred, 9 declined, 6 requested callback, 5 language barrier, 4 audio issues"*

### Section 5: Customer Signals Deep Dive (NEW)
- Title: "Customer Signals & Patterns"
- Two-column layout:
  - Left: Top objections from SUMMARY (actual customer language)
  - Right: Language preferences (Kannada/English/Hindi breakdown)
- Below: Agent performance table (restored per user spec)
  - Columns: Agent, Calls, Connected %, Booked %
  - Highlighted top performer

### Section 6: Operational View
- Source quality (existing, enhanced)
- Competitive intelligence (existing)
- Call quality & language (existing)

### Section 7: Recommended Actions (NEW — most important addition)
- Title: "Recommended Next Steps"
- 3-5 recommendation cards, each:
  - Action title
  - Reason (with data citation from actual SUMMARY excerpts)
  - Expected impact
- Examples:
  - **"Re-engage 14 deferrals"** — *14 customers said they'd decide later (next week/next month). Send SMS reminders and schedule callbacks in their stated timeframe.* → *Potential: 5-7 additional bookings*
  - **"Investigate competitive loss to Shady Island Motor"** — *3 customers mentioned going to Shady Island Motor. Mystery shop their service experience and pricing.* → *Potential: recover 2-3 lost customers*
  - **"Add Hindi language support"** — *5 callers specifically requested Hindi. Offering Hindi could improve connect rate and booking conversion for this segment.* → *Potential: 2-3 additional bookings*
  - **"Follow up on 6 callback requests"** — *6 customers explicitly asked to be called back. Only 2 had reattempts recorded.* → *Potential: 1-2 additional bookings*

---

## 5. New Analysis Functions

| Function | Purpose | Lines |
|---|---|---|
| `mineCustomerThemes(rows, colMap)` | Scans SUMMARY, groups by theme, extracts excerpts | ~60 |
| `generateStoryHeadline(themes, funnel, healthScore)` | Generates headline from dominant pattern | ~20 |
| `generateExecutiveNarrative(themes, funnel, trends, healthScore, agents, competitors)` | Builds 2-3 paragraph narrative | ~40 |
| `generateRecommendations(themes, funnel, competitors, callbacks)` | Generates recommended actions from data | ~30 |

## 6. New Render Functions

| Function | Purpose | Lines |
|---|---|---|
| `renderCustomerVoice(themes)` | Theme cards with excerpts | ~50 |
| `renderRecommendations(recs)` | Action cards | ~30 |
| `renderAgentTable(agents)` | Agent performance table | ~30 |

## 7. Restored Agent Performance

Add back as a table (not cards):
- Columns: Rank, Agent Name, Calls, Connected %, Booked %
- Top 3 ranked by booking rate
- Gold/silver/bronze badges
- Only visible when 2+ agents detected

## 8. CSS Additions (~200 lines)

| Component | Key classes |
|---|---|
| Customer voice cards | `.voice-grid`, `.voice-card.positive/neutral/negative`, `.voice-excerpt` |
| Quote styling | `.voice-quote` with left border, italic text, quotation mark |
| Recommendation cards | `.rec-card`, `.rec-action`, `.rec-reason`, `.rec-impact` |
| Story headline | `.story-headline` — large bold text |
| Agent table | `.agent-tbl` (restored), `.rank-gold/silver/bronze` |

## 9. Implementation Order

1. Add `mineCustomerThemes()` — the core text mining engine
2. Add `generateStoryHeadline()` + `generateExecutiveNarrative()` — narrative generation
3. Add `generateRecommendations()` — action recommendation engine
4. Add `renderCustomerVoice()` + `renderRecommendations()` + `renderAgentTable()`
5. Add CSS for all new components
6. Rewrite HTML section order in `#dashboardContent`
7. Rewrite the executive summary banner HTML
8. Integrate into `generateDashboard()` — call new functions, render new sections
9. Add agent column detection back (COL_AGENT from SUMMARY parsing already exists in parseSummary)
10. Update `clearDashboardOutput()` + PDF export

## 10. File Impact

- `dashboard.html`: ~+500 new lines (total ~4850)
- Plan document updated

## 11. Key Principle

**Every insight must cite evidence from the uploaded data.**
- Not: "Some customers are not interested"
- But: *"9 customers declined — 3 said 'bike was recently serviced', 2 said 'not required', 1 said 'will visit nearby service station'"*
- Not: "Language is a barrier"
- But: *"5 calls had language issues — customers requested Hindi, but the system only supports Kannada and English. This cost ~5% of potential connections."*

The dashboard should make the client feel like the system read every single call transcript and summarized the key themes for them.
