"use client";
import React, { useState, useEffect } from 'react';
import { 
  Lock, User, LogOut, Plus, Search, Edit2, Trash2, 
  X, Save, ChevronLeft, AlertCircle, CheckCircle2,
  Tag, PlusCircle, MinusCircle
} from 'lucide-react';

const API_BASE_URL = 'https://autobot-webapp-dev-unstable.gryd.in:60133/gryd';

// --- Types & Interfaces ---

export interface Auth {
  token: string;
  session_id: string;
  role?: string;
  user_id?: string;
  [key: string]: any;
}

export interface ToastState {
  message: string;
  type: 'success' | 'error';
}

export interface CampaignObjective {
  campaign_objective_id?: string;
  campaign_objective_name: string;
  campaign_objective_description: string;
  campaign_type: string;
  campaign_sub_type: string;
  dealership_id: string;
  dealer_name: string;
  brand_id: string;
  conversation_tone: string;
  purpose: string;
  purpose_steps: string[];
  custom_conversation_start_pattern: string[];
  target_audience_tags: string[];
  ctas: string[];
  required_attributes: string[];
  custom_campaign_attributes: Record<string, string>[];
  audience_attributes: Record<string, string>[];
  guardrails_guidelines: string;
  why_user_should_avail_this: string;
  reasons_users_may_not_be_interested: string;
  reasons_for_non_applicability: string;
  other_important_information: string;
  icon?: string;
  is_custom: boolean;
}

// --- Reusable Components ---

interface ToastProps {
  message: string;
  type: 'success' | 'error';
  onClose: () => void;
}

const Toast: React.FC<ToastProps> = ({ message, type, onClose }) => {
  useEffect(() => {
    const timer = setTimeout(onClose, 3000);
    return () => clearTimeout(timer);
  }, [onClose]);

  const bgColor = type === 'error' ? 'bg-red-100 text-red-800 border-red-200' : 'bg-green-100 text-green-800 border-green-200';
  const Icon = type === 'error' ? AlertCircle : CheckCircle2;

  return (
    <div className={`fixed bottom-4 right-4 flex items-center p-4 rounded-lg border ${bgColor} shadow-lg transition-all z-50`}>
      <Icon className="w-5 h-5 mr-2" />
      <span className="font-medium">{message}</span>
      <button onClick={onClose} className="ml-4 hover:opacity-75"><X className="w-4 h-4" /></button>
    </div>
  );
};

interface TagInputProps {
  tags?: string[];
  onChange: (tags: string[]) => void;
  placeholder?: string;
}

const TagInput: React.FC<TagInputProps> = ({ tags = [], onChange, placeholder }) => {
  const [input, setInput] = useState<string>('');

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && input.trim()) {
      e.preventDefault();
      if (!tags.includes(input.trim())) {
        onChange([...tags, input.trim()]);
      }
      setInput('');
    }
  };

  const removeTag = (tagToRemove: string) => {
    onChange(tags.filter(tag => tag !== tagToRemove));
  };

  return (
    <div className="w-full">
      <div className="flex flex-wrap gap-2 mb-2">
        {tags.map((tag, idx) => (
          <span key={idx} className="bg-blue-100 text-blue-800 px-2 py-1 rounded-md flex items-center text-sm font-medium">
            <Tag className="w-3 h-3 mr-1" />
            {tag}
            <button type="button" onClick={() => removeTag(tag)} className="ml-1 text-blue-600 hover:text-blue-900">
              <X className="w-3 h-3" />
            </button>
          </span>
        ))}
      </div>
      <input
        type="text"
        value={input}
        onChange={(e) => setInput(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder={placeholder || "Type and press Enter to add..."}
        className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none text-sm"
      />
    </div>
  );
};

interface ObjectListInputProps {
  items?: Record<string, string>[];
  onChange: (items: Record<string, string>[]) => void;
  columns: string[];
}

const ObjectListInput: React.FC<ObjectListInputProps> = ({ items = [], onChange, columns }) => {
  const addRow = () => {
    const newRow = columns.reduce((acc, col) => ({ ...acc, [col]: '' }), {} as Record<string, string>);
    onChange([...items, newRow]);
  };

  const updateRow = (index: number, col: string, value: string) => {
    const newItems = [...items];
    newItems[index][col] = value;
    onChange(newItems);
  };

  const removeRow = (index: number) => {
    onChange(items.filter((_, i) => i !== index));
  };

  return (
    <div className="w-full overflow-x-auto border border-slate-200 rounded-lg">
      <table className="w-full text-sm text-left">
        <thead className="text-xs text-slate-700 bg-slate-50 uppercase border-b">
          <tr>
            {columns.map(col => <th key={col} className="px-3 py-2">{col.replace('_', ' ')}</th>)}
            <th className="px-3 py-2 text-right">Actions</th>
          </tr>
        </thead>
        <tbody>
          {items.map((row, idx) => (
            <tr key={idx} className="border-b last:border-b-0">
              {columns.map(col => (
                <td key={col} className="p-2">
                  <input
                    type="text"
                    value={row[col] || ''}
                    onChange={(e) => updateRow(idx, col, e.target.value)}
                    className="w-full px-2 py-1 border border-slate-300 rounded text-sm focus:ring-1 focus:ring-blue-500 outline-none"
                    placeholder={col}
                  />
                </td>
              ))}
              <td className="p-2 text-right">
                <button type="button" onClick={() => removeRow(idx)} className="text-red-500 hover:text-red-700">
                  <MinusCircle className="w-5 h-5" />
                </button>
              </td>
            </tr>
          ))}
          {items.length === 0 && (
            <tr><td colSpan={columns.length + 1} className="p-4 text-center text-slate-500 italic">No attributes added yet.</td></tr>
          )}
        </tbody>
      </table>
      <div className="p-2 bg-slate-50 border-t">
        <button type="button" onClick={addRow} className="text-blue-600 hover:text-blue-800 flex items-center text-sm font-medium">
          <PlusCircle className="w-4 h-4 mr-1" /> Add Attribute
        </button>
      </div>
    </div>
  );
};

// --- Main Application ---

export default function App() {
  const [auth, setAuth] = useState<Auth | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [toast, setToast] = useState<ToastState | null>(null);

  // Data State
  const [objectives, setObjectives] = useState<CampaignObjective[]>([]);
  const [view, setView] = useState<'list' | 'form'>('list');
  const [editingItem, setEditingItem] = useState<CampaignObjective | null>(null);

  const showToast = (message: string, type: 'success' | 'error' = 'success') => setToast({ message, type });

  const getHeaders = (): HeadersInit => {
    if (!auth) return {};
    return {
      'Accept': 'application/json',
      'Content-Type': 'application/json',
      'X-GRYD-APPLICATION-ID': 'gryd',
      'X-GRYD-ENTERPRISE-ID': 'autocrm',
      'X-GRYD-ROLE': auth.role || 'agent',
      'X-GRYD-SESSION-ID': auth.session_id,
      'X-GRYD-TOKEN': auth.token
    };
  };

  const handleLogin = async (e: React.FormEvent, credentials: Record<string, string>) => {
    e.preventDefault();
    setLoading(true);
    try {
      const response = await fetch(`${API_BASE_URL}/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-GRYD-ENTERPRISE-ID': 'autocrm',
          'X-GRYD-SIGNUP-TOKEN': process.env.NEXT_PUBLIC_SIGNUP_API_KEY || 'tokengoeshere' // Replace with actual token or use env variable
        },
        body: JSON.stringify(credentials)
      });
      
      const data = await response.json();
      if (!response.ok) throw new Error(data.message || 'Login failed');
      
      setAuth(data);
      showToast('Login successful!');
    } catch (err: any) {
      showToast(err.message || 'An error occurred', 'error');
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = () => {
    setAuth(null);
    setObjectives([]);
    setView('list');
  };

  const fetchObjectives = async () => {
    setLoading(true);
    try {
      const response = await fetch(`${API_BASE_URL}/db/objects/campaign_objective`, {
        method: 'GET',
        headers: getHeaders()
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.message || 'Failed to fetch data');
      
      setObjectives(Array.isArray(data) ? data : (data.data || data.results || []));
    } catch (err: any) {
      showToast(err.message || 'An error occurred', 'error');
    } finally {
      setLoading(false);
    }
  };

  const saveObjective = async (formData: Partial<CampaignObjective>, id: string | null = null) => {
    setLoading(true);
    try {
      const endpoint = id 
        ? `${API_BASE_URL}/db/object/campaign_objective/${id}` 
        : `${API_BASE_URL}/db/object/campaign_objective`;
      
      const response = await fetch(endpoint, {
        method: id ? 'PATCH' : 'POST',
        headers: getHeaders(),
        body: JSON.stringify(formData)
      });
      
      if (!response.ok) {
        const errData = await response.json();
        throw new Error(errData.message || 'Failed to save');
      }
      
      showToast(`Campaign objective successfully ${id ? 'updated' : 'created'}`);
      setView('list');
      fetchObjectives();
    } catch (err: any) {
      showToast(err.message || 'An error occurred', 'error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (auth) {
      fetchObjectives();
    }
  }, [auth]);


  if (!auth) {
    return <LoginForm onLogin={handleLogin} loading={loading} toast={toast} onCloseToast={() => setToast(null)} />;
  }

  return (
    <div className="min-h-screen bg-slate-100 flex flex-col font-sans">
      {/* Top Navbar */}
      <nav className="bg-white shadow-sm border-b border-slate-200 px-6 py-3 flex justify-between items-center z-10 sticky top-0">
        <div className="flex items-center space-x-2">
          <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center">
            <Tag className="w-5 h-5 text-white" />
          </div>
          <h1 className="text-xl font-bold text-slate-800 tracking-tight">Campaign Objectives DB</h1>
        </div>
        <div className="flex items-center space-x-4">
          <span className="text-sm text-slate-500 flex items-center">
            <User className="w-4 h-4 mr-1" />
            {auth.user_id || 'Autocrm User'}
          </span>
          <button 
            onClick={handleLogout}
            className="flex items-center text-sm font-medium text-red-600 hover:text-red-800 transition-colors bg-red-50 px-3 py-1.5 rounded-md"
          >
            <LogOut className="w-4 h-4 mr-1" />
            Logout
          </button>
        </div>
      </nav>

      {/* Main Content Area */}
      <main className="flex-grow p-6 max-w-7xl mx-auto w-full">
        {view === 'list' ? (
          <ListView 
            objectives={objectives} 
            loading={loading} 
            onAdd={() => { setEditingItem(null); setView('form'); }}
            onEdit={(item) => { setEditingItem(item); setView('form'); }}
            onRefresh={fetchObjectives}
          />
        ) : (
          <FormView 
            item={editingItem} 
            loading={loading}
            onSave={(data) => saveObjective(data, editingItem?.campaign_objective_id || null)}
            onCancel={() => setView('list')}
          />
        )}
      </main>

      {toast && <Toast message={toast.message} type={toast.type} onClose={() => setToast(null)} />}
    </div>
  );
}

// --- Views ---

interface LoginFormProps {
  onLogin: (e: React.FormEvent, credentials: Record<string, string>) => void;
  loading: boolean;
  toast: ToastState | null;
  onCloseToast: () => void;
}

const LoginForm: React.FC<LoginFormProps> = ({ onLogin, loading, toast, onCloseToast }) => {
  const [creds, setCreds] = useState({ user_id: '', password: '' });

  return (
    <div className="min-h-screen bg-slate-100 flex items-center justify-center p-4">
      <div className="max-w-md w-full bg-white rounded-xl shadow-xl overflow-hidden">
        <div className="p-8">
          <div className="flex justify-center mb-6">
            <div className="bg-blue-600 p-3 rounded-full">
              <Lock className="w-8 h-8 text-white" />
            </div>
          </div>
          <h2 className="text-2xl font-bold text-center text-slate-800 mb-2">Sign In to Dashboard</h2>
          <p className="text-center text-slate-500 mb-8 text-sm">Use your Gryd Autobot credentials to access campaign objectives.</p>
          
          <form onSubmit={(e) => onLogin(e, creds)}>
            <div className="space-y-5">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">User ID</label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                    <User className="h-5 w-5 text-slate-400" />
                  </div>
                  <input
                    type="text"
                    required
                    value={creds.user_id}
                    onChange={e => setCreds({...creds, user_id: e.target.value})}
                    className="block w-full pl-10 pr-3 py-2 border border-slate-300 rounded-lg focus:ring-blue-500 focus:border-blue-500 text-sm"
                    placeholder="Enter User ID"
                  />
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Password</label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                    <Lock className="h-5 w-5 text-slate-400" />
                  </div>
                  <input
                    type="password"
                    required
                    value={creds.password}
                    onChange={e => setCreds({...creds, password: e.target.value})}
                    className="block w-full pl-10 pr-3 py-2 border border-slate-300 rounded-lg focus:ring-blue-500 focus:border-blue-500 text-sm"
                    placeholder="••••••••"
                  />
                </div>
              </div>
              <button
                type="submit"
                disabled={loading}
                className="w-full flex justify-center py-2.5 px-4 border border-transparent rounded-lg shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50"
              >
                {loading ? 'Authenticating...' : 'Sign In'}
              </button>
            </div>
          </form>
        </div>
      </div>
      {toast && <Toast message={toast.message} type={toast.type} onClose={onCloseToast} />}
    </div>
  );
};

interface ListViewProps {
  objectives: CampaignObjective[];
  loading: boolean;
  onAdd: () => void;
  onEdit: (item: CampaignObjective) => void;
  onRefresh: () => void;
}

const ListView: React.FC<ListViewProps> = ({ objectives, loading, onAdd, onEdit, onRefresh }) => {
  const [searchTerm, setSearchTerm] = useState<string>('');

  const filtered = objectives.filter(obj => 
    (obj.campaign_objective_name || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
    (obj.campaign_type || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
    (obj.dealer_name || '').toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden flex flex-col h-[calc(100vh-100px)]">
      {/* Header Actions */}
      <div className="p-4 border-b border-slate-200 flex justify-between items-center bg-slate-50">
        <div className="relative w-72">
          <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
            <Search className="h-4 w-4 text-slate-400" />
          </div>
          <input
            type="text"
            placeholder="Search objectives..."
            value={searchTerm}
            onChange={e => setSearchTerm(e.target.value)}
            className="block w-full pl-9 pr-3 py-2 border border-slate-300 rounded-lg focus:ring-blue-500 focus:border-blue-500 text-sm"
          />
        </div>
        <div className="flex space-x-3">
          <button 
            onClick={onRefresh} 
            disabled={loading}
            className="px-4 py-2 text-sm font-medium text-slate-700 bg-white border border-slate-300 rounded-lg hover:bg-slate-50 disabled:opacity-50"
          >
            Refresh
          </button>
          <button 
            onClick={onAdd}
            className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 flex items-center shadow-sm"
          >
            <Plus className="w-4 h-4 mr-1" /> Add Objective
          </button>
        </div>
      </div>

      {/* Table */}
      <div className="flex-grow overflow-auto">
        {loading && objectives.length === 0 ? (
          <div className="flex justify-center items-center h-full text-slate-500">Loading data...</div>
        ) : (
          <table className="min-w-full divide-y divide-slate-200">
            <thead className="bg-slate-50 sticky top-0 z-10">
              <tr>
                <th scope="col" className="px-6 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">ID / Name</th>
                <th scope="col" className="px-6 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Type / Sub-Type</th>
                <th scope="col" className="px-6 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Dealership</th>
                <th scope="col" className="px-6 py-3 text-center text-xs font-semibold text-slate-500 uppercase tracking-wider">Custom?</th>
                <th scope="col" className="px-6 py-3 text-right text-xs font-semibold text-slate-500 uppercase tracking-wider">Actions</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-slate-200">
              {filtered.length > 0 ? (
                filtered.map((obj) => (
                  <tr key={obj.campaign_objective_id} className="hover:bg-slate-50 transition-colors">
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="text-sm font-medium text-slate-900">{obj.campaign_objective_name}</div>
                      <div className="text-xs text-slate-500 max-w-[200px] truncate" title={obj.campaign_objective_id}>
                        {obj.campaign_objective_id}
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-blue-100 text-blue-800 mb-1 block w-max">
                        {obj.campaign_type || 'N/A'}
                      </span>
                      <div className="text-xs text-slate-500">{obj.campaign_sub_type || '-'}</div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="text-sm text-slate-900">{obj.dealer_name || 'All'}</div>
                      <div className="text-xs text-slate-500">{obj.dealership_id || '-'}</div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-center">
                      {obj.is_custom ? (
                        <span className="px-2 py-1 text-xs rounded-md bg-green-100 text-green-800 font-medium">Yes</span>
                      ) : (
                        <span className="px-2 py-1 text-xs rounded-md bg-slate-100 text-slate-600 font-medium">No</span>
                      )}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                      <button 
                        onClick={() => onEdit(obj)}
                        className="text-indigo-600 hover:text-indigo-900 bg-indigo-50 p-2 rounded-lg"
                        title="Edit Object"
                      >
                        <Edit2 className="w-4 h-4" />
                      </button>
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={5} className="px-6 py-10 text-center text-slate-500">
                    No campaign objectives found matching your criteria.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        )}
      </div>
      <div className="p-3 border-t border-slate-200 bg-slate-50 text-xs text-slate-500 text-right">
        Total Items: {filtered.length}
      </div>
    </div>
  );
};

interface FormViewProps {
  item: CampaignObjective | null;
  onSave: (data: CampaignObjective) => void;
  onCancel: () => void;
  loading: boolean;
}

const FormView: React.FC<FormViewProps> = ({ item, onSave, onCancel, loading }) => {
  const [formData, setFormData] = useState<CampaignObjective>({
    campaign_objective_name: '',
    campaign_objective_description: '',
    campaign_type: '',
    campaign_sub_type: '',
    dealership_id: '',
    dealer_name: '',
    brand_id: '',
    conversation_tone: '',
    purpose: '',
    purpose_steps: [],
    custom_conversation_start_pattern: [],
    target_audience_tags: [],
    ctas: [],
    required_attributes: [],
    custom_campaign_attributes: [],
    audience_attributes: [],
    guardrails_guidelines: '',
    why_user_should_avail_this: '',
    reasons_users_may_not_be_interested: '',
    reasons_for_non_applicability: '',
    other_important_information: '',
    icon: '',
    is_custom: false,
    ...(item || {}) // overwrite with existing if editing
  });

  const handleChange = <K extends keyof CampaignObjective>(field: K, value: CampaignObjective[K]) => {
    setFormData(prev => ({ ...prev, [field]: value }));
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    
    // Clean up the payload before saving to ensure the POST body only contains populated fields 
    // (matching the clean JSON reference structure you provided).
    const cleanPayload: Partial<CampaignObjective> = {};
    (Object.keys(formData) as Array<keyof CampaignObjective>).forEach(key => {
      const val = formData[key];
      if (typeof val === 'string') {
        if (val.trim() !== '') (cleanPayload as any)[key] = val;
      } else if (Array.isArray(val)) {
        if (val.length > 0) (cleanPayload as any)[key] = val;
      } else if (val !== null && val !== undefined) {
        (cleanPayload as any)[key] = val; 
      }
    });

    onSave(cleanPayload as CampaignObjective);
  };

  const ctaOptions = ["know-more", "register-to-event", "book-test-drive", "book-showroom-visit", "download-brochure", "book-home-test-drive", "get-onroad-price", "request-callback", "confirm-booking", "book-service", "order-accessory", "renew-insurance", "order-spare-part", "order-extended-warranty", "order-care-package"];
  const typeOptions = ["pre-sales", "post-sales", "dealership"];
  const subTypeOptions = ["brand awareness", "service overdue", "product awareness", "event", "lead generation", "lead qualification", "lead nurturing", "lead conversion", "workshop awareness", "offers", "new accessories", "new procedures", "customer retention", "service reminder", "upsell/cross-sell", "review", "feedback", "reminder", "product recall", "software update", "other"];
  const attrColumns = ["attribute_name", "attribute_value", "attribute_type", "attribute_description"];

  return (
    <div className="bg-white rounded-xl shadow-sm border border-slate-200 flex flex-col h-[calc(100vh-100px)]">
      {/* Form Header */}
      <div className="px-6 py-4 border-b border-slate-200 flex items-center justify-between bg-slate-50">
        <div className="flex items-center">
          <button onClick={onCancel} className="mr-4 text-slate-500 hover:text-slate-800">
            <ChevronLeft className="w-5 h-5" />
          </button>
          <h2 className="text-lg font-semibold text-slate-800">
            {item ? `Edit Objective: ${item.campaign_objective_id || item.campaign_objective_name}` : 'Create New Campaign Objective'}
          </h2>
        </div>
        <div className="flex space-x-3">
          <button type="button" onClick={onCancel} className="px-4 py-2 text-sm font-medium text-slate-700 bg-white border border-slate-300 rounded-lg hover:bg-slate-50">
            Cancel
          </button>
          <button 
            type="button" 
            onClick={handleSubmit} 
            disabled={loading}
            className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 flex items-center shadow-sm disabled:opacity-50"
          >
            <Save className="w-4 h-4 mr-2" /> {loading ? 'Saving...' : 'Save Objective'}
          </button>
        </div>
      </div>

      {/* Form Body - Scrollable */}
      <div className="flex-grow overflow-auto p-6 bg-slate-50/50">
        <form id="objective-form" className="max-w-5xl mx-auto space-y-8" onSubmit={handleSubmit}>
          
          {/* Section: Basic Info */}
          <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
            <h3 className="text-md font-semibold text-slate-800 mb-4 border-b pb-2">Basic Information</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="md:col-span-2">
                <label className="block text-sm font-medium text-slate-700 mb-1">Campaign Objective Name <span className="text-red-500">*</span></label>
                <input required type="text" value={formData.campaign_objective_name} onChange={e => handleChange('campaign_objective_name', e.target.value)} className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 text-sm outline-none" placeholder="e.g. Test Drive Push Q3" />
              </div>
              <div className="md:col-span-2">
                <label className="block text-sm font-medium text-slate-700 mb-1">Objective Description <span className="text-red-500">*</span></label>
                <textarea required rows={6} value={formData.campaign_objective_description} onChange={e => handleChange('campaign_objective_description', e.target.value)} className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 text-sm outline-none" placeholder="Describe the goal..."></textarea>
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Campaign Type</label>
                <select value={formData.campaign_type} onChange={e => handleChange('campaign_type', e.target.value)} className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 text-sm outline-none bg-white">
                  <option value="">Select Type</option>
                  {typeOptions.map(opt => <option key={opt} value={opt}>{opt}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Campaign Sub Type</label>
                <select value={formData.campaign_sub_type} onChange={e => handleChange('campaign_sub_type', e.target.value)} className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 text-sm outline-none bg-white">
                  <option value="">Select Sub Type</option>
                  {subTypeOptions.map(opt => <option key={opt} value={opt}>{opt}</option>)}
                </select>
              </div>
              <div className="md:col-span-2">
                <label className="block text-sm font-medium text-slate-700 mb-1">Purpose</label>
                <input type="text" value={formData.purpose} onChange={e => handleChange('purpose', e.target.value)} className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 text-sm outline-none" placeholder="Short purpose..." />
              </div>
              <div className="flex items-center mt-2">
                <input type="checkbox" id="is_custom" checked={formData.is_custom} onChange={e => handleChange('is_custom', e.target.checked)} className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500" />
                <label htmlFor="is_custom" className="ml-2 block text-sm font-medium text-slate-700">Is Custom Campaign?</label>
              </div>
            </div>
          </div>

          {/* Section: Dealership Assignment */}
          <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
            <h3 className="text-md font-semibold text-slate-800 mb-4 border-b pb-2">Dealership Mapping</h3>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Dealership ID</label>
                <input type="text" value={formData.dealership_id} onChange={e => handleChange('dealership_id', e.target.value)} className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 text-sm outline-none" placeholder="UID" />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Dealer Name</label>
                <input type="text" value={formData.dealer_name} onChange={e => handleChange('dealer_name', e.target.value)} className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 text-sm outline-none" placeholder="Name" />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Brand ID</label>
                <input type="text" value={formData.brand_id} onChange={e => handleChange('brand_id', e.target.value)} className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 text-sm outline-none" placeholder="Brand UID" />
              </div>
            </div>
          </div>

          {/* Section: Bot Behavior & Tone */}
          <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
            <h3 className="text-md font-semibold text-slate-800 mb-4 border-b pb-2">Bot Conversation & Strategy</h3>
            <div className="space-y-6">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Conversation Tone</label>
                <textarea rows={8} value={formData.conversation_tone} onChange={e => handleChange('conversation_tone', e.target.value)} className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 text-sm outline-none"></textarea>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">Custom Conversation Start Pattern (Tags)</label>
                  <TagInput tags={formData.custom_conversation_start_pattern} onChange={v => handleChange('custom_conversation_start_pattern', v)} />
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">Purpose Steps (Tags)</label>
                  <TagInput tags={formData.purpose_steps} onChange={v => handleChange('purpose_steps', v)} />
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Campaign Guardrails and Guidelines</label>
                <textarea rows={8} value={formData.guardrails_guidelines} onChange={e => handleChange('guardrails_guidelines', e.target.value)} className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 text-sm outline-none" placeholder="Strict rules for bot to follow..."></textarea>
              </div>
            </div>
          </div>

          {/* Section: Persuasion Logic */}
          <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
            <h3 className="text-md font-semibold text-slate-800 mb-4 border-b pb-2">Persuasion & Fallback Logic</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Why User Should Avail This</label>
                <textarea rows={8} value={formData.why_user_should_avail_this} onChange={e => handleChange('why_user_should_avail_this', e.target.value)} className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 text-sm outline-none"></textarea>
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Reasons Users May Not Be Interested</label>
                <textarea rows={8} value={formData.reasons_users_may_not_be_interested} onChange={e => handleChange('reasons_users_may_not_be_interested', e.target.value)} className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 text-sm outline-none"></textarea>
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Reasons for Non-Applicability</label>
                <textarea rows={6} value={formData.reasons_for_non_applicability} onChange={e => handleChange('reasons_for_non_applicability', e.target.value)} className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 text-sm outline-none"></textarea>
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Other Important Information</label>
                <textarea rows={4} value={formData.other_important_information} onChange={e => handleChange('other_important_information', e.target.value)} className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 text-sm outline-none"></textarea>
              </div>
            </div>
          </div>

          {/* Section: Targets & Requirements (Lists) */}
          <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
            <h3 className="text-md font-semibold text-slate-800 mb-4 border-b pb-2">Targets, CTAs & Required Configs</h3>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Call to Actions</label>
                <div className="h-40 overflow-y-auto border border-slate-200 rounded-lg p-2 bg-slate-50 space-y-1">
                  {ctaOptions.map(cta => (
                    <label key={cta} className="flex items-center text-sm cursor-pointer hover:bg-slate-100 p-1 rounded">
                      <input 
                        type="checkbox" 
                        className="mr-2 rounded text-blue-600 focus:ring-blue-500"
                        checked={formData.ctas.includes(cta)}
                        onChange={(e) => {
                          const newCtas = e.target.checked 
                            ? [...formData.ctas, cta] 
                            : formData.ctas.filter(c => c !== cta);
                          handleChange('ctas', newCtas);
                        }}
                      />
                      {cta}
                    </label>
                  ))}
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Target Audience Tags</label>
                <TagInput tags={formData.target_audience_tags} onChange={v => handleChange('target_audience_tags', v)} placeholder="Type tag & Enter" />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Required Attributes</label>
                <TagInput tags={formData.required_attributes} onChange={v => handleChange('required_attributes', v)} placeholder="Type required attr & Enter" />
              </div>
            </div>
          </div>

          {/* Section: Custom Attributes Tables */}
          <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
            <h3 className="text-md font-semibold text-slate-800 mb-4 border-b pb-2">Advanced Object Attributes</h3>
            <div className="space-y-6">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-2">Custom Campaign Attributes</label>
                <ObjectListInput 
                  items={formData.custom_campaign_attributes || []} 
                  onChange={v => handleChange('custom_campaign_attributes', v)} 
                  columns={attrColumns} 
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-2">Audience Attributes</label>
                <ObjectListInput 
                  items={formData.audience_attributes || []} 
                  onChange={v => handleChange('audience_attributes', v)} 
                  columns={attrColumns} 
                />
              </div>
            </div>
          </div>

        </form>
      </div>
    </div>
  );
};