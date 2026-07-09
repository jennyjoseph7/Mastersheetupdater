export interface FormatterTemplate {
  label: string;
  sourceToTarget: Record<string, string>;
  multiSource?: Record<string, string[]>;
  outputOrder: string[];
  defaults: Record<string, string>;
  normalizeMahindraModels?: boolean;
  normalizeToyotaModels?: boolean;
}

export const TEMPLATES: Record<string, FormatterTemplate> = {
  bullmenn_service: {
    label: 'Bullmenn - Service Reminder',
    sourceToTarget: {
      'Sale Date': 'purchase_date',
      'Dealer': 'workshop_code',
      'Phone No': 'phone_number',
      'Model': 'vehicle_model',
      'Chassis No': 'vin_number',
      'Sales Customer Name': 'person_name',
      'Vehicle Number': 'reg_number',
      'Last Service Date': 'last_service_date',
      'Service Due Date': 'next_service_due',
    },
    outputOrder: ['workshop_code', 'purchase_date', 'vin_number', 'next_service_due', 'person_name', 'vehicle_model', 'reg_number', 'phone_number', 'alt_phone_number_2', 'last_service_date'],
    defaults: {},
  },
  ambal_erode_service: {
    label: 'Ambal ERODE - Service Reminder',
    sourceToTarget: {
      'Dealer Code': 'workshop_code',
      'VIN': 'vin_number',
      'Due Date': 'next_service_due',
      'Cust. Name': 'person_name',
      'Model Name': 'vehicle_model',
      'Registration Num': 'reg_number',
      'Customer Mobile No.': 'phone_number',
      'Last Scheduled Service KM': 'odometer_reading',
      'Last Scheduled Service Date': 'last_service_date',
      'Current Loyalty Points': 'customer_score',
    },
    outputOrder: ['workshop_code', 'vin_number', 'next_service_due', 'person_name', 'vehicle_model', 'reg_number', 'phone_number', 'alt_phone_number_2', 'odometer_reading', 'last_service_date', 'customer_score', 'purpose_of_visit'],
    defaults: { purpose_of_visit: 'yearly service' },
  },
  ambal_saibaba_service: {
    label: 'Ambal SAIBABA - Service Reminder',
    sourceToTarget: {
      'Dealer Code': 'workshop_code',
      'VIN': 'vin_number',
      'Due Date': 'next_service_due',
      'Cust. Name': 'person_name',
      'Model Name': 'vehicle_model',
      'Registration Num': 'reg_number',
      'Mobile Number': 'phone_number',
      'Last Scheduled Service KM': 'odometer_reading',
      'Last Scheduled Service Date': 'last_service_date',
      'Current Loyalty Points': 'customer_score',
    },
    outputOrder: ['workshop_code', 'vin_number', 'next_service_due', 'person_name', 'vehicle_model', 'reg_number', 'phone_number', 'alt_phone_number_2', 'odometer_reading', 'last_service_date', 'customer_score', 'purpose_of_visit'],
    defaults: { purpose_of_visit: 'yearly service' },
  },
  suryabala_service: {
    label: 'SURYABALA - Service Reminder',
    sourceToTarget: {
      'Customer Name': 'person_name',
      'Contact Number': 'phone_number',
      'Model Name': 'vehicle_model',
      'Registration No.': 'reg_number',
      'Next Service Type': 'service_type',
      'Next Service Date': 'next_service_due',
      'Frame #': 'vin_number',
    },
    outputOrder: ['person_name', 'phone_number', 'vehicle_model', 'reg_number', 'service_type', 'next_service_due', 'vin_number'],
    defaults: {},
  },
  icare_feedback: {
    label: 'ICARE - Post Service Feedback',
    sourceToTarget: {
      'Location Name': 'showroom_code',
      'Bill No': 'lead_tags',
      'Customer': 'person_name',
      'Mobile No': 'phone_number',
    },
    multiSource: {
      lead_tags: ['Bill Number', 'Bill', 'Invoice No'],
      phone_number: ['Mobile Number', 'Phone', 'Contact Number', 'Customer Mobile'],
    },
    outputOrder: ['showroom_code', 'person_name', 'phone_number', 'lead_tags'],
    defaults: {},
  },
  anant_sales: {
    label: 'Anant Cars - Sales / Lead Campaign',
    sourceToTarget: {
      'Customer Name': 'person_name',
      'Customer Phone': 'phone_number',
      'Product Family': 'interested_vehicle_name',
    },
    multiSource: {
      phone_number: ['Customer Mobile', 'Mobile', 'Phone', 'Mobile Number', 'PHONE NUMBER', 'PHONE NO', 'CONTACT NUMBER', 'CONTACT NO'],
      interested_vehicle_name: ['Vehicle Model', 'MODEL', 'Product', 'Interested Vehicle', 'VARIANT'],
    },
    outputOrder: ['showroom_code', 'region_name', 'dealership_id', 'person_name', 'phone_number', 'interested_vehicle_name', 'interested_vehicle_brand_name', 'seating_capacity_preference', 'city', 'pincode', 'subdivision_name', 'alt_phone_number_2', 'lead_source'],
    defaults: { interested_vehicle_brand_name: 'Mahindra' },
    normalizeMahindraModels: true,
  },
  singhal_sales: {
    label: 'Singhal - Sales / Lead Campaign',
    sourceToTarget: {
      'CUSTOMER NAME': 'person_name',
      'MOBILE NUMBER': 'phone_number',
      'MODEL': 'interested_vehicle_name',
      'ADDRESS': 'city',
    },
    multiSource: {
      person_name: ['CUSTOMER NAME', 'Customer Name', 'CUSTOMERNAME', 'NAME', 'Full Name'],
      phone_number: ['MOBILE NUMBER', 'Mobile Number', 'PHONE', 'CONTACT NUMBER', 'MOBILE', 'MOBILE NO', 'CONTACT'],
      interested_vehicle_name: ['MODEL', 'Model', 'VEHICLE MODEL', 'CAR MODEL', 'MODEL NAME'],
      city: ['ADDRESS', 'Address', 'CITY', 'City', 'LOCATION'],
    },
    outputOrder: ['person_name', 'phone_number', 'interested_vehicle_name', 'interested_vehicle_brand_name', 'seating_capacity_preference', 'city'],
    defaults: { interested_vehicle_brand_name: 'Volkswagen' },
  },
  fortune_hyryder_sales: {
    label: 'Fortune Hyryder - Sales / Lead Campaign',
    sourceToTarget: {
      'Enquiry Name': 'person_name',
      'MODEL': 'interested_vehicle_name',
      'Contact Number': 'phone_number',
    },
    multiSource: {
      showroom_code: ['Showroom', 'SHOWROOM', 'Branch', 'BRANCH CODE', 'Location Name', 'DEALER CODE'],
      person_name: ['NAMES', 'CUSTOMER NAME', 'CUSTOMERNAME', 'CUSTOMER_NAME', 'ENQUIRY NAME', 'First Name'],
      phone_number: ['MOBILE NO', 'MOBILE NUMBER', 'MOBILENUMBER', 'MOBILE', 'PHONE NUMBER', 'CONTACT NUMBER', 'CONTACT NO'],
      interested_vehicle_name: ['Model', 'VEHICLE MODEL', 'INTERESTED VEHICLE', 'MODEL NAME'],
    },
    outputOrder: ['showroom_code', 'person_name', 'phone_number', 'interested_vehicle_name', 'interested_vehicle_brand_name'],
    defaults: {
      interested_vehicle_name: 'Urban Cruiser Hyryder',
      interested_vehicle_brand_name: 'Toyota Kirloskar Motor',
    },
  },
  fortune_toyota_post: {
    label: 'Fortune Toyota - Post Sales / Service Reminder',
    sourceToTarget: {
      'Service Due Date': 'next_service_due',
      'Workshop': 'workshop_code',
      'Predicted Service Type': 'service_plan_type',
      'Customer Name': 'person_name',
      'Contact Number': 'phone_number',
      'Reg No.': 'reg_number',
      'VIN No.': 'vin_number',
      'Model': 'vehicle_model',
      'Sale Date': 'purchase_date',
    },
    multiSource: {
      next_service_due: ['Service Due', 'Next Service Date', 'NEXT_SERVICE_DUE', 'SERVICE DUE DATE'],
      workshop_code: ['Workshop Code', 'BRANCH', 'Dealer Code', 'WORKSHOP'],
      service_plan_type: ['Predicted Service Type', 'Service Plan Type', 'SERVICE_PLAN_TYPE', 'SERVICE TYPE', 'PREDICTED SERVICE TYPE'],
      phone_number: ['Mobile No', 'Mobile Number', 'MOBILE', 'Phone', 'Customer Mobile', 'CONTACT NUMBER', 'CONTACT NO'],
      reg_number: ['Reg No', 'Registration No', 'Registration Number', 'REG NUMBER', 'VEHICLE NUMBER'],
      vin_number: ['VIN', 'VIN Number', 'Chassis No', 'Chassis Number', 'Frame #', 'CHASSIS NO', 'VIN NO'],
      vehicle_model: ['MODEL', 'Vehicle Model', 'Model Name', 'VEHICLE MODEL'],
      purchase_date: ['Purchase Date', 'Sales Date', 'SALE DATE'],
      person_name: ['Customer Name', 'CUST NAME', 'CLIENT NAME', 'CUSTOMER NAME'],
    },
    outputOrder: ['next_service_due', 'workshop_code', 'service_plan_type', 'person_name', 'phone_number', 'reg_number', 'vin_number', 'vehicle_model', 'purchase_date'],
    defaults: {},
    normalizeToyotaModels: true,
  },
  bimal_sales: {
    label: 'Bimal - Sales / Lead Campaign',
    sourceToTarget: {
      'CUST_NAME': 'person_name',
      'MOBILE': 'phone_number',
      'MODEL_DESC': 'interested_vehicle_name',
      'CITY': 'city',
      'PIN_CD': 'pincode',
      'STATE': 'subdivision_name',
      'ENQ_SOURCE': 'lead_source',
      'DEALER_MAP_CD': 'showroom_code',
    },
    multiSource: {
      person_name: ['CUST_NAME', 'Customer Name', 'CUSTOMER NAME', 'Customer', 'CUST NAME', 'NAME', 'Full Name', 'CUSTOMERNAME'],
      phone_number: ['MOBILE', 'Mobile', 'MOBILE NUMBER', 'Phone', 'PHONE NUMBER', 'Mobile No', 'CONTACT NUMBER', 'CONTACT NO', 'PHONE', 'MOBILE NO'],
      interested_vehicle_name: ['MODEL_DESC', 'Model', 'MODEL', 'Model Description', 'MODEL DESC', 'Vehicle Model', 'VEHICLE MODEL', 'INTERESTED VEHICLE', 'CAR MODEL'],
      city: ['CITY', 'City', 'CITY NAME'],
      pincode: ['PIN_CD', 'Pincode', 'Pin Code', 'PINCODE', 'PIN', 'PIN CODE'],
      subdivision_name: ['STATE', 'State'],
      lead_source: ['ENQ_SOURCE', 'Source', 'Enquiry Source', 'ENQUIRY MODE', 'ENQUIRY SOURCE', 'LEAD SOURCE', 'ENQUIRY_MODE'],
      showroom_code: ['DEALER_MAP_CD', 'Dealer Code', 'Dealer', 'DEALER', 'BRANCH CODE', 'LOC_CD', 'Dealer Map Code', 'DEALER CODE', 'SHOWROOM', 'BRANCH', 'Location Name'],
    },
    outputOrder: ['showroom_code', 'person_name', 'phone_number', 'interested_vehicle_name', 'interested_vehicle_brand_name', 'city', 'pincode', 'subdivision_name', 'lead_source'],
    defaults: { interested_vehicle_brand_name: 'Maruti Suzuki Arena' },
  },
  perfect_riders_service: {
    label: 'Perfect Riders',
    sourceToTarget: {
      'Network Code': 'workshop_code',
      'PERSON_NAME': 'person_name',
      'PHONE_NUMBER': 'phone_number',
      'VEHICLE_MODEL': 'vehicle_model',
      'REG_NUMBER': 'reg_number',
      'Previous Jobcard Date': 'last_service_date',
      'NEXT_SERVICE_DATE': 'next_service_due',
      'Chassis No': 'vin_number',
      'Retail Mobile No': 'alt_phone_number_2',
      'Previous Meter Reading': 'odometer_reading',
    },
    multiSource: {
      workshop_code: ['Workshop Code', 'WORKSHOP', 'Dealer Code', 'BRANCH CODE', 'Dealer Code*', 'Network Code'],
      person_name: ['Customer Name', 'CUSTOMER NAME', 'NAME', 'Full Name', 'PERSON NAME', 'CUST NAME', 'Customer Name*'],
      phone_number: ['Mobile No', 'Mobile Number', 'PHONE', 'Customer Mobile', 'CONTACT NUMBER', 'CONTACT NO', 'PHONE NO', 'Phone No*'],
      vehicle_model: ['MODEL', 'Vehicle Model', 'Model Name', 'VEHICLE MODEL', 'MODEL NAME', 'Model*'],
      reg_number: ['Reg No', 'Registration No', 'Registration Number', 'REG NUMBER', 'VEHICLE NUMBER', 'Reg No.', 'REG NO'],
      last_service_date: ['Last Service', 'Last Service Date', 'LAST SERVICE', 'SERVICE DATE', 'Last Service Date*', 'Previous Jobcard Date'],
      next_service_due: ['Next Service', 'Next Service Date', 'Service Due', 'Service Due Date', 'NEXT SERVICE', 'DUE DATE'],
      vin_number: ['VIN', 'VIN Number', 'Chassis No', 'CHASSIS NO', 'VIN NO', 'Chassis Number', 'Frame #', 'VIN Number*'],
      alt_phone_number_2: ['Retail Mobile No', 'Alt Phone', 'Alternate Mobile', 'Alt Mobile', 'SECONDARY MOBILE', 'Alternate Mobile No'],
      odometer_reading: ['Odometer', 'KM Reading', 'Last Service KM', 'Previous Meter Reading', 'Meter Reading', 'ODOMETER READING'],
    },
    outputOrder: ['workshop_code', 'region_name', 'dealership_id', 'next_service_due', 'person_name', 'vehicle_model', 'reg_number', 'vin_number', 'phone_number', 'alt_phone_number_2', 'odometer_reading', 'last_service_date', 'customer_score', 'purpose_of_visit'],
    defaults: {
      region_name: '',
      dealership_id: '',
      customer_score: '',
      purpose_of_visit: 'yearly service',
    },
  },
  saisamarth_sales: {
    label: 'Saisamarth - Sales / Lead Campaign',
    sourceToTarget: {
      'Customer Name': 'person_name',
      'Contact Number': 'phone_number',
      'Model Variant': 'existing_vehicle_model',
      'Sale Date': 'existing_vehicle_ownership_remarks',
    },
    multiSource: {
      person_name: ['Customer Name', 'CUSTOMER NAME', 'Full Name', 'Name', 'CUSTOMERNAME'],
      phone_number: ['Contact Number', 'CONTACT NUMBER', 'Mobile', 'Phone', 'Mobile Number', 'PHONE NUMBER', 'CONTACT NO'],
      existing_vehicle_model: ['Model Variant', 'Model', 'Variant', 'MODEL VARIANT', 'VEHICLE MODEL'],
      existing_vehicle_ownership_remarks: ['Sale Date', 'SaleDate', 'SALE DATE', 'Purchase Date', 'Date of Sale'],
    },
    outputOrder: ['person_name', 'phone_number', 'existing_vehicle_model', 'existing_vehicle_brand', 'lead_source', 'existing_vehicle_ownership_remarks'],
    defaults: {
      existing_vehicle_brand: 'Honda',
      lead_source: 'UIO Data',
    },
  },
};

/** Fortune Toyota model normalization */
export function normalizeToyotaVehicleModel(raw: unknown): string {
  const orig = String(raw || '').trim();
  if (!orig) return '';
  const s = orig.toLowerCase().replace(/\s+/g, ' ');
  const rules: [string, string][] = [
    ['glanza', 'Glanza'],
    ['urban cruiser taisor', 'Urban Cruiser Taisor'],
    ['urban cruiser hyryder hybrid', 'Urban Cruiser Hyryder Hybrid'],
    ['urban cruiser hyryder', 'Urban Cruiser Hyryder'],
    ['innova hycross hybrid', 'Innova Hycross Hybrid'],
    ['innova hycross', 'Innova Hycross'],
    ['innova crysta', 'Innova Crysta'],
    ['fortuner legender', 'Fortuner Legender'],
    ['fortuner', 'Fortuner'],
    ['camry hybrid', 'Camry Hybrid'],
    ['camry', 'Camry'],
    ['hilux', 'Hilux'],
    ['vellfire', 'Vellfire'],
    ['etios liva', 'Etios Liva'],
    ['etios', 'Etios'],
    ['corolla altis', 'Corolla Altis'],
  ];
  for (const [needle, replacement] of rules) {
    if (s === needle || s.includes(needle)) return replacement;
  }
  return orig;
}

/** Anant Cars Mahindra model normalization */
export function normalizeMahindraVehicleName(raw: unknown): string {
  const orig = String(raw || '').trim();
  if (!orig) return '';
  const s = orig.toLowerCase().replace(/\s+/g, ' ');
  const rules: [string, string][] = [
    ['xuv 3xo ev', 'XUV 3XO EV'],
    ['xuv3xo ev', 'XUV 3XO EV'],
    ['xev 9s', 'XEV 9S'],
    ['xev9s', 'XEV 9S'],
    ['xev 9e', 'XEV 9e'],
    ['xev9e', 'XEV 9e'],
    ['be 6', 'BE 6'],
    ['be6', 'BE 6'],
    ['thar roxx', 'Thar ROXX'],
    ['bolero neo', 'Bolero Neo'],
    ['scorpio n', 'Scorpio-N'],
    ['scorpio-n', 'Scorpio-N'],
    ['scorpio classic', 'Scorpio Classic'],
    ['xuv400 ev', 'XUV400 EV'],
    ['xuv700', 'XUV700'],
    ['xuv 700', 'XUV700'],
    ['xuv 7xo', 'XUV 7XO'],
    ['xuv300', 'XUV300'],
    ['xuv 300', 'XUV300'],
    ['xuv 3xo', 'XUV 3XO'],
    ['xuv3xo', 'XUV 3XO'],
    ['marazzo', 'Marazzo'],
    ['bolero', 'Bolero'],
    ['thar', 'Thar'],
    ['udo', 'UDO'],
  ];
  for (const [needle, replacement] of rules) {
    if (s === needle || s.includes(needle)) return replacement;
  }
  return orig;
}

/** Build target source map from template */
export function buildTargetSources(template: FormatterTemplate): Record<string, string[]> {
  const m: Record<string, string[]> = {};
  function add(target: string, sourceLabel: string) {
    const ck = normalizeHeader(sourceLabel);
    if (!ck) return;
    if (!m[target]) m[target] = [];
    if (!m[target].includes(ck)) m[target].push(ck);
  }
  for (const [src, target] of Object.entries(template.sourceToTarget || {})) {
    add(target, src);
  }
  if (template.multiSource) {
    for (const [target, list] of Object.entries(template.multiSource)) {
      for (const item of list) add(target, item);
    }
  }
  return m;
}

export function normalizeHeader(text: string): string {
  if (!text) return '';
  return String(text).toLowerCase().replace(/[\s._-]+/g, '').replace(/[^a-z0-9]/g, '').trim();
}

export function canonicalHeader(h: unknown): string {
  return normalizeHeader(String(h ?? ''));
}
