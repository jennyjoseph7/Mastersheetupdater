import { INJECTION_GUARD, USER_DATA_DELIMITER, USER_DATA_END_DELIMITER } from '@/lib/ai/ai-config';
import { POST_SALES_DISPOSITIONS } from './post-sales-dispositions';

export interface AiValidationRow {
  summary: string;
  history: string;
  currentDisp: string;
  dealerName: string;
  supportedLanguages: string;
  vehicleModel: string;
  outcome: string;
  callDate: string;
  campaignId: string;
  rowIndex: number;
}

export function buildDispoValidationPrompt(rows: AiValidationRow[], batchIndex: number, batchSize: number): { system: string; user: string; temperature: number; maxTokens: number } | null {
  if (!rows.length) return null;

  const dispKeys = Object.keys(POST_SALES_DISPOSITIONS);
  const dispDefs = dispKeys.map(k => `- "${k}": ${POST_SALES_DISPOSITIONS[k]}`).join('\n');
  const dealerContext = `Dealership: "${rows[0]?.dealerName || ''}"\nSupported Languages: "${rows[0]?.supportedLanguages || ''}"`;

  const promptLines = rows.map((c, idx) => {
    const safeSummary = sanitizeForPrompt(c.summary);
    const safeHistory = sanitizeForPrompt(c.history);
    const safeDisp = sanitizeForPrompt(c.currentDisp);
    const safeDealer = sanitizeForPrompt(c.dealerName);
    const safeLangs = sanitizeForPrompt(c.supportedLanguages);
    const safeModel = sanitizeForPrompt(c.vehicleModel);
    const safeOutcome = sanitizeForPrompt(c.outcome);
    const safeDate = sanitizeForPrompt(c.callDate);
    const safeCampaign = sanitizeForPrompt(c.campaignId);

    let line = `Row ${idx}:`;
    if (safeSummary) line += `\n--- BEGIN SUMMARY ---\n${safeSummary}\n--- END SUMMARY ---`;
    if (safeHistory) line += `\n--- BEGIN CONVERSATION HISTORY ---\n${safeHistory}\n--- END CONVERSATION HISTORY ---`;
    line += `\nCurrent Disposition: "${safeDisp}"`;
    line += `\nDealership: "${safeDealer}"`;
    line += `\nSupported Languages: "${safeLangs}"`;
    if (safeModel) line += `\nVehicle Model: "${safeModel}"`;
    if (safeOutcome) line += `\nCall Outcome: "${safeOutcome}"`;
    if (safeDate) line += `\nCall Date: "${safeDate}"`;
    if (safeCampaign) line += `\nCampaign ID: "${safeCampaign}"`;
    return line;
  }).join('\n\n---\n\n');

  const systemMsg = `You are a fair and accurate disposition auditor for an automotive post-sales (service/feedback) campaign. Your job is to evaluate whether the "Current Disposition" accurately describes the call. You are provided with two evidence sources: 1) a Summary (short description), and 2) a Conversation History (full transcript with timestamps). The Conversation History is the STRONGEST evidence if it is detailed and clear. However, if the Conversation History is empty, extremely short (e.g., just greeting exchange), or inconclusive, you MUST rely on the Summary and Current Disposition — do not flag them as incorrect unless there is a clear contradiction. Be balanced: if the current disposition reasonably fits the call context, mark it as correct (isCorrect: true). Only flag isCorrect: false when there is a clear mismatch, contradiction, or a significantly more accurate disposition available.

IMPORTANT DISPOSITION RULES:
1. Generic dispositions like "contacted", "connected", "completed", "answered" are raw call statuses, NOT specific dispositions. If the summary or transcript indicates a specific outcome (such as customer requesting a callback, busy, serviced, etc.), you MUST set isCorrect: false and set correctedDisposition to the matching specific disposition (e.g. "Requested Callback").
2. NEVER classify a call as "Others" if the summary or transcript mentions a callback request, follow-up call, busy customer, service booking, or vehicle serviced. "Others" is strictly for situations with zero relevance to any other category.
${INJECTION_GUARD}

VALID DISPOSITIONS:
${dispDefs}

CONFIRMED DATE EXTRACTION & CALENDAR MATH:
For each row, extract the "confirmedDate" — the specific date the CUSTOMER explicitly states, agrees, or commits to come for service:
- ONLY dates the customer commits to (e.g., "I'll come on Saturday", "book me for August 5th", "will bring it tomorrow").
- Do NOT extract the service due date mentioned by the agent (e.g., "your service is due on...").
- Do NOT extract dates from agent reminders.
- If the customer says "already serviced" or gives no future commitment date, set confirmedDate to null.
- RELATIVE DATE RESOLUTION & CALENDAR MATH:
  Use the row's "Call Date" as the reference base date:
  * If customer says "tomorrow": calculate (Call Date + 1 day).
  * If customer says "day after tomorrow": calculate (Call Date + 2 days).
  * If customer mentions a day of the week (e.g., "Saturday", "this Monday", "Friday"): calculate the exact calendar date of the next upcoming occurrence of that weekday relative to the Call Date.
    Example: If Call Date is 17/09/2026 (Thursday), and customer says "I will visit on Saturday", calculate Saturday = 09/19/2026.
  * If customer says "after 3 days": calculate (Call Date + 3 days).
- Format: mm/dd/yyyy`;

  const examples = `Example 1 (CORRECT):
Transcript: "Customer: Yes, I already serviced my bike at your workshop last Friday. Agent: Great, thank you for confirming."
Current Disposition: "Vehicle Serviced"
→ isCorrect: true, correctedDisposition: null
Reason: Transcript confirms the vehicle was serviced at this dealership workshop.

Example 2 (CORRECT - SHORT TRANSCRIPT):
Transcript: "Customer: Hello?"
Summary: "Voicemail reached, left a callback message."
Current Disposition: "Voicemail"
→ isCorrect: true, correctedDisposition: null
Reason: Transcript is inconclusive, but the Summary matches the disposition perfectly.

Example 3 (INCORRECT):
Transcript: "Customer: I will bring the car next week on Saturday for service."
Current Disposition: "Not Interested"
→ isCorrect: false, correctedDisposition: "Will call workshop themselves"
Reason: Customer intends to service the vehicle — they did not refuse the service.

Example 4 (INCORRECT):
Transcript: "Customer: I sold my car last month to someone else."
Current Disposition: "Not Interested"
→ isCorrect: false, correctedDisposition: "Has sold/given away the car"
Reason: "Has sold/given away the car" is the specific and correct disposition, which is more accurate than "Not Interested".

Example 5 (CORRECT):
Transcript: "Customer: I am very busy right now, please call me tomorrow morning. Agent: Sure."
Current Disposition: "Requested Callback"
→ isCorrect: true, correctedDisposition: null
Reason: The customer explicitly requested a callback later, matching the disposition.

Example 6 (INCORRECT):
Transcript: "Customer: I already serviced my car at a local workshop nearby."
Current Disposition: "Vehicle Serviced"
→ isCorrect: false, correctedDisposition: "Has serviced car in another dealership"
Reason: "Vehicle Serviced" is only for servicing done under this dealership campaign. Servicing elsewhere matches "Has serviced car in another dealership".

Example 7 (INCORRECT):
Transcript: "Customer: Hello? I can't hear you, hello?" [Call dropped]
Current Disposition: "No Response"
→ isCorrect: false, correctedDisposition: "Audio Issue"
Reason: The call disconnected due to hearing/audio problems, so "Audio Issue" is correct.

Example 8 (KEY PHRASE MATCHING — CORRECT):
Transcript: "Customer: I am not interested in this offer, please stop calling me."
Current Disposition: "Not Interested"
→ isCorrect: true, correctedDisposition: null
Reason: The transcript contains KEY PHRASES "I am not interested in this offer" and "please stop calling me" which both belong to the "Not Interested" disposition definition. This is a direct KEY PHRASES match.

Example 9 (KEY PHRASE MATCHING — INCORRECT):
Transcript: "Customer: I already got the service done at another workshop."
Current Disposition: "Not Interested"
→ isCorrect: false, correctedDisposition: "Has serviced car in another dealership"
Reason: The transcript contains KEY PHRASES "I already got the service done at another workshop" which belongs to "Has serviced car in another dealership", not "Not Interested". The KEY PHRASES match is the decisive signal.

Example 10 (CALLBACK REQUEST IN SUMMARY — GENERIC DISPOSITION "contacted"):
Summary: "Neha from Keerthi Triumph previously called to speak with the intended customer, who requested a callback at a more convenient time. Neha has initiated a follow-up call from Keerthi."
Current Disposition: "contacted"
→ isCorrect: false, correctedDisposition: "Requested Callback"
Reason: The summary explicitly states that the customer requested a callback at a convenient time. Update generic disposition "contacted" to "Requested Callback", NEVER to "Others".

Example 11 (AGENT DUE DATE REMINDER — NO CONFIRMED DATE):
Summary: "Neha from Keerthi Triumph Service Centre called Akhilesh Singh to remind him that his vehicle is due for service on August 1, 2026, and asked for a convenient time to visit the workshop."
Current Disposition: "contacted"
→ isCorrect: false, correctedDisposition: "Follow Up Required", confirmedDate: null
Reason: "August 1, 2026" is the agent stating the service due date, NOT a confirmed date by the customer. The customer never committed to or confirmed a visit date. Therefore confirmedDate MUST be null.

Example 12 (PLACED ON HOLD / NO CONVERSATION):
Summary: "Neha from Keerthi Triumph called to speak with the intended customer, who requested that the call be placed on hold."
Current Disposition: "Requested Callback"
→ isCorrect: false, correctedDisposition: "Customer Busy"
Reason: The customer was busy and put the call on hold. There was no actual request for a callback, and no service discussion took place. "Customer Busy" is the correct disposition.

Example 13 (VISIT PLANNED MISCLASSIFIED AS CALLBACK):
Summary: "Neha from Keerthi Triumph Service Centre called to remind the customer that their vehicle is due for service on August 1, 2026. The customer indicated they would be available to visit the workshop later this week, possibly on Friday."
Current Disposition: "Requested Callback"
→ isCorrect: false, correctedDisposition: "Showroom Visit Planned"
Reason: The customer explicitly stated they will visit the workshop. This is a strong commitment, so "Showroom Visit Planned" is much more accurate than a generic callback.`;

  const userPrompt = `LANGUAGE BARRIER RULE:
The active dealership is "${dealerContext}". The customer's transcript/summary may be in a language different from the dealership's supported languages. If the customer requested or attempted to speak in a language NOT in the supported languages list for their dealership, the disposition MUST be "Language barrier". Pay close attention to phrases like "I don't understand", "speak [language]", "[language] please", etc. — especially if the requested language is outside the supported set. The supported languages are only those listed for the dealership; any other language the customer requests is a barrier.

EXAMPLES (learn from these patterns):
${examples}

Now evaluate these rows. For EACH row, respond with ONE JSON object:
{"rowIndex":0,"isCorrect":true,"correctedDisposition":null,"confirmedDate":null,"confidence":"high","reason":"The summary clearly matches the disposition."}

Rows:
${USER_DATA_DELIMITER}
${promptLines}
${USER_DATA_END_DELIMITER}

Respond as a JSON array of objects, one per row in the same order. ONLY valid JSON.`;

  return {
    system: systemMsg,
    user: userPrompt,
    temperature: 0.3,
    maxTokens: 1800,
  };
}

export function parseLlmResponse(text: string, batchIndex: number, batchSize: number, batch?: any[]): { rowIndex: number; isCorrect: boolean; correctedDisposition: string | null; confirmedDate: string | null; confidence: string; reason: string }[] {
  // Parse the LLM response text into structured result objects.
  // rowIndex is set to the sequential position in the full candidates array.
  const parseItems = (items: any[]): { rowIndex: number; isCorrect: boolean; correctedDisposition: string | null; confirmedDate: string | null; confidence: string; reason: string }[] => {
    return items.map((item: any, idx: number) => {
      let isCorrect = Boolean(item.isCorrect);
      let correctedDisposition = item.correctedDisposition || null;
      let confirmedDate = item.confirmedDate || null;
      let reason = item.reason || '';

      // ponytail: deterministic guard against LLM classifying callback requests as "Others" or keeping generic "contacted"
      if (batch && batch[idx]) {
        const row = batch[idx];
        const combined = `${row.summary || ''} ${row.history || ''}`.toLowerCase();
        const currentDisp = String(row.currentDisp || '').trim().toLowerCase();
        const isCallback = /\b(?:requested\s+a\s+callback|requested\s+callback|callback\s+requested|asked\s+for\s+(?:a\s+)?callback|call\s*back\s+at\s+a\s+more\s+convenient\s+time|customer\s+requested\s+(?:a\s+)?call\s*back|initiated\s+a\s+follow-up\s+call)\b/i.test(combined);

        if (isCallback && (correctedDisposition === 'Others' || currentDisp === 'contacted' || currentDisp === 'connected' || isCorrect)) {
          isCorrect = false;
          correctedDisposition = 'Requested Callback';
          if (!reason) reason = 'Summary indicates customer requested a callback; updated to Requested Callback.';
        }
      }

      return {
        rowIndex: (batchIndex * batchSize) + idx,
        isCorrect,
        correctedDisposition,
        confirmedDate,
        confidence: item.confidence || 'medium',
        reason,
      };
    });
  };

  // Try direct JSON parse first
  try {
    const fullParsed = JSON.parse(text);
    if (Array.isArray(fullParsed)) {
      return parseItems(fullParsed);
    }
    if (typeof fullParsed === 'string') {
      const inner = JSON.parse(fullParsed);
      if (Array.isArray(inner)) return parseItems(inner);
    }
  } catch {
    // fall through to regex
  }

  // Try to extract JSON array from markdown code block or raw text
  const cleaned = text.replace(/```json\s*/gi, '').replace(/```/g, '').trim();
  const unescaped = cleaned.replace(/\\"/g, '"');
  const match = unescaped.match(/\[[\s\S]*\]/);
  if (match) {
    try {
      const parsed = JSON.parse(match[0]);
      if (Array.isArray(parsed)) return parseItems(parsed);
    } catch {
      return [];
    }
  }
  return [];
}

function sanitizeForPrompt(text: string): string {
  if (!text) return '';
  let s = String(text);
  s = s.replace(/[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]/g, '');
  s = s.replace(/"/g, "'");
  if (s.length > 2500) s = s.substring(0, 2500) + '...[truncated]';
  return s;
}

export function hashStr(str: string): string {
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    hash = ((hash << 5) - hash) + str.charCodeAt(i);
    hash |= 0;
  }
  return 'h' + Math.abs(hash).toString(36);
}
