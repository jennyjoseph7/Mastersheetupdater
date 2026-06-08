/* ═══════════════════════════════════════════════════════════════════════
   disposition_sync_v2.js — Application logic for disposition_sync_v2.html
   Extracted from inline <script> in the HTML file.
   ═══════════════════════════════════════════════════════════════════════ */

// ─── STATE ───────────────────────────────────────────────────────────────────

    let rawFile1 = null;

    let rawFile2 = null;

    let processedData = [];

    let qualityReport = null;

    let isProcessing = false;

    function cancelAiValidation() {
      AiValidator.cancel();
    }

    // ─── PRIORITY TABLE ───────────────────────────────────────────────────────────

    const BUSINESS_CONFIG = {

      dispositionPriority: {

        'test drive booked': 10,

        'converted': 10,

        'not interested': 9,

        'dnd': 9,

        'wrong number': 9,

        'interested': 8,

        'callback requested': 6,

        'call back': 6,

        'busy': 4,

        'not connected': 3,

        'no revert': 3,

        'user did not speak': 2,

      },

      terminalThreshold: 9,

      connectedDispositions: ['contacted', 'reached', 'engaged', 'converted'],

      notConnectedDispositions: ['attempted', 'busy'],

      seatingRules: [

        { matches: ['basalt'], value: '5 Seater' },

        { matches: ['aircross', 'c3'], value: '5 Seater & 7 Seater' },

        { matches: ['meridian', 'jeep'], value: '5 Seater & 7 Seater' },

      ],

      validation: {

        file1RequiredGroups: [

          { label: 'Phone', candidates: ['phone_number', 'phone', 'mobile'] },

          { label: 'Disposition', candidates: ['disposition'] },

          { label: 'Updated date', candidates: ['updated', 'call_date'] },

        ],

        file1RecommendedGroups: [

          { label: 'Full name', candidates: ['person_name', 'full_name', 'name'] },

          { label: 'City', candidates: ['city'] },

          { label: 'Campaign ID', candidates: ['campaign_id'] },

          { label: 'Lead source', candidates: ['lead_source'] },

          { label: 'Summary detail', candidates: ['disposition_detail'] },

          { label: 'Lead summary', candidates: ['lead_summary'] },

          { label: 'Model', candidates: ['name', 'model_preference', 'interested_vehicle_name'] },

          { label: 'Cohort', candidates: ['campaign_objective_name'] },

          { label: 'Session ID', candidates: ['last_session_id', 'session_id'] },

        ],

        file2RecommendedGroups: [

          { label: 'Phone', candidates: ['phone_number', 'phone', 'mobile', 'contact', 'contact_number'] },

          { label: 'Date/time', candidates: ['created', 'start_time', 'date', 'timestamp', 'call_date'] },

          { label: 'Summary', candidates: ['summary', 'call_summary', 'conversation_summary', 'notes'] },

          { label: 'Recording', candidates: ['call_recording', 'recording', 'recording_url', 'call_url', 'audio_url'] },

          { label: 'Sentiment', candidates: ['sentiment_score', 'sentiment', 'score'] },

          { label: 'Channel', candidates: ['channel', 'call_channel', 'communication_channel'] },

          { label: 'History', candidates: ['history', 'session_history', 'transcript', 'conversation_history', 'chat_history', 'messages'] },

          { label: 'Duration', candidates: ['duration', 'call_duration', 'recording_duration', 'talk_time'] },

        ],

      },

    };

    const DISPOSITION_PRIORITY = BUSINESS_CONFIG.dispositionPriority;

    const TERMINAL_THRESHOLD = BUSINESS_CONFIG.terminalThreshold;

    const CONNECTED_SET = new Set(BUSINESS_CONFIG.connectedDispositions);

    const NOT_CONNECTED_SET = new Set(BUSINESS_CONFIG.notConnectedDispositions);

    // ─── DEALER CONFIGS ────────────────────────────────────────────────────────────

    const COMMON_COLUMNS = [

      { header: 'Lead_Id', key: 'lead_id' },

      { header: 'Full_Name', key: 'full_name' },

      { header: 'Phone', key: 'phone' },

      { header: 'City', key: 'city' },

      { header: 'PIncode', key: 'pincode' },

      { header: 'Language', key: 'language' },

      { header: 'Lead_Source', key: 'lead_source' },

      { header: 'Cohort', key: 'cohort' },

      { header: 'Campaign_ID', key: 'campaign_id' },

      { header: 'Last_session_id', key: 'last_session_id' },

      { header: 'Call_Triggered', key: 'call_triggered' },

      { header: 'Outcome', key: 'outcome' },

      { header: 'Disposition', key: 'disposition' },

      { header: 'Summary', key: 'summary' },

      { header: 'Disposition_detail', key: 'disposition_detail' },

      { header: 'Manual_Disposition_detail', key: 'manual_disposition_detail' },

      { header: 'Call_Date', key: 'call_date' },

      { header: 'Number_of_attempts', key: 'num_attempts' },

      { header: 'Sentiment', key: 'sentiment' },

      { header: 'Recordings', key: 'recordings' },

      { header: 'Model', key: 'model' },

      { header: 'Seating', key: 'seating' },

    ];

    const STELLANTIS_COLUMNS = [

      { header: 'Lead_ID+A1', key: 'lead_id' },

      { header: 'Full_Name', key: 'full_name' },

      { header: 'Phone', key: 'phone' },

      { header: 'City', key: 'city' },

      { header: 'PIncode', key: 'pincode' },

      { header: 'Language', key: 'language' },

        { header: "Disposition_Detail_AI", key: "manual_disposition_detail" },

      { header: 'Source', key: 'lead_source' },

      { header: 'Cohort', key: 'cohort' },

      { header: 'Campaign_ID', key: 'campaign_id' },

      { header: 'Call Triggered', key: 'call_triggered' },

      { header: 'Outcome', key: 'outcome' },

      { header: 'Disposition', key: 'disposition' },

      { header: 'Disposition_Detail', key: 'disposition_detail' },

      { header: 'Conversions', key: 'conversion' },

      { header: 'SUMMARY', key: 'summary' },

      { header: 'Call_Date', key: 'call_date' },

      { header: 'Number of atempts', key: 'num_attempts' },

      { header: 'SENTIMENT', key: 'sentiment' },

      { header: 'Session_id', key: 'last_session_id' },

      { header: 'Call_Duration', key: 'call_duration' },

      { header: 'Channel', key: 'channel' },

      { header: 'Model', key: 'model' },

      { header: 'Seating', key: 'seating' },

    ];

    const DEALER_CONFIGS = {

      anant_cars:      { name: 'Anant Cars',      summarySource: 'lead_summary',      columns: COMMON_COLUMNS },

      chennai_ev:      { name: 'ChennaiEV',        summarySource: 'lead_summary',      columns: COMMON_COLUMNS },
      singhal:         { name: 'Singhal',          summarySource: 'lead_summary',      columns: COMMON_COLUMNS },

      fortune_hyryder: { name: 'Fortune Hyryder',  summarySource: 'lead_summary',      columns: COMMON_COLUMNS },

      fortune_honda:   { name: 'Fortune Honda',    summarySource: 'lead_summary',      columns: COMMON_COLUMNS },

      stellantis_wa:   { name: 'Stellantis WA',    summarySource: 'lead_summary',      columns: STELLANTIS_COLUMNS },

      default:         { name: 'Default',          summarySource: 'disposition_detail', columns: COMMON_COLUMNS },

    };

    /* ═══════════════════════════════════════════════════════════════════════

       LLM VALIDATION — PRESALES DISPOSITIONS

       ═══════════════════════════════════════════════════════════════════════ */

    var LLM_DISPOSITION_BATCH_SIZE = getConfigNumber('llmDispositionBatchSize', getConfigNumber('llmBatchSize', 6));
    var LLM_DISPOSITION_MAX_CONCURRENT = getConfigNumber('llmDispositionMaxConcurrent', 1);
    var LLM_DISPOSITION_MAX_RETRIES = getConfigNumber('llmDispositionMaxRetries', getConfigNumber('llmMaxRetries', 1));
    var LLM_DISPOSITION_TIMEOUT_MS = getConfigNumber('llmDispositionTimeoutMs', getConfigNumber('llmRequestTimeoutMs', 90000));
    var LLM_PROMPT_CHAR_LIMIT = getConfigNumber('llmDispositionPromptCharLimit', getConfigNumber('llmPromptCharLimit', 2500));
    var LLM_DISPOSITION_MAX_TOKENS = getConfigNumber('llmDispositionMaxOutputTokens', getConfigNumber('llmMaxOutputTokens', 1800));function syncApiKeyControl(message, tone) {

      var container = document.querySelector('.ai-key-control');

      var input = document.getElementById('openRouterApiKey');

      var status = document.getElementById('apiKeyStatus');

      var saveBtn = container ? container.querySelector('button:not(.subtle)') : null;

      var clearBtn = container ? container.querySelector('button.subtle') : null;

      var endpoint = getApiEndpoint();

      var isProxy = isProxyEndpoint(endpoint);

      

      var configuredKey = window.JEJO_CONFIG
        ? String(window.JEJO_CONFIG.nvidiaApiKey || window.JEJO_CONFIG.openRouterApiKey || '').trim()
        : '';

      var keyFromConfig = configuredKey && configuredKey !== 'YOUR_NVIDIA_API_KEY_HERE'
        ? configuredKey
        : '';

      

      var isAutoConfigured = isProxy || keyFromConfig;

      if (isAutoConfigured) {

        if (input) input.style.display = 'none';

        if (saveBtn) saveBtn.style.display = 'none';

        if (clearBtn) clearBtn.style.display = 'none';

        

        if (status) {

          if (isProxy) {

            status.textContent = '✓ AI Active (Secure Proxy)';

            status.className = 'api-key-status ok active-proxy';

            status.style.animation = 'pulse-proxy 2s infinite ease-in-out';

          } else {

            status.textContent = '✓ AI Active (Configured)';

            status.className = 'api-key-status ok';

          }

        }

      } else {

        if (input) input.style.display = '';

        if (saveBtn) saveBtn.style.display = '';

        if (clearBtn) clearBtn.style.display = '';

        

        var hasSavedKey = !!(localStorage.getItem(NVIDIA_KEY_STORAGE) || '').trim();

        if (input) {

          input.value = '';

          input.placeholder = hasSavedKey ? 'Key saved in browser' : 'NVIDIA API key';

        }

        if (status) {

          status.textContent = message || (hasSavedKey ? 'Saved locally' : 'Required');

          status.className = 'api-key-status ' + (tone || (hasSavedKey ? 'ok' : ''));

          status.style.animation = '';

        }

      }

    }

    function saveNvidiaApiKey() {

      var input = document.getElementById('openRouterApiKey');

      var key = input ? input.value.trim() : '';

      if (!key) {

        syncApiKeyControl(getApiKey() ? 'Already saved' : 'Paste key first', 'warn');

        return;

      }

      localStorage.setItem(NVIDIA_KEY_STORAGE, key);

      syncApiKeyControl('Saved locally', 'ok');

    }

    function clearNvidiaApiKey() {

      localStorage.removeItem(NVIDIA_KEY_STORAGE);

      syncApiKeyControl('Cleared', 'warn');

    }

    /**

     * Sanitize user-provided text before inserting into an LLM prompt.

     * Prevents prompt injection by:

     * 1. Replacing double quotes with single quotes to prevent string boundary breaking

     * 2. Stripping control characters (except newlines/tabs)

     * 3. Removing known prompt injection keywords

     * 4. Wrapping in clearly marked data boundaries

     */var ALL_DISPOSITIONS = {

      // ── Pre-Sales ──

      "Voicemail": "If the customer has asked to leave a message or voicemail.",

      "Rejected": "If the customer has rejected the offer or to even speak with the agent.",

      "Language barrier": "If the customer has asked to speak in a different language and did not finish the conversation or intent of the campaign.",

      "Is not decision maker": "the customer said they are not the right person to speak to about this in their family.",

      "Will decide later, will purchase within 15 days": "The customer said they would decide to buy the vehicle within 15 days.",

      "Will decide later, will purchase within 1 to 3 months": "The customer said they would decide to buy the vehicle within 1 to 3 months.",

      "Will decide later, exploring options": "The customer said they will decide on the purchase of the vehicle at a later time and are only exploring all their options now.",

      "No buying intent": "the customer Do not want to purchase a car. Neither are the interested in the car.",

      "Just Exploring": "the customer Only want to know about the vehicle but do not show intent to buy.",

      "Will call showroom themselves": "the customer will contact the dealership or showroom themselves.",

      "Requested Callback": "the customer Asked to call back at a later date and or time.",

      "Purchased elsewhere": "the customer Already purchased a vehicle elsewhere.",

      "Enquired for Pricing": "the customer by themselves asked for the price of the vehicle.",

      "Enquired for Specifications": "the customer by themselves asked for the specifications of the vehicle.",

      "Enquired for Test Drive": "the customer by themselves asked for a test drive of the vehicle.",

      "Enquired for Showroom Visit": "the customer by themselves asked for a showroom visit of the vehicle.",

      "Enquired for Brochure": "the customer by themselves asked for a brochure of the vehicle.",

      "Enquired for Dealership Details": "the customer by themselves asked for dealership details.",

      "Enquired for Others": "the customer by themselves asked for other details not listed above.",

      "Comparing with another brand": "The customer by themselves is comparing the vehicle with another brand.",

      "Customer Busy": "The customer was busy and could not speak at that moment.",

      "Call Disconnected": "The customer by themselves has disconnected the call.",

      "Others": "All other disposition details not listed above.",

      "General Inquiry": "the customer is Asking generic questions not specific to the purpose of the campaign or the vehicle.",

      "Not Interested": "the customer Specifically said they are not interested in the vehicle.",

      "Follow Up Required": "the customer Needs a follow up to convince them to complete the campaign objective.",

      "No Response": "the customer did not say anything at all.",

      "Lost to Competition": "the customer Bought a competitor brands vehicle.",

      "Test Drive Completed": "the customer Already completed a test drive.",

      "Invalid Lead": "the customer Not a valid lead.",

      "Purchase Postponed": "the customer indicates that the Purchase has been postponed",

      "Audio Issue": "There was issues with hearing the customer or the agent for either party.",

      "Showroom Visit Planned": "the customer Already booked a showroom visit.",

      "Converted": "The customer completes the purpose of the campaign and provides the necessary information.",

      // ── Additional ──

      "Talk to Human": "The customer asked to speak to a human agent or customer executive instead of the digital assistant.",

      "Interested in another car same dealership": "The customer is interested in a different vehicle model from the same dealership."

    };

    function getActiveDealerConfig() {

      var key = document.getElementById('dealerSelect').value;

      return DEALER_CONFIGS[key] || DEALER_CONFIGS.default;

    }

    function handleDealerChange() {

      var cfg = getActiveDealerConfig();

      setStatus('globalStatus', cfg.name + ' selected.', '');

      renderTableHeader();

      if (processedData.length) renderTable(processedData);

    }

    function renderTableHeader() {

      var cfg = getActiveDealerConfig();

      var head = document.getElementById('outputHead');

      head.innerHTML = cfg.columns.map(function(col) {

        if (col.key === 'full_name') return '<th class="th-sortable" data-sort-key="full_name" onclick="toggleSort(\'full_name\')">' + esc(col.header) + '</th>';

        if (col.key === 'phone') return '<th class="th-sortable" data-sort-key="phone" onclick="toggleSort(\'phone\')">' + esc(col.header) + '</th>';

        if (col.key === 'disposition') return '<th class="th-sortable" data-sort-key="disposition" onclick="toggleSort(\'disposition\')">' + esc(col.header) + '</th>';

        return '<th>' + esc(col.header) + '</th>';

      }).join('');

    }

    function getDispositionPriority(d) {

      if (!d) return 1;

      return DISPOSITION_PRIORITY[d.trim().toLowerCase()] ?? 1;

    }

    // ─── PHONE NORMALIZATION ──────────────────────────────────────────────────────





    // ─── DATE PARSING ──────────────────────────────────────────────────────────────

    function parseAutoEngageDate(str) {

      if (!str) return null;

      const s = String(str).trim();

      const m = s.match(/^(\d{1,2})\/(\d{1,2})\/(\d{4}),?\s+(\d{1,2}):(\d{2}):(\d{2})\s*(am|pm)?/i);

      if (m) {

        let [, dd, mm, yyyy, hh, min, sec, ampm] = m;

        dd = parseInt(dd, 10); mm = parseInt(mm, 10); yyyy = parseInt(yyyy, 10);

        hh = parseInt(hh, 10); min = parseInt(min, 10); sec = parseInt(sec, 10);

        if (ampm) {

          ampm = ampm.toLowerCase();

          if (ampm === 'pm' && hh !== 12) hh += 12;

          if (ampm === 'am' && hh === 12) hh = 0;

        }

        return new Date(yyyy, mm - 1, dd, hh, min, sec);

      }

      const dmy = s.match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})$/);

      if (dmy) {

        const dd = parseInt(dmy[1], 10);

        const mm = parseInt(dmy[2], 10);

        const yyyy = parseInt(dmy[3], 10);

        if (mm >= 1 && mm <= 12 && dd >= 1 && dd <= 31) {

          return new Date(yyyy, mm - 1, dd);

        }

      }

      const iso = s.match(/^(\d{4})-(\d{2})-(\d{2})(?:[T\s](\d{2}):(\d{2})(?::(\d{2}))?)?/);

      if (iso) {

        const yyyy = parseInt(iso[1], 10);

        const mm = parseInt(iso[2], 10);

        const dd = parseInt(iso[3], 10);

        const hh = parseInt(iso[4] || '0', 10);

        const min = parseInt(iso[5] || '0', 10);

        const sec = parseInt(iso[6] || '0', 10);

        if (mm >= 1 && mm <= 12 && dd >= 1 && dd <= 31) {

          return new Date(yyyy, mm - 1, dd, hh, min, sec);

        }

      }

      return null;

    }

    function formatCallDate(dateObj) {

      if (!dateObj) return '';

      const dd = String(dateObj.getDate()).padStart(2, '0');

      const mm = String(dateObj.getMonth() + 1).padStart(2, '0');

      const yyyy = dateObj.getFullYear();

      return `${dd}/${mm}/${yyyy}`;

    }

    function isDateStr(val) {

      return /\d{1,2}\/\d{1,2}\/\d{4}/.test(String(val));

    }

    function ordinalSuffix(n) {

      const s = ['th', 'st', 'nd', 'rd'];

      const v = n % 100;

      return n + (s[(v - 20) % 10] || s[v] || s[0]);

    }

    function formatTime12(dateObj) {

      if (!dateObj) return '';

      let h = dateObj.getHours();

      const m = dateObj.getMinutes();

      const ampm = h >= 12 ? 'pm' : 'am';

      h = h % 12 || 12;

      return `${h}:${String(m).padStart(2, '0')}${ampm}`;

    }

    const MONTH_NAMES = ['January', 'February', 'March', 'April', 'May', 'June',

      'July', 'August', 'September', 'October', 'November', 'December'];

    // ─── FILE READING ──────────────────────────────────────────────────────────────







    // ─── ROBUST COLUMN DETECTION (File 2 column-shift bug fix) ────────────────────

    function detectPhones(obj) {

      const phones = new Set();

      const exactNames = ['phone_number', 'phone', 'mobile', 'contact', 'contact_number'];

      for (const c of exactNames) {

        if (obj[c]) {

          const n = normalizePhone(obj[c]);

          if (n) phones.add(n);

        }

      }

      const raw = Array.isArray(obj.__raw) ? obj.__raw : Object.values(obj);

      for (const val of raw) {

        if (!val) continue;

        const s = String(val).trim();

        if (isPhoneLike(s)) {

          const n = normalizePhone(s);

          if (n) phones.add(n);

        }

        if (s.length > 10) {

          const matches = s.match(/\+?(?:91|0)?[\s\-]?\d{10,12}\b/g);

          if (matches) {

            for (const m of matches) {

              const n = normalizePhone(m);

              if (n) phones.add(n);

            }

          }

        }

      }

      return Array.from(phones);

    }

    function detectRecording(obj) {

      function cleanLink(str) {

        if (!str || typeof str !== 'string') return null;

        let s = str.trim();

        const low = s.toLowerCase();

        if (low === 'null' || low === 'n/a' || low === 'none' || low === '-' || s === '') return null;

        return s;

      }

      function extractUrl(str) {

        if (!str || typeof str !== 'string') return null;

        const m = str.match(/(?:https?|s3):\/\/[^\s"'<>\\[\]]+/i);

        return m ? m[0] : null;

      }

      const exactNames = ['call_recording', 'recording', 'recording_url', 'call_url',

        'audio_url', 'audio', 'media_url', 'record_url', 'call_record'];

      for (const c of exactNames) {

        if (obj[c]) {

          const val = cleanLink(obj[c]);

          if (val) {

            const url = extractUrl(val);

            return url || val;

          }

        }

      }

      for (const [k, v] of Object.entries(obj)) {

        if (!v || k === '__raw') continue;

        if (/record|audio|media/i.test(k)) {

          const clean = cleanLink(v);

          if (!clean) continue;

          const url = extractUrl(clean);

          if (url) return url;

          if (clean.length > 5 && !clean.includes('{')) return clean;

        }

      }

      if (Array.isArray(obj.__raw)) {

        let bestGuess = null;

        for (const val of obj.__raw) {

          const s = String(val || '').trim();

          const url = extractUrl(s);

          if (url) {

            const lower = url.toLowerCase();

            if (lower.includes('cloudphone') || lower.includes('record') ||

              lower.includes('audio') || lower.includes('.mp3') || lower.includes('.wav')) {

              return url;

            }

            if (url.length > 35 && !bestGuess) bestGuess = url;

          } else if (s.includes('.mp3') || s.includes('.wav') || s.includes('cloudphone')) {

            return s;

          }

        }

        if (bestGuess) return bestGuess;

      }

      return '';

    }

    function detectDate(obj) {

      const candidates = ['created', 'date', 'start_time', 'timestamp', 'call_date'];

      for (const c of candidates) {

        if (obj[c] && isDateStr(obj[c])) return obj[c];

      }

      for (const val of Object.values(obj)) {

        if (typeof val === 'string' && isDateStr(val)) return val;

      }

      return '';

    }

    function detectSummary(obj) {

      const candidates = ['summary', 'call_summary', 'conversation_summary', 'notes'];

      for (const c of candidates) {

        if (obj[c] && obj[c].length > 3) return obj[c];

      }

      return '';

    }

    function detectSentiment(obj) {

      const candidates = ['sentiment_score', 'sentiment', 'score'];

      for (const c of candidates) {

        if (obj[c] !== undefined && obj[c] !== '') return obj[c];

      }

      return '';

    }

    function detectChannel(obj) {

      const candidates = ['channel', 'call_channel', 'communication_channel'];

      for (const c of candidates) {

        if (obj[c] !== undefined && obj[c] !== '') return String(obj[c]).trim();

      }

      return '';

    }

    function detectDuration(obj) {

      const candidates = ['duration', 'call_duration', 'recording_duration', 'talk_time'];

      for (const c of candidates) {

        if (obj[c] !== undefined && obj[c] !== '') return String(obj[c]).trim();

      }

      return '';

    }

    function detectSessionId(obj) {

      const candidates = ['session_id', 'id', 'last_session_id'];

      for (const c of candidates) {

        if (obj[c] !== undefined && obj[c] !== '') return String(obj[c]).trim();

      }

      return '';

    }

    function detectSessionDisposition(obj) {

      const candidates = ['disposition_detail', 'disposition', 'call_disposition'];

      for (const c of candidates) {

        if (obj[c] !== undefined && obj[c] !== '') return String(obj[c]).trim();

      }

      return '';

    }

    // ─── SEATING DERIVATION ───────────────────────────────────────────────────────

    function deriveSeating(seating, model) {

      if (seating && seating.trim() !== '') return seating.trim();

      if (!model) return '';

      const m = model.toLowerCase();

      for (const rule of BUSINESS_CONFIG.seatingRules) {

        if (rule.matches.some(term => m.includes(term))) return rule.value;

      }

      return '';

    }

    // â”€â”€â”€ DATA QUALITY / RECONCILIATION â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    function getColumnNames(rows) {

      const cols = new Set();

      for (const row of rows) {

        Object.keys(row || {}).forEach(k => {

          if (k !== '__raw') cols.add(k);

        });

        if (cols.size) break;

      }

      return cols;

    }

    function getMissingColumnGroups(rows, groups) {

      const cols = getColumnNames(rows);

      return groups

        .filter(group => !group.candidates.some(candidate => cols.has(candidate)))

        .map(group => group.label);

    }

    function addQualityWarning(warnings, level, title, detail) {

      warnings.push({ level, title, detail });

    }

    function isLikelyIndianMobile(phone) {

      return /^[6-9]\d{9}$/.test(String(phone || ''));

    }

    function buildQualityReport(rows1, rows2, allLeads, sessionGroups, sessionMap, output, callTriggered) {

      const validation = BUSINESS_CONFIG.validation;

      const leadPhoneCounts = new Map();

      const invalidLeadRows = [];

      rows1.forEach((row, index) => {

        const rawPhone = row['phone_number'] || row['phone'] || row['mobile'] || '';

        const phone = normalizePhone(rawPhone);

        if (!phone) {

          invalidLeadRows.push({

            rowNumber: index + 2,

            name: row['person_name'] || '',

            rawPhone: rawPhone || '(blank)'

          });

          return;

        }

        leadPhoneCounts.set(phone, (leadPhoneCounts.get(phone) || 0) + 1);

      });

      const duplicatePhones = Array.from(leadPhoneCounts.entries())

        .filter(([, count]) => count > 1)

        .map(([phone, count]) => ({ phone, count }));

      let sessionRowsWithPhone = 0;

      const sessionRowsWithoutPhone = [];

      rows2.forEach((row, index) => {

        const phones = detectPhones(row).filter(isLikelyIndianMobile);

        if (phones.length) {

          sessionRowsWithPhone += 1;

        } else {

          sessionRowsWithoutPhone.push({ rowNumber: index + 2 });

        }

      });

      const sessionPhones = Object.keys(sessionGroups).filter(isLikelyIndianMobile);

      const sessionOnlyPhones = sessionPhones.filter(phone => !leadPhoneCounts.has(phone));

      const unmatchedLeads = output.filter(r => !sessionMap[r.phone]);

      const matchedLeadCount = output.length - unmatchedLeads.length;

      const unknownDispositionRows = output.filter(r => r.outcome === 'Unknown');

      const sessionSelectionCounts = { recording: 0, summary: 0, fallback: 0 };

      Object.values(sessionMap).forEach(session => {

        const reason = session.selectionReason || 'fallback';

        sessionSelectionCounts[reason] = (sessionSelectionCounts[reason] || 0) + 1;

      });

      const missingFile1Required = getMissingColumnGroups(rows1, validation.file1RequiredGroups);

      const missingFile1Recommended = getMissingColumnGroups(rows1, validation.file1RecommendedGroups);

      const missingFile2Recommended = getMissingColumnGroups(rows2, validation.file2RecommendedGroups);

      const warnings = [];

      if (!rows1.length) {

        addQualityWarning(warnings, 'danger', 'File 1 has no data rows', 'Audience & Leads parsed successfully, but no lead rows were found.');

      }

      if (!rows2.length) {

        addQualityWarning(warnings, 'danger', 'File 2 has no data rows', 'Sessions parsed successfully, but no session rows were found.');

      }

      if (missingFile1Required.length) {

        addQualityWarning(warnings, 'danger', 'File 1 required columns missing', `Missing: ${missingFile1Required.join(', ')}.`);

      }

      if (invalidLeadRows.length) {

        addQualityWarning(warnings, 'warn', 'Rows skipped because phone is invalid', `${invalidLeadRows.length} File 1 row(s) were skipped by the existing phone normalization rule.`);

      }

      if (duplicatePhones.length) {

        addQualityWarning(warnings, 'warn', 'Duplicate File 1 phone numbers found', `${duplicatePhones.length} phone number(s) appear more than once in Audience & Leads.`);

      }

      if (unmatchedLeads.length) {

        addQualityWarning(warnings, 'warn', 'Processed leads without a session match', `${unmatchedLeads.length} processed lead(s) did not match any Sessions row.`);

      }

      if (sessionOnlyPhones.length) {

        addQualityWarning(warnings, 'warn', 'Sessions not present in File 1', `${sessionOnlyPhones.length} session phone number(s) were not present in Audience & Leads.`);

      }

      if (unknownDispositionRows.length) {

        const names = Array.from(new Set(unknownDispositionRows.map(r => r.disposition || '(blank)'))).slice(0, 6);

        addQualityWarning(warnings, 'warn', 'Unknown dispositions need review', `${unknownDispositionRows.length} lead(s) mapped to Unknown. Examples: ${names.join(', ')}.`);

      }

      if (sessionRowsWithoutPhone.length) {

        addQualityWarning(warnings, 'warn', 'Session rows without detectable phone', `${sessionRowsWithoutPhone.length} File 2 row(s) had no detectable 10 digit phone.`);

      }

      if (!callTriggered) {

        addQualityWarning(warnings, 'warn', 'Call triggered text is empty', 'No valid session date range was detected from File 2.');

      }

      if (missingFile1Recommended.length) {

        addQualityWarning(warnings, 'info', 'File 1 optional columns missing', `Missing: ${missingFile1Recommended.join(', ')}.`);

      }

      if (missingFile2Recommended.length) {

        addQualityWarning(warnings, 'info', 'File 2 optional columns missing', `Missing: ${missingFile2Recommended.join(', ')}.`);

      }

      if (!warnings.length) {

        addQualityWarning(warnings, 'info', 'No review issues found', 'The batch passed validation and reconciliation checks.');

      }

      const metrics = [

        { label: 'Valid leads', value: output.length, tone: 'blue' },

        { label: 'Matched leads', value: matchedLeadCount, tone: 'green' },

        { label: 'Unmatched leads', value: unmatchedLeads.length, tone: unmatchedLeads.length ? 'amber' : 'green' },

        { label: 'Skipped rows', value: invalidLeadRows.length, tone: invalidLeadRows.length ? 'red' : 'green' },

        { label: 'Duplicate phones', value: duplicatePhones.length, tone: duplicatePhones.length ? 'amber' : 'green' },

        { label: 'Unknown dispositions', value: unknownDispositionRows.length, tone: unknownDispositionRows.length ? 'amber' : 'green' },

        { label: 'Selected by recording', value: sessionSelectionCounts.recording, tone: 'green' },

        { label: 'Selected by summary', value: sessionSelectionCounts.summary, tone: 'blue' },

        { label: 'Selection fallback', value: sessionSelectionCounts.fallback, tone: sessionSelectionCounts.fallback ? 'amber' : 'green' },

      ];

      const samples = [

        {

          title: 'Invalid File 1 phones',

          rows: invalidLeadRows.slice(0, 5).map(r => `Row ${r.rowNumber}: ${r.rawPhone}${r.name ? ' - ' + r.name : ''}`)

        },

        {

          title: 'Duplicate File 1 phones',

          rows: duplicatePhones.slice(0, 5).map(r => `${r.phone} appears ${r.count} times`)

        },

        {

          title: 'Leads without session match',

          rows: unmatchedLeads.slice(0, 5).map(r => `${r.phone}${r.full_name ? ' - ' + r.full_name : ''}`)

        },

        {

          title: 'Session-only phones',

          rows: sessionOnlyPhones.slice(0, 5)

        },

        {

          title: 'Unknown dispositions',

          rows: unknownDispositionRows.slice(0, 5).map(r => `${r.phone}: ${r.disposition || '(blank)'}`)

        },

        {

          title: 'Session selection method',

          rows: [

            `Recording priority: ${sessionSelectionCounts.recording}`,

            `Summary priority: ${sessionSelectionCounts.summary}`,

            `Fallback latest row: ${sessionSelectionCounts.fallback}`,

          ]

        },

      ].filter(section => section.rows.length);

      if (!samples.length) {

        samples.push({ title: 'No reconciliation samples', rows: ['No invalid, duplicate, unmatched, or unknown rows to sample.'] });

      }

      const reviewCount = warnings.filter(w => w.level !== 'info').length;

      return {

        status: reviewCount ? `${reviewCount} review item${reviewCount === 1 ? '' : 's'}` : 'Clean batch',

        subtitle: 'This report explains batch health only. It does not change Zoho formulas, copy output, or Excel export columns.',

        metrics,

        warnings,

        samples,

        counts: {

          file1Rows: rows1.length,

          file2Rows: rows2.length,

          sessionRowsWithPhone,

          sessionRowsWithoutPhone: sessionRowsWithoutPhone.length,

          sessionOnlyPhones: sessionOnlyPhones.length,

          allLeads: allLeads.length,

        }

      };

    }

    // ─── CORE PROCESSING ──────────────────────────────────────────────────────────

    async function processFiles() {

      if (!rawFile1 || !rawFile2) return;

      showOverlay('Parsing files…');

      await tick();

      try {

        const [ab1, ab2] = await Promise.all([

          readFileAsArrayBuffer(rawFile1),

          readFileAsArrayBuffer(rawFile2)

        ]);

        showOverlay('Parsing Audience & Leads…');

        await tick();

        const rows1 = parseSheet(ab1);

        showOverlay('Parsing Sessions…');

        await tick();

        const rows2 = parseSheet(ab2);

        showOverlay('Applying business logic…');

        await tick();

        // ── BUILD FILE 1 LIST ──────────────────────────────────────────────────

        const allLeads = [];

        for (const r of rows1) {

          const phone = normalizePhone(r['phone_number'] || r['phone'] || r['mobile'] || '');

          if (!phone) continue;

          allLeads.push({ row: r, phone });

        }

        // ── BUILD FILE 2 MAP ────────────────────────────────────────────────────

        const sessionGroups = {};

        for (const r of rows2) {

          const phones = detectPhones(r);

          for (const phone of phones) {

            if (!sessionGroups[phone]) sessionGroups[phone] = [];

            sessionGroups[phone].push(r);

          }

        }

        const sessionMap = {};

                  // ── Content-first session ranking ──
        // Keywords that indicate a real human conversation happened
        const STRONG_WORDS = ['spoke', 'discussed', 'explained', 'interested', 'booked',
          'confirmed', 'agreed', 'scheduled', 'test drive', 'demo', 'follow up',
          'quote', 'visit', 'converted', 'enquired', 'purchased',
          'selected', 'wants', 'wanted', 'asked for', 'requested', 'decided',
          'showroom', 'inquiry', 'pricing', 'financing', 'test drove'];
        // Keywords that indicate a junk/non-conversation
        const JUNK_WORDS = ['voicemail', 'no response', 'busy', 'unreachable',
          'wrong number', 'silent', 'already talked', 'callback only', 'auto call',
          'disconnected', 'missed', 'not reachable', 'could not connect',
          'no answer', 'not answered', 'call dropped', 'no reply',
          'customer did not respond', 'call failed', 'system generated',
          'no one spoke', 'no conversation', 'did not speak', 'did not answer',
          'not connected', 'call not completed'];

        function getSessionBucket(s) {
          var summ = (detectSummary(s) || '').trim().toLowerCase();
          var dur = parseInt(detectDuration(s), 10);
          var hasDuration = Number.isFinite(dur) && dur > 0;
          for (var wi = 0; wi < STRONG_WORDS.length; wi++) {
            if (summ.indexOf(STRONG_WORDS[wi]) >= 0) return 'strong';
          }
          for (var wj = 0; wj < JUNK_WORDS.length; wj++) {
            if (summ.indexOf(JUNK_WORDS[wj]) >= 0) return 'junk';
          }
          if (summ.length > 3) return 'weak';
          if (hasDuration) return 'weak';
          return 'junk';
        }

        function scoreSession(s) {
          var summ = (detectSummary(s) || '').trim().toLowerCase();
          var score = 0;
          for (var wi = 0; wi < STRONG_WORDS.length; wi++) {
            if (summ.indexOf(STRONG_WORDS[wi]) >= 0) { score += 1000; break; }
          }
          for (var wj = 0; wj < JUNK_WORDS.length; wj++) {
            if (summ.indexOf(JUNK_WORDS[wj]) >= 0) { score -= 800; break; }
          }
          if (summ.length > 5) score += 200;
          var dur = parseInt(detectDuration(s), 10);
          if (Number.isFinite(dur) && dur > 0) {
            score += Math.min(dur, 120);
          }
          var dateStr = detectDate(s) || s['start_time'] || '';
          var d = parseAutoEngageDate(dateStr);
          if (d) {
            score += d.getTime() / 1000000000000;
          }
          return score;
        }

        function sessionTimestamp(s) {
          var d = parseAutoEngageDate(detectDate(s) || s['start_time'] || '');
          return d ? d.getTime() : 0;
        }

for (const [phone, sessions] of Object.entries(sessionGroups)) {

          let best = null;
          let selectionReason = 'fallback';

          // ── Content-first session ranking ──
          // Keywords that indicate a real human conversation happened
          // First, always prefer a session with a recording (direct evidence)
          for (var si = 0; si < sessions.length; si++) {
            var s = sessions[si];
            var rec = detectRecording(s);
            if (rec) {
              best = s;
              selectionReason = 'recording';
              break;
            }
          }

          if (!best) {
            var scored = sessions.map(function(s) {
              return { session: s, bucket: getSessionBucket(s), score: scoreSession(s) };
            });

            var strong = scored.filter(function(s) { return s.bucket === 'strong'; });
            var weak = scored.filter(function(s) { return s.bucket === 'weak'; });
            var junk = scored.filter(function(s) { return s.bucket === 'junk'; });

            if (strong.length > 0) {
              // Strongest conversation with highest score
              strong.sort(function(a, b) { return b.score - a.score; });
              best = strong[0].session;
              selectionReason = 'summary';
            } else if (weak.length > 0) {
              // Among weak conversations, pick the one with longest meaningful duration
              var bestDur = -1;
              for (var wi2 = 0; wi2 < weak.length; wi2++) {
                var d = parseInt(detectDuration(weak[wi2].session), 10);
                if (Number.isFinite(d) && d > bestDur) {
                  best = weak[wi2].session;
                  bestDur = d;
                }
              }
              if (!best) best = weak[weak.length - 1].session;
              selectionReason = 'summary';
            } else {
              // All junk — pick the latest session by timestamp
              var latestTs = -1;
              for (var ji = 0; ji < junk.length; ji++) {
                var ts = sessionTimestamp(junk[ji].session);
                if (ts > latestTs) {
                  best = junk[ji].session;
                  latestTs = ts;
                }
              }
              if (!best) best = sessions[sessions.length - 1];
              selectionReason = 'fallback';
            }
          }

          if (!best) {
            best = sessions[sessions.length - 1];
            selectionReason = 'fallback';
          }

                    var histRaw = detectHistory(best);

          sessionMap[phone] = {

            selectionReason,

            recording: detectRecording(best),

            summary: detectSummary(best),

            sentiment: detectSentiment(best),

            dateStr: detectDate(best),

            startTime: best['start_time'] || '',

            channel: detectChannel(best),

            duration: detectDuration(best),

            session_id: detectSessionId(best),

            session_disposition: detectSessionDisposition(best),

            history_text: formatHistoryForPrompt(histRaw),

          };

        }

        // ── CALL TRIGGERED ─────────────────────────────────────────────────────

        let minDate = null, maxDate = null;

        for (const r of rows2) {

          const dStr = detectDate(r) || r['start_time'] || '';

          const d = parseAutoEngageDate(dStr);

          if (!d) continue;

          if (!minDate || d < minDate) minDate = d;

          if (!maxDate || d > maxDate) maxDate = d;

        }

        let callTriggered = '';

        if (minDate && maxDate) {

          const day = ordinalSuffix(minDate.getDate());

          const month = MONTH_NAMES[minDate.getMonth()];

          const tMin = formatTime12(minDate);

          const tMax = formatTime12(maxDate);

          callTriggered = `${day} ${month} Calls Triggered From ${tMin} - ${tMax}`;

        }

        // ── ASSEMBLE OUTPUT ROWS ───────────────────────────────────────────────

        const output = [];

        const startId = parseInt(document.getElementById('leadIdStart').value) || 0;

        const selectedLanguage = document.getElementById('langSelect').value;

        for (const { row, phone } of allLeads) {

          const disp = (row['disposition'] || '').trim();

          const dispLower = disp.toLowerCase();

          const priority = getDispositionPriority(disp);

          let outcome;

          if (CONNECTED_SET.has(dispLower)) {

            outcome = 'Connected';

          } else if (NOT_CONNECTED_SET.has(dispLower)) {

            outcome = 'Not Connected';

          } else if (disp && Object.keys(ALL_DISPOSITIONS).some(function(k) { return k.toLowerCase() === dispLower; })) {

            outcome = 'Connected';

          } else {

            outcome = 'Unknown';

            console.warn(`[Pre-Sales Sync] Unknown disposition "${disp}" for phone ${phone} — mapped to "Unknown". Check for typos or add to DISPOSITION_PRIORITY / CONNECTED_SET / NOT_CONNECTED_SET.`);

          }

          var dealerCfg = getActiveDealerConfig();

          var summarySrc = row[dealerCfg.summarySource] || row['disposition_detail'] || '';

          var summary = summarySrc.trim() || 'No Response';

          var dispositionDetail = row['disposition_detail'] || '';

          const callDateRaw = row['updated'] || '';

          const callDateObj = parseAutoEngageDate(callDateRaw);

          const callDate = formatCallDate(callDateObj);

          const model = (row['name'] || row['model_preference'] || row['interested_vehicle_name'] || '').replace(/[\[\]"']/g, '').trim();

          const seatingRaw = row['seating_capacity_preference'] || '';

          const seating = deriveSeating(seatingRaw, model);

          const sess = sessionMap[phone] || {};

          const isStellantis = document.getElementById('dealerSelect').value === 'stellantis_wa';

          const leadId = startId > 0 ? `L-${startId + output.length}` : `L-${output.length + 1}`;

          const formulaRow = startId > 0 ? startId + output.length : 2 + output.length;

          var dispositionText = (row['disposition_detail'] || '').toLowerCase();

          output.push({

            lead_id: leadId,

            full_name: row['person_name'] || '',

            phone,

            city: row['city'] || '',

            pincode: row['pincode'] || '',

            language: selectedLanguage,

            lead_source: row['lead_source'] || '',

            cohort: row['campaign_objective_name'] || '',

            campaign_id: row['campaign_id'] || '',

            last_session_id: isStellantis ? (sess.session_id || '') : (sess.session_id || row['last_session_id'] || row['session_id'] || ''),

            call_triggered: callTriggered,

            outcome,

            disposition: disp,

            summary: isStellantis ? (sess.summary || 'No Response') : summary,

            disposition_detail: isStellantis ? (sess.session_disposition || '') : dispositionDetail,

            manual_disposition_detail: '',

            call_date: callDate,

            num_attempts: `=COUNTIF(C:C;C${formulaRow})`,

            sentiment: sess.sentiment || '',

            recordings: sess.recording || '',

            model,

            seating,

            exclusion_flag: priority >= TERMINAL_THRESHOLD ? 'YES' : '',

            session_summary: sess.summary || '',

            session_history: sess.history_text || '',

            conversion: dispositionText.includes('converted') ? 'Yes' : '',

            channel: sess.channel || '',

            call_duration: sess.duration || '',

          });

        }

        processedData = output;

        qualityReport = buildQualityReport(rows1, rows2, allLeads, sessionGroups, sessionMap, output, callTriggered);

        renderTableHeader();

        renderTable(output);

        updateSortIndicators();

        renderConvertedTable(output);

        renderTestDriveTable(output);

        renderStats(output);

        renderQualityReport(qualityReport);

        hideOverlay();

        setStatus('globalStatus', `${output.length} leads processed. Ready to copy or export.`, 'ok');

        document.getElementById('pill3').classList.remove('active');

        document.getElementById('pill4').classList.add('active');

        document.getElementById('btnProcess').classList.remove('ready');

        document.getElementById('btnCopy').style.display = '';

        document.getElementById('btnCopy').disabled = false;

        document.getElementById('btnExport').style.display = '';

        document.getElementById('btnExport').disabled = false;

        document.getElementById('btnValidateAI').style.display = '';

        document.getElementById('btnValidateAI').disabled = false;

        document.getElementById('btnReset').style.display = '';

      } catch (e) {

        hideOverlay();

        setStatus('globalStatus', `Error: ${e.message}`, 'err');

        console.error(e);

      }

    }

    /* ═══════════════════════════════════════════════════════════════════════

       LLM DISPOSITION VALIDATION

       ═══════════════════════════════════════════════════════════════════════ */

    async function validateDispositionsWithLLM(force) {

      if (!processedData || processedData.length === 0) return;

      // Reset button text

      document.getElementById('btnValidateAI').textContent = 'Validating...';

      const apiKey = getApiKey();

      if (!apiKey) {

        setStatus('globalStatus', 'AI key required. Paste your key above and click Save.', 'err');

        return;

      }

      // Build list of valid dispositions

      const dispKeys = Object.keys(ALL_DISPOSITIONS);

      const dispDefs = dispKeys.map(k => `- "${k}": ${ALL_DISPOSITIONS[k]}`).join('\n');

      // Normalize disposition_detail casing to match the valid dispositions list
      function normalizeDisposition(disp) {
        if (!disp) return disp;
        var dispLower = disp.trim().toLowerCase();
        for (var key in ALL_DISPOSITIONS) {
          if (key.toLowerCase() === dispLower) {
            return key;
          }
        }
        return disp;
      }

      function hasValidSummary(r) {
        var summ = (r.session_summary || '').trim();
        var hist = (r.session_history || '').trim();
        var leadSumm = (r.summary || '').trim();
        if (!summ || summ === 'No Response' || summ === 'The session history is empty and contains no content to summarize.') {
          if (leadSumm && leadSumm !== 'No Response' && leadSumm.length > 3) {
            return true;
          }
        }
        return (summ && summ !== 'No Response' && summ !== 'The session history is empty and contains no content to summarize.') || (hist && hist.length > 0);
      }

      // Filter rows that have a meaningful session_summary OR session_history AND any disposition_detail

      const candidates = [];

      for (var i = 0; i < processedData.length; i++) {

        var r = processedData[i];

        var summ = (r.session_summary || '').trim();

        var hist = (r.session_history || '').trim();

        var disp = (r.disposition_detail || '').trim();

        // Skip rows where disposition_detail is 'No Response' — no actual conversation happened
        if (disp.toLowerCase() === 'no response') continue;

        if (hasValidSummary(r) && disp && r.outcome === 'Connected') {
          // Fall back to lead file summary when session summary is empty
          if (!summ || summ === 'No Response' || summ === 'The session history is empty and contains no content to summarize.') {
            var leadFallback = (r.summary || '').trim();
            if (leadFallback && leadFallback !== 'No Response' && leadFallback.length > 3) {
              summ = leadFallback;
            }
          }
          var normalizedDisp = normalizeDisposition(disp);

          candidates.push({ index: i, summary: summ, history: hist, currentDisp: normalizedDisp, model: r.model || '', outcome: r.outcome || '', callDuration: r.call_duration || '', leadSource: r.lead_source || '' });

        }

      }

      if (candidates.length === 0) {

        setStatus('globalStatus', 'No rows with session summaries to validate.', 'warn');

        return;

      }          // Show inline AI status bar instead of blocking overlay

      showAiStatusBar(candidates.length);

      var corrected = 0;

      var BATCH_SIZE = LLM_DISPOSITION_BATCH_SIZE;

      var correctedResults = {};

      // Check cache first — build a combined hash

      var cacheInput = candidates.map(function(c) { return c.summary + '||' + c.history + '||' + c.currentDisp + '||' + c.model + '||' + c.outcome + '||' + c.callDuration + '||' + c.leadSource; }).join('|');

      var cacheKey = 'disp-validate-v3-history-' + hashStr(cacheInput);

      var cached = force ? null : localStorage.getItem(cacheKey);

      var cachedParsed = null;

      if (cached) {

        try {

          cachedParsed = JSON.parse(cached);

        } catch(e) { console.warn("Cache parse failed, clearing:", e); cached = null; }

      }

      if (!cached) {

        var runnerOpts = {

          items: candidates,

          batchSize: BATCH_SIZE,

          maxConcurrent: LLM_DISPOSITION_MAX_CONCURRENT,

          minGapMs: 500,

          maxRetries: LLM_DISPOSITION_MAX_RETRIES,

          requestTimeoutMs: LLM_DISPOSITION_TIMEOUT_MS,

          cachedData: null,

          getCacheKey: null,

          buildPrompt: function(batch, batchIndex) {

            var dispDefs = Object.keys(ALL_DISPOSITIONS).map(function(k) { return '- "' + k + '": ' + ALL_DISPOSITIONS[k]; }).join('\n');

            var promptLines = batch.map(function(c, idx) {

              var safeSummary = sanitizeForPrompt(c.summary, LLM_PROMPT_CHAR_LIMIT);

              var safeHistory = sanitizeForPrompt(c.history, LLM_PROMPT_CHAR_LIMIT);

              var safeDisp = sanitizeForPrompt(c.currentDisp, LLM_PROMPT_CHAR_LIMIT);

              var safeModel = sanitizeForPrompt(c.model, LLM_PROMPT_CHAR_LIMIT);

              var safeOutcome = sanitizeForPrompt(c.outcome, LLM_PROMPT_CHAR_LIMIT);

              var safeDuration = sanitizeForPrompt(c.callDuration, LLM_PROMPT_CHAR_LIMIT);

              var safeSource = sanitizeForPrompt(c.leadSource, LLM_PROMPT_CHAR_LIMIT);

              var line = 'Row ' + idx + ':';

              if (safeSummary) line += '\n--- BEGIN SUMMARY ---\n' + safeSummary + '\n--- END SUMMARY ---';

              if (safeHistory) line += '\n--- BEGIN CONVERSATION HISTORY ---\n' + safeHistory + '\n--- END CONVERSATION HISTORY ---';

              line += '\nCurrent Disposition: "' + safeDisp + '"';

              if (safeModel) line += '\nVehicle Model: "' + safeModel + '"';

              if (safeOutcome) line += '\nCall Outcome: "' + safeOutcome + '"';

              if (safeDuration) line += '\nCall Duration: "' + safeDuration + '"';

              if (safeSource) line += '\nLead Source: "' + safeSource + '"';

              return line;

            }).join('\n\n---\n\n');

            var systemMsg = 'You are a strict disposition auditor for an automotive campaign. Your job is to CRITICALLY evaluate whether the "Current Disposition" accurately describes the call. You are provided with two evidence sources for each row: 1) a Summary (short description), and 2) a Conversation History (full transcript with timestamps). The Conversation History is the STRONGEST evidence — if it conflicts with the Summary, trust the History. Additional context (Vehicle Model, Call Outcome, Call Duration, Lead Source) is also provided — use it to rule out impossible dispositions. Default to "correct" unless the summary or history clearly contradicts the disposition. Only suggest a correction when you are highly confident.';

            var examples = 'Example 1:\nTranscript: "Customer said they would think about it and call back next week"\nCurrent Disposition: "Not Interested"\n→ isCorrect: false, correctedDisposition: "Will decide later, exploring options"\nReason: Customer did not say no — they deferred. Not Interested means explicit refusal.\n\n' +

              'Example 2:\nTranscript: "Customer asked about financing options and EMI plans"\nCurrent Disposition: "General Inquiry"\n→ isCorrect: false, correctedDisposition: "Enquired for Pricing"\nReason: Asking about pricing/financing is Enquired for Pricing, not generic.\n\n' +

              'Example 3:\nTranscript: "Customer said the vehicle is too expensive and they will look at other brands"\nCurrent Disposition: "Rejected"\n→ isCorrect: false, correctedDisposition: "Comparing with another brand"\nReason: Still in market, just price-shopping — not a hard rejection.\n\n' +

              'Example 4:\nTranscript: "Call dropped mid-conversation while discussing test drive"\nCurrent Disposition: "Follow Up Required"\n→ isCorrect: false, correctedDisposition: "Call Disconnected"\nReason: Call physically dropped. Follow Up Required is for completed conversations needing callback.\n\n' +

              'Example 5:\nTranscript: "Customer said they already own this model and do not need another"\nCurrent Disposition: "Not Interested"\n→ isCorrect: false, correctedDisposition: "No buying intent"\nReason: No buying intent is for customers who do not want to purchase a car at all.\n\n' +

              'Example 6:\nTranscript: "Customer asked to be called back after 5pm"\nCurrent Disposition: "Call Disconnected"\n→ isCorrect: false, correctedDisposition: "Requested Callback"\nReason: Customer explicitly requested a callback — not a disconnect.\n\n' +

              'Example 7:\nTranscript: "Customer kept asking about the vehicle but would not give their details"\nCurrent Disposition: "No buying intent"\n→ isCorrect: false, correctedDisposition: "Just Exploring"\nReason: Just Exploring means they want info without buying intent.\n\n' +

              'Example 8:\nTranscript: "Customer said they already booked a test drive at another dealership"\nCurrent Disposition: "Converted"\n→ isCorrect: false, correctedDisposition: "Lost to Competition"\nReason: Converted elsewhere = competitive loss, not a campaign conversion.\n\n' +

              'Example 9:\nTranscript: "The customer declined the call, stating they were busy."\nCurrent Disposition: "Rejected"\n→ isCorrect: false, correctedDisposition: "Customer Busy"\nReason: "Rejected" means explicit refusal of the offer. Saying "I am busy" means the customer was not available — they did not reject the product.';

            var userPrompt = 'VALID DISPOSITIONS:\n' + dispDefs + '\n\nEXAMPLES (learn from these patterns):\n' + examples + '\n\nNow evaluate these rows. For EACH row, respond with ONE JSON object:\n{"rowIndex":0,"isCorrect":true,"correctedDisposition":null,"confidence":"high","reason":"The summary clearly matches the disposition."}\n\nRows:\n' + promptLines + '\n\nRespond as a JSON array of objects, one per row in the same order. ONLY valid JSON.';

            return {

              system: systemMsg,

              user: userPrompt,

              temperature: 0.3,

              maxTokens: LLM_DISPOSITION_MAX_TOKENS

            };

          },

          parseResponse: function(text, batch, batchIndex) {

            var cleaned = text.replace(/```json\s*/gi, '').replace(/```/g, '').trim();

            var match = cleaned.match(/\[[\s\S]*\]/);

            if (match) {

              var parsed = JSON.parse(match[0]);

              // Assign rowIndex relative to the batch

              return parsed.map(function(item, idx) {

                return {

                  rowIndex: (batchIndex * BATCH_SIZE) + idx,

                  isCorrect: item.isCorrect,

                  correctedDisposition: item.correctedDisposition,

                  confidence: item.confidence,

                  reason: item.reason

                };

              });

            }

            return [];

          },

          buildHeaders: function() {

            var endpoint = getApiEndpoint();

            var isProxy = isProxyEndpoint(endpoint);

            var h = { 'Content-Type': 'application/json', 'Accept': 'application/json' };

            if (isProxy) {

              var handshake = (window.JEJO_CONFIG && window.JEJO_CONFIG.proxyHandshakeToken)

                ? window.JEJO_CONFIG.proxyHandshakeToken

                : 'jejo-presales-secure-handshake';

              h['X-Handshake-Token'] = handshake;

            } else {

              h['Authorization'] = 'Bearer ' + getApiKey();

              h['HTTP-Referer'] = window.location.origin;

              h['X-Title'] = 'AutoNage Pre-Sales Sync';

            }

            return h;

          },

          onProgress: function(done, total, message, pct) {

            updateAiStatusBar(done, total, message, pct, correctedResults);

          },

          signal: AiValidator.getSignal()

        };

        var runnerResult = await runLlmBatches(runnerOpts);

        

        // Check if aborted — don't apply results if user cancelled

        if (runnerResult.aborted) {

          hideAiStatusBar(correctedResults);

          return;

        }

        

        // Check for failed batches — don't silently treat failures as "correct"

        var failedCount = runnerResult.failedBatches ? runnerResult.failedBatches.length : 0;

        var totalBatches = Math.ceil(candidates.length / BATCH_SIZE);

        if (failedCount >= totalBatches) {

          hideAiStatusBar(correctedResults);

          setStatus('globalStatus', 'AI validation failed: all ' + totalBatches + ' batch(es) returned errors. Check your API key and proxy configuration, then try again.', 'err');

          return;

        }

        if (failedCount > 0) {

          console.warn('[AI Validation] ' + failedCount + ' of ' + totalBatches + ' batch(es) failed. Results are partial.');

        }

        

        corrected = runnerResult.correctedCount;

        // Build cache array from runner results and candidates

        // IMPORTANT: only cache results for rows that were actually processed (skip failed)

        var cacheArray = [];

        for (var idx = 0; idx < candidates.length; idx++) {

          var c = candidates[idx];

          var decision = runnerResult.results.get(idx);

          if (decision && decision.isCorrect === false && decision.correctedDisposition) {

            cacheArray.push({ rowIndex: idx, isCorrect: false, correctedDisposition: decision.correctedDisposition });

          } else if (decision) {

            cacheArray.push({ rowIndex: idx, isCorrect: true, correctedDisposition: null });

          }

          // If decision is undefined (batch failed), do NOT cache — forces re-run next time

        }

        if (cacheArray.length > 0) {

          try { localStorage.setItem(cacheKey, JSON.stringify(cacheArray)); } catch(e) { console.warn("localStorage write failed (private mode?):", e); }}

        // Apply corrections from runner results

        for (var ri = 0; ri < candidates.length; ri++) {

          var dec = runnerResult.results.get(ri);

          if (dec && dec.isCorrect === false && dec.correctedDisposition) {

            correctedResults[candidates[ri].index] = dec.correctedDisposition;

          }

        }

      } else {

        // Cache hit — parse cached data

        try {

          for (var ci = 0; ci < cachedParsed.length; ci++) {

            var item = cachedParsed[ci];

            if (item.isCorrect === false && item.correctedDisposition) {

              correctedResults[item.rowIndex] = item.correctedDisposition;

            }

          }

          corrected = Object.keys(correctedResults).length;

        } catch(e) { console.warn("localStorage write failed (private mode?):", e); }}

      // Apply corrections + mark validation status

      var correctedIndices = Object.keys(correctedResults);

      for (var k = 0; k < correctedIndices.length; k++) {

        var rowIdx = parseInt(correctedIndices[k]);

        if (processedData[rowIdx]) {

          processedData[rowIdx].manual_disposition_detail = correctedResults[rowIdx];

          processedData[rowIdx]._ai_status = 'corrected';

        }

      }

      for (var ci = 0; ci < candidates.length; ci++) {

        var cand = candidates[ci];

        if (processedData[cand.index] && !processedData[cand.index]._ai_status) {

          processedData[cand.index]._ai_status = 'verified';

        }

      }

      hideAiStatusBar(correctedResults);

      if (correctedIndices.length > 0) {

        renderTable(processedData);

        setStatus('globalStatus', 'AI validated ' + candidates.length + ' rows, corrected ' + correctedIndices.length + ' dispositions. Check Manual_Disposition_detail column.', 'ok');

      } else {

        setStatus('globalStatus', 'AI validated ' + candidates.length + ' rows — all dispositions appear correct.', 'ok');

      }

      // Switch button to re-run mode

      document.getElementById('btnValidateAI').textContent = '↻ Re-run AI';

      document.getElementById('btnValidateAI').onclick = function() { validateDispositionsWithLLM(true); };

    }

    // ─── RENDER TABLE ─────────────────────────────────────────────────────────────

    // ─── SORT STATE ──────────────────────────────────────────────────────────────

    let currentSortKey = 'full_name';   // 'full_name' | 'phone' | 'disposition' | null

    let currentSortDir = 'asc';   // 'asc' | 'desc' | null

    function toggleSort(key) {

      if (currentSortKey === key) {

        if (currentSortDir === 'asc') currentSortDir = 'desc';

        else if (currentSortDir === 'desc') { currentSortKey = null; currentSortDir = null; }

      } else {

        currentSortKey = key;

        currentSortDir = 'asc';

      }

      updateSortIndicators();

      renderTable(processedData);

    }

    function updateSortIndicators() {

      document.querySelectorAll('.th-sortable').forEach(th => {

        th.classList.remove('sort-asc', 'sort-desc');

        if (th.dataset.sortKey === currentSortKey && currentSortDir) {

          th.classList.add(currentSortDir === 'asc' ? 'sort-asc' : 'sort-desc');

        }

      });

    }

    function compareCaseSensitiveStrings(a, b) {

      if (a === b) return 0;

      return a < b ? -1 : 1;

    }

    function getSortedData(data) {

      let sorted = data;

      if (currentSortKey && currentSortDir) {

        sorted = [...data];

        const dir = currentSortDir === 'asc' ? 1 : -1;

        sorted.sort((a, b) => {

          const va = String(a[currentSortKey] || '');

          const vb = String(b[currentSortKey] || '');

          return dir * compareCaseSensitiveStrings(va, vb);

        });

      }

      const startId = parseInt(document.getElementById('leadIdStart').value) || 0;

      sorted.forEach((r, i) => {

        r.lead_id = startId > 0 ? `L-${startId + i}` : `L-${i + 1}`;

        const formulaRow = startId > 0 ? startId + i : 2 + i;

        r.num_attempts = `=COUNTIF(C:C;C${formulaRow})`;

      });

      return sorted;

    }

    const PREVIEW_LIMIT = 200;

    function renderTable(data) {

      data = getSortedData(data);

      var cfg = getActiveDealerConfig();

      var tbody = document.getElementById('outputBody');

      tbody.innerHTML = '';

      var preview = data.slice(0, PREVIEW_LIMIT);

      for (var ri = 0; ri < preview.length; ri++) {

        var r = preview[ri];

        var tr = document.createElement('tr');

        var colsHtml = '';

        for (var ci = 0; ci < cfg.columns.length; ci++) {

          var col = cfg.columns[ci];

          var val = r[col.key];

          if (col.key === 'phone') {

            colsHtml += '<td class="cell-phone">' + esc(val) + '</td>';

          } else if (col.key === 'call_recording' || col.key === 'recordings') {

            var recording = val;

            if (recording) {

              var href = String(recording).startsWith('http') || String(recording).startsWith('s3:') ? recording : 'https://' + recording;

              colsHtml += '<td><a class="cell-url" href="' + esc(href) + '" target="_blank" rel="noopener noreferrer" title="' + esc(recording) + '">Recording</a></td>';

            } else {

              colsHtml += '<td></td>';

            }

          } else if (col.key === 'outcome') {

            var oc = r.outcome === 'Connected' ? 'cell-connected' : r.outcome === 'Unknown' ? 'cell-unknown' : 'cell-not-connected';

            colsHtml += '<td class="' + oc + '">' + esc(r.outcome) + '</td>';

          } else if (col.key === 'disposition') {

            colsHtml += '<td class="' + getPrioClass(r.disposition) + '">' + esc(r.disposition) + '</td>';

          } else if (col.key === 'sentiment') {

            var sn = parseFloat(r.sentiment);

            var sc = isNaN(sn) ? '' : sn >= 0.6 ? 'cell-sentiment-high' : sn >= 0.3 ? 'cell-sentiment-mid' : 'cell-sentiment-low';

            colsHtml += '<td class="' + sc + '">' + esc(r.sentiment) + '</td>';

          } else if (col.key === 'manual_disposition_detail') {

            var status = r._ai_status || '';

            var badge = '<span class="ai-badge pending">—</span>';

            if (status === 'corrected') badge = '<span class="ai-badge corrected" title="AI suggested a correction">✎</span> ';

            else if (status === 'verified') badge = '<span class="ai-badge verified" title="AI verified this disposition is correct">✓</span> ';

            colsHtml += '<td>' + badge + esc(val) + '</td>';

          } else {

            colsHtml += '<td>' + esc(val) + '</td>';

          }

        }

        tr.innerHTML = colsHtml;

        tbody.appendChild(tr);

      }

      var cap = data.length > PREVIEW_LIMIT

        ? 'Showing first ' + PREVIEW_LIMIT + ' of ' + data.length + ' rows'

        : data.length + ' rows';

      document.getElementById('tableCaption').textContent = cap;

      document.getElementById('tableWrapper').style.display = 'block';

      document.getElementById('tableWrapper').classList.add('fade-in');

    }

    // ─── RENDER CONVERTED TABLE ──────────────────────────────────────────────────

    let convertedData = [];

    function renderConvertedTable(data) {

      convertedData = data.filter(r => r.conversion === 'Yes');

      if (convertedData.length === 0) {

        document.getElementById('convertedTableWrapper').style.display = 'none';

        return;

      }

      const tbody = document.getElementById('convertedBody');

      tbody.innerHTML = '';

      for (const r of convertedData) {

        let loc = '';

        const lowerSumm = String(r.session_summary || '').toLowerCase();

        if (lowerSumm.includes('bannerghatta road') || lowerSumm.includes('bannerghatta')) loc = 'Bannerghatta Road';

        else if (lowerSumm.includes('mysore rd') || lowerSumm.includes('mysore road')) loc = 'Mysore Rd';

        else if (lowerSumm.includes('ramanagara')) loc = 'Ramanagara';

        else if (lowerSumm.includes('marathahalli')) loc = 'Marathahalli';

        else if (lowerSumm.includes('kr puram') || lowerSumm.includes('k r puram')) loc = 'KR Puram';

        const tr = document.createElement('tr');

        tr.innerHTML = `

          <td>${esc(r.lead_id)}</td>

          <td>${esc(r.full_name)}</td>

          <td class="cell-phone">${esc(r.phone)}</td>

          <td>${esc(r.model)}</td>

          <td>${esc(r.language)}</td>

          <td>${esc(r.disposition_detail || r.disposition)}</td>

          <td>${esc(r.summary)}</td>

          <td>${esc(r.call_date)}</td>

          <td>${esc(loc)}</td>

        `;

        tbody.appendChild(tr);

      }

      document.getElementById('convertedTableWrapper').style.display = 'block';

      document.getElementById('convertedTableWrapper').classList.add('fade-in');

    }

    async function copyConvertedData() {

      if (!convertedData.length) return;

      const lines = [];

      for (const r of convertedData) {

        let loc = '';

        const lowerSumm = String(r.session_summary || '').toLowerCase();

        if (lowerSumm.includes('bannerghatta road') || lowerSumm.includes('bannerghatta')) loc = 'Bannerghatta Road';

        else if (lowerSumm.includes('mysore rd') || lowerSumm.includes('mysore road')) loc = 'Mysore Rd';

        else if (lowerSumm.includes('ramanagara')) loc = 'Ramanagara';

        else if (lowerSumm.includes('marathahalli')) loc = 'Marathahalli';

        else if (lowerSumm.includes('kr puram') || lowerSumm.includes('k r puram')) loc = 'KR Puram';

        const cols = [

          r.lead_id, r.full_name, r.phone, r.model, r.language, r.disposition_detail || r.disposition, r.summary, r.call_date, loc

        ].map(v => excelSafeTsvCell(v));

        lines.push(cols.join('\t'));

      }

      const tsv = lines.join('\n');

      try {

        await navigator.clipboard.writeText(tsv);

        const btn = document.getElementById('btnCopyConverted');

        btn.textContent = 'Copied';

        setTimeout(() => { btn.textContent = 'Copy Converted'; }, 2000);

      } catch (e) {

        console.error('Failed to copy converted table:', e);

      }

    }

    // ─── RENDER TEST DRIVE TABLE ──────────────────────────────────────────────────

    let testDriveData = [];

    function renderTestDriveTable(data) {

      testDriveData = data.filter(r => {

        var s = (r.disposition || r.disposition_detail || r.summary || '').toLowerCase();

        return s.includes('test drive completed') || s.includes('test-drive completed') || s.includes('completed test drive');

      });

      if (testDriveData.length === 0) {

        document.getElementById('testDriveTableWrapper').style.display = 'none';

        return;

      }

      const tbody = document.getElementById('testDriveBody');

      tbody.innerHTML = '';

      for (const r of testDriveData) {

        const tr = document.createElement('tr');

        tr.innerHTML = `

          <td>${esc(r.lead_id)}</td>

          <td class="cell-phone">${esc(r.phone)}</td>

          <td>${esc(r.model)}</td>

          <td>${esc(r.language)}</td>

          <td>${esc(r.call_date)}</td>

          <td>${esc(r.summary)}</td>

        `;

        tbody.appendChild(tr);

      }

      document.getElementById('testDriveTableWrapper').style.display = 'block';

      document.getElementById('testDriveTableWrapper').classList.add('fade-in');

    }

    async function copyTestDriveData() {

      if (!testDriveData.length) return;

      const lines = [];

      for (const r of testDriveData) {

        const cols = [

          r.lead_id, r.phone, r.model, r.language, r.call_date, r.summary

        ].map(v => excelSafeTsvCell(v));

        lines.push(cols.join('\t'));

      }

      const tsv = lines.join('\n');

      try {

        await navigator.clipboard.writeText(tsv);

        const btn = document.getElementById('btnCopyTestDrive');

        btn.textContent = 'Copied';

        setTimeout(() => { btn.textContent = 'Copy Test Drive'; }, 2000);

      } catch (e) {

        console.error('Failed to copy test drive table:', e);

      }

    }

    function getPrioClass(disp) {

      return getDispositionPriority(disp) >= 9 ? 'cell-terminal' : '';

    }



    // ─── RENDER STATS ─────────────────────────────────────────────────────────────

    function renderStats(data) {

      const total = data.length;

      const connected = data.filter(r => r.outcome === 'Connected').length;

      const notConn = data.filter(r => r.outcome === 'Not Connected').length;

      const excluded = data.filter(r => r.exclusion_flag === 'YES').length;

      const withRec = data.filter(r => r.recordings).length;

      const aiReady = data.filter(function(r) {
        if (r.outcome !== 'Connected') return false;
        var summ = (r.session_summary || '').trim();
        var hist = (r.session_history || '').trim();
        var leadSumm = (r.summary || '').trim();
        var hasLeadFallback = leadSumm && leadSumm !== 'No Response' && leadSumm.length > 3;
        var hasSession = (summ && summ !== 'No Response' && summ !== 'The session history is empty and contains no content to summarize.') || (hist && hist.length > 0);
        return (hasSession || hasLeadFallback) && (r.disposition_detail || '').trim();
      }).length;

      const skipped = connected - aiReady;

      document.getElementById('sTotal').textContent = total;

      document.getElementById('sConnected').textContent = connected;

      document.getElementById('sNotConn').textContent = notConn;

      document.getElementById('sAiReady').textContent = aiReady;

      document.getElementById('sSkipped').textContent = skipped;

      document.getElementById('sExcluded').textContent = excluded;

      document.getElementById('sRecording').textContent = withRec;

      document.getElementById('statsBar').style.display = 'flex';

      document.getElementById('statsBar').classList.add('fade-in');

    }

    function renderQualityReport(report) {

      if (!report) return;

      document.getElementById('qualityTitle').textContent = `Data quality - ${report.status}`;

      document.getElementById('qualitySubtitle').textContent = report.subtitle;

      document.getElementById('qualityMetrics').innerHTML = report.metrics.map(metric =>

        `<div class="quality-metric ${esc(metric.tone)}">

          <div class="label">${esc(metric.label)}</div>

          <div class="value">${esc(metric.value)}</div>

        </div>`

      ).join('');

      document.getElementById('qualityWarnings').innerHTML = report.warnings.map(item =>

        `<div class="quality-item ${esc(item.level)}">

          <strong>${esc(item.title)}</strong>

          <small>${esc(item.detail)}</small>

        </div>`

      ).join('');

      document.getElementById('qualitySamples').innerHTML = report.samples.map(section =>

        `<div class="quality-item">

          <strong>${esc(section.title)}</strong>

          ${section.rows.map(row => `<small class="quality-sample">${esc(row)}</small>`).join('')}

        </div>`

      ).join('');

      const card = document.getElementById('qualityCard');

      card.style.display = 'block';

      card.classList.add('fade-in');

    }

    async function copyQualityReport() {

      if (!qualityReport) return;

      const lines = [

        `Data Quality Report - ${qualityReport.status}`,

        '',

        'Metrics',

        ...qualityReport.metrics.map(metric => `${metric.label}: ${metric.value}`),

        '',

        'Warnings',

        ...qualityReport.warnings.map(item => `${item.title}: ${item.detail}`),

        '',

        'Reconciliation Samples',

        ...qualityReport.samples.flatMap(section => [

          section.title,

          ...section.rows.map(row => `- ${row}`)

        ])

      ];

      try {

        await navigator.clipboard.writeText(lines.join('\n'));

        const btn = document.getElementById('btnCopyQuality');

        btn.textContent = 'Copied';

        setTimeout(() => { btn.textContent = 'Copy Report'; }, 2000);

      } catch (e) {

        console.error('Failed to copy quality report:', e);

      }

    }

    function getDataRows(data, includeHeader) {

      var cfg = getActiveDealerConfig();

      var keys = cfg.columns.map(function(c) { return c.key; });

      var rows = includeHeader !== false ? [cfg.columns.map(function(c) { return c.header; })] : [];

      for (var ri = 0; ri < data.length; ri++) {

        var r = data[ri];

        var row = [];

        for (var ki = 0; ki < keys.length; ki++) {

          row.push(typeof r[keys[ki]] === 'string' ? r[keys[ki]].trim() : (r[keys[ki]] ?? ''));

        }

        rows.push(row);

      }

      return rows;

    }

    // ─── EXPORT TO EXCEL ──────────────────────────────────────────────────────────

    async function exportToExcel() {

      if (!processedData.length) return;

      var dataRows = getDataRows(getSortedData(processedData), true);

      var ws = XLSX.utils.aoa_to_sheet(dataRows);

      var wb = XLSX.utils.book_new();

      XLSX.utils.book_append_sheet(wb, ws, "Processed Leads");

      var summaryRows = [[

        'Full_Name', 'Phone', 'Outcome', 'Disposition', 'Disposition_detail', 'Manual_Disposition_detail', 'Summary', 'Call_Date', 'Session_Summary', 'Call_Duration', 'Channel'

      ]];

      for (var ri = 0; ri < processedData.length; ri++) {

        var r = processedData[ri];

        summaryRows.push([

          r.full_name, r.phone, r.outcome, r.disposition, r.disposition_detail || '', r.manual_disposition_detail || '', r.summary, r.call_date, r.session_summary || '', r.call_duration || '', r.channel || ''

        ].map(function(v) { return typeof v === 'string' ? v.trim() : v; }));

      }

      var summaryWs = XLSX.utils.aoa_to_sheet(summaryRows);

      XLSX.utils.book_append_sheet(wb, summaryWs, "Summary Source");

      wb.Workbook = wb.Workbook || {};

      wb.Workbook.Sheets = wb.SheetNames.map(function(name, index) { return { name: name, Hidden: index === 1 ? 1 : 0 }; });

      XLSX.writeFile(wb, "AutoNage_Disposition_Sync.xlsx");

    }

    // ─── COPY TO CLIPBOARD ────────────────────────────────────────────────────────

    async function copyData() {

      if (!processedData.length) return;

      var dataRows = getDataRows(getSortedData(processedData), false);

      var tsv = dataRows.map(function(row) {

        return row.map(function(v) { return excelSafeTsvCell(v); }).join('\t');

      }).join('\n');

      try {

        await navigator.clipboard.writeText(tsv);

        showCopyFeedback('ok');

      } catch {

        const ta = document.createElement('textarea');

        ta.value = tsv;

        ta.style.position = 'fixed';

        ta.style.left = '-9999px';

        document.body.appendChild(ta);

        ta.focus();

        ta.select();

        try {

          document.execCommand('copy');

          showCopyFeedback('ok');

        } catch {

          showCopyFeedback('warn');

        }

        document.body.removeChild(ta);

      }

    }

    function showCopyFeedback(type) {

      const msg = type === 'ok'

        ? 'Copied. Paste with Ctrl+V in Zoho.'

        : 'Auto-copy failed. Select and copy the table manually.';

      setStatus('globalStatus', msg, type);

      const btn = document.getElementById('btnCopy');

      if (!btn.dataset.origContent) btn.dataset.origContent = btn.innerHTML;

      btn.textContent = 'Copied';

      setTimeout(() => { btn.innerHTML = btn.dataset.origContent; }, 2000);

    }

    // ─── RESET ────────────────────────────────────────────────────────────────────

    function resetAll() {

      rawFile1 = null; rawFile2 = null; processedData = []; qualityReport = null;

      currentSortKey = 'full_name'; currentSortDir = 'asc';

      updateSortIndicators();

      ['f1', 'f2'].forEach(id => { document.getElementById(id).value = ''; });

      ['dz1', 'dz2'].forEach(id => { document.getElementById(id).classList.remove('has-file'); });

      ['st1', 'st2'].forEach(id => {

        const el = document.getElementById(id);

        el.className = 'dz-status';

        el.textContent = 'Drag & drop or click to browse';

      });

      document.getElementById('outputBody').innerHTML = '';

      document.getElementById('convertedBody').innerHTML = '';

      document.getElementById('testDriveBody').innerHTML = '';

      document.getElementById('qualityMetrics').innerHTML = '';

      document.getElementById('qualityWarnings').innerHTML = '';

      document.getElementById('qualitySamples').innerHTML = '';

      document.getElementById('tableWrapper').style.display = 'none';

      document.getElementById('convertedTableWrapper').style.display = 'none';

      document.getElementById('testDriveTableWrapper').style.display = 'none';

      document.getElementById('statsBar').style.display = 'none';

      document.getElementById('qualityCard').style.display = 'none';

      document.getElementById('btnCopy').style.display = 'none';

      document.getElementById('btnExport').style.display = 'none';

      document.getElementById('btnValidateAI').style.display = 'none';

      document.getElementById('btnValidateAI').textContent = 'Validate with AI';

      document.getElementById('btnValidateAI').onclick = function() { validateDispositionsWithLLM(); };

      document.getElementById('btnReset').style.display = 'none';

      document.getElementById('btnCopyQuality').textContent = 'Copy Report';

      document.getElementById('btnProcess').disabled = true;

      document.getElementById('btnProcess').classList.remove('ready');

      ['pill1', 'pill2', 'pill3', 'pill4'].forEach(id => document.getElementById(id).classList.remove('active'));

      setStatus('globalStatus', '', '');

    }

    // ─── UI HELPERS ───────────────────────────────────────────────────────────────

    function setStatus(id, msg, type) {

      const el = document.getElementById(id);

      if (!el) return;

      el.textContent = msg;

      el.className = 'status-msg' + (type ? ' ' + type : '');

    }

    function showOverlay(msg, total) {

      isProcessing = true;

      document.getElementById('processingMsg').textContent = msg;

      document.getElementById('processingOverlay').style.display = 'flex';

      var track = document.getElementById('progressTrack');

      var counter = document.getElementById('progressCounter');

      if (typeof total !== 'undefined' && total > 0) {

        track.style.display = 'block';

        counter.style.display = 'inline';

        counter.textContent = '0/' + total;

        document.getElementById('progressFill').style.width = '0%';

      } else {

        track.style.display = 'none';

        counter.style.display = 'none';

      }

    }

    function hideOverlay() {

      isProcessing = false;

      document.getElementById('processingOverlay').style.display = 'none';

    }

    function showAiStatusBar(total) {
      AiValidator.showStatusBar(total);
      var msg = document.getElementById('aiStatusMsg');
      var batch = document.getElementById('aiStatusBatch');
      if (msg) msg.textContent = 'AI validating ' + total + ' dispositions…';
      var numBatches = Math.ceil(total / LLM_DISPOSITION_BATCH_SIZE);
      if (batch) batch.textContent = '0/' + numBatches + ' batches';
    }

    function updateAiStatusBar(done, total, message, pct, correctedResults) {
      AiValidator.updateStatusBar(done, total, message, pct, correctedResults);
    }

    function hideAiStatusBar(correctedResults) {
      AiValidator.hideStatusBar(correctedResults, AiValidator.isCancelled(), function() { validateDispositionsWithLLM(true); });
    }

    function tick() { return new Promise(r => setTimeout(r, 20)); }

    function updateProcessBtn() {

      document.getElementById('btnProcess').disabled = !(rawFile1 && rawFile2);

      updateStepPills();

    }

    function setFileStatus(id, filename) {

      const el = document.getElementById(id);

      if (!el) return;

      el.className = 'dz-status ok';

      el.textContent = `Loaded: ${filename}`;

    }

    // ─── FILE INPUT HANDLING ──────────────────────────────────────────────────────

    function updateStepPills() {

      const p1 = document.getElementById('pill1');

      const p2 = document.getElementById('pill2');

      const p3 = document.getElementById('pill3');

      const p4 = document.getElementById('pill4');

      if (rawFile1) p1.classList.add('active'); else p1.classList.remove('active');

      if (rawFile2) p2.classList.add('active'); else p2.classList.remove('active');

      if (rawFile1 && rawFile2) {

        p3.classList.add('active');

        document.getElementById('btnProcess').classList.add('ready');

      } else {

        p3.classList.remove('active');

        document.getElementById('btnProcess').classList.remove('ready');

      }

    }

    document.getElementById('f1').addEventListener('change', async function () {

      if (!this.files[0]) return;

      rawFile1 = this.files[0];

      setFileStatus('st1', rawFile1.name);

      document.getElementById('dz1').classList.add('has-file');

      updateProcessBtn();

      updateStepPills();

      // Auto-detect last_session_id from the lead file

      try {

        const ab = await readFileAsArrayBuffer(rawFile1);

        const rows = parseSheet(ab);

        if (rows.length) {

          const idCandidates = ['last_session_id', 'session_id'];

          let idCol = null;

          for (const c of idCandidates) {

            if (rows[0].hasOwnProperty(c)) { idCol = c; break; }

          }

          if (idCol) {

            let maxId = 0;

            for (const row of rows) {

              const raw = String(row[idCol] || '').trim();

              const num = parseInt(raw, 10);

              if (!isNaN(num) && num > maxId) maxId = num;

            }

            if (maxId > 0) {

              const nextId = maxId + 1;

              document.getElementById('leadIdStart').value = nextId;

              setStatus('globalStatus', `Lead ID auto-set to ${nextId} (from last_session_id max: ${maxId})`, 'ok');

            }

          }

        }

      } catch (e) {

        console.warn('Could not auto-detect last_session_id:', e);

      }

    });

    document.getElementById('f2').addEventListener('change', function () {

      if (!this.files[0]) return;

      rawFile2 = this.files[0];

      setFileStatus('st2', rawFile2.name);

      document.getElementById('dz2').classList.add('has-file');

      updateProcessBtn();

      updateStepPills();

    });

    // ─── DRAG AND DROP ────────────────────────────────────────────────────────────

    function setupDragDrop(dzId, fileInputId) {

      const dz = document.getElementById(dzId);

      const fi = document.getElementById(fileInputId);

      dz.addEventListener('dragover', e => {

        e.preventDefault();

        dz.classList.add('drag-over');

      });

      dz.addEventListener('dragleave', () => dz.classList.remove('drag-over'));

      dz.addEventListener('drop', e => {

        e.preventDefault();

        dz.classList.remove('drag-over');

        const file = e.dataTransfer.files[0];

        if (!file) return;

        const dt = new DataTransfer();

        dt.items.add(file);

        fi.files = dt.files;

        fi.dispatchEvent(new Event('change'));

      });

      dz.addEventListener('keydown', e => {

        if (e.key === 'Enter' || e.key === ' ') fi.click();

      });

    }

    setupDragDrop('dz1', 'f1');

    setupDragDrop('dz2', 'f2');

    /* ── THEME ────────────────────────────────────────────────────────── */

    applyTheme(localStorage.getItem('jejo-theme') || 'dark');

    renderTableHeader();

    syncApiKeyControl();

    // ─── INTERACTIVE DOODLE GUIDE ────────────────────────────────────────────

    function cleanGuideArrow(sx, sy, ex, ey) {

      // Clean bezier curve with a slight arc - no randomness

      var cx = (sx + ex) / 2;

      var cy = (sy + ey) / 2 - 20;

      return 'M' + sx + ',' + sy + ' Q' + cx + ',' + cy + ' ' + ex + ',' + ey;

    }

    const guideSteps = [

      {

        selector: '#dz1',

        title: 'Upload Audience & Leads',

        desc: 'Drop your AutoEngage Audience & Leads export here. This file contains lead info, dispositions, model preferences, and seating capacity.',

        arrow: cleanGuideArrow

      },

      {

        selector: '#dz2',

        title: 'Upload Sessions',

        desc: 'Drop the Sessions export here. It provides call summaries, recording URLs, sentiment scores, and channel info per phone number.',

        arrow: cleanGuideArrow

      },

      {

        selector: '#btnProcess',

        title: 'Process Both Files',

        desc: 'Once both files are uploaded, click this to merge them into the Zoho Master Sheet format with business rules applied automatically.',

        arrow: cleanGuideArrow

      },

      {

        selector: '#dealerSelect',

        title: 'Choose Dealership',

        desc: 'Select your dealership from this dropdown. It controls the output column layout, business rules, and summary source column.',

        arrow: cleanGuideArrow

      },

      {

        selector: '#btnCopy',

        title: 'Copy All Data',

        desc: 'After processing, click here to copy the entire output table to clipboard. Then paste directly into your Zoho Master Sheet.',

        arrow: cleanGuideArrow

      },

      {

        selector: '#btnExport',

        title: 'Export Excel',

        desc: 'Prefer a file? This exports the processed data as a .xlsx file with all columns and formatting ready to download.',

        arrow: cleanGuideArrow

      },

      {

        selector: '#btnReset',

        title: 'Reset',

        desc: 'Clears all uploaded files, processed data, stats, and tables so you can start a fresh batch from scratch.',

        arrow: cleanGuideArrow

      }

    ];

    var guideCurrentStep = 0;

    var guideActive = false;

    var guideUnhiddenEl = null;      // element currently made visible by guide

    var guideUnhiddenOrig = '';      // its original display value

    function guideRestoreUnhidden() {

      if (guideUnhiddenEl) {

        guideUnhiddenEl.style.display = guideUnhiddenOrig;

        guideUnhiddenEl.style.visibility = '';

        guideUnhiddenEl = null;

        guideUnhiddenOrig = '';

      }

    }

    function startGuide() {

      guideCurrentStep = 0;

      guideActive = true;

      guideUnhiddenEl = null;

      guideUnhiddenOrig = '';

      document.getElementById('guideOverlay').classList.add('active');

      document.body.style.overflow = 'hidden';

      updateGuideStep();

    }

    function exitGuide() {

      guideRestoreUnhidden();

      guideActive = false;

      document.getElementById('guideOverlay').classList.remove('active');

      document.getElementById('guideHighlight').classList.remove('show');

      document.getElementById('guideCard').classList.remove('show');

      document.getElementById('guideArrowSvg').innerHTML = '';

      document.body.style.overflow = '';

    }

    function nextGuideStep() {

      if (guideCurrentStep < guideSteps.length - 1) {

        guideCurrentStep++;

        updateGuideStep();

      }

    }

    function prevGuideStep() {

      if (guideCurrentStep > 0) {

        guideCurrentStep--;

        updateGuideStep();

      }

    }

    function updateGuideStep() {

      var step = guideSteps[guideCurrentStep];

      var el = document.querySelector(step.selector);

      if (!el) return;

      // Restore previously unhidden element only if it's not the current one

      if (guideUnhiddenEl && guideUnhiddenEl !== el) {

        guideRestoreUnhidden();

      }

      // If element is hidden, make it VISIBLE so user can see it

      if (el.style.display === 'none' || getComputedStyle(el).display === 'none') {

        guideUnhiddenEl = el;

        guideUnhiddenOrig = el.style.display;

        el.style.display = 'inline-flex';

        el.style.visibility = 'visible';

      }

      // Position highlight around target

      var hl = document.getElementById('guideHighlight');

      var rect = el.getBoundingClientRect();

      var pad = 6;

      hl.style.left = (rect.left - pad) + 'px';

      hl.style.top = (rect.top - pad) + 'px';

      hl.style.width = (rect.width + pad * 2) + 'px';

      hl.style.height = (rect.height + pad * 2) + 'px';

      hl.style.borderRadius = Math.max(8, getComputedStyle(el).borderRadius ? parseInt(getComputedStyle(el).borderRadius) : 8) + 'px';

      hl.classList.add('show');

      // Update card content

      document.getElementById('guideCardTitle').innerHTML =

        esc(step.title) + ' <span class="guide-card-step">' + (guideCurrentStep + 1) + ' of ' + guideSteps.length + '</span>';

      document.getElementById('guideCardDesc').textContent = step.desc;

      // Enable/disable prev/next buttons

      document.getElementById('guidePrevBtn').style.opacity = guideCurrentStep === 0 ? '0.35' : '1';

      document.getElementById('guideNextBtn').style.opacity = guideCurrentStep === guideSteps.length - 1 ? '0.35' : '1';

      // Position the card below the target element with a gap

      var card = document.getElementById('guideCard');

      var cardW = Math.min(340, window.innerWidth - 32);

      var targetCenterX = rect.left + rect.width / 2;

      var cardLeft = Math.max(16, Math.min(window.innerWidth - cardW - 16, targetCenterX - cardW / 2));

      var cardTop = rect.bottom + 20;

      // If card would go off the bottom, place it above

      var cardH = 200;

      if (cardTop + cardH > window.innerHeight - 20) {

        cardTop = Math.max(16, rect.top - cardH - 20);

      }

      card.style.left = cardLeft + 'px';

      card.style.top = cardTop + 'px';

      card.style.maxWidth = cardW + 'px';

      card.classList.add('show');

      // Draw doodle arrow from card to target

      var svg = document.getElementById('guideArrowSvg');

      var cardCenterX = cardLeft + cardW / 2;

      var cardEdgeY, targetEdgeX, targetEdgeY;

      var arrowFromX, arrowFromY;

      if (cardTop > rect.bottom) {

        // Card is below target — arrow goes from card top to target bottom

        cardEdgeY = cardTop;

        arrowFromX = cardCenterX + (Math.random() - 0.5) * 40;

        arrowFromY = cardEdgeY;

        targetEdgeX = targetCenterX + (Math.random() - 0.5) * 30;

        targetEdgeY = rect.bottom;

      } else {

        // Card is above target — arrow goes from card bottom to target top

        cardEdgeY = cardTop + cardH;

        arrowFromX = cardCenterX + (Math.random() - 0.5) * 40;

        arrowFromY = cardEdgeY;

        targetEdgeX = targetCenterX + (Math.random() - 0.5) * 30;

        targetEdgeY = rect.top;

      }

      var pathData = step.arrow(arrowFromX, arrowFromY, targetEdgeX, targetEdgeY);

      // Add arrowhead

      var headSize = 10;

      var headAngle = Math.atan2(targetEdgeY - arrowFromY, targetEdgeX - arrowFromX);

      var hx1 = targetEdgeX - headSize * Math.cos(headAngle - 0.45);

      var hy1 = targetEdgeY - headSize * Math.sin(headAngle - 0.45);

      var hx2 = targetEdgeX - headSize * Math.cos(headAngle + 0.45);

      var hy2 = targetEdgeY - headSize * Math.sin(headAngle + 0.45);

      svg.innerHTML = '' +

        '<defs>' +

          '<filter id="guideShadow" x="-2" y="-2" width="4" height="4">' +

            '<feDropShadow dx="0" dy="0" stdDeviation="1.5" flood-color="rgba(239,68,68,0.4)" flood-opacity="1"/>' +

          '</filter>' +

        '</defs>' +

        '<path d="' + pathData + '" fill="none" stroke="#ef4444" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" filter="url(#guideShadow)" opacity="0.9"/>' +

        '<path d="M' + targetEdgeX + ',' + targetEdgeY + ' L' + hx1 + ',' + hy1 + ' L' + hx2 + ',' + hy2 + ' Z" fill="#ef4444" opacity="0.9"/>';

      // Scroll target into view only if truly out of view — instant, no smooth animation

      if (rect.top < 0 || rect.bottom > window.innerHeight - 100) {

        el.scrollIntoView({ block: 'nearest' });

      }

    }

    // Keyboard shortcuts

    document.addEventListener('keydown', function(e) {

      if (!guideActive) return;

      if (e.key === 'Escape') {

        exitGuide();

        e.preventDefault();

      } else if (e.key === 'ArrowRight' || e.key === 'ArrowDown') {

        nextGuideStep();

        e.preventDefault();

      } else if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') {

        prevGuideStep();

        e.preventDefault();

      }

    });

    // Window resize handler — reposition on resize

    window.addEventListener('resize', function() {

      if (guideActive) updateGuideStep();

    });
