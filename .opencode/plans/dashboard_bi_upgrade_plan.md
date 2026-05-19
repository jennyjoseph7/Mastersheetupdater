# Dashboard → Premium BI Platform — Implementation Plan

## 1. Overview

Transform the existing campaign dashboard (`dashboard.html`) from a static KPI reporting screen into an intelligent Business Intelligence platform. The system ingests Zoho Master Sheet exports (CSV/XLSX), automatically classifies every row using disposition taxonomies, mines the SUMMARY transcript column for call outcomes, and generates **context-aware narrative insights** that explain every number using real operational patterns.

---

## 2. REAL SUMMARY PATTERNS (Observed from Production Data)

The SUMMARY column follows semi-structured prose. Key patterns identified from real Perfect Riders data:

### 2.1 Agent Name Extraction

| Pattern | Example |
|---|---|
| `agent, {Name} from {Dealership}` | "The agent, Lakshmi from Perfect Riders Yamaha Service Center" |
| `agent named {Name} from` | "An agent named Lakshmi from Perfect Riders Yamaha Service Center" |
| `An agent from {Dealership}` (no name) | "An agent from Perfect Riders Yamaha Service Center" |
| Name correction pattern | "Lakshmi (later Priya)" or "initially Lakshmi, then Priya" |
| Digital assistant pattern | "A digital sales assistant from Perfect Riders Yamaha Service Center" |

### 2.2 Call Outcome Classification Patterns

| Category | Real Transcript Signals |
|---|---|
| **VOICEMAIL** | "call was answered by an automated voicemail system", "generic voicemail message was detected", "At the tone, please record your message", "When you have finished recording, you may hang up", "voicemail detection tool confirmed", "automated voicemail greeting", "Beep, beep", "Please stay on the line" (interpreted as voicemail) |
| **LANGUAGE_BARRIER** | "do not speak English, only Hindi and Kannada", "requested Hindi", "only Kannada or English are supported", "offered a choice of language", "language barrier" |
| **ALREADY_SERVICED** | "service had already been completed", "service already done", "already serviced elsewhere", "bike had already been serviced", "bike was recently serviced" |
| **SERVICE_BOOKED** | "appointment was successfully booked", "service appointment was successfully confirmed", "booked for Saturday, May 9, 2026, at 11:00 AM", "agent confirmed the booking" |
| **DEFERRED** | "initially deferred booking", "will decide later", "will call back later", "out of station", "out of town", "next week", "next month", "will come next month", timeframe mentions |
| **NOT_INTERESTED** | "user declined the service", "not required", "not interested", "repeatedly declined", "user declined to book" |
| **CALLBACK_REQUESTED** | "requested a callback", "call back later", "callback after {time}", "call back at {time}", "requested to call back" |
| **CUSTOMER_BUSY** | "driving and unable to speak", "in a meeting", "at work", "was riding", "currently out of station", "unavailable to speak" |
| **AUDIO_ISSUE** | "audio issues", "unclear audio", "voice quality", "could not hear", "difficulty hearing", "repeatedly 'Hello?'", "communication breakdown" |
| **SOLD_VEHICLE** | "sold the bike and no longer own it", "given away", "no longer own the vehicle", "had sold it" |
| **WRONG_PERSON** | "belongs to their son", "not the right person", "not the decision maker", "belongs to someone else" |
| **COMPETITIVE_LOSS** | Specific competitor service locations: "Shady Island Motor", "Miles", "General Electric", "Yellanka Newton", "Garth Motors Yamaha", "Chandan Yamaha" |
| **ESCALATION_NEEDED** | "could not provide this specific information", "transfer the user to a human agent" |
| **NO_RESPONSE** | "user did not respond", "user remained silent", "no audible response", "user was unresponsive" |
| **DISSATISFIED** | "expressed significant dissatisfaction", "negative feedback", "poor service", "complaint", "unhappy" |
| **AI_QUESTION** | "questioning if the agent was an AI", "asked about gradient descent", "are you an AI", "what model are you" |
| **CALL_DISCONNECTED** | "call dropped", "ended abruptly", "user ended the call" |

### 2.3 Extractable Data Points from SUMMARY

| Data Point | Regex Pattern |
|---|---|
| Agent name | `agent[,\s]+(\w+)(?:\s+\(later\s+(\w+)\))?` |
| Customer name | `(?:contacted\|called\|to)\s+(\w+(?:\s+\w+)?)(?:\s+regarding)` |
| Vehicle model | `(?:for\|their\|a\|about)\s+(?:Yamaha\s+)?([\w\s]+?)\s+(?:bike\|\(reg)` |
| Registration | `\(([\w\s]+?)\)` after vehicle model |
| Last service date | `last service was on (\w+\s+\d+,\s+\d{4})` |
| Next due date | `due by (\w+\s+\d+,\s+\d{4})\|before (\w+\s+\d+,\s+\d{4})` |
| Booked date/time | `booked for\s+(.+?)(?:,\|\s+by)` |
| Booked location | `(Lalbagh\|Jayanagar)` |
| Language chosen | `(?:selected\|chose\|opted for\|preferred)\s+(\w+)` |
| Competitor location | `serviced(?:\s+at)?\s+(.+?)(?:\.\|,\|and)` (in "already serviced" context) |
| Callback time | `(?:callback\|call back)\s+(?:in\|after\|at\|for)\s+(.+?)(?:\.\|,\|the)` |

---

## 3. Architecture

### 3.1 New Data: SUMMARY Parser

```javascript
parseSummary(text) -> {
  agentName: string | null,
  agentNameCorrected: string | null,    // "Priya" if "Lakshmi (later Priya)"
  customerName: string | null,
  vehicleModel: string | null,
  regNumber: string | null,
  lastServiceDate: string | null,
  nextDueDate: string | null,
  bookingDate: string | null,
  bookingTime: string | null,
  bookingLocation: 'Lalbagh' | 'Jayanagar' | null,
  languageChosen: string | null,
  languageRequested: string | null,     // e.g. "Hindi" when not supported
  competitorLocation: string | null,    // where they went instead
  isVoicemail: boolean,
  isLanguageBarrier: boolean,
  isAlreadyServiced: boolean,
  isBooked: boolean,
  isDeferred: boolean,
  isNotInterested: boolean,
  isCallbackRequested: boolean,
  callbackTime: string | null,
  isCustomerBusy: boolean,
  isAudioIssue: boolean,
  isSoldVehicle: boolean,
  isWrongPerson: boolean,
  isEscalated: boolean,
  isNoResponse: boolean,
  isDissatisfied: boolean,
  isDisconnected: boolean,
  isAiQuestion: boolean,
  rawOutcomeCategory: string,          // best matched outcome category
  confidence: number                   // 0-1 match confidence
}
```

### 3.2 Disposition Taxonomy Maps

```
DISPOSITIONS_PRE  -- 50+ categories with keywords, intent, action fields
DISPOSITIONS_POST -- 40+ categories with keywords, intent, action fields
```

Each entry format:
```javascript
'Already Serviced': {
  keywords: [
    'already serviced', 'service already completed', 'service already done',
    'already done', 'already completed', 'already serviced elsewhere',
    'bike was recently serviced', 'bike had already been serviced',
    'service had already been completed'
  ],
  intent: 'negative',
  action: 'dead'
}
```

### 3.3 Full classification pipeline

```
For each row:
  1. Parse SUMMARY with parseSummary() -> structured call data
  2. Match DISPOSITION_DETAILS / UPDATED_DISPOSITION against taxonomy keywords
  3. If no match, fall back to SUMMARY parsed outcome category
  4. If still no match, fall back to STATUS / OUTCOME column
  5. Store: { category, intent, action, confidence, summaryParsed, sourceFields }
```

---

## 4. Analysis Engine Functions

### 4.1 `analyzeConversionFunnel(data, classified)`

Builds and explains the full conversion funnel with drop-off reasons.

- Funnel stages: Total -> Connected -> Booked/Converted
- Drop-off reasons: group non-converting rows by summaryParsed.rawOutcomeCategory
- Extract competitor names from summaryParsed.competitorLocation
- Count how many went to each competitor

**Sample narrative:**
> "96 leads -> 65 connected (68%) -> 12 booked (18% conversion). Of 53 connected but not booked: 15 already serviced elsewhere (incl. 3 at Shady Island Motor, 2 at Miles), 14 deferred/will decide later, 9 not interested, 6 requested callback, 5 language barrier, 4 audio issues."

### 4.2 `analyzeDispositionPatterns(classified)`

Category distribution with intent grouping.

**Sample narrative:**
> "'Already serviced elsewhere' (15) and 'Deferred / decide later' (14) are the top outcomes. 22% of calls resulted in voicemail. Only 12.5% booked service. 5% had audio issues blocking communication."

### 4.3 `analyzeInvalidLeadBreakdown(classified, rows)`

Detailed breakdown of invalid/unreachable lead reasons.

**Sample narrative:**
> "8 invalid leads: 3 wrong contact numbers, 2 vehicles sold/given away, 2 wrong person/not decision maker, 1 unsubscribed/DND request."

### 4.4 `analyzeDecisionPipeline(classified)`

Groups by decision timeframe using parsed callbackTime, bookingDate, and deferred patterns.

Time buckets: Immediate (booked), This week (1-3d), Next week (4-7d), Two weeks (8-14d), Month+ (15-30d), Unknown

**Sample narrative:**
> "Service decision pipeline: 12 booked, 5 will decide within 1-3 days, 8 within 4-7 days, 3 within 8-14 days, 6 within 15-30 days. 22 active opportunities."

### 4.5 `analyzeAgentPerformance(classified)`

Extracts agent names from summaryParsed.agentName, groups by agent.

**Sample narrative:**
> "Agent Lakshmi handled 78 calls (connected: 68%, booked: 15%). Agent Priya handled 12 calls (connected: 58%, booked: 8%). Lakshmi outperforms by 10pp in connection rate and 7pp in booking rate."

### 4.6 `analyzeCallbackBehavior(classified)`

Callback request volume, timing preferences, reattempt tracking.

**Sample narrative:**
> "6 customers requested callback. Timing: 2 said 'call back in 30 min', 1 said 'call after 7 PM', 1 said 'call tomorrow morning'. Only 2 had reattempt records."

### 4.7 `analyzeLanguageBarriers(classified)`

Mines language-related patterns from SUMMARY.

**Sample narrative:**
> "Language mismatch flagged in 5 calls: 3 requested Hindi (not supported), 1 preferred only Hindi/Kannada, 1 requested Tamil. Language support gap costs ~5% of potential connections."

### 4.8 `analyzeCompetitiveLosses(classified)`

Extracts competitor service center names from summaryParsed.competitorLocation.

**Sample narrative:**
> "15 customers serviced elsewhere. Known competitors: Shady Island Motor (3), Miles (2), General Electric (1), Yellanka Newton (1), Garth Motors Yamaha (1), Chandan Yamaha (1). 5 unspecified."

### 4.9 `analyzeSentimentFromTranscript(classified)`

Sentiment detection from SUMMARY texts.

**Sample narrative:**
> "Transcript sentiment: 78% neutral, 14% positive, 8% negative. 3 calls contained complaints. 12 callers expressed willingness to visit/come in."

### 4.10 `analyzeCallPatterns(rows)`

Day-of-week distribution, peak days, anomalies.

**Sample narrative:**
> "Calls peaked on Wednesdays (28 calls, 20% of weekly total). Saturdays saw lowest volume (4 calls). Wednesday had 3.5x more activity than Tuesday."

### 4.11 `detectAnomalies(classified, dailyCounts)`

Statistical anomaly detection across dimensions.

**Sample narrative:**
> "3 anomalies: (1) 5 Mar had 48 calls, 2.7x daily avg of 18. (2) 'Already serviced' spiked to 40% on 7 May (vs 15% avg)."

### 4.12 `generateExecutiveSummary(allInsights, metrics)`

Combines all analytic outputs into a single premium narrative.

**Sections:** Campaign overview -> Connection & conversion rates -> Top 5-6 insights -> Key problems -> Recommendations

**Sample narrative:**
> "This Perfect Riders post-sales campaign processed 96 leads over 14 days (28 Apr - 11 May). Connected rate: 68% (65/96). Service booked: 12 (18% conversion from connected). Pipeline: 37 active opportunities (5 this week, 8 next week, 6 within month). 15 leads already serviced elsewhere -- competitors include Shady Island Motor, Miles, and General Electric. Language barrier affected 5 calls. Agent Lakshmi leads performance (68% connected, 15% booked). Recommended: SMS re-engagement for 22 deferrals, competitive callback for 15 lost leads, check campaign source for 3 wrong numbers."

### 4.13 `computeHealthScore(metrics, insights)`

0-100 campaign health score:
- Connected rate: 30 pts
- Booking/conversion rate: 30 pts
- Invalid lead rate: 15 pts (inverted)
- Callback deficit: 15 pts (inverted)
- Pipeline volume: 10 pts

Score: >=75 green, 50-74 amber, <50 red

---

## 5. New HTML Sections (in order within #dashboardContent)

### 5.1 Executive Summary Banner #execSummary
- Hero card with glass-morphism, 4px left accent border (green/amber/red)
- Title + narrative paragraph + health score badge

### 5.2 Insight Alert Chips #insightStrip
- Horizontal flex row, max 6 pills, color-coded by severity

### 5.3 Conversion Funnel #conversionFunnel
- 3-stage visual funnel with drop-off reasons below

### 5.4 Disposition Intelligence Panel #dispositionIntelligence
- Top 12 categories as horizontal bars, color by intent

### 5.5 Decision Pipeline Visual #decisionPipeline
- Timeline buckets: Booked -> This Week -> Next Week -> 2 Weeks -> Month+ -> Unknown

### 5.6 Lead Quality Scorecard #leadQualityScorecard
- 3-card grid: wrong numbers / sold & wrong person / duplicates

### 5.7 Anomaly Alerts #anomalySection
- Cards per anomaly with severity, description, suggested action

### 5.8 Competitive Intelligence Panel #competitiveIntel
- Competitor names + counts + market share bar

### 5.9 Language & Quality Panel #languageQuality
- Language breakdown, audio issues, disconnects

---

## 6. JavaScript Implementation Order

### Phase 1: Data Structures
1. `parseSummary(text)` -- SUMMARY parser
2. `DISPOSITIONS_PRE` -- Pre-sales taxonomy
3. `DISPOSITIONS_POST` -- Post-sales taxonomy
4. `classifyRow(row, mode, colMap)` -- Row classifier
5. `classifyAllRows(rows, mode)` -- Batch classifier

### Phase 2: Analysis Functions
6. `analyzeConversionFunnel(classified)`
7. `analyzeDispositionPatterns(classified)`
8. `analyzeInvalidLeadBreakdown(classified, rows)`
9. `analyzeDecisionPipeline(classified)`
10. `analyzeAgentPerformance(classified)`
11. `analyzeCallbackBehavior(classified)`
12. `analyzeLanguageBarriers(classified)`
13. `analyzeCompetitiveLosses(classified)`
14. `analyzeSentimentFromTranscript(classified)`
15. `analyzeCallPatterns(rows, colMap)`
16. `detectAnomalies(classified, dailyCounts)`
17. `generateExecutiveSummary(insights, metrics)`
18. `computeHealthScore(metrics, insights)`

### Phase 3: Render Functions
19. `renderExecutiveSummary(summary)`
20. `renderInsightStrip(insights)`
21. `renderConversionFunnel(funnel)`
22. `renderDispositionIntelligence(patterns)`
23. `renderAgentPerformance(agents)`
24. `renderDecisionPipeline(pipeline)`
25. `renderLeadQualityScorecard(lq)`
26. `renderAnomalySection(anomalies)`
27. `renderCompetitiveIntel(competitors)`
28. `renderLanguageQuality(langData)`

### Phase 4: Integration in generateDashboard()
Modified flow:
```
classify all rows ->
  13 analysis functions ->
  compute health score ->
  render exec summary ->
  render insight strip ->
  render KPIs (existing) ->
  render funnel ->
  render disposition ->
  render agent performance ->
  render pipeline ->
  render lead quality ->
  render anomalies ->
  render competitive intel ->
  render language quality ->
  render charts (existing) ->
  render pending panel (existing)
```

---

## 7. Edge Cases & Guardrails

| Scenario | Handling |
|---|---|
| No SUMMARY column | SUMMARY parser skipped; uses disposition columns only |
| No taxonomy match | Tagged 'Unclassified' |
| Zero invalid leads | Scorecard hidden |
| Zero anomalies | Anomaly section hidden |
| Single agent detected | Agent panel hidden |
| No competitors found | Competitive intel hidden |
| < 10 rows | Insights with "limited sample" disclaimer |
| All voicemail | Executive summary flags red critical |
| Empty SUMMARY on all rows | Classification via disposition columns still works |
| "Summary couldn't be generated" | Treated as empty |

---

## 8. Files Modified

Only `dashboard.html` (existing ~2854 lines):

| Area | Lines Added |
|---|---|
| CSS styles | ~+450 |
| Taxonomy maps | ~+150 |
| SUMMARY parser | ~+80 |
| Analysis engine | ~+500 |
| Render functions | ~+400 |
| HTML sections | ~+150 |
| Integration code | ~+30 |
| **Total** | **~+1760** |
