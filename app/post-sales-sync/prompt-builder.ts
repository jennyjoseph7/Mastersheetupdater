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
${INJECTION_GUARD}

VALID DISPOSITIONS:
${dispDefs}`;

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
Reason: The transcript contains KEY PHRASES "I already got the service done at another workshop" which belongs to "Has serviced car in another dealership", not "Not Interested". The KEY PHRASES match is the decisive signal.`;

  const userPrompt = `LANGUAGE BARRIER RULE:
The active dealership is "${dealerContext}". The customer's transcript/summary may be in a language different from the dealership's supported languages. If the customer requested or attempted to speak in a language NOT in the supported languages list for their dealership, the disposition MUST be "Language barrier". Pay close attention to phrases like "I don't understand", "speak [language]", "[language] please", etc. — especially if the requested language is outside the supported set. The supported languages are only those listed for the dealership; any other language the customer requests is a barrier.

EXAMPLES (learn from these patterns):
${examples}

Now evaluate these rows. For EACH row, respond with ONE JSON object:
{"rowIndex":0,"isCorrect":true,"correctedDisposition":null,"confidence":"high","reason":"The summary clearly matches the disposition."}

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

export function parseLlmResponse(text: string, batchIndex: number, batchSize: number): { rowIndex: number; isCorrect: boolean; correctedDisposition: string | null; confidence: string; reason: string }[] {
  // Parse the LLM response text into structured result objects.
  // rowIndex is set to the sequential position in the full candidates array.
  const parseItems = (items: any[]): { rowIndex: number; isCorrect: boolean; correctedDisposition: string | null; confidence: string; reason: string }[] => {
    return items.map((item: any, idx: number) => ({
      rowIndex: (batchIndex * batchSize) + idx,
      isCorrect: Boolean(item.isCorrect),
      correctedDisposition: item.correctedDisposition || null,
      confidence: item.confidence || 'medium',
      reason: item.reason || '',
    }));
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
