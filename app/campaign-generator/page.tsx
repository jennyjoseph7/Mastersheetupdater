'use client';
import { useState, useEffect, useCallback, useRef } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/hooks/useAuth';
import { getApiEndpoint, getLlmModel } from '@/lib/ai/ai-config';
import Nav from '@/components/Nav';
import BrandLogo from '@/components/BrandLogo';
import ThemeToggle from '@/components/ThemeToggle';
import { useToast } from '@/components/Toast';
import { useConfigs, type SavedConfig, generateId } from '@/lib/templates';
import { CAMPAIGN_FAMILIES, CAMPAIGN_TYPES, CAMPAIGN_SUB_TYPES, CTA_OPTIONS, WORKFLOW_OPTIONS, CampaignFamily, CAMPAIGN_TYPE_LABELS } from './campaign-families';
import { SEED_OBJECTIVES, type SeedObjective, searchSeeds, getSeedObjectiveById } from './seed-objectives';
import styles from './campaign-generator.module.css';

const ALL_FIELD_KEYS = [
  'campaign_objective_id', 'campaign_type', 'campaign_sub_type',
  'campaign_objective_name', 'campaign_objective_description',
  'purpose', 'dealership_id', 'dealer_name', 'brand_id', 'brand_name', 'search_term',
  'custom_conversation_start_pattern', 'purpose_steps',
  'conversation_tone', 'why_user_should_avail_this',
  'reasons_users_may_not_be_interested', 'reasons_for_non_applicability',
  'guardrails_guidelines', 'other_important_information',
  'doc_data', 'is_custom', 'icon',
  'target_audience_tags', 'required_attributes', 'ctas', 'workflows',
  'custom_campaign_attributes', 'audience_attributes',
];

const OBJECT_LIST_KEYS = ['custom_campaign_attributes', 'audience_attributes'];
const STRING_LIST_KEYS = ['target_audience_tags', 'required_attributes', 'ctas', 'workflows', 'purpose_steps', 'custom_conversation_start_pattern'];

const AI_EDITABLE_FIELDS = [
  'campaign_objective_name',
  'why_user_should_avail_this', 'reasons_users_may_not_be_interested', 'reasons_for_non_applicability',
  'custom_conversation_start_pattern', 'conversation_tone', 'purpose', 'purpose_steps',
  'guardrails_guidelines', 'other_important_information', 'campaign_objective_description',
  'filter_params',
  'required_attributes', 'target_audience_tags', 'ctas', 'workflows',
  'custom_campaign_attributes', 'audience_attributes',
];

const FIELD_LABELS: Record<string, string> = {
  campaign_objective_name: 'Campaign Objective Name',
  dealership_id: 'Dealership ID', dealer_name: 'Dealer Name',
  brand_id: 'Brand ID', brand_name: 'Brand Name',
  why_user_should_avail_this: 'Why User Should Avail This',
  reasons_users_may_not_be_interested: 'Reasons Users May Not Be Interested',
  reasons_for_non_applicability: 'Reasons for Non-applicability',
  custom_conversation_start_pattern: 'Conversation Start Pattern',
  conversation_tone: 'Conversation Tone',
  purpose: 'Purpose', purpose_steps: 'Purpose Steps',
  guardrails_guidelines: 'Guardrails & Guidelines',
  other_important_information: 'Other Important Information',
  campaign_objective_description: 'Campaign Objective Description',
  filter_params: 'Filter Params',
  vehicle_model: 'Vehicle Model', dealer_city: 'Dealer City',
  preferred_date: 'Preferred Date', preferred_time: 'Preferred Time',
  service_type: 'Service Type', last_service_date: 'Last Service Date',
  odometer_reading: 'Odometer Reading',
  template_name: 'Template Name', cta_text: 'CTA Button Text',
  media_type: 'Media Type', media_url: 'Media URL',
};

interface CampaignObjective {
  [key: string]: unknown;
  campaign_objective_id: string;
  campaign_type: string;
  campaign_sub_type: string;
  campaign_objective_name: string;
  campaign_objective_description: string;
  purpose: string;
  dealership_id: string;
  dealer_name: string;
  brand_id: string;
  search_term: string;
  custom_conversation_start_pattern: string;
  purpose_steps: string;
  conversation_tone: string;
  why_user_should_avail_this: string;
  reasons_users_may_not_be_interested: string;
  reasons_for_non_applicability: string;
  guardrails_guidelines: string;
  other_important_information: string;
  doc_data: Record<string, unknown>;
  is_custom: boolean;
  filter_params: Record<string, unknown>;
}

function esc(val: string): string {
  return String(val || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

function SuggestionCard({ fieldKey, value, onAccept, onReject }: { fieldKey: string; value: string; onAccept: () => void; onReject: () => void }) {
  return (
    <div className={styles['ai-suggestion']}>
      <span className={styles['ai-sg-icon']}>AI</span>
      <span className={styles['ai-sg-text']}><strong>{FIELD_LABELS[fieldKey] || fieldKey}</strong> suggests: {value}</span>
      <span className={styles['ai-sg-actions']}>
        <button className={styles['btn-sg-accept']} onClick={onAccept} aria-label="Accept">&#10003;</button>
        <button className={styles['btn-sg-reject']} onClick={onReject} aria-label="Reject">&#10007;</button>
      </span>
    </div>
  );
}

function TagPicker({ options, value, onChange }: { options: string[]; value: string; onChange: (v: string) => void; label: string }) {
  const all = value ? value.split(',').map(s => s.trim()).filter(Boolean) : [];
  const normalOpts = options.filter(o => o !== 'other');
  const selected = all.filter(t => t !== 'other' && !t.startsWith('other:'));
  const hasOther = all.some(t => t === 'other' || t.startsWith('other:'));
  const otherVal = hasOther ? all.find(t => t.startsWith('other:'))?.slice(6) || '' : '';
  function toggle(opt: string) {
    if (opt === 'other') {
      if (hasOther) {
        onChange(selected.join(', '));
      } else {
        onChange([...selected, 'other:'].join(', '));
      }
      return;
    }
    const idx = selected.indexOf(opt);
    if (idx >= 0) selected.splice(idx, 1);
    else selected.push(opt);
    const result = hasOther ? [...selected, 'other:' + otherVal] : selected;
    onChange(result.join(', '));
  }
  function setOther(val: string) {
    const rest = all.filter(t => t !== 'other' && !t.startsWith('other:'));
    if (val.trim()) {
      rest.push('other:' + val.trim());
    }
    onChange(rest.join(', '));
  }
  return (
    <div>
      <div className={styles['tag-picker']}>
        {normalOpts.map(opt => (
          <span key={opt} className={`${styles['tag-chip']} ${selected.includes(opt) ? styles['tag-selected'] : ''}`} onClick={() => toggle(opt)}>
            {opt.replace(/-/g, ' ')}
          </span>
        ))}
        {options.includes('other') && (
          <span className={`${styles['tag-chip']} ${hasOther ? styles['tag-selected'] : ''}`} onClick={() => toggle('other')}>
            Other…
          </span>
        )}
      </div>
      {hasOther && (
        <div className={styles['other-row']}>
          <input type="text" className={styles['other-input']} value={otherVal} onChange={e => setOther(e.target.value)} placeholder="Enter custom value" />
        </div>
      )}
      {all.length > 0 && <div className={styles['tag-values']}>{all.map(t => t.startsWith('other:') ? t.slice(6) : t).join(', ')}</div>}
    </div>
  );
}

function ObjectListEditor({ value, onChange, keyLabel, valueLabel }: { value: string; onChange: (v: string) => void; keyLabel?: string; valueLabel?: string }) {
  let items: { key: string; val: string }[] = [];
  try {
    const parsed = JSON.parse(value || '[]');
    if (Array.isArray(parsed)) items = parsed;
  } catch {}
  function update(items: { key: string; val: string }[]) {
    onChange(JSON.stringify(items));
  }
  function addItem() {
    update([...items, { key: '', val: '' }]);
  }
  function removeItem(idx: number) {
    const next = [...items]; next.splice(idx, 1); update(next);
  }
  function changeItem(idx: number, field: 'key' | 'val', v: string) {
    const next = [...items]; next[idx] = { ...next[idx], [field]: v }; update(next);
  }
  return (
    <div className={styles['obj-editor']}>
      {items.map((item, i) => (
        <div key={i} className={styles['obj-row']}>
          <input type="text" value={item.key} onChange={e => changeItem(i, 'key', e.target.value)} placeholder={keyLabel || 'Key'} className={styles['obj-input']} />
          <input type="text" value={item.val} onChange={e => changeItem(i, 'val', e.target.value)} placeholder={valueLabel || 'Value'} className={styles['obj-input']} />
          <button className={styles['obj-remove']} onClick={() => removeItem(i)} title="Remove">&times;</button>
        </div>
      ))}
      <button className={`${styles.btn} ${styles['btn-secondary']}`} onClick={addItem} style={{ fontSize: '0.75rem', padding: '0.35rem 0.7rem' }}>+ Add {keyLabel || 'Attribute'}</button>
    </div>
  );
}

interface SavedTemplate extends SavedConfig {
  id: string;
  name: string;
  description: string;
  savedAt: string;
  familyId: string;
  subType: string;
  isCustom: boolean;
  formValues: Record<string, string>;
  aiSuggestions: Record<string, string>;
  aiBrief: string;
}

const DRAFT_KEY = 'jejo-cg-draft';
const HISTORY_KEY = 'jejo-cg-history';
const VARIANTS_KEY = 'jejo-cg-variants';

interface VariantEntry {
  seedId: string;
  lang: string;
  channel: string;
  formValues: Record<string, string>;
  aiBrief: string;
  updatedAt: string;
}

const LANGUAGES = [
  { id: 'en', label: 'English' },
  { id: 'hi', label: 'Hindi' },
  { id: 'kn', label: 'Kannada' },
  { id: 'ml', label: 'Malayalam' },
  { id: 'ta', label: 'Tamil' },
  { id: 'te', label: 'Telugu' },
];

const CHANNELS = [
  { id: 'voice', label: 'Voice' },
  { id: 'whatsapp', label: 'WhatsApp' },
];

function getAllVariants(): VariantEntry[] {
  try {
    const raw = localStorage.getItem(VARIANTS_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch { return []; }
}

function saveVariantEntry(entry: VariantEntry) {
  const all = getAllVariants();
  const idx = all.findIndex(v => v.seedId === entry.seedId && v.lang === entry.lang && v.channel === entry.channel);
  if (idx >= 0) {
    all[idx] = entry;
  } else {
    all.push(entry);
  }
  localStorage.setItem(VARIANTS_KEY, JSON.stringify(all));
}

function deleteVariantEntry(seedId: string, lang: string, channel: string) {
  const all = getAllVariants().filter(v => !(v.seedId === seedId && v.lang === lang && v.channel === channel));
  localStorage.setItem(VARIANTS_KEY, JSON.stringify(all));
}

function getVariantsForSeed(seedId: string): VariantEntry[] {
  return getAllVariants().filter(v => v.seedId === seedId);
}

function stripBomKeys(obj: Record<string, unknown>): void {
  for (const key of Object.keys(obj)) {
    if (key.charCodeAt(0) === 0xFEFF) {
      obj[key.slice(1)] = obj[key];
      delete obj[key];
    }
  }
}

export default function CampaignGeneratorPage() {
  const log = (...args: unknown[]) => console.log('[CampaignGen]', ...args);
  log('Page mounted');
  const { isAuthenticated, loading } = useAuth();
  const router = useRouter();
  const { showToast } = useToast();

  const [campaignType, setCampaignType] = useState('pre-sales');
  const [currentFamilyId, setCurrentFamilyId] = useState('presales_voice');
  const [subType, setSubType] = useState('');
  const [subTypeOther, setSubTypeOther] = useState('');
  const [formValues, setFormValues] = useState<Record<string, string>>({});
  const [isCustom, setIsCustom] = useState(false);
  const [selectedSeedId, setSelectedSeedId] = useState<string | null>(null);
  const [seedSearchQuery, setSeedSearchQuery] = useState('');
  const [showSeedPicker, setShowSeedPicker] = useState(false);
  const [variants, setVariants] = useState<VariantEntry[]>([]);
  const [activeLang, setActiveLang] = useState('en');
  const [activeChannel, setActiveChannel] = useState('voice');
  const [statusMsg, setStatusMsg] = useState('');
  const [statusType, setStatusType] = useState('');
  const [downloadBtnDisabled, setDownloadBtnDisabled] = useState(true);
  const [jsonPreview, setJsonPreview] = useState('');
  const [fieldCount, setFieldCount] = useState(0);
  const [fieldFilled, setFieldFilled] = useState(0);
  const [fieldPct, setFieldPct] = useState('0%');

  // AI state
  const [aiBrief, setAiBrief] = useState('');
  const [aiLoading, setAiLoading] = useState(false);
  const [aiError, setAiError] = useState('');
  const [aiResult, setAiResult] = useState('');
  const [aiSuggestions, setAiSuggestions] = useState<Record<string, string>>({});
  const [aiHistory, setAiHistory] = useState<Array<{ brief: string; time: string }>>([]);
  const abortRef = useRef<AbortController | null>(null);

  // Template state
  const store = useConfigs<SavedTemplate>('jejo-cg-templates');
  const [showSaveDialog, setShowSaveDialog] = useState(false);
  const [saveDialogName, setSaveDialogName] = useState('');
  const [saveDialogDesc, setSaveDialogDesc] = useState('');
  const [loadConfirmId, setLoadConfirmId] = useState<string | null>(null);
  const [dragIndex, setDragIndex] = useState<number | null>(null);
  const [dropTargetIdx, setDropTargetIdx] = useState<number | null>(null);

  const family = CAMPAIGN_FAMILIES[currentFamilyId];
  const subTypes = family?.subTypes || [];
  const extraFields = family?.extraFields || [];
  const fieldOverrides = family?.fieldOverrides || {};

  // Save/restore draft
  useEffect(() => {
    if (loading || !isAuthenticated) return;
    try {
      const raw = sessionStorage.getItem(DRAFT_KEY);
      if (raw) {
        const draft = JSON.parse(raw);
        if (draft.fields) {
          setFormValues(prev => {
            const merged = { ...prev };
            for (const k of Object.keys(draft.fields)) {
              if (draft.fields[k]) merged[k] = draft.fields[k];
            }
            return merged;
          });
        }
        if (draft.isCustom !== undefined) setIsCustom(draft.isCustom);
        if (draft.campaignType) setCampaignType(draft.campaignType);
        if (draft.familyId && CAMPAIGN_FAMILIES[draft.familyId]) {
          setCurrentFamilyId(draft.familyId);
          setSubType(draft.subType || CAMPAIGN_FAMILIES[draft.familyId].subTypes[0]?.id || '');
        }
        if (draft.suggestions && Object.keys(draft.suggestions).length > 0) {
          setAiSuggestions(draft.suggestions);
        }
        if (draft.aiBrief) setAiBrief(draft.aiBrief);
        if (draft.selectedSeedId) {
          setSelectedSeedId(draft.selectedSeedId);
          setVariants(getVariantsForSeed(draft.selectedSeedId));
        }
        if (draft.activeLang) setActiveLang(draft.activeLang);
        if (draft.activeChannel) setActiveChannel(draft.activeChannel);
      }
    } catch (_) {}
  }, [loading, isAuthenticated]);

  const saveDraft = useCallback(() => {
    const draft = {
      fields: formValues,
      isCustom,
      campaignType,
      familyId: currentFamilyId,
      subType,
      suggestions: aiSuggestions,
      aiBrief,
      selectedSeedId,
      activeLang,
      activeChannel,
    };
    try { sessionStorage.setItem(DRAFT_KEY, JSON.stringify(draft)); } catch (_) {}
  }, [formValues, isCustom, campaignType, currentFamilyId, subType, aiSuggestions, aiBrief, selectedSeedId, activeLang, activeChannel]);

  useEffect(() => { if (isAuthenticated) saveDraft(); }, [formValues, isCustom, aiSuggestions, aiBrief, isAuthenticated, saveDraft]);

  // Load history + templates on mount
  useEffect(() => {
    try {
      const raw = localStorage.getItem(HISTORY_KEY);
      if (raw) setAiHistory(JSON.parse(raw));
    } catch (_) {}
  }, []);

  useEffect(() => {
    if (!loading && !isAuthenticated) router.push('/login');
  }, [loading, isAuthenticated, router]);
  if (!isAuthenticated && !loading) return null;

  function getValue(key: string): string {
    return formValues[key] ?? '';
  }

  function setValue(key: string, value: string) {
    setFormValues(prev => ({ ...prev, [key]: value }));
  }

  function handleFormChange(key: string, value: string) {
    setValue(key, value);
  }

  function onCampaignTypeChange(type: string) {
    setCampaignType(type);
  }

  function onTabClick(familyId: string) {
    if (selectedSeedId) unlinkSeed();
    setCurrentFamilyId(familyId);
    const f = CAMPAIGN_FAMILIES[familyId];
    if (f && f.subTypes.length > 0) {
      const first = CAMPAIGN_SUB_TYPES[0];
      setSubType(first);
      setSubTypeOther('');
    }
  }

  function applySeedObjective(seed: SeedObjective) {
    setSelectedSeedId(seed.id);
    setFormValues({ ...seed.fields });
    setAiSuggestions({});
    setAiBrief('');
    setAiError('');
    setAiResult('');
    const fam = CAMPAIGN_FAMILIES[seed.familyId];
    if (fam) {
      setCurrentFamilyId(seed.familyId);
      setCampaignType(fam.campaignType);
    }
    setSubType(seed.subType);
    setShowSeedPicker(false);
    setSeedSearchQuery('');
    setActiveLang('en');
    setActiveChannel('voice');
    // Load variants for this seed
    setVariants(getVariantsForSeed(seed.id));
  }

  function unlinkSeed() {
    setSelectedSeedId(null);
    setVariants([]);
  }

  function loadVariant(lang: string, channel: string) {
    if (!selectedSeedId) return;
    const seed = getSeedObjectiveById(selectedSeedId);
    if (!seed) return;
    const existing = getVariantsForSeed(selectedSeedId);
    const match = existing.find(v => v.lang === lang && v.channel === channel);
    if (match) {
      // Load existing variant
      setFormValues({ ...match.formValues });
      setAiBrief(match.aiBrief || '');
      setAiError('');
      setAiResult('');
      setActiveLang(lang);
      setActiveChannel(channel);
      showToast(`Loaded ${LANGUAGES.find(l => l.id === lang)?.label} ${CHANNELS.find(c => c.id === channel)?.label} variant`);
    } else {
      // Pre-fill AI brief for creating new variant in this language/channel
      // Keep current form values intact (don't reset to seed defaults)
      setActiveLang(lang);
      setActiveChannel(channel);
      const langLabel = LANGUAGES.find(l => l.id === lang)?.label || lang;
      const chLabel = CHANNELS.find(c => c.id === channel)?.label || channel;
      setAiBrief(`Create a ${langLabel} ${chLabel} variant of the campaign "${formValues.campaign_objective_name || seed.name}". Keep the same purpose, tone, and structure but adapt for ${langLabel} language and ${chLabel} channel.`);
    }
  }

  function saveCurrentAsVariant() {
    if (!selectedSeedId) return;
    const entry: VariantEntry = {
      seedId: selectedSeedId,
      lang: activeLang,
      channel: activeChannel,
      formValues: { ...formValues },
      aiBrief,
      updatedAt: new Date().toISOString(),
    };
    saveVariantEntry(entry);
    setVariants(getVariantsForSeed(selectedSeedId));
    const langLabel = LANGUAGES.find(l => l.id === activeLang)?.label || activeLang;
    const chLabel = CHANNELS.find(c => c.id === activeChannel)?.label || activeChannel;
    showToast(`Saved ${langLabel} ${chLabel} variant`);
  }

  function deleteVariant(lang: string, channel: string) {
    if (!selectedSeedId) return;
    deleteVariantEntry(selectedSeedId, lang, channel);
    setVariants(getVariantsForSeed(selectedSeedId));
    const langLabel = LANGUAGES.find(l => l.id === lang)?.label || lang;
    const chLabel = CHANNELS.find(c => c.id === channel)?.label || channel;
    showToast(`Deleted ${langLabel} ${chLabel} variant`);
  }

  function getVariantStatus(lang: string, channel: string): 'created' | 'active' | 'none' {
    if (activeLang === lang && activeChannel === channel) return 'active';
    return variants.some(v => v.lang === lang && v.channel === channel) ? 'created' : 'none';
  }

  function createAllMissingVariants() {
    if (!selectedSeedId) return;
    const seed = getSeedObjectiveById(selectedSeedId);
    if (!seed) return;
    const existing = getVariantsForSeed(selectedSeedId);
    let count = 0;
    for (const lang of LANGUAGES) {
      for (const ch of CHANNELS) {
        if (!existing.some(v => v.lang === lang.id && v.channel === ch.id)) {
          const entry: VariantEntry = {
            seedId: selectedSeedId,
            lang: lang.id,
            channel: ch.id,
            formValues: { ...seed.fields, campaign_objective_name: `${seed.fields.campaign_objective_name || seed.name} - ${lang.label} ${ch.label}` },
            aiBrief: `${lang.label} ${ch.label} variant of ${seed.name}`,
            updatedAt: new Date().toISOString(),
          };
          saveVariantEntry(entry);
          count++;
        }
      }
    }
    setVariants(getVariantsForSeed(selectedSeedId));
    showToast(`Created ${count} missing variants`);
  }

  function buildSearchTerm(fam: CampaignFamily, subTypeLabel: string): string {
    const parts: string[] = [];
    const name = getValue('campaign_objective_name');
    const dealer = getValue('dealer_name');
    const brand = getValue('brand_id');
    const vehicle = getValue('vehicle_model') || getValue('service_type') || '';
    if (name) parts.push(name);
    if (dealer) parts.push(dealer);
    if (brand) parts.push(brand);
    if (vehicle) parts.push(vehicle);
    parts.push(fam.label, subTypeLabel);
    return parts.join(' | ');
  }

  function parseFilterParams(): Record<string, unknown> {
    const val = getValue('filter_params').trim();
    if (!val) return {};
    try { return JSON.parse(val) as Record<string, unknown>; }
    catch { return { _parse_error: 'Invalid JSON' }; }
  }

  function slugify(s: string): string {
    return String(s || '').toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');
  }

  function splitLines(s: string): string[] {
    return String(s || '').split('\n').map(l => l.trim()).filter(Boolean);
  }

  function splitTags(s: string): string[] {
    return String(s || '').split(',').map(t => t.trim().replace(/^other:/, '')).filter(Boolean);
  }

  function parseObjList(s: string): Record<string, string>[] {
    try { const p = JSON.parse(s || '[]'); return Array.isArray(p) ? p : []; }
    catch { return []; }
  }

  function buildCampaignObjective(): Record<string, unknown> {
    const fam = CAMPAIGN_FAMILIES[currentFamilyId];
    const subTypeVal = subType === 'other' ? subTypeOther : subType;

    const obj: Record<string, unknown> = {
      campaign_objective_id: slugify(fam.label) + '-' + slugify(getValue('campaign_objective_name')) + '-' + (getValue('dealership_id') || 'campaign'),
      campaign_type: campaignType,
      campaign_sub_type: subTypeVal,
      campaign_objective_name: getValue('campaign_objective_name'),
      campaign_objective_description: getValue('campaign_objective_description'),
      purpose: getValue('purpose'),
      purpose_steps: splitLines(getValue('purpose_steps')),
      dealership_id: getValue('dealership_id'),
      dealer_name: getValue('dealer_name'),
      brand_id: getValue('brand_id'),
      search_term: buildSearchTerm(fam, subTypeVal),
      custom_conversation_start_pattern: splitLines(getValue('custom_conversation_start_pattern')),
      conversation_tone: getValue('conversation_tone'),
      why_user_should_avail_this: getValue('why_user_should_avail_this'),
      reasons_users_may_not_be_interested: getValue('reasons_users_may_not_be_interested'),
      reasons_for_non_applicability: getValue('reasons_for_non_applicability'),
      guardrails_guidelines: getValue('guardrails_guidelines'),
      other_important_information: getValue('other_important_information'),
      required_attributes: splitTags(getValue('required_attributes')),
      target_audience_tags: splitTags(getValue('target_audience_tags')),
      ctas: splitTags(getValue('ctas')),
      workflows: splitTags(getValue('workflows')),
      custom_campaign_attributes: parseObjList(getValue('custom_campaign_attributes')),
      audience_attributes: parseObjList(getValue('audience_attributes')),
      parents: getValue('dealership_id') ? [{ dealership_id: getValue('dealership_id') }] : [],
      doc_data: {
        created_by: 'Campaign Objective Generator',
        created_at: '',
        version: '2.0',
        campaign_family: fam.id,
        campaign_sub_type_id: subType,
      },
      is_custom: isCustom,
      filter_params: parseFilterParams(),
    };

    for (const ef of extraFields) {
      obj[ef.key] = getValue(ef.key);
    }

    return obj;
  }

  function updateAll() {
    const obj = buildCampaignObjective();
    renderAutoFields(obj);
    renderPreview(obj);
    updateStats(obj);
    setDownloadBtnDisabled(!String(obj.campaign_objective_name || '').trim());
  }

  function renderAutoFields(_obj: Record<string, unknown>) {}

  function updateStats(obj: Record<string, unknown>) {
    let filled = 0;
    const fam = CAMPAIGN_FAMILIES[currentFamilyId];
    const countableKeys = ALL_FIELD_KEYS.filter(k =>
      k !== 'campaign_objective_id' && k !== 'search_term' &&
      k !== 'doc_data' && k !== 'is_custom' && k !== 'filter_params' &&
      k !== 'campaign_sub_type'
    ).length + fam.extraFields.length;

    for (const k of ALL_FIELD_KEYS) {
      if (k === 'is_custom' || k === 'filter_params' || k === 'doc_data' ||
          k === 'campaign_objective_id' || k === 'campaign_sub_type' || k === 'search_term') continue;
      const v = obj[k];
      if (v !== undefined && v !== null && String(v).trim() !== '') filled++;
    }

    for (const ef of fam.extraFields) {
      const v = obj[ef.key];
      if (v !== undefined && v !== null && String(v).trim() !== '') filled++;
    }

    setFieldCount(countableKeys);
    setFieldFilled(filled);
    setFieldPct(Math.round((filled / Math.max(countableKeys, 1)) * 100) + '%');
  }

  function renderPreview(obj: Record<string, unknown>) {
    setJsonPreview(JSON.stringify(obj, null, 2));
  }

  function syntaxHighlight(json: string): string {
    return json
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"([^"\\]*(?:\\.[^"\\]*)*)"\s*:/g, '<span class="json-key">"$1"</span>:')
      .replace(/: "([^"\\]*(?:\\.[^"\\]*)*)"/g, ': <span class="json-string">"$1"</span>')
      .replace(/: (-?\d+\.?\d*)/g, ': <span class="json-number">$1</span>')
      .replace(/: (true|false)/g, ': <span class="json-bool">$1</span>')
      .replace(/: null/g, ': <span class="json-null">null</span>');
  }

  function downloadJSON() {
    const obj = buildCampaignObjective();
    (obj.doc_data as Record<string, unknown>).created_at = new Date().toISOString();
    const name = String(obj.campaign_objective_name || '');
    if (!name.trim()) {
      setStatusMsg('Fill in at least the Campaign Objective Name.');
      setStatusType('warn');
      return;
    }
    const blob = new Blob([JSON.stringify(obj, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    const safeName = name.replace(/[^a-z0-9]+/gi, '_').replace(/^_+|_+$/g, '').toLowerCase() || 'campaign';
    a.href = url;
    a.download = safeName + '_' + new Date().toISOString().slice(0, 10) + '.json';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    setStatusMsg('Downloaded: ' + a.download);
    setStatusType('ok');
  }

  async function copyJSON() {
    const obj = buildCampaignObjective();
    (obj.doc_data as Record<string, unknown>).created_at = new Date().toISOString();
    if (!String(obj.campaign_objective_name || '').trim()) {
      setStatusMsg('Fill in at least the Campaign Objective Name.');
      setStatusType('warn');
      return;
    }
    try {
      await navigator.clipboard.writeText(JSON.stringify(obj, null, 2));
      showToast('Copied to clipboard');
      setStatusMsg('JSON copied to clipboard.');
      setStatusType('ok');
    } catch {
      setStatusMsg('Failed to copy.');
      setStatusType('err');
    }
  }

  function clearForm() {
    if (!confirm('Clear all form fields?')) return;
    setFormValues({});
    setIsCustom(false);
    setAiSuggestions({});
    setAiBrief('');
    setAiError('');
    setAiResult('');
    setStatusMsg('');
    setStatusType('');
    sessionStorage.removeItem(DRAFT_KEY);
  }

  /* ══════════════════════════════════════════════════════════════════
     TEMPLATES
     ══════════════════════════════════════════════════════════════════ */
  function saveTemplate() {
    const name = saveDialogName.trim();
    if (!name) { showToast('Enter a template name'); return; }
    const tpl: SavedTemplate = {
      id: generateId(),
      name,
      description: saveDialogDesc.trim(),
      savedAt: new Date().toLocaleString(),
      familyId: currentFamilyId,
      subType,
      isCustom,
      formValues: { ...formValues },
      aiSuggestions: { ...aiSuggestions },
      aiBrief,
    };
    store.save(tpl);
    setShowSaveDialog(false);
    setSaveDialogName('');
    setSaveDialogDesc('');
    showToast(`Saved template: ${name}`);
  }

  function loadTemplate(tpl: SavedTemplate) {
    if (loadConfirmId === tpl.id) {
      // Confirmed — apply
      setCurrentFamilyId(tpl.familyId);
      setSubType(tpl.subType);
      setIsCustom(tpl.isCustom);
      setFormValues({ ...tpl.formValues });
      setAiSuggestions({ ...tpl.aiSuggestions });
      setAiBrief(tpl.aiBrief);
      setLoadConfirmId(null);
      showToast(`Loaded template: ${tpl.name}`);
      window.scrollTo({ top: 0, behavior: 'smooth' });
    } else {
      setLoadConfirmId(tpl.id);
      // Auto-reset after 3s
      setTimeout(() => setLoadConfirmId(prev => prev === tpl.id ? null : prev), 3000);
    }
  }

  function deleteTemplate(id: string) {
    store.remove(id);
    if (loadConfirmId === id) setLoadConfirmId(null);
  }

  function clearTemplates() {
    if (!confirm('Delete all saved templates?')) return;
    store.clear();
  }

  function clearHistory() {
    setAiHistory([]);
    localStorage.removeItem(HISTORY_KEY);
  }

  function openSaveDialog() {
    const name = getValue('campaign_objective_name') || 'Untitled';
    setSaveDialogName(name);
    setSaveDialogDesc('');
    setShowSaveDialog(true);
  }

  function exportTemplate(tpl: SavedTemplate) {
    store.exportConfig(tpl, tpl.name);
    showToast(`Exported template: ${tpl.name}`);
  }

  function importTemplate(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    if (!file.name.endsWith('.json')) {
      showToast('Only .json files supported');
      e.target.value = '';
      return;
    }
    const reader = new FileReader();
    reader.onload = (ev) => {
      try {
        const text = ev.target?.result as string;
        const parsed = JSON.parse(text);

        // Strip BOM characters from all keys
        if (parsed && typeof parsed === 'object') stripBomKeys(parsed);

        // Unwrap paginated wrapper: { data: [...] }
        let obj = parsed;
        if (obj && obj.data && Array.isArray(obj.data) && obj.data.length > 0) {
          obj = obj.data[0];
          if (obj && typeof obj === 'object') stripBomKeys(obj);
        }

        if (!obj || typeof obj !== 'object') {
          showToast('Invalid template file');
          return;
        }

        // Format 1: Direct SavedTemplate (exported via "Export Template")
        if (obj.familyId && obj.formValues) {
          const tpl: SavedTemplate = {
            id: obj.id || generateId(),
            name: obj.name || 'Imported Template',
            description: obj.description || '',
            savedAt: obj.savedAt || new Date().toLocaleString(),
            familyId: obj.familyId,
            subType: obj.subType || '',
            isCustom: !!obj.isCustom,
            formValues: obj.formValues || {},
            aiSuggestions: obj.aiSuggestions || {},
            aiBrief: obj.aiBrief || '',
          };
          store.save(tpl);
          showToast(`Imported template: ${tpl.name}`);
          return;
        }

        // Format 2/3: CampaignObjective or API response — extract flat fields
        const formValues: Record<string, string> = {};
        for (const key of ALL_FIELD_KEYS) {
          const val = obj[key];
          if (val !== undefined && val !== null) {
            if (typeof val === 'string' && val.trim()) {
              formValues[key] = val;
            } else if (Array.isArray(val)) {
              const joined = val.filter((v: unknown) => typeof v === 'string').join('\n');
              if (joined.trim()) formValues[key] = joined;
            }
          }
        }

        // Map campaign_type to familyId
        let familyId = 'presales_voice';
        const ct = String(obj.campaign_type || '').toLowerCase();
        const matchFamily = Object.values(CAMPAIGN_FAMILIES).find(f => f.campaignType === ct);
        if (matchFamily) {
          familyId = matchFamily.id;
        } else if (ct.includes('service') || ct.includes('post')) {
          familyId = 'service_voice';
        } else if (ct.includes('whatsapp') || ct.includes('wa_')) {
          familyId = 'whatsapp';
        }

        // Map campaign_sub_type
        let subType = '';
        const cst = String(obj.campaign_sub_type || '').toLowerCase().trim();
        if (cst) {
          const match = CAMPAIGN_SUB_TYPES.find(st => st.toLowerCase() === cst);
          if (match) subType = match;
        }

        const tpl: SavedTemplate = {
          id: obj.campaign_objective_id || generateId(),
          name: obj.campaign_objective_name || 'Imported Campaign',
          description: obj.campaign_objective_description || '',
          savedAt: new Date().toLocaleString(),
          familyId,
          subType: subType || CAMPAIGN_SUB_TYPES[0],
          isCustom: !!obj.isCustom,
          formValues,
          aiSuggestions: {},
          aiBrief: '',
        };
        store.save(tpl);
        showToast(`Imported campaign: ${tpl.name}`);
      } catch {
        showToast('Failed to parse template file');
      }
    };
    reader.readAsText(file);
    // Reset so re-importing the same file works
    e.target.value = '';
  }

  /* ══════════════════════════════════════════════════════════════════
     DRAG & DROP
     ══════════════════════════════════════════════════════════════════ */
  function handleDragStart(index: number) {
    setDragIndex(index);
  }

  function handleDragOver(e: React.DragEvent, idx: number) {
    e.preventDefault(); // Allow drop
    const rect = (e.currentTarget as HTMLElement).getBoundingClientRect();
    const midY = rect.top + rect.height / 2;
    // Show indicator before this card if cursor in top half, after if in bottom half
    const target = e.clientY < midY ? idx : idx + 1;
    if (target !== dropTargetIdx) setDropTargetIdx(target);
  }

  function handleDrop() {
    if (dragIndex === null || dropTargetIdx === null) {
      setDragIndex(null);
      setDropTargetIdx(null);
      return;
    }
    store.setConfigs(prev => {
      const updated = [...prev];
      const [moved] = updated.splice(dragIndex!, 1);
      // Adjust target: after removing at dragIndex, indices after it shift down by 1
      const target = dropTargetIdx > dragIndex! ? dropTargetIdx - 1 : dropTargetIdx;
      updated.splice(target, 0, moved);
      return updated;
    });
    setDragIndex(null);
    setDropTargetIdx(null);
  }

  function handleDragEnd() {
    setDragIndex(null);
    setDropTargetIdx(null);
  }

  function handleBodyDragOver(e: React.DragEvent) {
    e.preventDefault();
    // When dragging past the last card, allow drop at the very end
    const body = e.currentTarget as HTMLElement;
    const children = body.querySelectorAll('[draggable]');
    if (children.length === 0) return;
    const last = children[children.length - 1] as HTMLElement;
    const lastRect = last.getBoundingClientRect();
    // If cursor is below the last card, set drop target to end
    if (e.clientY > lastRect.bottom) {
      if (dropTargetIdx !== store.count) setDropTargetIdx(store.count);
    }
  }

  /* ══════════════════════════════════════════════════════════════════
     AI GENERATION
     ══════════════════════════════════════════════════════════════════ */
  function getEditableFields(): string[] {
    return AI_EDITABLE_FIELDS.concat(extraFields.map(ef => ef.key));
  }

  async function doAiGenerate(brief: string) {
    if (!brief.trim()) return;
    setAiLoading(true);
    setAiError('');
    setAiResult('');

    const controller = new AbortController();
    abortRef.current = controller;
    const timeout = setTimeout(() => controller.abort(), 45000);

    const fam = CAMPAIGN_FAMILIES[currentFamilyId];
    const extraDesc = fam.extraFields.map(ef => `- ${ef.key} (${ef.label}): ${ef.hint}`).join('\n');

    const systemPrompt = [
      'You are a campaign objective generator for automotive voice AI and WhatsApp campaigns.',
      'Given a free-form brief, generate a complete campaign objective JSON with the following fields:',
      '',
      'Basic Info:',
      '- campaign_objective_name (string): Short descriptive name',
      '',
      'Context & Purpose:',
      '- why_user_should_avail_this (string): Value proposition',
      '- reasons_users_may_not_be_interested (string): Objection handling',
      '- reasons_for_non_applicability (string): When campaign does not apply',
      '',
      'Conversation Flow:',
      '- custom_conversation_start_pattern (string): Opening line',
      '- conversation_tone (string): Speaking style',
      '- purpose (string): Core campaign purpose',
      '- purpose_steps (string): Step-by-step flow',
      '',
      'Guardrails:',
      '- guardrails_guidelines (string): Rules the AI must follow',
      '- other_important_information (string): Additional context',
      '- campaign_objective_description (string): Brief description',
      '- filter_params (string): Optional JSON filter config',
      '',
      `Extra fields for "${fam.label}":`,
      extraDesc,
      '',
      'Also include campaign_type, campaign_family, and campaign_sub_type:',
      '- campaign_type (string): One of pre-sales, post-sales, dealership',
      '- campaign_family (string): One of presales_voice, service_voice, whatsapp',
      '- campaign_sub_type (string): Pick the most appropriate from: brand awareness, service overdue, product awareness, event, lead generation, lead qualification, lead nurturing, lead conversion, workshop awareness, offers, new accessories, new procedures, customer retention, service reminder, upsell/cross-sell, review, feedback, reminder, product recall, software update',
      'Detect the family, type, and sub-type from the brief context.',
      '',
      'CRITICAL: Generate ALL of the above fields. For any field the brief does not explicitly specify, infer a reasonable default based on the campaign context. Never omit a field.',
      'Do NOT include markdown fences or commentary.',
    ].join('\n');

    const userContent = `Brief:\n${brief}`;

    try {
      const cfg = (typeof window !== 'undefined' ? (window as any).JEJO_CONFIG : null) || {};
      const res = await fetch(getApiEndpoint(), {
        method: 'POST',
        signal: controller.signal,
        headers: {
          'Content-Type': 'application/json',
          'X-GRYD-TOKEN': (typeof window !== 'undefined' ? sessionStorage.getItem('gryd_token') : '') || '',
          'X-GRYD-SESSION-ID': (typeof window !== 'undefined' ? sessionStorage.getItem('gryd_session_id') : '') || '',
          'X-GRYD-ENTERPRISE-ID': (typeof window !== 'undefined' ? sessionStorage.getItem('gryd_enterprise_id') : '') || 'autocrm',
          'X-GRYD-SIGNUP-TOKEN': cfg.grydSignupToken || '',
          'X-GRYD-APPLICATION-ID': 'autocrm',
        },
        body: JSON.stringify({
          model: getLlmModel(),
          messages: [
            { role: 'system', content: systemPrompt },
            { role: 'user', content: userContent },
          ],
          temperature: 0.3,
          max_tokens: 1600,
        }),
      });
      clearTimeout(timeout);
      setAiLoading(false);

      if (!res.ok) {
        const errText = await res.text().catch(() => '');
        setAiError(`API ${res.status}: ${errText.slice(0, 200)}`);
        return;
      }

      const data = await res.json();
      let text = '';
      if (data.choices && data.choices[0]) {
        text = data.choices[0].message?.content || data.choices[0].text || '';
      }
      if (!text) {
        setAiError('Empty response from AI');
        return;
      }

      // Parse response
      text = text.replace(/^```(?:json)?\s*([\s\S]*?)\s*```$/i, '$1').trim();
      console.log('[CampaignGen] AI raw response:', text);
      let parsed: Record<string, string> = {};
      try {
        let obj = JSON.parse(text);
        if (typeof obj === 'string') { obj = JSON.parse(obj); }
        if (typeof obj === 'object' && obj !== null) {
          // Auto-switch family, type, and sub-type
          if (obj.campaign_family && CAMPAIGN_FAMILIES[obj.campaign_family]) {
            setCurrentFamilyId(obj.campaign_family);
            setCampaignType(CAMPAIGN_FAMILIES[obj.campaign_family].campaignType);
          }
          if (obj.campaign_type && CAMPAIGN_TYPES.includes(obj.campaign_type as any)) {
            setCampaignType(obj.campaign_type);
          }
          if (obj.campaign_sub_type) {
            const match = CAMPAIGN_SUB_TYPES.find(st => st === obj.campaign_sub_type);
            if (match) setSubType(match);
            else if (obj.campaign_sub_type !== 'other') setSubType(obj.campaign_sub_type);
          }
          // Extract editable fields
          const editable = getEditableFields();
          for (const k of editable) {
            if (obj[k] !== undefined && obj[k] !== null && String(obj[k]).trim() !== '') {
              parsed[k] = String(obj[k]);
            }
          }
        }
      } catch {
        setAiError('AI returned invalid JSON');
        return;
      }

      if (Object.keys(parsed).length === 0) {
        const snippet = text.length > 200 ? text.slice(0, 200) + '...' : text;
        setAiError(`AI returned no usable fields. Raw response: ${snippet}`);
        return;
      }

      setAiResult(JSON.stringify(parsed, null, 2));
      setAiSuggestions(prev => {
        // Keep existing for fields AI didn't touch
        const merged = { ...prev };
        for (const [k, v] of Object.entries(parsed)) {
          merged[k] = v;
        }
        return merged;
      });

      // Save history
      const historyRaw = localStorage.getItem(HISTORY_KEY);
      const history = historyRaw ? JSON.parse(historyRaw) : [];
      history.unshift({ brief, time: new Date().toLocaleString() });
      if (history.length > 5) history.length = 5;
      localStorage.setItem(HISTORY_KEY, JSON.stringify(history));
      setAiHistory(history);

      showToast(`AI generated ${Object.keys(parsed).length} field suggestions`);
    } catch (err: unknown) {
      clearTimeout(timeout);
      setAiLoading(false);
      if (err instanceof Error && err.name === 'AbortError') {
        setAiError('Request cancelled');
      } else {
        setAiError('AI request failed.');
      }
    }
  }

  function acceptSuggestion(key: string) {
    const val = aiSuggestions[key];
    if (!val) return;
    setFormValues(prev => ({ ...prev, [key]: val }));
    const next = { ...aiSuggestions };
    delete next[key];
    setAiSuggestions(next);
  }

  function rejectSuggestion(key: string) {
    const next = { ...aiSuggestions };
    delete next[key];
    setAiSuggestions(next);
  }

  function applyAllSuggestions() {
    const keys = Object.keys(aiSuggestions);
    if (keys.length === 0) return;
    setFormValues(prev => {
      const next = { ...prev };
      for (const k of keys) next[k] = aiSuggestions[k];
      return next;
    });
    setAiSuggestions({});
    showToast(`Accepted ${keys.length} suggestions`);
  }

  function dismissAllSuggestions() {
    setAiSuggestions({});
  }

  function onAiBriefChange(val: string) {
    setAiBrief(val);
  }

  // Render helpers
  const obj = buildCampaignObjective();
  const highlightHtml = jsonPreview ? syntaxHighlight(jsonPreview) : '';
  const suggestionCount = Object.keys(aiSuggestions).length;

  log('Rendered');
  return (
    <div className="sub-page">
      <header>
        <div className="header-inner">
          <div className="header-left">
            <BrandLogo />
            <div>
              <h1>Campaign Objective</h1>
              <div className="header-sub">For voice AI &amp; WhatsApp</div>
            </div>
          </div>
          <div className="header-right">
            <Nav />
            <ThemeToggle />
          </div>
        </div>
      </header>

      <main className={styles.main}>
        {/* AI Quick Generate Panel */}
        <section className={`${styles['ai-panel']} ${styles['fade-up']} ${styles['stagger-1']}`}>
          <div className={styles['ai-panel-title']}>AI Generate</div>
          <div className={styles['step-note']}>Type what campaign you need — AI fills every field. Review &amp; accept each suggestion.</div>
          <div className={styles['ai-quick-row']}>
            <textarea
              className={styles['ai-quick-input']}
              value={aiBrief}
              onChange={e => onAiBriefChange(e.target.value)}
              maxLength={2000}
              rows={3}
              placeholder="e.g. Test drive booking campaign for Mahindra Hyryder"
            />
            <div className={styles['ai-quick-footer']}>
              <span className={styles['ai-char-count']}>{aiBrief.length} / 2000</span>
              <button
                className={`${styles.btn} ${styles['btn-primary']}`}
                onClick={() => doAiGenerate(aiBrief)}
                disabled={aiLoading || aiBrief.trim().length === 0}
              >
                {aiLoading ? 'Generating...' : 'Generate'}
              </button>
            </div>
          </div>
          {aiLoading && <div className={styles['ai-loading']}><div className={styles['ai-spinner']} /> Analyzing your brief...</div>}
          {aiError && (
            <div className={styles['ai-error']}>
              <span>{aiError}</span>
              <button className={`${styles.btn} ${styles['btn-secondary']}`} onClick={() => doAiGenerate(aiBrief)} style={{ padding: '0.3rem 0.7rem', fontSize: '0.8rem' }}>Retry</button>
            </div>
          )}
          {aiResult && (
            <div className={styles['ai-result']}>
              <div className={styles['ai-result-header']}>
                <span>Generated JSON Preview</span>
                <button className={`${styles.btn} ${styles['btn-secondary']}`} onClick={applyAllSuggestions} disabled={suggestionCount === 0} style={{ padding: '0.3rem 0.7rem', fontSize: '0.8rem' }}>
                  Accept All {suggestionCount > 0 ? `(${suggestionCount})` : ''}
                </button>
              </div>
              <pre className={styles['ai-json-preview']}>{aiResult}</pre>
            </div>
          )}
          {/* History panel */}
          {/* Templates Section */}
          <div className={styles['tpl-section']}>
            <div className={styles['tpl-section-title']}>
              <span className={styles['tpl-section-header-left']} onClick={e => (e.currentTarget.parentElement?.parentElement as HTMLElement).classList.toggle(styles.collapsed)}>
                <span>Templates ({store.count})</span>
                <span className={styles['ai-history-arrow']}>&lsaquo;</span>
              </span>
              <span className={styles['tpl-section-header-right']}>
                <span className={styles['tpl-import-link']} onClick={() => store.importFileRef.current?.click()}>Import</span>
                {store.count > 0 && <span className={styles['tpl-import-link']} onClick={clearTemplates} style={{ marginLeft: '0.5rem', color: 'var(--text-muted)' }}>Clear All</span>}
                <input ref={store.importFileRef} type="file" accept=".json" onChange={importTemplate} style={{ display: 'none' }} />
              </span>
            </div>
            <div className={styles['tpl-section-body']} onDragOver={handleBodyDragOver}>
              {store.count === 0 ? (
                <div className={styles['tpl-empty']}>
                  No saved templates yet.
                  <span className={styles['tpl-empty-hint']}>Fill the form and use &ldquo;Save as Template&rdquo; in Step 7.</span>
                </div>
              ) : store.configs.map((tpl, idx) => (
                <div key={`wrap-${tpl.id}`} className={styles['tpl-card-wrap']}>
                  {dropTargetIdx === idx && <div className={styles['tpl-drop-indicator']} />}
                  <div
                    key={`card-${tpl.id}`}
                    className={`${styles['tpl-card']} ${dragIndex === idx ? styles['tpl-dragging'] : ''} ${loadConfirmId === tpl.id ? styles['tpl-loading'] : ''}`}
                    draggable
                    onDragStart={() => handleDragStart(idx)}
                    onDragOver={e => handleDragOver(e, idx)}
                    onDrop={() => handleDrop()}
                    onDragEnd={handleDragEnd}
                  >
                  <span className={styles['tpl-drag-handle']} aria-label="Drag to reorder">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
                      <circle cx="9" cy="5" r="1.5" fill="currentColor" />
                      <circle cx="15" cy="5" r="1.5" fill="currentColor" />
                      <circle cx="9" cy="12" r="1.5" fill="currentColor" />
                      <circle cx="15" cy="12" r="1.5" fill="currentColor" />
                      <circle cx="9" cy="19" r="1.5" fill="currentColor" />
                      <circle cx="15" cy="19" r="1.5" fill="currentColor" />
                    </svg>
                  </span>
                  <div className={styles['tpl-card-main']} onClick={() => loadTemplate(tpl)}>
                    <div className={styles['tpl-name']}>{tpl.name}</div>
                    {tpl.description && <div className={styles['tpl-desc']}>{tpl.description}</div>}
                    <div className={styles['tpl-meta']}>
                      <span className={styles['tpl-meta-item']}>{tpl.savedAt}</span>
                      <span className={styles['tpl-meta-item']}>{CAMPAIGN_FAMILIES[tpl.familyId]?.label || tpl.familyId}</span>
                    </div>
                    {loadConfirmId === tpl.id && (
                      <div className={styles['tpl-confirm']}>Click again to load &rarr;</div>
                    )}
                  </div>
                  <button
                    className={styles['tpl-export-btn']}
                    onClick={e => { e.stopPropagation(); exportTemplate(tpl); }}
                    title="Export template as JSON"
                  >
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4M7 10l5 5 5-5M12 15V3"/></svg>
                  </button>
                  <button
                    className={styles['tpl-delete-btn']}
                    onClick={e => { e.stopPropagation(); deleteTemplate(tpl.id); }}
                    title="Delete template"
                  >
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><path d="M18 6L6 18M6 6l12 12"/></svg>
                  </button>
                </div>
              </div>
              ))}
              {dropTargetIdx === store.count && (
                <div className={styles['tpl-card-wrap']}>
                  <div className={styles['tpl-drop-indicator']} />
                </div>
              )}
            </div>
          </div>

          {/* History panel */}
          <div className={styles['ai-history-wrap']}>
            <div className={styles['ai-history-title']} onClick={e => (e.currentTarget.parentElement as HTMLElement).classList.toggle(styles.collapsed)}>
              <span>Recent Generations ({aiHistory.length})</span>
              <span style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                {aiHistory.length > 0 && <span className={styles['tpl-import-link']} style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }} onClick={e => { e.stopPropagation(); clearHistory(); }}>Clear All</span>}
                <span className={styles['ai-history-arrow']}>&lsaquo;</span>
              </span>
            </div>
            <div className={styles['ai-history-body']}>
              {aiHistory.length === 0 ? (
                <div className={styles['ai-history-empty']}>No previous generations</div>
              ) : aiHistory.map((item, i) => (
                <div key={i} className={styles['ai-history-item']} onClick={() => setAiBrief(item.brief)}>
                  <span className={styles['ai-h-brief']}>{item.brief}</span>
                  <span className={styles['ai-h-time']}>{item.time}</span>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* Step 1: Campaign Family */}
        <section className={`${styles.panel} ${styles['fade-up']} ${styles['stagger-2']}`}>
          <div className={styles['section-header']}>
            <span className={styles['step-badge']}>1</span>
            <div className={styles['section-title']}>Campaign Family</div>
          </div>
          <div className={styles['step-note']}>Select a pre-built seed objective or configure from scratch.</div>

          {/* Seed Library Selector */}
          <div className={styles['seed-section']}>
            {selectedSeedId ? (
              <div className={styles['seed-active']}>
                <span className={styles['seed-badge']}>Seed</span>
                <span className={styles['seed-active-name']}>{getSeedObjectiveById(selectedSeedId)?.name || 'Unknown Seed'}</span>
                <span className={styles['seed-hint']}>Fields are pre-filled from this seed. Edit any field to customize.</span>
                <button className={`${styles.btn} ${styles['btn-secondary']}`} style={{ padding: '0.3rem 0.7rem', fontSize: '0.78rem' }} onClick={unlinkSeed}>Unlink Seed</button>
              </div>
            ) : (
              <>
                <div className={styles['seed-header']}>
                  <span className={styles['seed-header-title']}>Seed Library</span>
                  <span className={styles['seed-header-count']}>{SEED_OBJECTIVES.length} pre-built objectives</span>
                  <button
                    className={`${styles.btn} ${styles['seed-toggle-btn']}`}
                    onClick={() => setShowSeedPicker(!showSeedPicker)}
                  >
                    {showSeedPicker ? 'Cancel' : 'Browse Seeds'}
                  </button>
                </div>
                {showSeedPicker && (
                  <div className={styles['seed-picker']}>
                    <input
                      type="text"
                      className={styles['seed-search-input']}
                      value={seedSearchQuery}
                      onChange={e => setSeedSearchQuery(e.target.value)}
                      placeholder="Search seeds by name, vehicle, or tag..."
                      autoFocus
                    />
                    <div className={styles['seed-list']}>
                      {searchSeeds(seedSearchQuery).map(seed => (
                        <div
                          key={seed.id}
                          className={styles['seed-item']}
                          onClick={() => applySeedObjective(seed)}
                        >
                          <div className={styles['seed-item-left']}>
                            <span className={styles['seed-item-name']}>{seed.name}</span>
                            <span className={styles['seed-item-desc']}>{seed.description}</span>
                          </div>
                          <div className={styles['seed-item-right']}>
                            <span className={styles['seed-item-family']}>{CAMPAIGN_FAMILIES[seed.familyId]?.label || seed.familyId}</span>
                            <span className={styles['seed-item-tags']}>{seed.tags.slice(0, 3).join(' · ')}</span>
                          </div>
                          {seed.verified && <span className={styles['seed-verified']}>✓</span>}
                          {seed.isPlaceholder && <span className={styles['seed-placeholder']}>Draft</span>}
                        </div>
                      ))}
                      {searchSeeds(seedSearchQuery).length === 0 && (
                        <div className={styles['seed-empty']}>No seeds match your search.</div>
                      )}
                    </div>
                  </div>
                )}
              </>
            )}
          </div>

          <div className={styles['type-select-row']}>
            <label>Campaign Type</label>
            {CAMPAIGN_TYPES.map(t => (
              <button key={t} className={`${styles['type-btn']} ${campaignType === t ? styles['type-btn-active'] : ''}`} onClick={() => onCampaignTypeChange(t)}>
                {CAMPAIGN_TYPE_LABELS[t]}
              </button>
            ))}
          </div>
          <div className={styles['family-tabs']}>
            {Object.values(CAMPAIGN_FAMILIES).map(f => (
              <button
                key={f.id}
                className={`${styles['family-tab']} ${currentFamilyId === f.id ? styles.active : ''}`}
                onClick={() => onTabClick(f.id)}
              >
                <span className={styles['tab-icon']} dangerouslySetInnerHTML={{ __html: f.icon }} />
                <span className={styles['tab-label']}>{f.label}</span>
                <span className={styles['tab-desc']}>{f.description}</span>
              </button>
            ))}
          </div>
          <div className={styles['sub-type-row']}>
            <label>Sub-type</label>
            <select className={styles['sub-type-select']} value={subType} onChange={e => { setSubType(e.target.value); if (e.target.value !== 'other') setSubTypeOther(''); }}>
              {CAMPAIGN_SUB_TYPES.map(st => (
                <option key={st} value={st}>{st}</option>
              ))}
              <option value="other">Other…</option>
            </select>
            {subType === 'other' && (
              <input type="text" className={styles['sub-type-other']} value={subTypeOther} onChange={e => setSubTypeOther(e.target.value)} placeholder="Enter custom sub-type" autoFocus />
            )}
          </div>
        </section>

        {/* Step 2: Basic Info */}
        <section className={`${styles.panel} ${styles['fade-up']} ${styles['stagger-3']}`}>
          <div className={styles['section-header']}>
            <span className={styles['step-badge']}>2</span>
            <div className={styles['section-title']}>Basic Information</div>
          </div>
          <div className={styles['form-grid']}>
            <div className={`${styles['form-group']} ${styles.full}`}>
              <label>Campaign Objective Name</label>
              <input type="text" value={getValue('campaign_objective_name')} onChange={e => handleFormChange('campaign_objective_name', e.target.value)} placeholder="e.g. Toyota Hyryder TDB Outbound - Malayalam" />
              {aiSuggestions.campaign_objective_name && <SuggestionCard fieldKey="campaign_objective_name" value={aiSuggestions.campaign_objective_name} onAccept={() => acceptSuggestion('campaign_objective_name')} onReject={() => rejectSuggestion('campaign_objective_name')} />}
            </div>
            <div className={styles['form-group']}>
              <label>Dealership ID</label>
              <input type="text" value={getValue('dealership_id')} onChange={e => handleFormChange('dealership_id', e.target.value)} placeholder="e.g. DL-001" />
              {aiSuggestions.dealership_id && <SuggestionCard fieldKey="dealership_id" value={aiSuggestions.dealership_id} onAccept={() => acceptSuggestion('dealership_id')} onReject={() => rejectSuggestion('dealership_id')} />}
            </div>
            <div className={styles['form-group']}>
              <label>Dealer Name</label>
              <input type="text" value={getValue('dealer_name')} onChange={e => handleFormChange('dealer_name', e.target.value)} placeholder="e.g. Fortune Toyota" />
              {aiSuggestions.dealer_name && <SuggestionCard fieldKey="dealer_name" value={aiSuggestions.dealer_name} onAccept={() => acceptSuggestion('dealer_name')} onReject={() => rejectSuggestion('dealer_name')} />}
            </div>
            <div className={styles['form-group']}>
              <label>Brand ID</label>
              <input type="text" value={getValue('brand_id')} onChange={e => handleFormChange('brand_id', e.target.value)} placeholder="e.g. TKM" />
              {aiSuggestions.brand_id && <SuggestionCard fieldKey="brand_id" value={aiSuggestions.brand_id} onAccept={() => acceptSuggestion('brand_id')} onReject={() => rejectSuggestion('brand_id')} />}
            </div>
            <div className={styles['form-group']}>
              <label>Brand Name</label>
              <input type="text" value={getValue('brand_name')} onChange={e => handleFormChange('brand_name', e.target.value)} placeholder="e.g. Toyota Kirloskar Motor" />
              {aiSuggestions.brand_name && <SuggestionCard fieldKey="brand_name" value={aiSuggestions.brand_name} onAccept={() => acceptSuggestion('brand_name')} onReject={() => rejectSuggestion('brand_name')} />}
            </div>
          </div>
          {extraFields.length > 0 && (
            <div className={styles['field-group']}>
              <div className={styles['field-group-title']}>Campaign-Specific Fields</div>
              <div className={styles['form-grid']}>
                {extraFields.map(ef => (
                  <div key={ef.key} className={styles['form-group']}>
                    <label>{ef.label}</label>
                    <div className={styles['field-hint']}>{ef.hint}</div>
                    <input type="text" value={getValue(ef.key)} onChange={e => handleFormChange(ef.key, e.target.value)} placeholder={ef.hint} />
                    {aiSuggestions[ef.key] && <SuggestionCard fieldKey={ef.key} value={aiSuggestions[ef.key]} onAccept={() => acceptSuggestion(ef.key)} onReject={() => rejectSuggestion(ef.key)} />}
                  </div>
                ))}
              </div>
            </div>
          )}
        </section>

        {/* Step 3: Why */}
        <section className={`${styles.panel} ${styles['fade-up']} ${styles['stagger-4']}`}>
          <div className={styles['section-header']}>
            <span className={styles['step-badge']}>3</span>
            <div className={styles['section-title']}>Why</div>
          </div>
          <div className={styles['section-sub']}>Value proposition, objections, and non-applicability cases.</div>
          <div className={styles['form-grid']}>
            <div className={`${styles['form-group']} ${styles.full}`}>
              <label>Why User Should Avail This</label>
              <div className={styles['field-hint']}>Value proposition and benefits</div>
              <textarea value={getValue('why_user_should_avail_this')} onChange={e => handleFormChange('why_user_should_avail_this', e.target.value)} placeholder="e.g. Great fuel efficiency, smooth drive..." />
              {aiSuggestions.why_user_should_avail_this && <SuggestionCard fieldKey="why_user_should_avail_this" value={aiSuggestions.why_user_should_avail_this} onAccept={() => acceptSuggestion('why_user_should_avail_this')} onReject={() => rejectSuggestion('why_user_should_avail_this')} />}
            </div>
            <div className={`${styles['form-group']} ${styles.full}`}>
              <label>Reasons Users May Not Be Interested</label>
              <div className={styles['field-hint']}>{fieldOverrides.reasons_users_may_not_be_interested?.hint || 'Objection handling for voice AI'}</div>
              <textarea value={getValue('reasons_users_may_not_be_interested')} onChange={e => handleFormChange('reasons_users_may_not_be_interested', e.target.value)} placeholder="e.g. Not looking to buy right now, Already booked..." />
              {aiSuggestions.reasons_users_may_not_be_interested && <SuggestionCard fieldKey="reasons_users_may_not_be_interested" value={aiSuggestions.reasons_users_may_not_be_interested} onAccept={() => acceptSuggestion('reasons_users_may_not_be_interested')} onReject={() => rejectSuggestion('reasons_users_may_not_be_interested')} />}
            </div>
            <div className={`${styles['form-group']} ${styles.full}`}>
              <label>Reasons For Non-applicability</label>
              <div className={styles['field-hint']}>{fieldOverrides.reasons_for_non_applicability?.hint || 'When the campaign does not apply'}</div>
              <textarea value={getValue('reasons_for_non_applicability')} onChange={e => handleFormChange('reasons_for_non_applicability', e.target.value)} placeholder="e.g. Already purchased vehicle, Not in service area..." />
              {aiSuggestions.reasons_for_non_applicability && <SuggestionCard fieldKey="reasons_for_non_applicability" value={aiSuggestions.reasons_for_non_applicability} onAccept={() => acceptSuggestion('reasons_for_non_applicability')} onReject={() => rejectSuggestion('reasons_for_non_applicability')} />}
            </div>
          </div>
        </section>

        {/* Step 4: Conversation Flow */}
        <section className={`${styles.panel} ${styles['fade-up']} ${styles['stagger-5']}`}>
          <div className={styles['section-header']}>
            <span className={styles['step-badge']}>4</span>
            <div className={styles['section-title']}>Conversation Flow</div>
          </div>
          <div className={styles['section-sub']}>Define the opening, tone, purpose, and step-by-step flow.</div>
          <div className={styles['form-grid']}>
            <div className={`${styles['form-group']} ${styles.full}`}>
              <label>{fieldOverrides.custom_conversation_start_pattern?.label || 'Custom Conversation Start Pattern'}</label>
              <div className={styles['field-hint']}>{fieldOverrides.custom_conversation_start_pattern?.hint || 'Opening line for the AI agent'}</div>
              <textarea value={getValue('custom_conversation_start_pattern')} onChange={e => handleFormChange('custom_conversation_start_pattern', e.target.value)} placeholder="e.g. Hello (customer_name), this is (agent_name)..." />
              {aiSuggestions.custom_conversation_start_pattern && <SuggestionCard fieldKey="custom_conversation_start_pattern" value={aiSuggestions.custom_conversation_start_pattern} onAccept={() => acceptSuggestion('custom_conversation_start_pattern')} onReject={() => rejectSuggestion('custom_conversation_start_pattern')} />}
            </div>
            <div className={styles['form-group']}>
              <label>{fieldOverrides.conversation_tone?.label || 'Conversation Tone'}</label>
              <div className={styles['field-hint']}>{fieldOverrides.conversation_tone?.hint || 'Agent speaking style'}</div>
              <input type="text" value={getValue('conversation_tone')} onChange={e => handleFormChange('conversation_tone', e.target.value)} placeholder="e.g. Friendly, professional, persuasive" />
              {aiSuggestions.conversation_tone && <SuggestionCard fieldKey="conversation_tone" value={aiSuggestions.conversation_tone} onAccept={() => acceptSuggestion('conversation_tone')} onReject={() => rejectSuggestion('conversation_tone')} />}
            </div>
            <div className={`${styles['form-group']} ${styles.full}`}>
              <label>Purpose</label>
              <div className={styles['field-hint']}>Core purpose of the campaign</div>
              <textarea value={getValue('purpose')} onChange={e => handleFormChange('purpose', e.target.value)} placeholder="e.g. Book a test drive for the Urban Cruiser Hyryder..." />
              {aiSuggestions.purpose && <SuggestionCard fieldKey="purpose" value={aiSuggestions.purpose} onAccept={() => acceptSuggestion('purpose')} onReject={() => rejectSuggestion('purpose')} />}
            </div>
            <div className={`${styles['form-group']} ${styles.full}`}>
              <label>{fieldOverrides.purpose_steps?.label || 'Purpose Steps'}</label>
              <div className={styles['field-hint']}>{fieldOverrides.purpose_steps?.hint || 'Step-by-step flow (voice) or workflow stages'}</div>
              <textarea value={getValue('purpose_steps')} onChange={e => handleFormChange('purpose_steps', e.target.value)} placeholder="1. Greet and introduce\n2. Confirm customer identity..." />
              {aiSuggestions.purpose_steps && <SuggestionCard fieldKey="purpose_steps" value={aiSuggestions.purpose_steps} onAccept={() => acceptSuggestion('purpose_steps')} onReject={() => rejectSuggestion('purpose_steps')} />}
            </div>
          </div>
        </section>

        {/* Step 5: Guardrails */}
        <section className={`${styles.panel} ${styles['fade-up']} ${styles['stagger-6']}`}>
          <div className={styles['section-header']}>
            <span className={styles['step-badge']}>5</span>
            <div className={styles['section-title']}>Guardrails &amp; Configuration</div>
          </div>
          <div className={styles['form-grid']}>
            <div className={`${styles['form-group']} ${styles.full}`}>
              <label>Guardrails &amp; Guidelines</label>
              <div className={styles['field-hint']}>Rules the AI must follow</div>
              <textarea value={getValue('guardrails_guidelines')} onChange={e => handleFormChange('guardrails_guidelines', e.target.value)} placeholder="e.g. Do not share pricing unless asked..." />
              {aiSuggestions.guardrails_guidelines && <SuggestionCard fieldKey="guardrails_guidelines" value={aiSuggestions.guardrails_guidelines} onAccept={() => acceptSuggestion('guardrails_guidelines')} onReject={() => rejectSuggestion('guardrails_guidelines')} />}
            </div>
            <div className={`${styles['form-group']} ${styles.full}`}>
              <label>Other Important Information</label>
              <div className={styles['field-hint']}>Additional context, disclaimers, or notes</div>
              <textarea value={getValue('other_important_information')} onChange={e => handleFormChange('other_important_information', e.target.value)} placeholder="e.g. Campaign runs Mon-Sat 10 AM to 6 PM..." />
              {aiSuggestions.other_important_information && <SuggestionCard fieldKey="other_important_information" value={aiSuggestions.other_important_information} onAccept={() => acceptSuggestion('other_important_information')} onReject={() => rejectSuggestion('other_important_information')} />}
            </div>
            <div className={`${styles['form-group']} ${styles.full}`}>
              <label>Campaign Objective Description</label>
              <div className={styles['field-hint']}>Brief description of the campaign</div>
              <textarea value={getValue('campaign_objective_description')} onChange={e => handleFormChange('campaign_objective_description', e.target.value)} placeholder="e.g. Outbound voice campaign..." />
              {aiSuggestions.campaign_objective_description && <SuggestionCard fieldKey="campaign_objective_description" value={aiSuggestions.campaign_objective_description} onAccept={() => acceptSuggestion('campaign_objective_description')} onReject={() => rejectSuggestion('campaign_objective_description')} />}
            </div>
            <div className={`${styles['form-group']} ${styles['checkbox-row']}`}>
              <input type="checkbox" id="is_custom" checked={isCustom} onChange={e => setIsCustom(e.target.checked)} />
              <label htmlFor="is_custom" style={{ textTransform: 'none', letterSpacing: 0, fontSize: '0.82rem', color: 'var(--text)' }}>Mark as custom campaign</label>
            </div>
            <div className={`${styles['form-group']} ${styles.full}`}>
              <label>Filter Params (JSON)</label>
              <div className={styles['field-hint']}>Optional campaign filter configuration</div>
              <textarea value={getValue('filter_params')} onChange={e => handleFormChange('filter_params', e.target.value)} placeholder='e.g. {"city": ["Chennai", "Bangalore"]}' />
              {aiSuggestions.filter_params && <SuggestionCard fieldKey="filter_params" value={aiSuggestions.filter_params} onAccept={() => acceptSuggestion('filter_params')} onReject={() => rejectSuggestion('filter_params')} />}
            </div>
          </div>
          {suggestionCount > 0 && (
            <div className={styles['ai-dismiss-link']}>
              <a href="#" onClick={e => { e.preventDefault(); dismissAllSuggestions(); }}>Dismiss All Suggestions</a>
            </div>
          )}
        </section>

        {/* Step 6: Tags & Attributes */}
        <section className={`${styles.panel} ${styles['fade-up']} ${styles['stagger-7']}`}>
          <div className={styles['section-header']}>
            <span className={styles['step-badge']}>6</span>
            <div className={styles['section-title']}>Tags &amp; Attributes</div>
          </div>
          <div className={styles['section-sub']}>Configure tags, CTAs, workflows, and custom attributes.</div>
          <div className={styles['field-group']}>
            <div className={styles['field-group-title']}>Required Attributes</div>
            <TagPicker options={family.requiredAttributes} value={getValue('required_attributes')} onChange={v => handleFormChange('required_attributes', v)} label="required_attributes" />
            {aiSuggestions.required_attributes && <SuggestionCard fieldKey="required_attributes" value={aiSuggestions.required_attributes} onAccept={() => acceptSuggestion('required_attributes')} onReject={() => rejectSuggestion('required_attributes')} />}
          </div>
          <div className={styles['field-group']}>
            <div className={styles['field-group-title']}>Target Audience Tags</div>
            <TagPicker options={family.targetAudienceTags} value={getValue('target_audience_tags')} onChange={v => handleFormChange('target_audience_tags', v)} label="target_audience_tags" />
            {aiSuggestions.target_audience_tags && <SuggestionCard fieldKey="target_audience_tags" value={aiSuggestions.target_audience_tags} onAccept={() => acceptSuggestion('target_audience_tags')} onReject={() => rejectSuggestion('target_audience_tags')} />}
          </div>
          <div className={styles['field-group']}>
            <div className={styles['field-group-title']}>CTAs</div>
            <TagPicker options={[...CTA_OPTIONS]} value={getValue('ctas')} onChange={v => handleFormChange('ctas', v)} label="ctas" />
            {aiSuggestions.ctas && <SuggestionCard fieldKey="ctas" value={aiSuggestions.ctas} onAccept={() => acceptSuggestion('ctas')} onReject={() => rejectSuggestion('ctas')} />}
          </div>
          <div className={styles['field-group']}>
            <div className={styles['field-group-title']}>Workflows</div>
            <TagPicker options={[...WORKFLOW_OPTIONS, 'other']} value={getValue('workflows')} onChange={v => handleFormChange('workflows', v)} label="workflows" />
            {aiSuggestions.workflows && <SuggestionCard fieldKey="workflows" value={aiSuggestions.workflows} onAccept={() => acceptSuggestion('workflows')} onReject={() => rejectSuggestion('workflows')} />}
          </div>
          <div className={styles['field-group']}>
            <div className={styles['field-group-title']}>Custom Campaign Attributes</div>
            <div className={styles['field-hint']} style={{ marginBottom: '0.5rem' }}>Key-value pairs for campaign-specific configuration</div>
            <ObjectListEditor value={getValue('custom_campaign_attributes')} onChange={v => handleFormChange('custom_campaign_attributes', v)} keyLabel="Attribute Key" valueLabel="Attribute Value" />
            {aiSuggestions.custom_campaign_attributes && <SuggestionCard fieldKey="custom_campaign_attributes" value={aiSuggestions.custom_campaign_attributes} onAccept={() => acceptSuggestion('custom_campaign_attributes')} onReject={() => rejectSuggestion('custom_campaign_attributes')} />}
          </div>
          <div className={styles['field-group']}>
            <div className={styles['field-group-title']}>Audience Attributes</div>
            <div className={styles['field-hint']} style={{ marginBottom: '0.5rem' }}>Key-value pairs describing audience characteristics</div>
            <ObjectListEditor value={getValue('audience_attributes')} onChange={v => handleFormChange('audience_attributes', v)} keyLabel="Attribute Key" valueLabel="Attribute Value" />
            {aiSuggestions.audience_attributes && <SuggestionCard fieldKey="audience_attributes" value={aiSuggestions.audience_attributes} onAccept={() => acceptSuggestion('audience_attributes')} onReject={() => rejectSuggestion('audience_attributes')} />}
          </div>
        </section>

        {/* Step 7: Auto-generated Fields */}
        <section className={`${styles.panel} ${styles['fade-up']} ${styles['stagger-8']}`}>
          <div className={styles['section-header']}>
            <span className={styles['step-badge']}>7</span>
            <div className={styles['section-title']}>Auto-generated Fields</div>
          </div>
          <div className={styles['section-sub']}>These are computed automatically from your inputs. Edit source fields above to update.</div>
          <div className={styles['stats-bar']}>
            <div className={styles['stat-card']}>
              <div className={styles['stat-label']}>Fields Total</div>
              <div className={styles['stat-value']}>{fieldCount}</div>
            </div>
            <div className={styles['stat-card']}>
              <div className={styles['stat-label']}>Fields Filled</div>
              <div className={styles['stat-value']}>{fieldFilled}</div>
            </div>
            <div className={styles['stat-card']}>
              <div className={styles['stat-label']}>Completion</div>
              <div className={styles['stat-value']}>{fieldPct}</div>
            </div>
          </div>
          <div className={styles['form-grid']}>
            <div className={`${styles['form-group']} ${styles.full}`}>
              <label>Campaign Objective ID</label>
              <div className={styles['field-hint']}>Auto-generated format: campaign_type-name-dealership_id</div>
              <div className={styles['auto-field']}>{String(obj.campaign_objective_id || '')}</div>
            </div>
            <div className={styles['form-group']}>
              <label>Campaign Type</label>
              <div className={styles['auto-field']}>{String(obj.campaign_type || '')}</div>
            </div>
            <div className={styles['form-group']}>
              <label>Campaign Sub-type</label>
              <div className={styles['auto-field']}>{String(obj.campaign_sub_type || '')}</div>
            </div>
            <div className={`${styles['form-group']} ${styles.full}`}>
              <label>Search Term</label>
              <div className={styles['field-hint']}>Auto-generated from campaign context for search indexing</div>
              <div className={styles['auto-field']}>{String(obj.search_term || '')}</div>
            </div>
            <div className={`${styles['form-group']} ${styles.full}`}>
              <label>Doc Data</label>
              <div className={styles['field-hint']}>Auto-generated metadata</div>
              <div className={styles['auto-field']}>{JSON.stringify(obj.doc_data)}</div>
            </div>
          </div>
        </section>

        {/* Step 8: Language & Channel Variants */}
        {selectedSeedId && (
          <section className={`${styles.panel} ${styles['fade-up']} ${styles['stagger-9']}`}>
            <div className={styles['section-header']}>
              <span className={styles['step-badge']}>8</span>
              <div className={styles['section-title']}>Language &amp; Channel Variants</div>
            </div>
            <div className={styles['step-note']}>Manage variants across 6 languages and 2 channels. Green = created. Click a cell to load that variant.</div>
            <div className={styles['lang-grid']}>
              {/* Header row */}
              <div className={styles['lang-row']}>
                <div className={styles['lang-label']}></div>
                {CHANNELS.map(ch => (
                  <div key={ch.id} className={styles['lang-label']} style={{ textAlign: 'center', fontSize: '0.72rem' }}>{ch.label}</div>
                ))}
              </div>
              {LANGUAGES.map(lang => (
                <div key={lang.id} className={styles['lang-row']}>
                  <div className={styles['lang-label']}>{lang.label}</div>
                  {CHANNELS.map(ch => {
                    const status = getVariantStatus(lang.id, ch.id);
                    return (
                      <div
                        key={`${lang.id}-${ch.id}`}
                        className={`${styles['lang-cell']} ${status !== 'none' ? styles[status] : ''}`}
                        onClick={() => loadVariant(lang.id, ch.id)}
                        title={
                          status === 'active' ? `Currently editing ${lang.label} ${ch.label}` :
                          status === 'created' ? `Load ${lang.label} ${ch.label} variant` :
                          `Create ${lang.label} ${ch.label} variant`
                        }
                      >
                        {status === 'none' ? '—' : lang.label}
                      </div>
                    );
                  })}
                </div>
              ))}
            </div>
            <div className={styles['lang-actions']}>
              <button className={`${styles.btn} ${styles['btn-primary']}`} onClick={saveCurrentAsVariant} style={{ fontSize: '0.82rem', padding: '0.45rem 1rem' }}>
                Save {LANGUAGES.find(l => l.id === activeLang)?.label} {CHANNELS.find(c => c.id === activeChannel)?.label}
              </button>
              <button className={`${styles.btn} ${styles['btn-secondary']}`} onClick={createAllMissingVariants} style={{ fontSize: '0.82rem', padding: '0.45rem 1rem' }}>
                Create All Missing
              </button>
              <button className={`${styles.btn} ${styles['btn-secondary']}`} onClick={() => deleteVariant(activeLang, activeChannel)} style={{ fontSize: '0.82rem', padding: '0.45rem 1rem' }}>
                Delete Active
              </button>
            </div>
            <div className={styles['lang-summary']}>
              <strong>{variants.length}</strong> of <strong>{LANGUAGES.length * CHANNELS.length}</strong> variants created
              &middot; Active: <strong>{LANGUAGES.find(l => l.id === activeLang)?.label} {CHANNELS.find(c => c.id === activeChannel)?.label}</strong>
            </div>
          </section>
        )}

        {/* Step 9: Preview & Export */}
        <section className={`${styles.panel} ${styles['fade-up']} ${styles['stagger-10']}`}>
          <div className={styles['section-header']}>
            <span className={styles['step-badge']}>9</span>
            <div className={styles['section-title']}>Preview &amp; Export</div>
          </div>
          <div className={styles['section-sub']}>Your campaign objective as a structured JSON. Copy or download it.</div>
          <div className={styles.controls}>
            <button className={`${styles.btn} ${styles['btn-primary']}`} id="downloadBtn" onClick={downloadJSON} disabled={downloadBtnDisabled}>Download JSON</button>
            <button className={`${styles.btn} ${styles['btn-secondary']}`} onClick={copyJSON}>Copy to Clipboard</button>
            <button className={`${styles.btn} ${styles['btn-secondary']}`} onClick={openSaveDialog} disabled={!String(obj.campaign_objective_name || '').trim()}>Save as Template</button>
            <button className={`${styles.btn} ${styles['btn-secondary']}`} onClick={clearForm}>Clear All</button>
          </div>
          <div className={styles['json-preview']} dangerouslySetInnerHTML={{ __html: highlightHtml || '<span class="json-null">null</span> — fill out the form above' }} />
          <div className={`${styles.status} ${statusType ? styles[statusType] : ''}`}>{statusMsg}</div>
        </section>
      </main>

      {/* Save as Template Dialog */}
      {showSaveDialog && (
        <div className={styles['tpl-overlay']} onClick={() => setShowSaveDialog(false)}>
          <div className={styles['tpl-dialog']} onClick={e => e.stopPropagation()}>
            <div className={styles['tpl-dialog-header']}>
              <span className={styles['tpl-dialog-title']}>Save as Template</span>
              <button className={styles['tpl-dialog-close']} onClick={() => setShowSaveDialog(false)}>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><path d="M18 6L6 18M6 6l12 12"/></svg>
              </button>
            </div>
            <div className={styles['tpl-dialog-body']}>
              <div className={styles['form-group']}>
                <label>Template Name</label>
                <input
                  type="text"
                  value={saveDialogName}
                  onChange={e => setSaveDialogName(e.target.value)}
                  placeholder="e.g. Hyryder TDB Bangalore"
                  autoFocus
                  onKeyDown={e => { if (e.key === 'Enter') saveTemplate(); }}
                />
              </div>
              <div className={styles['form-group']}>
                <label>Description <span style={{ fontWeight: 400, color: 'var(--cg-text-muted)' }}>(optional)</span></label>
                <textarea
                  value={saveDialogDesc}
                  onChange={e => setSaveDialogDesc(e.target.value)}
                  placeholder="What's this template for?"
                  rows={2}
                />
              </div>
              <div className={styles['tpl-dialog-footer']}>
                <button className={`${styles.btn} ${styles['btn-secondary']}`} onClick={() => setShowSaveDialog(false)}>Cancel</button>
                <button className={`${styles.btn} ${styles['btn-primary']}`} onClick={saveTemplate} disabled={!saveDialogName.trim()}>Save</button>
              </div>
            </div>
          </div>
        </div>
      )}

      <footer>AutoNage — Campaign Objective Generator</footer>

      <style dangerouslySetInnerHTML={{ __html:
        `.json-key { color: var(--cg-accent); }
         .json-string { color: #63d6a3; }
         .json-number { color: #f59e0b; }
         .json-bool { color: #eab308; }
         .json-null { color: var(--cg-text-muted); }`
      }} />
    </div>

  );
}
