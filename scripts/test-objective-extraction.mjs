import { parseDescription, resolveObjectives, processCreditData, repairEncoding } from '../app/credit-report/credit-utils.ts';

console.log('=== RUNNING OBJECTIVE EXTRACTION & ENCODING TESTS ===\n');

let failed = false;

function assert(condition, message) {
  if (!condition) {
    console.error(`❌ FAIL: ${message}`);
    failed = true;
  } else {
    console.log(`✅ PASS: ${message}`);
  }
}

// Test Case 1: Service Reminder with en-dash (should NOT trigger compound join)
const t1 = parseDescription('post-sales - Service Reminder – Perfect Riders Yamaha - PRV_L1_Aug24 - voice_phone - airtel - 919999999999');
assert(t1.stage === 'post-sales', 'Test 1 Stage is post-sales');
assert(t1.rawObjective === 'Service Reminder – Perfect Riders Yamaha', `Test 1 Objective is "${t1.rawObjective}" (expected "Service Reminder – Perfect Riders Yamaha")`);
assert(t1.campaign === 'PRV_L1_Aug24', `Test 1 Campaign is "${t1.campaign}" (expected "PRV_L1_Aug24")`);

// Test Case 1b: Mojibake "â" repair
const t1b = parseDescription('post-sales - Service Reminder â Perfect Riders Yamaha - PRV_L1_Aug24 - voice_phone - airtel - 919999999999');
assert(t1b.rawObjective === 'Service Reminder – Perfect Riders Yamaha', `Test 1b Mojibake repair: "${t1b.rawObjective}" (expected "Service Reminder – Perfect Riders Yamaha")`);

// Test Case 2: Exact "Perfect Riders" compound objective (segments 1 to 3 joined)
const t2 = parseDescription('post-sales - Perfect Riders - Service Reminder - WhatsApp - PRWA_OCT10_S1 - unknown - Rml - None');
assert(t2.stage === 'post-sales', 'Test 2 Stage is post-sales');
assert(t2.rawObjective === 'Perfect Riders - Service Reminder - WhatsApp', `Test 2 Objective is "${t2.rawObjective}" (expected "Perfect Riders - Service Reminder - WhatsApp")`);
assert(t2.campaign === 'PRWA_OCT10_S1', `Test 2 Campaign is "${t2.campaign}" (expected "PRWA_OCT10_S1")`);

// Test Case 3: Standard single segment objective
const t3 = parseDescription('pre-sales - R2_Pre_sales_WA - R2_Camp - whatsapp_chat - provider - 918888888888');
assert(t3.stage === 'pre-sales', 'Test 3 Stage is pre-sales');
assert(t3.rawObjective === 'R2_Pre_sales_WA', `Test 3 Objective is "${t3.rawObjective}" (expected "R2_Pre_sales_WA")`);
assert(t3.campaign === 'R2_Camp', `Test 3 Campaign is "${t3.campaign}" (expected "R2_Camp")`);

// Test Case 4: None objective resolution via campaign keyword
const t4 = parseDescription('post-sales - None - Inbound Lead Handling - whatsapp_chat - provider - None');
assert(t4.stage === 'post-sales', 'Test 4 Stage is post-sales');
assert(t4.rawObjective === '', `Test 4 Raw Objective is empty for None`);
assert(t4.campaign === 'Inbound Lead Handling', `Test 4 Campaign is "${t4.campaign}" (expected "Inbound Lead Handling")`);

const resolvedT4 = resolveObjectives([{ stage: t4.stage, rawObjective: t4.rawObjective, campaign: t4.campaign, rowIdx: 0 }]);
assert(resolvedT4[0].objective === 'Inbound Lead Handling', `Test 4 Resolved objective is "${resolvedT4[0].objective}" (expected "Inbound Lead Handling", never "None")`);

// Test Case 5: Full integration with Perfect Riders sample dataset
console.log('\n--- Test Case 5: Perfect Riders aggregation simulation ---');
const prRows = [
  // 3 campaigns under "Service Reminder – Perfect Riders Yamaha" (must aggregate into ONE objective)
  {
    'Billing ID': 'PR1',
    'Date & Time': '02 May 2026, 10:00 am',
    'Item Name': 'call_connected',
    'Channel': 'voice_phone',
    'Description': 'post-sales - Service Reminder – Perfect Riders Yamaha - PRV_L1_Aug24 - voice_phone - airtel - 919999999999',
    'Quantity': '1',
    'Credits Spent': '100',
    'Status': 'success'
  },
  {
    'Billing ID': 'PR2',
    'Date & Time': '03 May 2026, 10:00 am',
    'Item Name': 'call_connected',
    'Channel': 'voice_phone',
    'Description': 'post-sales - Service Reminder – Perfect Riders Yamaha - PRV_L2_Sep24 - voice_phone - airtel - 919999999999',
    'Quantity': '1',
    'Credits Spent': '200',
    'Status': 'success'
  },
  {
    'Billing ID': 'PR3',
    'Date & Time': '04 May 2026, 10:00 am',
    'Item Name': 'call_connected',
    'Channel': 'voice_phone',
    'Description': 'post-sales - Service Reminder â Perfect Riders Yamaha - PRV_L3_Oct24 - voice_phone - airtel - 919999999999',
    'Quantity': '1',
    'Credits Spent': '300',
    'Status': 'success'
  },
  // Compound objective rows
  {
    'Billing ID': 'PR4',
    'Date & Time': '05 May 2026, 10:00 am',
    'Item Name': 'message_delivered',
    'Channel': 'whatsapp_chat',
    'Description': 'post-sales - Perfect Riders - Service Reminder - WhatsApp - PRWA_OCT10_S1 - unknown - Rml - None',
    'Quantity': '1',
    'Credits Spent': '400',
    'Status': 'success'
  },
  // Inbound Lead Handling via None row
  {
    'Billing ID': 'PR5',
    'Date & Time': '06 May 2026, 10:00 am',
    'Item Name': 'message_delivered',
    'Channel': 'whatsapp_chat',
    'Description': 'post-sales - None - Inbound Lead Handling - whatsapp_chat - airtel - None',
    'Quantity': '1',
    'Credits Spent': '50',
    'Status': 'success'
  }
];

const prMetrics = processCreditData(prRows, 'Perfect Riders');
console.log('Aggregated Objectives count:', prMetrics.objectives.length);
prMetrics.objectives.forEach(o => {
  console.log(`  - [${o.rank}] "${o.objective}": ${o.totalCredits} credits (from ${o.startDate} to ${o.endDate})`);
});

// Verify that the 3 campaigns under "Service Reminder – Perfect Riders Yamaha" merged into ONE objective with 600 credits!
const yamObj = prMetrics.objectives.find(o => o.objective.includes('Perfect Riders Yamaha'));
assert(yamObj !== undefined, 'Found Service Reminder – Perfect Riders Yamaha objective');
assert(yamObj?.totalCredits === 600, `Merged credits for Yamaha objective is ${yamObj?.totalCredits} (expected 600)`);
assert(!yamObj?.objective.includes('PRV_'), `Yamaha objective does not contain campaign code: "${yamObj?.objective}"`);
assert(!yamObj?.objective.includes('voice_phone'), `Yamaha objective does not contain channel token: "${yamObj?.objective}"`);
assert(!yamObj?.objective.includes('â'), `Yamaha objective does not contain "â": "${yamObj?.objective}"`);

if (failed) {
  console.error('\n❌ SOME TESTS FAILED!');
  process.exit(1);
} else {
  console.log('\n🎉 ALL OBJECTIVE EXTRACTION TESTS PASSED!');
}
