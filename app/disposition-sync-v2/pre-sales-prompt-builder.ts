import { INJECTION_GUARD, USER_DATA_DELIMITER, USER_DATA_END_DELIMITER } from '@/lib/ai/ai-config';

export const ALL_DISPOSITIONS: Record<string, string> = {

  // ── Pre-Sales (Canonical AutoBot Master Taxonomy + Legacy Aliases) ──

  "Converted": "The customer completes the purpose of the campaign and provides the necessary information. KEY PHRASES: \"I will come in for the service\", \"please book my appointment\", \"yes I am interested please schedule it\", \"I want to book a service appointment\", \"please confirm my booking\", \"I will come to the service center tomorrow\", \"yes please go ahead and schedule the service\", \"I would like to avail this service\", \"book my slot for next week\", \"I am ready to come in for the service\", \"yes please proceed with the booking\", \"I am coming to the workshop this weekend\", \"I want to schedule a service visit\", \"I will be there at the appointed time\", \"thank you I will come for the service\"",

  "Feedback Provided": "The customer provides feedback, rating, or review about the vehicle, dealership, or inquiry experience. KEY PHRASES: \"I want to give feedback\", \"service was good\", \"rating is 5 stars\", \"feedback about sales team\", \"overall experience was satisfactory\", \"my review of the dealership\"",

  "Test Drive Booked": "The customer successfully books or confirms a specific test drive slot with date and time. KEY PHRASES: \"test drive booked for tomorrow\", \"book test drive for Saturday 10 AM\", \"I have scheduled a test drive\", \"test drive slot confirmed\", \"booked test drive for this weekend\"",

  "Showroom Visit Booked": "The customer explicitly confirms a showroom visit with both date and time. KEY PHRASES: \"I will visit the showroom tomorrow at 11 AM\", \"booked showroom visit for Saturday\", \"I am coming to the showroom on Friday afternoon\", \"confirmed visit to dealership at 4 PM\", \"schedule visit for tomorrow morning\"",

  "Showroom Visit Planned": "The customer agrees or plans to visit the showroom, but the exact date and time are not yet confirmed. KEY PHRASES: \"I have a visit planned to the showroom\", \"I plan to visit next week\", \"I am scheduled to visit sometime soon\", \"I am coming to the showroom soon\", \"my visit is planned for next week\", \"I will drop by your dealership soon\"",

  "Will decide later, will purchase within 15 days": "The customer said they would decide to buy the vehicle within 15 days. KEY PHRASES: \"I will decide in a couple of days\", \"give me 2 to 3 days to decide\", \"I will get back to you in a few days\", \"I need 2 days to think about it\", \"let me check and I will call you back in 2 days\", \"I will decide within the next 3 days\", \"give me some time, I will let you know in 2 to 3 days\", \"I will confirm in a day or two\", \"I need a few days to decide on this\", \"I will let you know in about 3 days\", \"I will decide in the next few days\"",

  "Will decide later, will purchase within 1 to 3 months": "The customer said they would decide to buy the vehicle within 1 to 3 months. KEY PHRASES: \"I will decide in about a month\", \"give me a month's time to decide\", \"I will get back to you in 3 to 4 weeks\", \"I need about 20 days to decide\", \"I will confirm in a month\", \"I will decide within the next month\", \"call me after a month I will have an answer\", \"I need about 30 days to check and confirm\", \"I will decide in around 3 weeks to a month\", \"give me a month to think it over\", \"I will decide in about 2 months\", \"call me after 2 months I will decide then\"",

  "Will decide later, exploring options": "The customer said they will decide on the purchase of the vehicle at a later time and are only exploring all their options now. KEY PHRASES: \"I am just looking around\", \"I am exploring all my options\", \"I haven't decided yet\", \"I am still considering my choices\", \"I will think about it and let you know\", \"I need to compare first\", \"I am not ready to commit yet\", \"just browsing for now\", \"I will let you know later when I decide\", \"I am gathering information before deciding\"",

  "Just Exploring": "The customer only wants to know about the vehicle but does not show active intent to buy. KEY PHRASES: \"I am just exploring\", \"I just want to know about the vehicle\", \"I am checking options\", \"I do not show intent to buy\", \"I am only looking for information\", \"just browsing, not buying now\", \"I am in the early stages of research\"",

  "Will call showroom themselves": "The customer will contact the dealership or showroom themselves directly. KEY PHRASES: \"I will call the showroom myself\", \"I will contact the dealership directly\", \"let me reach out to them on my own\", \"I will call them myself\", \"I do not need you to call, I will call them\", \"I prefer to call the showroom directly\", \"I will call the sales team myself\"",

  "Requested Callback": "The customer asked to call back at a later date or specific time (same day or week). KEY PHRASES: \"requested a callback\", \"requested callback\", \"callback requested\", \"asked for a callback\", \"customer requested a callback\", \"requested a callback at a more convenient time\", \"initiated a follow-up call\", \"follow-up call\", \"call me back sometime later\", \"please call me after some time\", \"call me in the evening\", \"can you call back tomorrow\", \"please call me next week\", \"I am busy right now call me later\", \"call me after an hour\", \"please call again in some time\", \"I am in a meeting call me later\", \"call me back in the afternoon\", \"can you call after two days\", \"I am occupied call me later\", \"please call me after 6 PM\", \"I will be free later call me then\", \"call me back at this time tomorrow\", callback, call back later",

  "Follow Up Required": "The customer shows interest but needs follow up next week or later to convince them. KEY PHRASES: \"I need to think about it\", \"I will consider and get back to you\", \"can you call me again next week\", \"I need to discuss with my family first\", \"not ready to decide yet, please follow up\", \"send me more information first\", \"I am interested but need more details\"",

  "Purchased elsewhere": "The customer already purchased a vehicle elsewhere. KEY PHRASES: \"I already purchased a car from another dealer\", \"I already bought a vehicle elsewhere\", \"I purchased a car from a different showroom\", \"already purchased from another brand\", \"already bought, not interested anymore\", \"I already made the purchase elsewhere\", \"I already have a car from another dealer\"",

  "Enquired for Pricing": "The customer asked for the price, on-road price, offers, or discounts of the vehicle. KEY PHRASES: \"what is the price of the vehicle\", \"how much does it cost\", \"what is the pricing\", \"I want to know the price\", \"can you tell me the cost\", \"what is the price range\", \"do you have a price list\", \"how much is the car\", \"what is the on-road price\"",

  "Enquired for Offers": "The customer asked about current offers, discounts, festive schemes, or special deals on the vehicle. KEY PHRASES: \"what are the offers\", \"any discounts available\", \"are there any offers\", \"what is the special offer\", \"discount schemes\", \"festive offers available\", \"any cash benefits\"",

  "Enquired for EMI": "The customer asked about EMI, down payment, loan schemes, interest rates, or financing options. KEY PHRASES: \"what is the EMI\", \"how much is the down payment\", \"do you have loan options\", \"what is the monthly installment\", \"interest rate on car loan\", \"finance schemes available\", \"what will be the EMI per month\"",

  "Enquired for Specifications": "The customer asked for the specifications, mileage, engine, or features of the vehicle. KEY PHRASES: \"what are the specifications\", \"tell me about the features\", \"what is the mileage\", \"what engine does it have\", \"what is the fuel type\", \"does it have automatic transmission\", \"what is the seating capacity\", \"what are the safety features\", \"I want to know the specs\"",

  "Enquired for Test Drive": "The customer asked for a test drive or wanted to experience the vehicle. KEY PHRASES: \"can I book a test drive\", \"I want to schedule a test drive\", \"when can I take a test drive\", \"is a test drive available\", \"I would like to test drive the car\", \"how do I book a test drive\", \"I want to experience the vehicle first\"",

  "Enquired for Showroom Visit": "The customer asked about visiting the showroom or showroom timings. KEY PHRASES: \"can I visit the showroom\", \"I want to come to the showroom\", \"when is the showroom open\", \"I would like to see the car at the showroom\", \"can I come see the vehicle\", \"I want a showroom visit\", \"when can I visit your dealership\"",

  "Enquired for Brochure": "The customer asked for a brochure, catalog, or spec sheet. KEY PHRASES: \"can I get a brochure\", \"send me the brochure please\", \"I want the vehicle brochure\", \"where can I download the brochure\", \"I need a brochure for this car\", \"brochure please\", \"share the brochure link\"",

  "Enquired for Dealership Details": "The customer asked for dealership address, location, or contact info. KEY PHRASES: \"what is your dealership address\", \"where is your showroom located\", \"can you give me the dealership contact\", \"what are your opening hours\", \"how do I reach your showroom\", \"I need the dealership location\", \"give me the showroom address\"",

  "Interested in another car same dealership": "The customer is interested in a different vehicle model from the same dealership. KEY PHRASES: \"I am interested in a different model\", \"I want to know about another car from your showroom\", \"I am looking for a different vehicle\", \"not this model but I am interested in another one\", \"I want to see the other model you have\", \"I am interested in a different variant\", \"show me another model from your dealership\", \"I am looking for a different car than this one\", \"I want information about another vehicle you sell\", \"I am interested in a different car from your showroom\", \"not this one, I like another model from your brand\"",

  "Enquired for Car Exchange": "The customer asked about vehicle trade-in, evaluation, or exchange bonus offers. KEY PHRASES: \"can I exchange my old car\", \"do you offer exchange\", \"what is the exchange bonus\", \"I want to trade in my old vehicle\", \"car evaluation for exchange\", \"exchange offer available\", \"value of my old vehicle\"",

  "Enquired for Stock & Availability": "The customer asked about vehicle stock availability, waiting period, or delivery timeline. KEY PHRASES: \"is this model available in stock\", \"what is the waiting period\", \"when can I get delivery\", \"do you have ready stock\", \"which colors are in stock\", \"how long for delivery\"",

  "Comparing with another brand": "The customer is comparing the vehicle with another brand or competitor. KEY PHRASES: \"I am comparing this with another brand\", \"I am also looking at other brands\", \"how does this compare to Brand X\", \"I am considering other options too\", \"I want to compare before deciding\", \"I am looking at competitors as well\"",

  "Customer Busy": "The customer was busy and could not speak at that moment without giving a callback time. KEY PHRASES: \"I am busy right now\", \"I am in a meeting\", \"I am driving at the moment\", \"I am at work can't talk\", \"I am currently occupied\", \"I am in the middle of something\", \"I am not free now\", \"this is not a good time\", \"I am with a client right now\", \"I am in a conference\", \"I am on the other line\", \"I cannot talk I am busy\", \"I am attending to something urgent\", \"I am in a class right now\"",

  "Call Disconnected": "Live interaction was established, but the customer disconnected early or hung up abruptly. KEY PHRASES: \"call got disconnected\", \"customer hung up\", \"line went dead\", \"the call dropped\", \"the line disconnected suddenly\", \"we lost the connection\", \"the call cut off\", \"I got disconnected\", \"the network dropped the call\", \"the call got cut in between\", \"we were talking and then it disconnected\", \"the line broke\", \"call ended unexpectedly\", \"suddenly the call ended\"",

  "Agent Disconnected Call": "The agent or system disconnected early due to flow boundary or silence. KEY PHRASES: \"call ended by agent\", \"system ended call\", \"call timed out\", \"disconnected by system\"",

  "General Inquiry": "The customer asked generic questions not specific to the vehicle campaign. KEY PHRASES: \"can you tell me more about the company\", \"what does your company do\", \"how can I reach you\", \"do you have a website\", \"what is your customer care number\", \"general questions about the brand\", \"I want to know about your services in general\"",

  "Not Interested": "The customer explicitly said they are not interested in the vehicle. KEY PHRASES: \"I am not interested in this offer\", \"I have no interest in buying right now\", \"don't need any car\", \"I am not looking for any vehicle\", \"I am not interested please don't call\", \"I don't want this\", \"I have no interest in anything from you\", \"I am not interested in anything you are offering\", \"this does not interest me\", \"not interested in any sales campaign\", \"please don't waste my time I am not interested\"",

  "No buying intent": "The customer does not want to purchase a car nor are they interested in the car. KEY PHRASES: \"I do not want to purchase a car\", \"I have no intention of buying\", \"I am not looking to buy a car\", \"no buying intent at all\", \"I have no interest in purchasing a car\", \"I do not plan to buy a car\", \"I am not in the market for a car right now\"",

  "Lost to Competition": "The customer bought a competitor brand's vehicle. KEY PHRASES: \"I already bought from a competitor\", \"I purchased a different brand\", \"I went with another manufacturer\", \"I bought a car from Brand X instead\", \"I chose another brand over yours\", \"I already have a vehicle from your competitor\", \"I made the purchase with another dealer\"",

  "Purchase Postponed": "The customer indicates that the purchase has been postponed. KEY PHRASES: \"I will buy later not now\", \"my purchase is postponed\", \"I am delaying the purchase\", \"I will buy after some months\", \"not buying right now, maybe later\", \"the purchase has been deferred to next quarter\", \"I will purchase once I have the funds ready\"",

  "Invalid Lead": "The customer is not a valid lead or wrong number. KEY PHRASES: \"this is not a valid number\", \"the number is not reachable\", \"I don't know anything about this\", \"there is no such person here\", \"this lead is incorrect\", \"the information you have is wrong\", \"I don't have any vehicle from this brand\", \"I never owned such a car\", \"this number is not associated with any service\", \"the details you have are outdated and wrong\", \"this is an invalid record\", \"I have no relation to this vehicle\"",

  "Voicemail": "If the call reached voicemail, IVR greeting, or automated system. KEY PHRASES: \"please leave a message\", \"your call is very important to us\", \"the person you are trying to reach is not available\", \"please leave your name and number\", \"we will get back to you as soon as possible\", \"you have reached the voicemail of\", \"please call back later\", voicemail greeting, automated message, recording prompt",

  "No Response": "The customer did not speak or respond at all. KEY PHRASES: the customer remained completely silent, did not respond, no answer on the call, complete silence on the line, customer did not speak a single word, dead air during the call, customer did not acknowledge, no verbal response from the customer",

  "Language barrier": "The customer asked to speak in a different language and the conversation could not finish. KEY PHRASES: \"I do not understand what you are saying\", \"can you speak in Hindi\", \"I speak Telugu only\", \"please talk in Kannada\", \"I cannot follow English\", \"main Hindi mein baat karta hoon\", \"nenu Telugu lo matladatha\", \"do you speak Tamil\", \"I don't know this language\", \"I can't understand you\", \"please get someone who speaks Malayalam\", \"I need to speak in my language\", \"I am not comfortable in English\", \"speak slower I don't understand\", \"what language are you speaking?\"",

  "Audio Issue": "There were technical audio issues hearing either party. KEY PHRASES: \"I cannot hear you properly\", \"your voice is breaking\", \"you are sounding very distant\", \"I am not able to hear clearly\", \"there is a lot of disturbance\", \"I can barely hear you\", \"the audio is not clear\", \"your voice is cutting in and out\", \"speak louder I can't hear\", \"there is an echo on the line\", \"I cannot hear what you are saying\", \"the audio is very poor\", \"I am struggling to hear your voice\", \"you are breaking up I can't hear\"",

  "Talk to Human": "The customer asked to speak to a human executive. KEY PHRASES: \"I want to talk to a real person\", \"can you connect me to a human executive\", \"I need to speak with a customer service representative\", \"please transfer me to an actual person\", \"I don't want to talk to a machine\", \"connect me to a human agent please\", \"I need to speak with someone who can help directly\", \"can I talk to a live person\", \"I want to speak with a customer care executive\", \"please connect me to your support team\", \"I need a human to help me with this\", \"let me speak to your manager\", \"I want to talk to a real human being\", \"transfer me to a customer service agent\"",

  "Is not decision maker": "The customer said they are not the right person to speak to in their family. KEY PHRASES: \"I am not the owner of the vehicle\", \"the car belongs to my father\", \"my husband handles all car matters\", \"someone else takes care of the vehicle\", \"I cannot decide about this\", \"you need to speak to the owner\", \"this is not my vehicle to decide on\", \"I don't handle the car maintenance\", \"my son takes care of the car\", \"the vehicle is registered under my wife's name\", \"I am just the driver\", \"the decision maker is not here\", \"I have no authority to book service\", \"you need to talk to the person who owns the car\"",

  "Test Drive Completed": "The customer already completed a test drive. KEY PHRASES: \"I already did the test drive\", \"I have already taken a test drive\", \"test drive was completed last week\", \"I already experienced the vehicle\", \"I have already driven the car\", \"test drive completed with your dealership\"",

  "Rejected": "The customer repeatedly rejected the offer or refused to speak. KEY PHRASES: \"I am not interested in this\", \"please stop calling me\", \"do not call me again\", \"I do not want this service\", \"I already said no\", \"how many times do I have to say no\", \"I told you I am not interested\", \"please remove my number\", \"I don't need anything from you\", \"stop wasting my time\", \"I am not going to take this service\", \"do not contact me anymore\", \"I have no requirement at this time\", \"not now and not ever\"",

  "Enquired for Others": "The customer asked for other details not listed above. KEY PHRASES: \"I have another question\", \"can I ask about something else\", \"I need other information\", \"I want to know about something different\", \"this is not what I was looking for, I need...\"",

  "Others": "All other disposition details not listed above. KEY PHRASES: any other response that does not match any of the above dispositions exactly, miscellaneous responses, unique situations not covered by other categories. NOTE: NEVER use 'Others' if the summary or conversation indicates a callback was requested ('Requested Callback'), customer was busy, test drive booked, or showroom visit planned.",
};

export interface AiValidationCandidate {
  index: number;
  summary: string;
  history: string;
  currentDisp: string;
  model: string;
  outcome: string;
  callDuration: string;
  leadSource: string;
}

export interface LlmParseResult {
  rowIndex: number;
  isCorrect: boolean;
  correctedDisposition: string | null;
  preferredShowroom: string | null;
  confidence: string;
  reason: string;
}

export function buildPreSalesValidationPrompt(
  batch: AiValidationCandidate[],
  batchIndex: number,
  batchSize: number,
): { system: string; user: string; temperature: number; maxTokens: number } | null {
  if (!batch.length) return null;

  const dispDefs = Object.keys(ALL_DISPOSITIONS).map(k => `- "${k}": ${ALL_DISPOSITIONS[k]}`).join('\n');

  const promptLines = batch.map((c, idx) => {
    const safeSummary = sanitizeForPrompt(c.summary);
    const safeHistory = sanitizeForPrompt(c.history);
    const safeDisp = sanitizeForPrompt(c.currentDisp);
    const safeModel = sanitizeForPrompt(c.model);
    const safeOutcome = sanitizeForPrompt(c.outcome);
    const safeDuration = sanitizeForPrompt(c.callDuration);
    const safeSource = sanitizeForPrompt(c.leadSource);

    let line = `Row ${idx}:`;
    if (safeSummary) line += `\n--- BEGIN SUMMARY ---\n${safeSummary}\n--- END SUMMARY ---`;
    if (safeHistory) line += `\n--- BEGIN CONVERSATION HISTORY ---\n${safeHistory}\n--- END CONVERSATION HISTORY ---`;
    line += `\nCurrent Disposition: "${safeDisp}"`;
    if (safeModel) line += `\nVehicle Model: "${safeModel}"`;
    if (safeOutcome) line += `\nCall Outcome: "${safeOutcome}"`;
    if (safeDuration) line += `\nCall Duration: "${safeDuration}"`;
    if (safeSource) line += `\nLead Source: "${safeSource}"`;
    return line;
  }).join('\n\n---\n\n');

  const systemMsg = `You are a fair and accurate disposition auditor for automotive Pre-Sales campaigns. Your job is to evaluate whether the "Current Disposition" accurately describes the call. You are provided with two evidence sources: 1) a Summary (short description), and 2) a Conversation History (full transcript with timestamps). The Conversation History is the STRONGEST evidence if it is detailed and clear. However, if the Conversation History is empty, extremely short (e.g., just greeting exchange), or inconclusive, you MUST rely on the Summary and Current Disposition — do not flag them as incorrect unless there is a clear contradiction.
${INJECTION_GUARD}

General guidance for automotive outbound calls — use the KEY PHRASES to detect the correct disposition:`;

  const examples = `Example 1 (CORRECT):
Transcript: "Customer: Hello? Agent: Hello, I am calling from Yamaha to discuss the FZ vehicle. Customer: Yes, I am busy right now, call me in the evening. Agent: Sure, thank you."
Current Disposition: "Requested Callback"
→ isCorrect: true, correctedDisposition: null
Reason: The transcript clearly shows the customer asked for a callback, matching the disposition.

Example 2 (CORRECT - SHORT TRANSCRIPT):
Transcript: "Customer: Hello?"
Summary: "Spoke to customer Rajesh. He said he is not interested in buying a car right now and hung up."
Current Disposition: "Not Interested"
→ isCorrect: true, correctedDisposition: null
Reason: The transcript is too short/inconclusive, but the Summary explicitly states the customer is not interested, which matches the disposition.

Example 3 (CORRECT - EMPTY TRANSCRIPT):
Transcript: ""
Summary: "Voicemail. Left a message."
Current Disposition: "Voicemail"
→ isCorrect: true, correctedDisposition: null
Reason: Transcript is empty, but the Summary matches the disposition perfectly.

Example 4 (INCORRECT):
Transcript: "Customer: I will think about it and call you back next week."
Current Disposition: "Not Interested"
→ isCorrect: false, correctedDisposition: "Will decide later, exploring options"
Reason: Customer did not reject the offer — they deferred the decision. Not Interested is for explicit refusal.

Example 5 (INCORRECT):
Transcript: "Customer: How much does the FZ model cost? Agent: It is 1.2 Lakhs. Customer: Can you send details?"
Current Disposition: "General Inquiry"
→ isCorrect: false, correctedDisposition: "Enquired for Pricing"
Reason: Customer specifically asked for pricing/costs, so "Enquired for Pricing" is more specific and accurate than "General Inquiry".

Example 6 (INCORRECT):
Transcript: "Customer: The vehicle is too expensive, I will buy a Honda instead."
Current Disposition: "Rejected"
→ isCorrect: false, correctedDisposition: "Comparing with another brand"
Reason: Customer is comparing the model with a competitor brand, so "Comparing with another brand" is the most specific disposition.

Example 7 (INCORRECT):
Transcript: "Agent: Hello? Customer: Hello. [Call disconnected/dropped]"
Current Disposition: "Follow Up Required"
→ isCorrect: false, correctedDisposition: "Call Disconnected"
Reason: The call disconnected abruptly. "Call Disconnected" is the correct status, rather than "Follow Up Required".

Example 8 (CORRECT):
Transcript: "Customer: I already bought a Pulsar last week from another dealer."
Current Disposition: "Purchased elsewhere"
→ isCorrect: true, correctedDisposition: null
Reason: The transcript confirms the customer bought the vehicle elsewhere, matching the disposition.

Example 9 (KEY PHRASE MATCHING — CORRECT):
Transcript: "Customer: I am just looking around, I haven't decided yet."
Current Disposition: "Will decide later, exploring options"
→ isCorrect: true, correctedDisposition: null
Reason: The transcript contains KEY PHRASES "I am just looking around" and "I haven't decided yet" which both belong to "Will decide later, exploring options". This is a direct KEY PHRASES match.

Example 10 (KEY PHRASE MATCHING — INCORRECT):
Transcript: "Customer: I already bought a car from a different showroom last week."
Current Disposition: "Not Interested"
→ isCorrect: false, correctedDisposition: "Purchased elsewhere"
Reason: The transcript contains KEY PHRASES "I already bought a car" and "from a different showroom" which belong to "Purchased elsewhere", not "Not Interested". The KEY PHRASES match is the decisive signal.`;

  const userPrompt = `VALID DISPOSITIONS:\n${dispDefs}\n\nEXAMPLES (learn from these patterns):\n${examples}\n\nNow evaluate these rows. For EACH row, respond with ONE JSON object:\n{"rowIndex":0,"isCorrect":true,"correctedDisposition":null,"preferredShowroom":null,"confidence":"high","reason":"The summary clearly matches the disposition."}\n\nAlso include "preferredShowroom": the customer's preferred dealership showroom or branch location if explicitly mentioned in the summary or conversation transcript (e.g. "Bannerghatta Road", "Marathahalli"). Return null if not mentioned.\n\nRows:\n${USER_DATA_DELIMITER}\n${promptLines}\n${USER_DATA_END_DELIMITER}\n\nRespond as a JSON array of objects, one per row in the same order. ONLY valid JSON.`;

  return {
    system: systemMsg,
    user: userPrompt,
    temperature: 0.3,
    maxTokens: 1800,
  };
}

export function parseLlmResponse(text: string, batchIndex: number, batchSize: number): LlmParseResult[] {
  const parseItems = (items: any[]): LlmParseResult[] => {
    return items.map((item: any, idx: number) => ({
      rowIndex: (batchIndex * batchSize) + idx,
      isCorrect: Boolean(item.isCorrect),
      correctedDisposition: item.correctedDisposition || null,
      preferredShowroom: item.preferredShowroom || null,
      confidence: item.confidence || 'medium',
      reason: item.reason || '',
    }));
  };

  // Try direct JSON parse first
  let cleaned = text.trim();
  try {
    const fullParsed = JSON.parse(cleaned);
    if (Array.isArray(fullParsed)) return parseItems(fullParsed);
    if (typeof fullParsed === 'string') {
      const inner = JSON.parse(fullParsed);
      if (Array.isArray(inner)) return parseItems(inner);
    }
  } catch { /* fall through */ }

  // Strip markdown fences
  cleaned = cleaned.replace(/```(?:json)?\s*/gi, '').replace(/```/g, '').replace(/\\"/g, '"').trim();

  // Try JSON.parse on cleaned text
  try {
    const parsed = JSON.parse(cleaned);
    if (Array.isArray(parsed)) return parseItems(parsed);
  } catch { /* fall through */ }

  // Try to extract a JSON array via regex
  const match = cleaned.match(/\[[\s\S]*?\]/);
  if (match) {
    try {
      const parsed = JSON.parse(match[0]);
      if (Array.isArray(parsed)) return parseItems(parsed);
    } catch { /* fall through */ }
  }

  // Try line-by-line: scan for individual JSON objects
  const lines = cleaned.split('\n').filter(l => l.trim());
  const results: LlmParseResult[] = [];
  for (const line of lines) {
    try {
      const parsed = JSON.parse(line.trim());
      if (parsed && typeof parsed === 'object' && !Array.isArray(parsed)) {
        results.push({ rowIndex: (batchIndex * batchSize) + results.length, isCorrect: Boolean(parsed.isCorrect), correctedDisposition: parsed.correctedDisposition || null, preferredShowroom: parsed.preferredShowroom || null, confidence: parsed.confidence || 'medium', reason: parsed.reason || '' });
      }
    } catch { /* skip unparseable lines */ }
  }
  if (results.length > 0) return results;

  console.warn('[parseLlmResponse] Failed to parse LLM response for batch', batchIndex, 'text:', text.slice(0, 200));
  return [];
}

export function hashStr(str: string): string {
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    hash = ((hash << 5) - hash) + str.charCodeAt(i);
    hash |= 0;
  }
  return 'h' + Math.abs(hash).toString(36);
}

function sanitizeForPrompt(text: string): string {
  if (!text) return '';
  let s = String(text);
  s = s.replace(/[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]/g, '');
  s = s.replace(/"/g, "'");
  if (s.length > 2500) s = s.substring(0, 2500) + '...[truncated]';
  return s;
}
