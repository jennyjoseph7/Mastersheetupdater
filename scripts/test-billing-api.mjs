import { getDatePresetBounds, normalizeBillingItem } from '../app/credit-report/billing-api.ts';
import { processCreditData } from '../app/credit-report/credit-utils.ts';

console.log('=== RUNNING BILLING API UTILS & NORMALIZATION TESTS ===\n');

let failed = false;
function assert(condition, message) {
  if (!condition) {
    console.error(`❌ FAIL: ${message}`);
    failed = true;
  } else {
    console.log(`✅ PASS: ${message}`);
  }
}

// 1. Date Preset Bounds Test
const todayBounds = getDatePresetBounds('today');
assert(todayBounds.startDate instanceof Date, 'today startDate is Date');
assert(todayBounds.endDate instanceof Date, 'today endDate is Date');
assert(todayBounds.startDate.getHours() === 0, 'today start is 00:00:00');
assert(todayBounds.endDate.getHours() === 23, 'today end is 23:59:59');

const customBounds = getDatePresetBounds('custom', '2026-11-01', '2026-11-10');
assert(customBounds.startDate.getFullYear() === 2026, 'custom year is 2026');
assert(customBounds.startDate.getDate() === 1, 'custom start date is 1');
assert(customBounds.endDate.getDate() === 10, 'custom end date is 10');

// 2. Normalization Test
const rawApiItem = {
  status: 'success',
  channel: 'voice_phone',
  created: 1794578365.021988,
  updated: 1794578365.0226586,
  currency: 'credits',
  item_name: 'call_completed',
  billing_id: '2c777ead-dee6-322c-a18d-9ecb66f2fc61',
  item_price: 0.133,
  item_total: 3.325,
  item_units: 'seconds',
  campaign_id: '274fff2e-2e0c-3c25-aa00-2eee8564e091',
  dealership_id: 'rng-automobiles-private-limited-india',
  item_quantity: 25.0,
  item_description: 'pre-sales - Shenbaka - victoris special campaign - SB_VICTORIS_NOV13_S1 - voice_phone - tatatele - 919514714194',
  transaction_date: '2026-11-13T13:59:24.819813+0000',
  transaction_type: 'debit',
};

const norm = normalizeBillingItem(rawApiItem);
assert(norm['billing_id'] === '2c777ead-dee6-322c-a18d-9ecb66f2fc61', 'billing_id preserved');
assert(norm['credits_spent'] === 3.325, 'credits_spent numeric match');
assert(norm['quantity'] === 25.0, 'quantity numeric match');
assert(norm['channel'] === 'voice_phone', 'channel preserved');
assert(norm['item_name'] === 'call_completed', 'item_name preserved');
assert(norm['description'].includes('victoris special campaign'), 'description preserved');

// 3. Compatibility with processCreditData
const metrics = processCreditData([norm], 'Shenbaka');
assert(metrics.totalCredits === 3.325, `Total credits matches (expected 3.325, got ${metrics.totalCredits})`);
assert(metrics.voiceCredits === 3.325, `Voice credits matches (expected 3.325, got ${metrics.voiceCredits})`);
assert(metrics.debitsCount === 1, `Debits count is 1 (got ${metrics.debitsCount})`);
assert(metrics.objectives.length === 1, `Found 1 objective (got ${metrics.objectives.length})`);
assert(metrics.objectives[0].objective === 'Shenbaka', `Objective matches (got "${metrics.objectives[0].objective}")`);

if (failed) {
  process.exit(1);
} else {
  console.log('\n🎉 ALL BILLING API & NORMALIZATION TESTS PASSED!\n');
}
