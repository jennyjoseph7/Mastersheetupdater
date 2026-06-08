/* ═══════════════════════════════════════════════════════════════════════
   post_sales_disposition.js — Application logic for post_sales_disposition.html
   Extracted from inline <script> in the HTML file.
   ═══════════════════════════════════════════════════════════════════════ */

let rawFile1 = null;

    let rawFile2 = null;

    let processedData = [];

    let qualityReport = null;

    let bookedRows = [];

    let completedRows = [];

    let notInterestedRows = [];

    const DEALERSHIPS = {

      ambal_service: {

        name: 'Ambal',

        workflow: 'Post-Sales Service Reminder',

        mode: 'post-sales',

        leadColumns: ['reg_number', 'vin_number', 'campaign_id', 'person_name', 'phone_number', 'vehicle_model', 'customer_score', 'workshop_code', 'next_service_due', 'odometer_reading'],

        sessionColumns: ['status', 'duration', 'start_time', 'summary', 'call_recording', 'sentiment_score', 'disposition_detail']

      },

      bullmen_service: {

        name: 'Bullmen',

        workflow: 'Post-Sales Service Reminder',

        mode: 'post-sales',

        leadColumns: ['reg_number', 'campaign_id', 'person_name', 'phone_number', 'vehicle_model', 'workshop_code', 'next_service_due', 'vin_number'],

        sessionColumns: ['status', 'summary', 'duration', 'start_time', 'call_recording', 'sentiment_score', 'disposition_detail']

      },

      fortune_service: {

        name: 'Fortune Toyota',

        workflow: 'Post-Sales Service Reminder',

        mode: 'post-sales',

        leadColumns: ['campaign_id', 'person_name', 'phone_number', 'vehicle_model', 'reg_number', 'vin_number', 'next_service_due'],

        sessionColumns: ['status', 'duration', 'start_time', 'summary', 'call_recording', 'sentiment_score', 'disposition_detail', 'service_type']

      },

      icare_feedback: {

        name: 'Icare',

        workflow: 'Post-Sales Feedback Reminder',

        mode: 'post-sales',

        leadColumns: ['campaign_id', 'person_name', 'phone_number', 'vehicle_model', 'reg_number', 'vin_number', 'showroom_code'],

        sessionColumns: ['status', 'duration', 'start_time', 'summary', 'call_recording', 'sentiment_score', 'disposition_detail']

      },

      pressana_post_service_feedback: {

        name: 'Pressana Kia',

        workflow: 'Post Service Feedback',

        mode: 'post-sales',

        leadColumns: ['campaign_id', 'phone_number', 'last_service_date'],

        sessionColumns: ['duration', 'status', 'start_time', 'sentiment_score', 'summary', 'call_recording', 'disposition_detail']

      },

      perfect_riders_service: {

        name: 'Perfect Riders',

        workflow: 'Post-Sales Service Reminder',

        mode: 'post-sales',

        leadColumns: ['campaign_id', 'phone_number', 'existing_vehicle_model'],

        sessionColumns: ['duration', 'status', 'start_time', 'sentiment_score', 'summary', 'call_recording', 'disposition_detail']

      },

      pressana_service_feedback: {

        name: 'Pressana',

        workflow: 'Post-Sales Service Reminder and Service Feedback',

        mode: 'post-sales',

        leadColumns: ['campaign_id', 'phone_number', 'existing_vehicle_model'],

        sessionColumns: ['duration', 'status', 'start_time', 'sentiment_score', 'summary', 'call_recording', 'disposition_detail']

      },

      suryabala_service: {

        name: 'Suryabala Honda',

        workflow: 'Post-Sales Service Reminder',

        mode: 'post-sales',

        leadColumns: ['reg_number', 'campaign_id', 'person_name', 'phone_number', 'vehicle_model', 'next_service_due', 'last_service_type', 'vin_number'],

        sessionColumns: ['status', 'summary', 'duration', 'start_time', 'call_recording', 'sentiment_score', 'disposition_detail']

      },

    };

    const OUTPUT_SCHEMAS = {

      // Columns derived from disposition.md requirements. Each schema defines the final

      // output table/clipboard/export column order per dealer.

      pressana_service_feedback: [

        { header: 'PHONE_NUMBER', key: 'phone_number' },

        { header: 'VEHICLE_MODEL', key: 'vehicle_model' },

        { header: 'STATUS', key: 'session_status' },

        { header: 'SUMMARY', key: 'summary' },

        { header: 'DISPOSITION_DETAILS', key: 'disposition' },

        { header: 'UPDATED_DISPOSITION', key: 'updated_disposition' },

        { header: 'CALL_DATE', key: 'call_date' },

        { header: 'SENTIMENT_SCORE', key: 'sentiment_score' },

        { header: 'RECORDINGS', key: 'call_recording' },

        { header: 'DURATION', key: 'duration' },

        { header: 'CAMPAIGN_ID', key: 'campaign_id' },

        { header: 'SESSION_ID', key: 'last_session_id' },

        { header: 'INTERESTED', key: 'interested' },

        { header: 'NUMBER OF ATTEMPTS', key: 'number_of_attempts' },

        { header: 'AUTONGAGE', key: 'autongage_disposition' },

      ],

      pressana_post_service_feedback: [

        { header: 'PHONE_NUMBER', key: 'phone_number' },

        { header: 'LAST_SERVICE_DATE', key: 'last_service_date' },

        { header: 'STATUS', key: 'session_status' },

        { header: 'SUMMARY', key: 'summary' },

        { header: 'DISPOSITION_DETAILS', key: 'disposition' },

        { header: 'UPDATED_DISPOSITION', key: 'updated_disposition' },

        { header: 'CALL_DATE', key: 'call_date' },

        { header: 'SENTIMENT', key: 'sentiment_score' },

        { header: 'RECORDINGS', key: 'call_recording' },

        { header: 'RECORDING_DURATION', key: 'duration' },

        { header: 'CAMPAIGN_ID', key: 'campaign_id' },

        { header: 'LAST_SESSION_ID', key: 'last_session_id' },

        { header: 'INTERESTED', key: 'interested' },

        { header: 'NUMBER_OF_ATTEMPTS', key: 'number_of_attempts' },

        { header: 'AUTONGAGE_DISPOSITION', key: 'autongage_disposition' },

      ],

      ambal_service: [

        { header: 'PERSON_NAME', key: 'person_name' },

        { header: 'PHONE_NUMBER', key: 'phone_number' },

        { header: 'REG_NUMBER', key: 'reg_number' },

        { header: 'VEHICLE_MODEL', key: 'vehicle_model' },

        { header: 'VIN', key: 'vin_number' },

        { header: 'STATUS', key: 'session_status' },

        { header: 'DISPOSITION_DETAILS', key: 'disposition' },

        { header: 'UPDATED_DISPOSITION', key: 'updated_disposition' },

        { header: 'SUMMARY', key: 'summary' },

        { header: 'CALL_DATE', key: 'call_date' },

        { header: 'SENTIMENT', key: 'sentiment_score' },

        { header: 'RECORDINGS', key: 'call_recording' },

        { header: 'DURATION', key: 'duration' },

        { header: 'CAMPAIGN_ID', key: 'campaign_id' },

        { header: 'SESSION_ID', key: 'last_session_id' },

        { header: 'CUSTOMER_SCORE', key: 'customer_score' },

        { header: 'NEXT_SERVICE_DUE', key: 'next_service_due' },

        { header: 'ODOMETER_READING', key: 'odometer_reading' },

        { header: 'PURPOSE_OF_VISIT', key: 'purpose_of_visit' },

      ],

      perfect_riders_service: [

        { header: 'WORKSHOP_CODE', key: 'workshop_code' },

        { header: 'PERSON_NAME', key: 'person_name' },

        { header: 'PHONE_NUMBER', key: 'phone_number' },

        { header: 'VEHICLE_MODEL', key: 'vehicle_model' },

        { header: 'REG_NUMBER', key: 'reg_number' },

        { header: 'VIN_NUMBER', key: 'vin_number' },

        { header: 'STATUS', key: 'session_status' },

        { header: 'SUMMARY', key: 'summary' },

        { header: 'DISPOSITION_DETAILS', key: 'disposition' },

        { header: 'Updated Disposition', key: 'updated_disposition' },

        { header: 'LAST_SERVICE_DATE', key: 'last_service_date' },

        { header: 'NEXT_SERVICE_DATE', key: 'next_service_due' },

        { header: 'CALL_DATE', key: 'call_date' },

        { header: 'SENTIMENT_SCORE', key: 'sentiment_score' },

        { header: 'RECORDINGS', key: 'call_recording' },

        { header: 'DURATION', key: 'duration' },

        { header: 'CAMPAIGN_ID', key: 'campaign_id' },

        { header: 'SESSION_ID', key: 'last_session_id' },

        { header: 'INTERESTED', key: 'interested' },

        { header: 'NUMBER OF ATTEMPTS', key: 'number_of_attempts' },

      ],

      fortune_service: [

        { header: 'PERSON_NAME', key: 'person_name' },

        { header: 'PHONE_NUMBER', key: 'phone_number' },

        { header: 'VEHICLE_MODEL', key: 'vehicle_model' },

        { header: 'REG_NUMBER', key: 'reg_number' },

        { header: 'VIN_NUMBER', key: 'vin_number' },

        { header: 'SUMMARY', key: 'summary' },

        { header: 'STATUS', key: 'session_status' },

        { header: 'DISPOSITION_DETAILS', key: 'disposition_detail' },

        { header: 'MANUAL_DISPOSITION', key: 'manual_disposition' },

        { header: 'CALL_DATE', key: 'call_date' },

        { header: 'SENTIMENT', key: 'sentiment_score' },

        { header: 'RECORDINGS', key: 'call_recording' },

        { header: 'DURATION', key: 'duration' },

        { header: 'CAMPAIGN_ID', key: 'campaign_id' },

        { header: 'SESSION_ID', key: 'last_session_id' },

        { header: 'INTERESTED', key: 'interested' },

        { header: 'SERVICE_TYPE', key: 'service_type' },

        { header: 'NEXT_SERVICE_DATE', key: 'next_service_due' },

        { header: 'NUMBER OF ATTEMPTS', key: 'number_of_attempts' },

      ],

      icare_feedback: [

        { header: 'PERSON_NAME', key: 'person_name' },

        { header: 'PHONE_NUMBER', key: 'phone_number' },

        { header: 'ID', key: 'lead_tags' },

        { header: 'SHOWROOM_CODE', key: 'showroom_code' },

        { header: 'SUMMARY', key: 'summary' },

        { header: 'STATUS', key: 'session_status' },

        { header: 'DISPOSITION_DETAILS', key: 'disposition' },

        { header: 'UPDATED_DISPOSITION', key: 'updated_disposition' },

        { header: 'CALL_DATE', key: 'call_date' },

        { header: 'SENTIMENT', key: 'sentiment_score' },

        { header: 'RECORDINGS', key: 'call_recording' },

        { header: 'RECORDING_DURATION', key: 'duration' },

        { header: 'CAMPAIGN_ID', key: 'campaign_id' },

        { header: 'LAST_SESSION_ID', key: 'last_session_id' },

        { header: 'SATISFIED', key: 'satisfied' },

        { header: 'NUMBER_OF_ATTEMPTS', key: 'number_of_attempts' },

        { header: 'AUTONGAGE_DISPOSITION', key: 'autongage_disposition' },

      ],

      bullmen_service: [

        { header: 'PERSON_NAME', key: 'person_name' },

        { header: 'PHONE_NUMBER', key: 'phone_number' },

        { header: 'VEHICLE_MODEL', key: 'vehicle_model' },

        { header: 'REG_NUMBER', key: 'reg_number' },

        { header: 'VIN', key: 'vin_number' },

        { header: 'DEALER_CODE', key: 'dealer_code' },

        { header: 'SUMMARY', key: 'summary' },

        { header: 'STATUS', key: 'session_status' },

        { header: 'DISPOSITION_DETAILS', key: 'disposition' },

        { header: 'UPDATED_DISPOSITION', key: 'updated_disposition' },

        { header: 'CALL_DATE', key: 'call_date' },

        { header: 'SENTIMENT', key: 'sentiment_score' },

        { header: 'RECORDINGS', key: 'call_recording' },

        { header: 'DURATION', key: 'duration' },

        { header: 'CAMPAIGN_ID', key: 'campaign_id' },

        { header: 'LAST_SESSION_ID', key: 'last_session_id' },

        { header: 'NEXT_SERVICE_DATE', key: 'next_service_due' },

        { header: 'INTERESTED', key: 'interested' },

        { header: 'NUMBER_OF_ATTEMPTS', key: 'number_of_attempts' },

        { header: 'AUTONGAGE_DISPOSITION', key: 'autongage_disposition' },

      ],

      suryabala_service: [

        { header: 'PERSON_NAME', key: 'person_name' },

        { header: 'PHONE_NUMBER', key: 'phone_number' },

        { header: 'VEHICLE_MODEL', key: 'vehicle_model' },

        { header: 'REG_NUMBER', key: 'reg_number' },

        { header: 'VIN_NUMBER', key: 'vin_number' },

        { header: 'SUMMARY', key: 'summary' },

        { header: 'STATUS', key: 'session_status' },

        { header: 'DISPOSITION_DETAILS', key: 'disposition' },

        { header: 'UPDATED_DISPOSITION', key: 'updated_disposition' },

        { header: 'CALL_DATE', key: 'call_date' },

        { header: 'SENTIMENT', key: 'sentiment_score' },

        { header: 'RECORDINGS', key: 'call_recording' },

        { header: 'DURATION', key: 'duration' },

        { header: 'CAMPAIGN_ID', key: 'campaign_id' },

        { header: 'SESSION_ID', key: 'last_session_id' },

        { header: 'INTERESTED', key: 'interested' },

        { header: 'SERVICE_TYPE', key: 'last_service_type' },

        { header: 'NEXT_SERVICE_DATE', key: 'next_service_due' },

        { header: 'NUMBER_OF_ATTEMPTS', key: 'number_of_attempts' },

      ],

    };

    function getOutputColumnsForDealer(dealerKey) {

      return OUTPUT_SCHEMAS[dealerKey] || [

        { header: 'PHONE_NUMBER', key: 'phone_number' },

        { header: 'SUMMARY', key: 'summary' },

        { header: 'STATUS', key: 'session_status' },

        { header: 'DISPOSITION_DETAILS', key: 'disposition' },

        { header: 'UPDATED_DISPOSITION', key: 'updated_disposition' },

        { header: 'CALL_DATE', key: 'call_date' },

        { header: 'RECORDINGS', key: 'call_recording' },

        { header: 'CAMPAIGN_ID', key: 'campaign_id' },

      ];

    }

    const DISPOSITION_RULES = [

      { terms: ['service booked', 'service appointment booked', 'appointment booked', 'booking confirmed', 'slot booked'], outcome: 'Connected', priority: 10, terminal: true },

      { terms: ['vehicle serviced', 'service completed', 'serviced'], outcome: 'Connected', priority: 10, terminal: true },

      { terms: ['feedback given', 'feedback received', 'feedback completed', 'feedback captured', 'happy customer'], outcome: 'Connected', priority: 10, terminal: true },

      { terms: ['complaint', 'escalation', 'negative feedback', 'unhappy', 'dissatisfied'], outcome: 'Connected', priority: 9, terminal: true },

      { terms: ['not interested', 'refused service', 'service not required', 'already serviced'], outcome: 'Connected', priority: 9, terminal: true },

      { terms: ['wrong number', 'invalid number'], outcome: 'Not Connected', priority: 9, terminal: true },

      { terms: ['dnd', 'do not disturb'], outcome: 'Not Connected', priority: 9, terminal: true },

      { terms: ['callback requested', 'call back', 'asked to call later'], outcome: 'Connected', priority: 7, terminal: false },

      { terms: ['connected', 'contacted', 'spoken', 'customer answered', 'answered'], outcome: 'Connected', priority: 6, terminal: false },

      { terms: ['not reachable', 'not connected', 'no answer', 'ringing', 'switched off', 'busy', 'user did not speak', 'voicemail'], outcome: 'Not Connected', priority: 3, terminal: false }

    ];

    const PREVIEW_LIMIT = 200;

    const ROLE_CONFIDENCE_MARGIN = 2;

    // ── SORT STATE (mirrors pre-sales sheet behaviour) ────────────────────────────

    // Sortable keys in this tool: person_name | phone_number | disposition_detail

    let currentSortKey = 'person_name';   // default sort by name

    let currentSortDir = 'asc';           // 'asc' | 'desc' | null

    function toggleSort(key) {

      if (currentSortKey === key) {

        if (currentSortDir === 'asc') currentSortDir = 'desc';

        else if (currentSortDir === 'desc') { currentSortKey = null; currentSortDir = null; }

      } else {

        currentSortKey = key;

        currentSortDir = 'asc';

      }

      updateSortIndicators();

      renderTable();

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

      return sorted;

    }



    function safeRecordingHref(value) {

      const raw = String(value ?? '').trim();

      if (!raw) return null;

      const lower = raw.toLowerCase();

      if (lower.startsWith('javascript:') || lower.startsWith('data:') || lower.startsWith('vbscript:')) return null;

      if (lower.startsWith('http://') || lower.startsWith('https://')) return raw;

      if (lower.startsWith('s3:')) return raw;

      // If it looks like a domain/path, assume https; otherwise omit link.

      if (/^[a-z0-9.-]+\.[a-z]{2,}(?:[/:?#].*)?$/i.test(raw)) return `https://${raw}`;

      return null;

    }















    function detectPhones(obj) {

      const phones = new Set();

      const exactNames = ['phone_number', 'phone', 'mobile', 'contact', 'contact_number', 'customer_phone', 'mobile_number'];

      for (const c of exactNames) {

        const n = normalizePhone(obj[c]);

        if (n) phones.add(n);

      }

      const raw = Array.isArray(obj.__raw) ? obj.__raw : Object.values(obj);

      for (const val of raw) {

        const s = clean(val);

        if (!s) continue;

        if (isPhoneLike(s)) {

          const n = normalizePhone(s);

          if (n) phones.add(n);

        }

        const matches = s.match(/\+?(?:91|0)?[\s-]?\d{10,12}\b/g);

        if (matches) {

          for (const m of matches) {

            const n = normalizePhone(m);

            if (n) phones.add(n);

          }

        }

      }

      return Array.from(phones);

    }

    function get(row, candidates) {

      for (const c of candidates) {

        if (row && row[c] !== undefined && clean(row[c]) !== '') return clean(row[c]);

      }

      return '';

    }

    function detectDate(row) {

      return get(row, [

        'start_time',

        'start_date',

        'call_start_time',

        'call_time',

        'created',

        'created_at',

        'date',

        'timestamp',

        'call_date',

        'updated',

        'updated_at'

      ]);

    }

    function detectRecording(row) {

      const direct = get(row, ['call_recording', 'recording', 'recording_url', 'call_url', 'audio_url', 'media_url']);

      if (direct) return direct;

      for (const [k, v] of Object.entries(row || {})) {

        if (k === '__raw' || !/record|audio|media/i.test(k)) continue;

        if (clean(v)) return clean(v);

      }

      return '';

    }

    function parseAutoEngageDate(str) {

      if (!str) return null;

      const s = String(str).trim();

      const dmyTime = s.match(/^(\d{1,2})\/(\d{1,2})\/(\d{4}),?\s*(\d{1,2})?:?(\d{2})?:?(\d{2})?\s*(am|pm)?/i);

      if (dmyTime) {

        let [, dd, mm, yyyy, hh, min, sec, ampm] = dmyTime;

        dd = parseInt(dd, 10);

        mm = parseInt(mm, 10);

        yyyy = parseInt(yyyy, 10);

        hh = parseInt(hh || '0', 10);

        min = parseInt(min || '0', 10);

        sec = parseInt(sec || '0', 10);

        if (ampm) {

          ampm = ampm.toLowerCase();

          if (ampm === 'pm' && hh !== 12) hh += 12;

          if (ampm === 'am' && hh === 12) hh = 0;

        }

        return new Date(yyyy, mm - 1, dd, hh, min, sec);

      }

      const iso = s.match(/^(\d{4})-(\d{2})-(\d{2})(?:[T\s](\d{2}):(\d{2})(?::(\d{2}))?)?/);

      if (iso) {

        return new Date(parseInt(iso[1], 10), parseInt(iso[2], 10) - 1, parseInt(iso[3], 10),

          parseInt(iso[4] || '0', 10), parseInt(iso[5] || '0', 10), parseInt(iso[6] || '0', 10));

      }

      const parsed = new Date(s);

      return Number.isNaN(parsed.getTime()) ? null : parsed;

    }

    function formatDate(str) {

      const d = parseAutoEngageDate(str);

      if (!d) return clean(str);

      return `${String(d.getMonth() + 1).padStart(2, '0')}/${String(d.getDate()).padStart(2, '0')}/${d.getFullYear()}`;

    }

    function convertEpochToIST(val) {

      if (!val) return '';

      var num = typeof val === 'number' ? val : Number(String(val).trim());

      if (!Number.isFinite(num) || num < 1000000000) return String(val).trim();

      var ts = num < 10000000000000 ? num * 1000 : num;

      var d = new Date(ts + (5.5 * 60 * 60 * 1000));

      if (isNaN(d.getTime())) return String(val).trim();

      var dd = String(d.getUTCDate()).padStart(2, '0');

      var mm = String(d.getUTCMonth() + 1).padStart(2, '0');

      var yyyy = d.getUTCFullYear();

      return dd + '/' + mm + '/' + yyyy;

    }

    function normalizedText(value) {

      return clean(value).toLowerCase().replace(/[_-]+/g, ' ').replace(/\s+/g, ' ');

    }

    function classifyDisposition(disposition, status, summary) {

      const text = normalizedText([disposition, status, summary].filter(Boolean).join(' '));

      if (!text) return { outcome: 'Unknown', priority: 1, terminal: false };

      for (const rule of DISPOSITION_RULES) {

        if (rule.terms.some(term => text.includes(term))) {

          return { outcome: rule.outcome, priority: rule.priority, terminal: rule.terminal };

        }

      }

      if (text.includes('completed') || text.includes('success')) {

        return { outcome: 'Connected', priority: 5, terminal: false };

      }

      if (text.includes('failed') || text.includes('missed')) {

        return { outcome: 'Not Connected', priority: 3, terminal: false };

      }

      return { outcome: 'Unknown', priority: 1, terminal: false };

    }

    function isServiceBooked(row) {

      var ud = clean(row.updated_disposition);

      if (ud === 'Converted') return true;

      const text = normalizedText(row.disposition_detail || '');

      return ['service booked', 'service appointment booked', 'appointment booked', 'slot booked', 'booking confirmed'].some(term => text.includes(term));

    }

    function isFeedbackOrEscalation(row) {

      const text = normalizedText([row.disposition_detail, row.summary, row.session_status].join(' '));

      return ['feedback', 'complaint', 'escalation', 'unhappy', 'dissatisfied', 'negative'].some(term => text.includes(term));

    }

    function isServiceCompleted(row) {

      var ud = clean(row.updated_disposition);

      if (ud === 'Has serviced car in another dealership' || ud === 'Existing Dealer Contact') return true;

      const text = normalizedText(row.disposition_detail || '');

      return ['vehicle serviced', 'service completed', 'has serviced car in another dealership'].some(term => text.includes(term));

    }

    function isNotInterested(row) {

      var ud = clean(row.updated_disposition);

      if (ud === 'Not Interested' || ud === 'Invalid Lead' || ud === 'Rejected') return true;

      const text = normalizedText(row.disposition_detail || '');

      return ['not interested', 'refused service', 'service not required', 'already serviced'].some(term => text.includes(term));

    }

    function extractPerfectRidersLocation(summary) {

      const text = normalizedText(summary);

      if (!text) return '';

      if (text.includes('jayanagar')) return 'JAYANAGAR';

      if (text.includes('lalbagh')) return 'LALBAGH';

      return '';

    }

    function extractPerfectRidersCRE(summary) {

      const text = normalizedText(summary);

      if (!text) return '';

      // Extract remarks after 'remarks:' or 'cre:' markers if present

      const remarkMatch = text.match(/remarks?\s*[:\-]\s*(.+)/i);

      if (remarkMatch) return remarkMatch[1].trim();

      const creMatch = text.match(/cre\s*[:\-]\s*(.+)/i);

      if (creMatch) return creMatch[1].trim();

      // Fallback: return first 120 chars as a remark summary

      const truncated = summary.trim().substring(0, 120);

      return truncated.length < summary.trim().length ? truncated + '…' : truncated;

    }

    // ─── HISTORY DETECTION & FORMATTING ─────────────────────────────────────

    function sessionScore(row) {

      let score = 0;

      const date = parseAutoEngageDate(detectDate(row));

      if (date) score += date.getTime() / 100000000;

      if (get(row, ['disposition_detail', 'disposition', 'disposition_details'])) score += 10000;

      if (detectRecording(row)) score += 1000;

      if (get(row, ['summary', 'call_summary', 'conversation_summary', 'notes'])) score += 500;

      if (get(row, ['status', 'call_status'])) score += 200;

      return score;

    }

    function getSelectedDealer() {

      return DEALERSHIPS[document.getElementById('dealerSelect').value];

    }

    function buildSessionMap(rows) {

      const groups = {};

      for (const row of rows) {

        for (const phone of detectPhones(row)) {

          if (!groups[phone]) groups[phone] = [];

          groups[phone].push(row);

        }

      }

      const map = {};

      for (const [phone, sessions] of Object.entries(groups)) {

        const best = sessions.slice().sort((a, b) => sessionScore(b) - sessionScore(a))[0];

        var histRaw = detectHistory(best);

        map[phone] = {

          row: best,

          count: sessions.length,

          status: get(best, ['status', 'session_status', 'call_status', 'conversation_status']),

          disposition: get(best, ['updated_disposition', 'disposition_detail', 'disposition', 'disposition_details', 'call_disposition']),

          duration: get(best, ['duration', 'call_duration', 'talk_time', 'total_duration']),

          startTime: detectDate(best),

          summary: get(best, ['summary', 'call_summary', 'conversation_summary', 'notes', 'remarks']),

          recording: detectRecording(best),

          sentiment: get(best, ['sentiment_score', 'sentiment', 'sentiment_label', 'score']),

          // duration must come from Sessions (File 2). Some exports only have a generic "duration".

          recordingDuration: get(best, ['duration', 'call_duration', 'recording_length', 'recording_time', 'audio_duration', 'duration', 'call_duration']),

          lastSessionId: get(best, ['last_session_id', 'session_id', 'sessionid', 'id', 'call_id']),

          serviceType: get(best, ['service_type', 'service_type_session']),

          history_raw: histRaw,

          history_text: formatHistoryForPrompt(histRaw),

        };

      }

      return { map, groups };

    }

    function addQualityIssue(issues, level, text, blocking = false) {

      issues.push({ level, text, blocking: blocking || level === 'danger' });

    }

    function sampleSourceRow(row, label) {

      const raw = Array.isArray(row.__raw) ? row.__raw.map(clean).filter(Boolean).slice(0, 4).join(' | ') : '';

      return raw ? `${label}: ${raw}` : label;

    }

    function getOutputFieldChecks(dealerKey) {

      const keys = new Set(getOutputColumnsForDealer(dealerKey).map(col => col.key).filter(Boolean));

      const checks = [];

      if (keys.has('phone_number')) checks.push({ key: 'phone_number', label: 'Phone number', level: 'danger' });

      if (keys.has('campaign_id')) checks.push({ key: 'campaign_id', label: 'Campaign ID', level: 'warn' });

      if (keys.has('session_status')) checks.push({ key: 'session_status', label: 'Status', level: 'warn' });

      if (keys.has('call_date')) checks.push({ key: 'call_date', label: 'Call date', level: 'warn' });

      if (keys.has('disposition')) checks.push({ key: 'disposition', label: 'Disposition details', level: 'warn' });

      else if (keys.has('disposition_detail')) checks.push({ key: 'disposition_detail', label: 'Disposition details', level: 'warn' });

      if (keys.has('person_name')) checks.push({ key: 'person_name', label: 'Person name', level: 'warn' });

      if (keys.has('reg_number')) checks.push({ key: 'reg_number', label: 'Registration number', level: 'warn' });

      if (keys.has('vin_number')) checks.push({ key: 'vin_number', label: 'VIN number', level: 'warn' });

      if (keys.has('workshop_code')) checks.push({ key: 'workshop_code', label: 'Workshop code', level: 'warn' });

      if (keys.has('last_service_date')) checks.push({ key: 'last_service_date', label: 'Last service date', level: 'warn' });

      if (keys.has('next_service_due')) checks.push({ key: 'next_service_due', label: 'Next service date', level: 'warn' });

      return checks;

    }

    function evaluateFileRoles(role1, role2) {

      const defaultScore = role1.lead + role2.session; // File 1 = Leads, File 2 = Sessions

      const swappedScore = role2.lead + role1.session; // File 2 = Leads, File 1 = Sessions

      const filesSwapped = swappedScore > defaultScore;

      const bestScore = Math.max(defaultScore, swappedScore);

      const margin = Math.abs(defaultScore - swappedScore);

      const confidence = bestScore === 0 ? 'unknown' : margin >= ROLE_CONFIDENCE_MARGIN ? 'high' : 'low';

      return {

        filesSwapped,

        confidence,

        margin,

        defaultScore,

        swappedScore,

        file1: role1,

        file2: role2

      };

    }

    function buildQualityReport({ leadRows, sessionRows, leads, sessionGroups, output, dealer, dealerKey, roleInfo }) {

      const warnings = [];

      const samples = [];

      const leadPhones = new Map();

      const invalidLeads = [];

      leadRows.forEach((row, index) => {

        const phone = normalizePhone(get(row, ['phone_number', 'phone', 'mobile', 'contact_number', 'mobile_number']));

        if (!phone) invalidLeads.push(sampleSourceRow(row, `Lead row ${index + 2}`));

        else leadPhones.set(phone, (leadPhones.get(phone) || 0) + 1);

      });

      const leadPhoneSet = new Set(leads.map(item => item.phone));

      const duplicatePhones = Array.from(leadPhones.entries()).filter(([, count]) => count > 1);

      const sessionPhones = Object.keys(sessionGroups);

      const matched = output.filter(r => r._matched).length;

      const unmatched = output.filter(r => !r._matched);

      const unknownRows = output.filter(r => r.outcome === 'Unknown');

      const missingLeadColumns = missingColumns(leadRows, dealer.leadColumns);

      const missingSessionColumns = missingColumns(sessionRows, dealer.sessionColumns);

      const sessionsWithoutPhone = sessionRows.filter(row => !detectPhones(row).length).length;

      const sessionOnlyPhones = sessionPhones.filter(phone => !leadPhoneSet.has(phone));

      const outputColumns = getOutputColumnsForDealer(dealerKey);

      const outputKeys = new Set(outputColumns.map(col => col.key).filter(Boolean));

      const missingOutputFields = getOutputFieldChecks(dealerKey)

        .map(check => ({

          ...check,

          count: output.filter(row => !clean(row[check.key])).length

        }))

        .filter(check => check.count > 0);

      const missingRecordings = outputKeys.has('call_recording')

        ? output.filter(row => row._matched && !clean(row.call_recording)).length

        : 0;

      if (roleInfo.filesSwapped) {

        addQualityIssue(

          warnings,

          roleInfo.confidence === 'high' ? 'info' : 'warn',

          `Upload order auto-detected as swapped: File 2 is treated as Leads and File 1 as Sessions. Role scores default=${roleInfo.defaultScore}, swapped=${roleInfo.swappedScore}.`

        );

      }

      if (roleInfo.confidence !== 'high') {

        addQualityIssue(

          warnings,

          'warn',

          `Upload role confidence is ${roleInfo.confidence}. Confirm File 1/File 2 are the intended lead and session exports before using the output.`

        );

      }

      if (!leadRows.length) addQualityIssue(warnings, 'danger', 'Leads file has no data rows.');

      if (!sessionRows.length) addQualityIssue(warnings, 'danger', 'Sessions file has no data rows.');

      if (!output.length) addQualityIssue(warnings, 'danger', 'No master-sheet rows were produced.');

      if (output.length && sessionRows.length && matched === 0) {

        addQualityIssue(warnings, 'danger', 'No processed leads matched a Sessions row. Check the campaign batch or upload order before copy/export.');

      }

      if (invalidLeads.length) addQualityIssue(warnings, 'warn', `${invalidLeads.length} lead row(s) were skipped because phone number was invalid.`);

      if (duplicatePhones.length) addQualityIssue(warnings, 'warn', `${duplicatePhones.length} duplicate lead phone number(s) found.`);

      if (unmatched.length) addQualityIssue(warnings, 'warn', `${unmatched.length} lead(s) did not match a Sessions row.`);

      if (sessionOnlyPhones.length) addQualityIssue(warnings, 'info', `${sessionOnlyPhones.length} Sessions phone number(s) were not present in Leads.`);

      if (sessionsWithoutPhone) addQualityIssue(warnings, 'warn', `${sessionsWithoutPhone} session row(s) had no detectable phone number.`);

      if (unknownRows.length) addQualityIssue(warnings, 'warn', `${unknownRows.length} row(s) mapped to Unknown outcome. Review post-sales disposition rules.`);

      for (const check of missingOutputFields) {

        addQualityIssue(warnings, check.level, `${check.count} output row(s) are missing ${check.label}.`);

      }

      if (missingRecordings) addQualityIssue(warnings, 'info', `${missingRecordings} matched row(s) have no recording URL.`);

      if (missingLeadColumns.length) addQualityIssue(warnings, 'info', `Lead columns not found for ${dealer.name}: ${missingLeadColumns.join(', ')}.`);

      if (missingSessionColumns.length) addQualityIssue(warnings, 'info', `Session columns not found for ${dealer.name}: ${missingSessionColumns.join(', ')}.`);

      const blocked = warnings.some(w => w.blocking);

      const review = warnings.some(w => w.level === 'warn' || w.level === 'danger');

      if (!warnings.length) addQualityIssue(warnings, 'ok', 'All validation checks passed. Ready to copy or export.');

      if (invalidLeads.length) samples.push({ title: 'Invalid lead phones', rows: invalidLeads.slice(0, 5) });

      if (duplicatePhones.length) samples.push({ title: 'Duplicate lead phones', rows: duplicatePhones.slice(0, 5).map(([phone, count]) => `${phone} appears ${count} times`) });

      const unmatchedSamples = unmatched.slice(0, 5).map(r => `${r.phone_number}${r.person_name ? ' - ' + r.person_name : ''}`);

      if (unmatchedSamples.length) samples.push({ title: 'Unmatched leads', rows: unmatchedSamples });

      if (sessionOnlyPhones.length) samples.push({ title: 'Session-only phones', rows: sessionOnlyPhones.slice(0, 5) });

      if (unknownRows.length) samples.push({ title: 'Unknown outcomes', rows: unknownRows.slice(0, 5).map(r => `${r.phone_number}: ${r.disposition_detail || r.session_status || '(blank)'}`) });

      if (missingOutputFields.length) {

        samples.push({

          title: 'Missing output fields',

          rows: missingOutputFields.slice(0, 5).map(check => `${check.label}: ${check.count} row(s)`)

        });

      }

      if (!samples.length) samples.push({ title: 'No samples', rows: ['No invalid, duplicate, unmatched, or unknown rows to sample.'] });

      return {

        title: blocked ? 'Blocked - fix input files' : (review ? 'Review needed' : 'Ready to copy'),

        state: blocked ? 'blocked' : (review ? 'review' : 'clean'),

        canExport: output.length > 0 && !blocked,

        warnings,

        samples,

        counts: {

          leadRows: leadRows.length,

          sessionRows: sessionRows.length,

          leads: leads.length,

          matched,

          unmatched: unmatched.length,

          invalidLeads: invalidLeads.length,

          duplicatePhones: duplicatePhones.length,

          sessionPhones: sessionPhones.length,

          sessionOnlyPhones: sessionOnlyPhones.length,

          sessionsWithoutPhone,

          unknown: unknownRows.length

        },

        roleInfo,

        summary: [

          `${leads.length} valid lead(s)`,

          `${matched}/${output.length} matched`,

          `${sessionPhones.length} session phone(s)`,

          `role confidence: ${roleInfo.confidence}`

        ]

      };

    }

    function missingColumns(rows, expected) {

      if (!rows.length || !expected || expected.some(col => col.startsWith('Use '))) return [];

      const cols = new Set(Object.keys(rows[0]).filter(k => k !== '__raw'));

      return expected.filter(col => !cols.has(canonicalHeader(col)));

    }

    function scoreFileRole(rows) {

      if (!rows.length) return { lead: 0, session: 0 };

      const cols = new Set(Object.keys(rows[0]).filter(k => k !== '__raw'));

      const leadHints = [

        'phone_number', 'person_name', 'customer_name', 'name', 'campaign_id',

        'vehicle_model', 'reg_number', 'vin_number', 'next_service_due',

        'last_service_date', 'lead_tags', 'lead_id'

      ];

      const sessionHints = [

        'status', 'session_status', 'call_status', 'summary', 'call_summary',

        'disposition_detail', 'disposition', 'duration', 'start_time', 'start_date',

        'created', 'call_date', 'sentiment_score', 'sentiment',

        'call_recording', 'recording_url', 'session_id', 'last_session_id'

      ];

      let lead = 0;

      let session = 0;

      for (const key of leadHints) if (cols.has(key)) lead++;

      for (const key of sessionHints) if (cols.has(key)) session++;

      return { lead, session };

    }

    async function processFiles() {

      const dealerKey = document.getElementById('dealerSelect').value;

      const dealer = DEALERSHIPS[dealerKey];

      if (!rawFile1 || !rawFile2) return;

      showOverlay('Parsing files...');

      await tick();

      try {

        const startId = parseInt(document.getElementById('leadIdStart')?.value, 10) || 0;

        const selectedLanguage = document.getElementById('langSelect')?.value || '';

        const [ab1, ab2] = await Promise.all([readFileAsArrayBuffer(rawFile1), readFileAsArrayBuffer(rawFile2)]);

        const rows1 = parseSheet(ab1);

        const rows2 = parseSheet(ab2);

        const role1 = scoreFileRole(rows1);

        const role2 = scoreFileRole(rows2);

        const roleInfo = evaluateFileRoles(role1, role2);

        const filesSwapped = roleInfo.filesSwapped;

        const leadRows = filesSwapped ? rows2 : rows1;

        const sessionRows = filesSwapped ? rows1 : rows2;

        showOverlay('Reconciling leads and sessions...');

        await tick();

        const leads = [];

        for (const row of leadRows) {

          const phone = normalizePhone(get(row, ['phone_number', 'phone', 'mobile', 'contact_number', 'mobile_number']));

          if (!phone) continue;

          leads.push({ row, phone });

        }

        const { map: sessionMap, groups: sessionGroups } = buildSessionMap(sessionRows);

        const output = [];

        for (const { row, phone } of leads) {

          const sess = sessionMap[phone] || {};

          const classification = classifyDisposition(sess.disposition, sess.status, sess.summary);

          const vehicleModel = get(row, ['vehicle_model', 'existing_vehicle_model', 'model', 'car_model']);

          const leadId = startId > 0 ? `L-${startId + output.length}` : '';

          const attempts = sess.count || (sessionGroups[phone]?.length || 0);

          const interested = classification.outcome === 'Connected' ? 'YES' : '';

          const satisfied = (classification.outcome === 'Connected' && isFeedbackOrEscalation({ disposition_detail: sess.disposition, summary: sess.summary, session_status: sess.status }))

            ? 'YES'

            : '';

          output.push({

            lead_id: leadId,

            dealership: dealer.name,

            workflow: dealer.workflow,

            campaign_id: get(row, ['campaign_id', 'campaign']),

            phone_number: phone,

            person_name: get(row, ['person_name', 'person_name1', 'customer_name', 'name', 'full_name']),

            reg_number: get(row, ['reg_number', 'registration_number', 'vehicle_registration_number']),

            vin_number: get(row, ['vin_number', 'vin', 'chassis_number']),

            vehicle_model: vehicleModel,

            language: selectedLanguage,

            workshop_code: get(row, ['workshop_code', 'workshop', 'location_code', 'dealer_code', 'dealer']),

            dealer_code: get(row, ['workshop_code', 'workshop', 'location_code', 'dealer_code', 'dealer']),

            lead_tags: get(row, ['lead_tags', 'lead_tag', 'tags', 'tag', 'id', 'lead_id', 'leadid', 'customer_id']),

            next_service_due: get(row, ['next_service_due', 'service_due_date', 'next_due_date']),

            last_service_date: dealerKey === 'perfect_riders_service'

              ? convertEpochToIST(get(row, [

                  'last_service_date',

                  'last_service_dt',

                  'last_service_done_date',

                  'last_service_done',

                  'last_service_on',

                  'last_service',

                  'service_date',

                  'service_done_date',

                  'service_completed_date'

                ]))

              : get(row, [

                  'last_service_date',

                  'last_service_dt',

                  'last_service_done_date',

                  'last_service_done',

                  'last_service_on',

                  'last_service',

                  'service_date',

                  'service_done_date',

                  'service_completed_date'

                ]),

            customer_score: get(row, ['customer_score', 'score']),

            odometer_reading: get(row, ['odometer_reading', 'odometer', 'kms']),

            last_service_type: get(row, ['last_service_type', 'service_type']),

            manual_disposition: get(row, [

              'manual_disposition',

              'manual disposition',

              'manual_disposition_detail',

              'manual_disposition_details',

              'manual_disposition_status',

              'manual_dispo',

              'manual_status'

            ]),

            session_status: sess.status || '',

            disposition: sess.disposition || '',

            disposition_detail: sess.disposition || '',

            outcome: classification.outcome,

            call_date: formatDate(sess.startTime || ''),

            duration: sess.duration || '',

            summary: sess.summary || '',

            session_history: sess.history_text || '',

            sentiment_score: sess.sentiment || '',

            call_recording: sess.recording || '',

            recording_duration: sess.recordingDuration || '',

            last_session_id: sess.lastSessionId || '',

            number_of_attempts: dealerKey === 'perfect_riders_service' && startId > 0

              ? `=COUNTIF(C:C;${phone})`

              : (attempts ? String(attempts) : ''),

            interested,

            satisfied,

            autongage_disposition: sess.disposition || '',

            service_location: dealerKey === 'perfect_riders_service'

              ? extractPerfectRidersLocation(sess.summary)

              : '',

            service_type: sess.serviceType || '',

            lead_row_id: get(row, ['id', 'lead_id', 'leadid', 'customer_id']),

            exclusion_flag: classification.terminal ? 'YES' : '',

            _matched: Boolean(sess.row),

            _priority: classification.priority

          });

        }

        processedData = output;

        qualityReport = buildQualityReport({ leadRows, sessionRows, leads, sessionGroups, output, dealer, dealerKey, roleInfo });

        // Separate preview rows by disposition type

        var allOutput = output;

        // Classify rows with mutual exclusion: each row goes to at most one preview table

        bookedRows = allOutput.filter(isServiceBooked);

        completedRows = allOutput.filter(function(r) { return !isServiceBooked(r) && isServiceCompleted(r); });

        notInterestedRows = allOutput.filter(function(r) { return !isServiceBooked(r) && !isServiceCompleted(r) && isNotInterested(r); });

        processedData = allOutput;

        renderAll();

        hideOverlay();

        const roleNote = filesSwapped ? ' Upload order was auto-swapped.' : '';

        const statusType = qualityReport.canExport ? (qualityReport.state === 'review' ? 'warn' : 'ok') : 'err';

        const statusText = qualityReport.canExport

          ? `${output.length} post-sales lead(s) processed for ${dealer.name}.${roleNote}`

          : `${output.length} post-sales lead(s) processed, but copy/export is blocked until validation issues are fixed.${roleNote}`;

        setStatus('globalStatus', statusText, statusType);

        document.getElementById('btnCopy').style.display = '';

        document.getElementById('btnCopy').disabled = !qualityReport.canExport;

        document.getElementById('btnExport').style.display = '';

        document.getElementById('btnExport').disabled = !qualityReport.canExport;

        document.getElementById('btnValidateAI').style.display = '';

        document.getElementById('btnValidateAI').disabled = false;

        document.getElementById('btnValidateAI').textContent = 'Validate with AI';

        document.getElementById('btnValidateAI').onclick = function() { validateDispositionsWithLLM(); };

        document.getElementById('btnReset').style.display = '';

      } catch (e) {

        hideOverlay();

        console.error(e);

        setStatus('globalStatus', `Error: ${e.message}`, 'err');

      }

    }

    function renderAll() {

      renderStats();

      renderQualityReport();

      renderTable();

      renderPreviewTables();

    }

    function renderStats() {

      const matched = processedData.filter(r => r._matched).length;

      const booked = bookedRows.length;

      const completed = completedRows.length;

      const notInterested = notInterestedRows.length;

      const notConnected = processedData.filter(r => r.outcome === 'Not Connected').length;

      const unknown = processedData.filter(r => r.outcome === 'Unknown').length;

      document.getElementById('statLeads').textContent = processedData.length;

      document.getElementById('statMatched').textContent = matched;

      document.getElementById('statBooked').textContent = booked;

      document.getElementById('statCompleted').textContent = completed;

      document.getElementById('statNotInterested').textContent = notInterested;

      document.getElementById('statNotConnected').textContent = notConnected;

      document.getElementById('statUnknown').textContent = unknown;

      document.getElementById('statsBar').style.display = 'flex';

    }

    function renderQualityReport() {

      if (!qualityReport) return;

      const card = document.getElementById('qualityCard');

      card.className = `quality-card ${qualityReport.state || 'review'}`;

      document.getElementById('qualityTitle').textContent = qualityReport.title;

      document.getElementById('qualityMeta').textContent = (qualityReport.summary || []).join(' - ');

      document.getElementById('qualityWarnings').innerHTML = qualityReport.warnings

        .map(w => `<div class="quality-item ${esc(w.level)}">${esc(w.text)}</div>`).join('');

      document.getElementById('qualitySamples').innerHTML = qualityReport.samples

        .map(s => `<div class="quality-item info"><strong>${esc(s.title)}</strong><br>${s.rows.map(r => esc(r)).join('<br>')}</div>`).join('');

      card.style.display = 'block';

    }

    function renderTable() {

      const dealer = getSelectedDealer();

      const OUTPUT_COLUMNS = getOutputColumnsForDealer(document.getElementById('dealerSelect').value);

      const head = document.getElementById('outputHead');

      const body = document.getElementById('outputBody');

      head.innerHTML = OUTPUT_COLUMNS.map(col => {

        if (col.key === 'person_name') {

          return `<th class="th-sortable" data-sort-key="person_name" onclick="toggleSort('person_name')">${esc(col.header)}</th>`;

        }

        if (col.key === 'phone_number') {

          return `<th class="th-sortable" data-sort-key="phone_number" onclick="toggleSort('phone_number')">${esc(col.header)}</th>`;

        }

        if (col.key === 'disposition_detail') {

          return `<th class="th-sortable" data-sort-key="disposition_detail" onclick="toggleSort('disposition_detail')">${esc(col.header)}</th>`;

        }

        return `<th>${esc(col.header)}</th>`;

      }).join('');

      body.innerHTML = '';

      const sorted = getSortedData(processedData);

      for (const r of sorted.slice(0, PREVIEW_LIMIT)) {

        const tr = document.createElement('tr');

        tr.innerHTML = OUTPUT_COLUMNS.map(col => {

          const val = r[col.key] || '';

          if (col.key === 'phone_number') return `<td class="cell-phone">${esc(val)}</td>`;

          if (col.key === 'call_recording' && val) {

            const href = safeRecordingHref(val);

            if (!href) return `<td title="${esc(val)}">${esc(val)}</td>`;

            return `<td><a class="cell-url" href="${esc(href)}" target="_blank" rel="noopener noreferrer" title="${esc(val)}">Recording</a></td>`;

          }

          if (col.key === 'updated_disposition') {

            var st = r._ai_status || '';

            var badge = '<span class="ai-badge pending">—</span>';

            if (st === 'corrected') badge = '<span class="ai-badge corrected" title="AI suggested a correction">✎</span> ';

            else if (st === 'verified') badge = '<span class="ai-badge verified" title="AI verified this disposition is correct">✓</span> ';

            return '<td>' + badge + esc(val) + '</td>';

          }

          return `<td title="${esc(val)}">${esc(val)}</td>`;

        }).join('');

        body.appendChild(tr);

      }

      document.getElementById('tableCaption').textContent = processedData.length > PREVIEW_LIMIT

        ? `Showing first ${PREVIEW_LIMIT} of ${processedData.length} rows`

        : `${processedData.length} rows`;

      document.getElementById('tableWrapper').style.display = 'block';

      updateSortIndicators();

    }

    function renderPreviewTables() {

      renderPreviewBookedTable();

      renderPreviewCompletedTable();

      renderPreviewNotInterestedTable();

    }

    function renderPreviewBookedTable() {

      const dealerKey = document.getElementById('dealerSelect').value;

      const isPerfectRiders = dealerKey === 'perfect_riders_service';

      const wrapper = document.getElementById('bookedTableWrapper');

      const body = document.getElementById('bookedBody');

      const caption = document.getElementById('bookedCaption');

      if (!bookedRows.length) { wrapper.style.display = 'none'; return; }

      body.innerHTML = '';

      bookedRows.slice(0, PREVIEW_LIMIT).forEach(function(r) {

        var tr = document.createElement('tr');

        var location = isPerfectRiders ? extractPerfectRidersLocation(r.summary || r.disposition_detail) : '';

        var creRemarks = isPerfectRiders ? extractPerfectRidersCRE(r.summary || r.disposition_detail) : '';

        tr.innerHTML = '<td class="cell-phone">' + esc(r.phone_number) + '</td>'

          + '<td>' + esc(r.vehicle_model) + '</td>'

          + '<td>' + esc(r.disposition_detail || r.disposition) + '</td>'

          + '<td>' + esc(location) + '</td>'

          + '<td>' + esc(r.call_date) + '</td>'

          + '<td>' + esc(creRemarks) + '</td>'

          + '<td></td>';

        body.appendChild(tr);

      });

      caption.textContent = bookedRows.length > PREVIEW_LIMIT ? 'Showing first ' + PREVIEW_LIMIT + ' of ' + bookedRows.length + ' rows' : bookedRows.length + ' rows';

      wrapper.style.display = 'block';

    }

    function renderPreviewCompletedTable() {

      const dealerKey = document.getElementById('dealerSelect').value;

      const isPerfectRiders = dealerKey === 'perfect_riders_service';

      const wrapper = document.getElementById('completedTableWrapper');

      const body = document.getElementById('completedBody');

      const caption = document.getElementById('completedCaption');

      if (!completedRows.length) { wrapper.style.display = 'none'; return; }

      body.innerHTML = '';

      completedRows.slice(0, PREVIEW_LIMIT).forEach(function(r) {

        var tr = document.createElement('tr');

        var location = isPerfectRiders ? extractPerfectRidersLocation(r.summary || r.disposition_detail) : '';

        var creRemarks = isPerfectRiders ? extractPerfectRidersCRE(r.summary || r.disposition_detail) : '';

        tr.innerHTML = '<td class="cell-phone">' + esc(r.phone_number) + '</td>'

          + '<td>' + esc(r.vehicle_model) + '</td>'

          + '<td>' + esc(r.disposition_detail || r.disposition) + '</td>'

          + '<td>' + esc(location) + '</td>'

          + '<td>' + esc(r.call_date) + '</td>'

          + '<td>' + esc(creRemarks) + '</td>';

        body.appendChild(tr);

      });

      caption.textContent = completedRows.length > PREVIEW_LIMIT ? 'Showing first ' + PREVIEW_LIMIT + ' of ' + completedRows.length + ' rows' : completedRows.length + ' rows';

      wrapper.style.display = 'block';

    }

    function renderPreviewNotInterestedTable() {

      const dealerKey = document.getElementById('dealerSelect').value;

      const isPerfectRiders = dealerKey === 'perfect_riders_service';

      const wrapper = document.getElementById('notInterestedTableWrapper');

      const body = document.getElementById('notInterestedBody');

      const caption = document.getElementById('notInterestedCaption');

      if (!notInterestedRows.length) { wrapper.style.display = 'none'; return; }

      body.innerHTML = '';

      notInterestedRows.slice(0, PREVIEW_LIMIT).forEach(function(r) {

        var tr = document.createElement('tr');

        var creRemarks = isPerfectRiders ? extractPerfectRidersCRE(r.summary || r.disposition_detail) : '';

        tr.innerHTML = '<td class="cell-phone">' + esc(r.phone_number) + '</td>'

          + '<td>' + esc(r.vehicle_model) + '</td>'

          + '<td>' + esc(r.summary) + '</td>'

          + '<td>' + esc(r.call_date) + '</td>'

          + '<td>' + esc(creRemarks) + '</td>';

        body.appendChild(tr);

      });

      caption.textContent = notInterestedRows.length > PREVIEW_LIMIT ? 'Showing first ' + PREVIEW_LIMIT + ' of ' + notInterestedRows.length + ' rows' : notInterestedRows.length + ' rows';

      wrapper.style.display = 'block';

    }

    function rowsToTsv(rows, keys) {

      return rows.map(r => keys.map(k => excelSafeTsvCell(r[k])).join('\t')).join('\n');

    }

    async function copyText(text, statusText) {

      try {

        await navigator.clipboard.writeText(text);

      } catch {

        const ta = document.createElement('textarea');

        ta.value = text;

        ta.style.position = 'fixed';

        ta.style.left = '-9999px';

        document.body.appendChild(ta);

        ta.focus();

        ta.select();

        document.execCommand('copy');

        document.body.removeChild(ta);

      }

      setStatus('globalStatus', statusText, 'ok');

    }

    async function copyData() {

      if (!processedData.length) return;

      if (qualityReport && !qualityReport.canExport) {

        setStatus('globalStatus', 'Copy is blocked. Fix the validation issues shown in Data quality first.', 'err');

        return;

      }

      const OUTPUT_COLUMNS = getOutputColumnsForDealer(document.getElementById('dealerSelect').value);

      const sortedRows = getSortedData(processedData);

      await copyText(rowsToTsv(sortedRows, OUTPUT_COLUMNS.map(c => c.key)), 'Copied rows. Paste with Ctrl+V in Zoho.');

      const btn = document.getElementById('btnCopy');

      const old = btn.innerHTML;

      btn.textContent = 'Copied';

      setTimeout(() => { btn.innerHTML = old; }, 3000);

    }

    async function copyPreviewRows(type) {

      var rows, keys;

      if (type === 'booked') {

        rows = bookedRows;

        keys = ['phone_number', 'vehicle_model', 'disposition_detail', 'service_location', 'call_date', 'cre_remarks', 'common_remarks'];

      } else if (type === 'completed') {

        rows = completedRows;

        keys = ['phone_number', 'vehicle_model', 'disposition_detail', 'service_location', 'call_date', 'cre_remarks'];

      } else {

        rows = notInterestedRows;

        keys = ['phone_number', 'vehicle_model', 'summary', 'call_date', 'cre_remarks'];

      }

      if (!rows || !rows.length) { setStatus('globalStatus', 'No rows to copy.', 'warn'); return; }

      var data = rows.map(function(r) {

        var dealerKey = document.getElementById('dealerSelect').value;

        var isPerfectRiders = dealerKey === 'perfect_riders_service';

        var location = isPerfectRiders ? extractPerfectRidersLocation(r.summary || r.disposition_detail) : '';

        var creRemarks = isPerfectRiders ? extractPerfectRidersCRE(r.summary || r.disposition_detail) : '';

        return keys.map(function(k) {

          if (k === 'service_location') return location;

          if (k === 'cre_remarks') return creRemarks;

          if (k === 'common_remarks') return '';

          if (k === 'disposition_detail') return r.disposition_detail || r.disposition || '';

          if (k === 'summary') return r.summary || '';

          return String(r[k] || '').replace(/\t/g, ' ').replace(/\r?\n/g, ' ');

        }).join('\t');

      }).join('\n');

      await copyText(data, 'Copied ' + rows.length + ' preview row(s).');

      var btnMap = { booked: 'btnCopyBooked', completed: 'btnCopyCompleted', notInterested: 'btnCopyNotInterested' };

      var btn = document.getElementById(btnMap[type]);

      if (btn) {

        var orig = btn.textContent;

        btn.textContent = 'Copied';

        setTimeout(function() { btn.textContent = orig; }, 3000);

      }

    }

    async function copyQualityReport() {

      if (!qualityReport) return;

      const lines = [

        `Post-Sales Data Quality - ${qualityReport.title}`,

        `Copy/export: ${qualityReport.canExport ? 'READY' : 'BLOCKED'}`,

        ...(qualityReport.summary || []),

        '',

        ...qualityReport.warnings.map(w => `${w.level.toUpperCase()}: ${w.text}`),

        '',

        ...qualityReport.samples.flatMap(s => [s.title, ...s.rows.map(r => `- ${r}`), ''])

      ];

      await copyText(lines.join('\n'), 'Copied quality report.');

      const btn = document.getElementById('btnCopyQuality');

      btn.textContent = 'Copied';

      setTimeout(() => { btn.textContent = 'Copy Report'; }, 1800);

    }

    function exportToExcel() {

      if (!processedData.length) return;

      if (qualityReport && !qualityReport.canExport) {

        setStatus('globalStatus', 'Export is blocked. Fix the validation issues shown in Data quality first.', 'err');

        return;

      }

      const OUTPUT_COLUMNS = getOutputColumnsForDealer(document.getElementById('dealerSelect').value);

      const headers = OUTPUT_COLUMNS.map(c => c.header);

      const keys = OUTPUT_COLUMNS.map(c => c.key);

      const sortedRows = getSortedData(processedData);

      const dataRows = [headers, ...sortedRows.map(r => keys.map(k => r[k] ?? ''))];

      const wb = XLSX.utils.book_new();

      XLSX.utils.book_append_sheet(wb, XLSX.utils.aoa_to_sheet(dataRows), 'Output');

      if (bookedRows.length) {

        XLSX.utils.book_append_sheet(wb, XLSX.utils.aoa_to_sheet([

          ['PHONE_NUMBER', 'VEHICLE_MODEL', 'DISPOSITION_DETAILS', 'LOCATION', 'CALL_DATE (MM/DD/YYYY)', 'Perfect Riders CRE Remarks', 'COMMON REMARKS'],

          ...bookedRows.map(function(r) {

            var dealerKey = document.getElementById('dealerSelect').value;

            var isPR = dealerKey === 'perfect_riders_service';

            return [r.phone_number || '', r.vehicle_model || '', r.disposition_detail || r.disposition || '', isPR ? extractPerfectRidersLocation(r.summary || r.disposition_detail) : '', r.call_date || '', isPR ? extractPerfectRidersCRE(r.summary || r.disposition_detail) : '', ''];

          })

        ]), 'Service Booked');

      }

      if (completedRows.length) {

        XLSX.utils.book_append_sheet(wb, XLSX.utils.aoa_to_sheet([

          ['PHONE_NUMBER', 'VEHICLE_MODEL', 'DISPOSITION_DETAILS', 'LOCATION', 'CALL_DATE (MM/DD/YYYY)', 'Perfect Riders CRE Remarks'],

          ...completedRows.map(function(r) {

            var dealerKey = document.getElementById('dealerSelect').value;

            var isPR = dealerKey === 'perfect_riders_service';

            return [r.phone_number || '', r.vehicle_model || '', r.disposition_detail || r.disposition || '', isPR ? extractPerfectRidersLocation(r.summary || r.disposition_detail) : '', r.call_date || '', isPR ? extractPerfectRidersCRE(r.summary || r.disposition_detail) : ''];

          })

        ]), 'Service Completed');

      }

      if (notInterestedRows.length) {

        XLSX.utils.book_append_sheet(wb, XLSX.utils.aoa_to_sheet([

          ['PHONE_NUMBER', 'VEHICLE_MODEL', 'SUMMARY', 'CALL_DATE (MM/DD/YYYY)', 'Perfect Riders CRE Remarks'],

          ...notInterestedRows.map(function(r) {

            var dealerKey = document.getElementById('dealerSelect').value;

            var isPR = dealerKey === 'perfect_riders_service';

            return [r.phone_number || '', r.vehicle_model || '', r.summary || '', r.call_date || '', isPR ? extractPerfectRidersCRE(r.summary || r.disposition_detail) : ''];

          })

        ]), 'Not Interested');

      }

      const dealer = getSelectedDealer();

      const safeName = dealer.name.replace(/[^a-z0-9]+/gi, '_').replace(/^_+|_+$/g, '');

      XLSX.writeFile(wb, `AutoNage_Post_Sales_${safeName}.xlsx`);

    }

    function resetAll() {

      rawFile1 = null;

      rawFile2 = null;

      processedData = [];

      qualityReport = null;

      bookedRows = [];

      completedRows = [];

      notInterestedRows = [];

      currentSortKey = 'person_name'; currentSortDir = 'asc';

      ['f1', 'f2'].forEach(id => { document.getElementById(id).value = ''; });

      ['dz1', 'dz2'].forEach(id => document.getElementById(id).classList.remove('has-file'));

      document.getElementById('st1').className = 'dz-status';

      document.getElementById('st2').className = 'dz-status';

      document.getElementById('st1').textContent = 'Drag and drop or click to browse';

      document.getElementById('st2').textContent = 'Drag and drop or click to browse';

      ['statsBar', 'qualityCard', 'tableWrapper', 'bookedTableWrapper', 'completedTableWrapper', 'notInterestedTableWrapper'].forEach(function(id) {

        var el = document.getElementById(id);

        if (el) el.style.display = 'none';

      });

      ['outputBody', 'bookedBody', 'completedBody', 'notInterestedBody', 'qualityWarnings', 'qualitySamples', 'qualityMeta'].forEach(function(id) {

        var el = document.getElementById(id);

        if (el) el.innerHTML = '';

      });

      document.getElementById('btnCopy').style.display = 'none';

      document.getElementById('btnExport').style.display = 'none';

      document.getElementById('btnValidateAI').style.display = 'none';

      document.getElementById('btnValidateAI').textContent = 'Validate with AI';

      document.getElementById('btnValidateAI').onclick = function() { validateDispositionsWithLLM(); };

      document.getElementById('btnReset').style.display = 'none';

      setStatus('globalStatus', '', '');

      updateSortIndicators();

      updateProcessButton();

    }

    function setStatus(id, msg, type) {

      const el = document.getElementById(id);

      el.textContent = msg || '';

      el.className = 'status-msg' + (type ? ' ' + type : '');

    }

    function showOverlay(msg) {

      document.getElementById('processingMsg').textContent = msg;

      document.getElementById('processingOverlay').style.display = 'flex';

    }

    function hideOverlay() {

      document.getElementById('processingOverlay').style.display = 'none';

    }

    // ── AI Validation Status Bar (non-blocking) ──────────────────────────
    function showAiStatusBar(total) {
      AiValidator.showStatusBar(total);
      var msg = document.getElementById('aiStatusMsg');
      var batch = document.getElementById('aiStatusBatch');
      if (msg) msg.textContent = 'AI validating ' + total + ' dispositions\u2026';
      var numBatches = Math.ceil(total / LLM_DISPOSITION_BATCH_SIZE);
      if (batch) batch.textContent = '0/' + numBatches + ' batches';
    }

    function updateAiStatusBar(done, total, message, pct, correctedResults) {
      AiValidator.updateStatusBar(done, total, message, pct, correctedResults);
    }

    function hideAiStatusBar(correctedResults) {
      AiValidator.hideStatusBar(correctedResults, AiValidator.isCancelled(), function() { validateDispositionsWithLLM(true); });
    }

    function tick() {

      return new Promise(resolve => setTimeout(resolve, 20));

    }

    function updateProcessButton() {

      const dealer = getSelectedDealer();

      document.getElementById('btnProcess').disabled = !(rawFile1 && rawFile2);

    }

    function setFileStatus(id, filename) {

      const el = document.getElementById(id);

      el.className = 'dz-status ok';

      el.textContent = `Loaded: ${filename}`;

    }

    function handleDealerChange() {

      const dealer = getSelectedDealer();

      document.getElementById('leadCols').textContent = dealer.leadColumns.join(' - ');

      document.getElementById('sessionCols').textContent = dealer.sessionColumns.join(' - ');

      setStatus('globalStatus', `${dealer.name} ${dealer.workflow} selected.`, '');

      updateProcessButton();

    }

    document.getElementById('f1').addEventListener('change', function () {

      if (!this.files[0]) return;

      rawFile1 = this.files[0];

      setFileStatus('st1', rawFile1.name);

      document.getElementById('dz1').classList.add('has-file');

      updateProcessButton();

    });

    document.getElementById('f2').addEventListener('change', function () {

      if (!this.files[0]) return;

      rawFile2 = this.files[0];

      setFileStatus('st2', rawFile2.name);

      document.getElementById('dz2').classList.add('has-file');

      updateProcessButton();

    });

    function setupDragDrop(dzId, fileInputId) {

      const dz = document.getElementById(dzId);

      const input = document.getElementById(fileInputId);

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

        input.files = dt.files;

        input.dispatchEvent(new Event('change'));

      });

      dz.addEventListener('keydown', e => {

        if (e.key === 'Enter' || e.key === ' ') input.click();

      });

    }

    /* ═══════════════════════════════════════════════════════════════════════

       LLM VALIDATION — POST-SALES DISPOSITIONS

       ═══════════════════════════════════════════════════════════════════════ */var LLM_DISPOSITION_BATCH_SIZE = getConfigNumber('llmDispositionBatchSize', getConfigNumber('llmBatchSize', 6));
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
        ? String(window.JEJO_CONFIG.nvidiaApiKey || '').trim()
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

    var POST_SALES_DISPOSITIONS = {

      "Voicemail": "If the customer has asked to leave a message or voicemail.",

      "Rejected": "If the customer has rejected the offer or to even speak with the agent. repeated rejection.",

      "Language barrier": "If the customer has asked to speak in a different language and did not finish the conversation or intent of the campaign.",

      "Vehicle is commercial or part of a fleet": "The vehicle is a commercial vehicle and not applicable for the campaign purpose.",

      "Vehicle is not being run": "Vehicle is unused and not being run.",

      "Requires special spare parts": "The vehicle requires special spare parts for repair.",

      "Others": "All other disposition details not listed above.",

      "Wrong contact number": "Customer tells the agent they have the wrong person or number that was contacted",

      "Has sold/given away the car": "The customer has sold or given away the vehicle.",

      "Has moved to another location": "The customer has moved to another location.",

      "Cannot make decision on servicing": "The customer the agent has called is not the right person to make the decision.",

      "Will call workshop themselves": "The customer will contact the workshop themselves.",

      "Requested Callback": "The customer asked the agent to call back at a later date and or time.",

      "Looking for a discount": "The customer is looking for a discount on the campaign purpose.",

      "Has serviced car in another dealership": "The customer has serviced the vehicle in another dealership.",

      "Will decide tomorrow": "The customer said they would decide to service the vehicle tomorrow.",

      "Will decide within 1 to 3 days": "The customer said they would decide to service the vehicle within 1 to 3 days.",

      "Will decide within 4 to 7 days": "The customer said they would decide to service the vehicle within 4 to 7 days.",

      "Will decide within 8 to 14 days": "The customer said they would decide to service the vehicle within 8 to 14 days.",

      "Will decide within 15 to 30 days": "The customer said they would decide to service the vehicle within 15 to 30 days.",

      "Will decide within 31 to 60 days": "The customer said they would decide to service the vehicle within 31 to 60 days.",

      "Will decide within 61 to 90 days": "The customer said they would decide to service the vehicle within 61 to 90 days.",

      "Will decide after 90 days": "The customer said they would decide to service the vehicle after 90 days.",

      "Unsubscribed": "The customer asked to unsubscribed from the campaign.",

      "Call Disconnected": "The call ended abruptly without completing the campaign objective.",

      "Audio Issue": "There was issues with hearing the customer or the agent for either party.",

      "Call Quality Issue": "There was issues with the quality of the call.",

      "Connection Issue": "There was issues with the connection between the customer and the agent.",

      "Customer Busy": "The customer was busy.",

      "No Response": "The customer did not say anything at all.",

      "Price Inquiry": "The customer is interested in the price of the service.",

      "Lost to Competition": "the customer already did the campaign objective from a competitors workshop",

      "Invalid Lead": "Not a valid lead.",

      "Not Interested": "The customer specifically said they are not interested or declined the offer/service.",

      "Service Postponed": "They decided or implied they will postpone the service.",

      "Showroom Visit Planned": "Already booked a showroom visit.",

      "Existing Dealer Contact": "The customer already did the campaign objective from an existing dealership.",

      "Contact Fatigue": "customer implied they were being contacted too many times by the agent.",

      "Converted": "The customer completes the purpose of the campaign and provides the necessary information.",

      "Talk to Human": "The customer asked to speak to a human agent or customer executive instead of the digital assistant.",

      "Interested in another car same dealership": "The customer is interested in a different vehicle model from the same dealership."

    };

    var DEALER_LANGUAGES = {

      perfect_riders_service: ['Kannada', 'English'],

      fortune_service: ['Telugu', 'English'],

      ambal_service: ['Tamil', 'English'],

      bullmen_service: ['Tamil', 'English'],

      pressana_service_feedback: ['Tamil', 'English'],

      pressana_post_service_feedback: ['Tamil', 'English'],

      suryabala_service: ['Tamil', 'English'],

      icare_feedback: ['Tamil', 'English']

    };

    async function validateDispositionsWithLLM(force) {

      if (!processedData || processedData.length === 0) return;

      document.getElementById('btnValidateAI').textContent = 'Validating...';

      const apiKey = getApiKey();

      if (!apiKey) {

        setStatus('globalStatus', 'AI key required. Paste your key above and click Save.', 'err');

        return;

      }

      const dispKeys = Object.keys(POST_SALES_DISPOSITIONS);

      const dispDefs = dispKeys.map(k => `- "${k}": ${POST_SALES_DISPOSITIONS[k]}`).join('\n');

      var dealerKey = document.getElementById('dealerSelect').value;

      var dealerCfg = DEALERSHIPS[dealerKey];

      var dealerName = dealerCfg ? dealerCfg.name : 'Unknown Dealership';

      var supportedLangs = DEALER_LANGUAGES[dealerKey] || ['English'];

      const candidates = [];

      for (var i = 0; i < processedData.length; i++) {

        var r = processedData[i];

        var summ = (r.summary || '').trim();

        var hist = (r.session_history || '').trim();

        var disp = (r.disposition_detail || r.disposition || '').trim();

        var hasText = (summ && summ !== 'No Response' && summ !== 'The session history is empty and contains no content to summarize.') || (hist && hist.length > 0);

        if (hasText && disp) {

          candidates.push({ index: i, summary: summ, history: hist, currentDisp: disp, callDate: r.call_date || '', outcome: r.outcome || '', vehicleModel: r.vehicle_model || '', campaignId: r.campaign_id || '', dealerName: dealerName, supportedLanguages: supportedLangs.join(', ') });

        }

      }

      if (candidates.length === 0) {

        setStatus('globalStatus', 'No rows with session summaries to validate.', 'warn');

        return;

      }

      showAiStatusBar(candidates.length);

      var corrected = 0;

      var BATCH_SIZE = LLM_DISPOSITION_BATCH_SIZE;

      var correctedResults = {};

      var cacheInput = candidates.map(function(c) { return c.summary + '||' + c.history + '||' + c.currentDisp + '||' + c.callDate + '||' + c.outcome + '||' + c.vehicleModel + '||' + c.campaignId + '||' + c.dealerName + '||' + c.supportedLanguages; }).join('|');

      var cacheKey = 'ps-disp-validate-v3-history-' + hashStr(cacheInput);

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

            var dispKeys = Object.keys(POST_SALES_DISPOSITIONS);

            var dispDefs = dispKeys.map(function(k) { return '- "' + k + '": ' + POST_SALES_DISPOSITIONS[k]; }).join('\n');

            var dealerContext = 'Dealership: "' + (batch.length > 0 ? batch[0].dealerName : '') + '"\nSupported Languages: "' + (batch.length > 0 ? batch[0].supportedLanguages : '') + '"';

            var promptLines = batch.map(function(c, idx) {

              var safeSummary = sanitizeForPrompt(c.summary, LLM_PROMPT_CHAR_LIMIT);

              var safeHistory = sanitizeForPrompt(c.history, LLM_PROMPT_CHAR_LIMIT);

              var safeDisp = sanitizeForPrompt(c.currentDisp, LLM_PROMPT_CHAR_LIMIT);

              var safeDealer = sanitizeForPrompt(c.dealerName, LLM_PROMPT_CHAR_LIMIT);

              var safeLangs = sanitizeForPrompt(c.supportedLanguages, LLM_PROMPT_CHAR_LIMIT);

              var safeModel = sanitizeForPrompt(c.vehicleModel, LLM_PROMPT_CHAR_LIMIT);

              var safeOutcome = sanitizeForPrompt(c.outcome, LLM_PROMPT_CHAR_LIMIT);

              var safeDate = sanitizeForPrompt(c.callDate, LLM_PROMPT_CHAR_LIMIT);

              var safeCampaign = sanitizeForPrompt(c.campaignId, LLM_PROMPT_CHAR_LIMIT);

              var line = 'Row ' + idx + ':';

              if (safeSummary) line += '\n--- BEGIN SUMMARY ---\n' + safeSummary + '\n--- END SUMMARY ---';

              if (safeHistory) line += '\n--- BEGIN CONVERSATION HISTORY ---\n' + safeHistory + '\n--- END CONVERSATION HISTORY ---';

              line += '\nCurrent Disposition: "' + safeDisp + '"';

              line += '\nDealership: "' + safeDealer + '"';

              line += '\nSupported Languages: "' + safeLangs + '"';

              if (safeModel) line += '\nVehicle Model: "' + safeModel + '"';

              if (safeOutcome) line += '\nCall Outcome: "' + safeOutcome + '"';

              if (safeDate) line += '\nCall Date: "' + safeDate + '"';

              if (safeCampaign) line += '\nCampaign ID: "' + safeCampaign + '"';

              return line;

            }).join('\n\n---\n\n');

            var systemMsg = 'You are a strict disposition auditor for an automotive post-sales (service/feedback) campaign. Your job is to CRITICALLY evaluate whether the "Current Disposition" accurately describes the call. You are provided with two evidence sources for each row: 1) a Summary (short description), and 2) a Conversation History (full transcript with timestamps). The Conversation History is the STRONGEST evidence — if it conflicts with the Summary, trust the History. Additional context (Dealership, Supported Languages, Vehicle Model, Call Outcome, Call Date, Campaign ID) is also provided — use it to rule out impossible dispositions. Do NOT default to "correct" — scrutinize each match carefully.';

            var examples = 'Example 1:\nTranscript: "Customer said they will bring the car next week for service"\nCurrent Disposition: "Not Interested"\n→ isCorrect: false, correctedDisposition: "Converted"\nReason: Customer intends to service — they did not refuse.\n\n' +

              'Example 2:\nTranscript: "Customer complained about poor service quality and long wait times"\nCurrent Disposition: "Feedback Given"\n→ isCorrect: false, correctedDisposition: "Complaint / Escalation"\nReason: This is a complaint, not neutral feedback.\n\n' +

              'Example 3:\nTranscript: "Customer said the car was already serviced at another workshop"\nCurrent Disposition: "Vehicle Serviced"\n→ isCorrect: false, correctedDisposition: "Already Serviced"\nReason: Already Serviced means elsewhere. Vehicle Serviced means this campaign\'s service was done.\n\n' +

              'Example 4:\nTranscript: "Call went to ringtone but no one picked up"\nCurrent Disposition: "Not Reachable"\n→ isCorrect: false, correctedDisposition: "No Response"\nReason: No Response means the call connected but was not answered. Not Reachable means phone is off.\n\n' +

              'Example 5:\nTranscript: "Customer asked what services are included in the free service package"\nCurrent Disposition: "Happy Customer"\n→ isCorrect: false, correctedDisposition: "Requested Service Details"\nReason: The customer is asking for information, not expressing satisfaction.\n\n' +

              'Example 6:\nTranscript: "Customer said not interested and hung up"\nCurrent Disposition: "Call Completed"\n→ isCorrect: false, correctedDisposition: "Not Interested"\nReason: Customer explicitly declined.\n\n' +

              'Example 7:\nTranscript: "Customer mentioned they have sold the car"\nCurrent Disposition: "Not Interested"\n→ isCorrect: false, correctedDisposition: "Sold / Given Away"\nReason: Sold / Given Away is more specific than Not Interested.\n\n' +

              'Example 8:\nTranscript: "Call went to voicemail, left a message"\nCurrent Disposition: "Not Reachable"\n→ isCorrect: false, correctedDisposition: "Voicemail"\nReason: Reaching voicemail is not the same as not reachable.\n\n' +

              'Example 9:\nTranscript: "Customer said \'I only speak Hindi\' but dealer supports Kannada/English"\nCurrent Disposition: "Not Interested"\n→ isCorrect: false, correctedDisposition: "Language barrier"\nReason: Language barrier — customer needs a language outside the supported set for this dealership.\n\n' +

              'Example 10:\nTranscript: "Customer said they already serviced at another dealership"\nCurrent Disposition: "Not Interested"\n→ isCorrect: false, correctedDisposition: "Has serviced car in another dealership"\nReason: More specific — they did service elsewhere.\n\n' +

              'Example 11:\nTranscript: "Customer asked for a callback later"\nCurrent Disposition: "No Response"\n→ isCorrect: false, correctedDisposition: "Requested Callback"\nReason: Customer explicitly requested a callback.\n\n' +

              'Example 12:\nTranscript: "Phone rang multiple times but no one answered"\nCurrent Disposition: "Wrong Contact Number"\n→ isCorrect: false, correctedDisposition: "No Response"\nReason: No Response means call connected but unanswered. Wrong Contact Number means wrong number.\n\n' +

              'Example 13:\nTranscript: "Could not hear the customer clearly due to network issues"\nCurrent Disposition: "No Response"\n→ isCorrect: false, correctedDisposition: "Audio Issue"\nReason: Audio Issue is more specific — there was a technical problem.\n\n' +

              'Example 14:\nTranscript: "Customer confirmed they would come in for service on Saturday and provided email"\nCurrent Disposition: "Not Interested"\n→ isCorrect: false, correctedDisposition: "Converted"\nReason: Customer completed the campaign purpose and provided info — this is a conversion.\n\n' +

              'Example 15:\nTranscript: "Customer was very happy with the service and said thank you"\nCurrent Disposition: "Converted"\n→ isCorrect: false, correctedDisposition: "Happy Customer"\nReason: Happy Customer is more appropriate — no booking or info provision.';

            var userPrompt = 'VALID DISPOSITIONS:\n' + dispDefs + '\n\nLANGUAGE BARRIER RULE:\nThe active dealership is "' + dealerContext + '". The customer\'s transcript/summary may be in a language different from the dealership\'s supported languages. If the customer requested or attempted to speak in a language NOT in the supported languages list for their dealership, the disposition MUST be "Language barrier". Pay close attention to phrases like "I don\'t understand", "speak [language]", "[language] please", etc. — especially if the requested language is outside the supported set. The supported languages are only those listed for the dealership; any other language the customer requests is a barrier.\n\nEXAMPLES (learn from these patterns):\n' + examples + '\n\nNow evaluate these rows. For EACH row, respond with ONE JSON object:\n{"rowIndex":0,"isCorrect":true,"correctedDisposition":null,"confidence":"high","reason":"The summary clearly matches the disposition."}\n\nRows:\n' + promptLines + '\n\nRespond as a JSON array of objects, one per row in the same order. ONLY valid JSON.';

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

                : 'jejo-postsales-secure-handshake';

              h['X-Handshake-Token'] = handshake;

            } else {

              h['Authorization'] = 'Bearer ' + getApiKey();

              h['HTTP-Referer'] = window.location.origin;

              h['X-Title'] = 'AutoNage Post-Sales Sync';

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

        

        corrected = runnerResult.correctedCount;

        // Build cache array

        var cacheArray = [];

        for (var idx = 0; idx < candidates.length; idx++) {

          var decision = runnerResult.results.get(idx);

          if (decision && decision.isCorrect === false && decision.correctedDisposition) {

            cacheArray.push({ rowIndex: candidates[idx].index, isCorrect: false, correctedDisposition: decision.correctedDisposition });

          } else {

            cacheArray.push({ rowIndex: idx, isCorrect: true, correctedDisposition: null });

          }

        }

        try { localStorage.setItem(cacheKey, JSON.stringify(cacheArray)); } catch(e) { console.warn("localStorage write failed (private mode?):", e); }// Apply corrections

        for (var ri = 0; ri < candidates.length; ri++) {

          var dec = runnerResult.results.get(ri);

          if (dec && dec.isCorrect === false && dec.correctedDisposition) {

            correctedResults[candidates[ri].index] = dec.correctedDisposition;

          }

        }

      } else {

        // Cache hit

        try {

          for (var ci = 0; ci < cachedParsed.length; ci++) {

            var item = cachedParsed[ci];

            if (item.isCorrect === false && item.correctedDisposition) {

              correctedResults[item.rowIndex] = item.correctedDisposition;

            }

          }

          corrected = Object.keys(correctedResults).length;

        } catch(e) { console.warn("localStorage write failed (private mode?):", e); }}

var correctedIndices = Object.keys(correctedResults);

      for (var k = 0; k < correctedIndices.length; k++) {

        var rowIdx = parseInt(correctedIndices[k]);

        if (processedData[rowIdx]) {

          processedData[rowIdx].updated_disposition = correctedResults[rowIdx];

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

        renderTable();

        // Re-classify preview tables to pick up updated_disposition changes from AI

        var allForPreview = processedData;

        bookedRows = allForPreview.filter(isServiceBooked);

        completedRows = allForPreview.filter(function(r) { return !isServiceBooked(r) && isServiceCompleted(r); });

        notInterestedRows = allForPreview.filter(function(r) { return !isServiceBooked(r) && !isServiceCompleted(r) && isNotInterested(r); });

        renderPreviewBookedTable();

        renderPreviewCompletedTable();

        renderPreviewNotInterestedTable();

        setStatus('globalStatus', 'AI validated ' + candidates.length + ' rows, corrected ' + correctedIndices.length + ' dispositions. Check Updated Disposition column.', 'ok');

      } else {

        setStatus('globalStatus', 'AI validated ' + candidates.length + ' rows — all dispositions appear correct.', 'ok');

      }

      document.getElementById('btnValidateAI').textContent = '↻ Re-run AI';

      document.getElementById('btnValidateAI').onclick = function() { validateDispositionsWithLLM(true); };

    }

    syncApiKeyControl();

    applyTheme(localStorage.getItem('jejo-theme') || 'dark');

    setupDragDrop('dz1', 'f1');

    setupDragDrop('dz2', 'f2');

    handleDealerChange();
