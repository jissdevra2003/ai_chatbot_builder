import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  ArrowLeft,
  Settings,
  Bot,
  Save,
  Trash2,
  Sparkles,
  Copy,
  Check,
  FileText,
  Key,
  BookOpen,
  Code,
} from 'lucide-react';
import AppLayout from '../../components/Layout/AppLayout';
import DeleteChatbotDialog from './DeleteChatbotDialog';
import KnowledgeBaseTab from './KnowledgeBaseTab';
import EmbedWidgetTab from './EmbedWidgetTab';
import { chatbotsAPI } from '../../api/client';
import './Chatbots.css';

const MODEL_OPTIONS = [
  { value: 'gemini-3.6-flash', label: 'Gemini 3.6 Flash', desc: 'Fast & efficient' },
  { value: 'gemini-2.5-flash', label: 'Gemini 2.5 Flash', desc: 'Balanced performance' },
  { value: 'gemini-2.5-pro', label: 'Gemini 2.5 Pro', desc: 'Most capable' },
];

export default function ChatbotDetailPage() {
  const { chatbotId } = useParams();
  const navigate = useNavigate();

  const [chatbot, setChatbot] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  // Settings form
  const [formData, setFormData] = useState(null);
  const [isSaving, setIsSaving] = useState(false);
  const [saveError, setSaveError] = useState(null);
  const [showSaveToast, setShowSaveToast] = useState(false);
  const [hasChanges, setHasChanges] = useState(false);

  // Delete dialog
  const [showDelete, setShowDelete] = useState(false);

  // API key copy
  const [copied, setCopied] = useState(false);

  // Active tab
  const [activeTab, setActiveTab] = useState('settings');

  // Fetch chatbot
  useEffect(() => {
    const fetchChatbot = async () => {
      try {
        setError(null);
        const response = await chatbotsAPI.get(chatbotId);
        const data = response.data;
        setChatbot(data);
        setFormData({
          name: data.name,
          description: data.description || '',
          system_prompt: data.system_prompt,
          model_name: data.model_name,
          temperature: data.temperature,
          chunk_size: data.chunk_size,
          chunk_overlap: data.chunk_overlap,
        });
      } catch (err) {
        if (err.response?.status === 404) {
          setError('Chatbot not found.');
        } else {
          setError('Failed to load chatbot details.');
        }
        console.error('Failed to fetch chatbot:', err);
      } finally {
        setIsLoading(false);
      }
    };
    fetchChatbot();
  }, [chatbotId]);

  // Track changes
  useEffect(() => {
    if (!chatbot || !formData) return;
    const changed =
      formData.name !== chatbot.name ||
      formData.description !== (chatbot.description || '') ||
      formData.system_prompt !== chatbot.system_prompt ||
      formData.model_name !== chatbot.model_name ||
      formData.temperature !== chatbot.temperature ||
      formData.chunk_size !== chatbot.chunk_size ||
      formData.chunk_overlap !== chatbot.chunk_overlap;
    setHasChanges(changed);
  }, [formData, chatbot]);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
  };

  const handleNumberChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: parseFloat(value) }));
  };

  const handleIntChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: parseInt(value, 10) }));
  };

  const handleSave = async () => {
    setIsSaving(true);
    setSaveError(null);

    try {
      // Only send changed fields
      const updates = {};
      if (formData.name !== chatbot.name) updates.name = formData.name.trim();
      if (formData.description !== (chatbot.description || ''))
        updates.description = formData.description.trim() || null;
      if (formData.system_prompt !== chatbot.system_prompt)
        updates.system_prompt = formData.system_prompt.trim();
      if (formData.model_name !== chatbot.model_name)
        updates.model_name = formData.model_name;
      if (formData.temperature !== chatbot.temperature)
        updates.temperature = formData.temperature;
      if (formData.chunk_size !== chatbot.chunk_size)
        updates.chunk_size = formData.chunk_size;
      if (formData.chunk_overlap !== chatbot.chunk_overlap)
        updates.chunk_overlap = formData.chunk_overlap;

      if (Object.keys(updates).length === 0) return;

      const response = await chatbotsAPI.update(chatbotId, updates);
      setChatbot(response.data);
      setShowSaveToast(true);
      setTimeout(() => setShowSaveToast(false), 3000);
    } catch (err) {
      const message =
        err.response?.data?.detail || 'Failed to save changes.';
      setSaveError(typeof message === 'string' ? message : JSON.stringify(message));
    } finally {
      setIsSaving(false);
    }
  };

  const handleCopyApiKey = async () => {
    try {
      await navigator.clipboard.writeText(chatbot.api_key);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Fallback for non-HTTPS
      const textarea = document.createElement('textarea');
      textarea.value = chatbot.api_key;
      document.body.appendChild(textarea);
      textarea.select();
      document.execCommand('copy');
      document.body.removeChild(textarea);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const handleDeleteSuccess = () => {
    navigate('/chatbots', { replace: true });
  };

  // Loading state
  if (isLoading) {
    return (
      <AppLayout pageTitle="Chatbot Settings">
        <div className="chatbot-detail-header">
          <button className="chatbot-detail-back" onClick={() => navigate('/chatbots')}>
            <ArrowLeft size={20} />
          </button>
          <div className="chatbot-detail-info">
            <div className="skeleton" style={{ height: 28, width: 200, marginBottom: 8 }} />
            <div className="skeleton" style={{ height: 16, width: 140 }} />
          </div>
        </div>
        <div className="skeleton" style={{ height: 400, borderRadius: 'var(--radius-lg)' }} />
      </AppLayout>
    );
  }

  // Error state
  if (error) {
    return (
      <AppLayout pageTitle="Error">
        <div className="empty-state">
          <div className="empty-state-icon">
            <Bot size={28} />
          </div>
          <h3>{error}</h3>
          <p>The chatbot you're looking for might have been deleted or you don't have access.</p>
          <button className="btn btn-primary" onClick={() => navigate('/chatbots')}>
            Back to chatbots
          </button>
        </div>
      </AppLayout>
    );
  }

  return (
    <AppLayout pageTitle={chatbot.name}>
      {/* Header */}
      <div className="chatbot-detail-header">
        <button
          className="chatbot-detail-back"
          onClick={() => navigate('/chatbots')}
          aria-label="Back to chatbots"
        >
          <ArrowLeft size={20} />
        </button>
        <div className="chatbot-detail-info">
          <h1>{chatbot.name}</h1>
          <p>{chatbot.description || 'No description'}</p>
        </div>
      </div>

      {/* Tabs */}
      <div className="chatbot-tabs">
        <button
          className={`chatbot-tab ${activeTab === 'settings' ? 'active' : ''}`}
          onClick={() => setActiveTab('settings')}
        >
          <Settings size={16} />
          Settings
        </button>
        <button
          className={`chatbot-tab ${activeTab === 'knowledge' ? 'active' : ''}`}
          onClick={() => setActiveTab('knowledge')}
        >
          <BookOpen size={16} />
          Knowledge Base
        </button>
        <button
          className={`chatbot-tab ${activeTab === 'embed' ? 'active' : ''}`}
          onClick={() => setActiveTab('embed')}
        >
          <Code size={16} />
          Embed Widget
        </button>
        <button
          className={`chatbot-tab ${activeTab === 'api' ? 'active' : ''}`}
          onClick={() => setActiveTab('api')}
        >
          <Key size={16} />
          API Key
        </button>
      </div>

      {/* Settings Tab */}
      {activeTab === 'settings' && formData && (
        <>
          <div className="settings-panel">
            <div className="settings-panel-header">
              <h3>General Settings</h3>
              <p>Configure your chatbot's identity and behavior.</p>
            </div>

            {saveError && (
              <div className="toast toast-error" style={{ marginBottom: 'var(--space-4)' }}>
                {saveError}
              </div>
            )}

            <div className="settings-form">
              {/* Name & Description row */}
              <div className="settings-form-row">
                <div className="form-group">
                  <label className="form-label" htmlFor="settings-name">
                    Chatbot name
                  </label>
                  <input
                    id="settings-name"
                    className="form-input"
                    type="text"
                    name="name"
                    value={formData.name}
                    onChange={handleChange}
                  />
                </div>
                <div className="form-group">
                  <label className="form-label" htmlFor="settings-description">
                    Description
                  </label>
                  <input
                    id="settings-description"
                    className="form-input"
                    type="text"
                    name="description"
                    value={formData.description}
                    onChange={handleChange}
                    placeholder="Optional description"
                  />
                </div>
              </div>

              {/* System Prompt */}
              <div className="form-group">
                <label className="form-label" htmlFor="settings-prompt">
                  System prompt
                </label>
                <textarea
                  id="settings-prompt"
                  className="form-textarea"
                  name="system_prompt"
                  value={formData.system_prompt}
                  onChange={handleChange}
                  rows={5}
                />
                <div className="form-hint">
                  Instructions that define the chatbot's personality and behavior.
                </div>
              </div>

              {/* Model & Temperature row */}
              <div className="settings-form-row">
                <div className="form-group">
                  <label className="form-label" htmlFor="settings-model">
                    <Sparkles size={14} style={{ verticalAlign: 'middle', marginRight: '4px' }} />
                    AI Model
                  </label>
                  <select
                    id="settings-model"
                    className="form-select"
                    name="model_name"
                    value={formData.model_name}
                    onChange={handleChange}
                  >
                    {MODEL_OPTIONS.map((opt) => (
                      <option key={opt.value} value={opt.value}>
                        {opt.label} — {opt.desc}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="form-group">
                  <label className="form-label" htmlFor="settings-temperature">
                    Temperature: {formData.temperature.toFixed(1)}
                  </label>
                  <input
                    id="settings-temperature"
                    type="range"
                    name="temperature"
                    min="0"
                    max="2"
                    step="0.1"
                    value={formData.temperature}
                    onChange={handleNumberChange}
                    className="form-range"
                  />
                  <div className="form-hint" style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span>Precise (0.0)</span>
                    <span>Creative (2.0)</span>
                  </div>
                </div>
              </div>

              {/* Chunk Settings row */}
              <div className="settings-form-row">
                <div className="form-group">
                  <label className="form-label" htmlFor="settings-chunk-size">
                    <FileText size={14} style={{ verticalAlign: 'middle', marginRight: '4px' }} />
                    Chunk size
                  </label>
                  <input
                    id="settings-chunk-size"
                    className="form-input"
                    type="number"
                    name="chunk_size"
                    value={formData.chunk_size}
                    onChange={handleIntChange}
                    min={100}
                    max={5000}
                  />
                  <div className="form-hint">Characters per chunk (100–5000)</div>
                </div>
                <div className="form-group">
                  <label className="form-label" htmlFor="settings-chunk-overlap">
                    Chunk overlap
                  </label>
                  <input
                    id="settings-chunk-overlap"
                    className="form-input"
                    type="number"
                    name="chunk_overlap"
                    value={formData.chunk_overlap}
                    onChange={handleIntChange}
                    min={0}
                    max={1000}
                  />
                  <div className="form-hint">Overlapping characters between chunks (0–1000)</div>
                </div>
              </div>

              {/* Save Actions */}
              <div className="settings-form-actions">
                <button
                  className="btn btn-secondary"
                  onClick={() => {
                    setFormData({
                      name: chatbot.name,
                      description: chatbot.description || '',
                      system_prompt: chatbot.system_prompt,
                      model_name: chatbot.model_name,
                      temperature: chatbot.temperature,
                      chunk_size: chatbot.chunk_size,
                      chunk_overlap: chatbot.chunk_overlap,
                    });
                  }}
                  disabled={!hasChanges || isSaving}
                >
                  Discard changes
                </button>
                <button
                  className="btn btn-primary"
                  onClick={handleSave}
                  disabled={!hasChanges || isSaving}
                  id="save-chatbot-settings"
                >
                  {isSaving ? (
                    <>
                      <span className="spinner spinner-sm" />
                      Saving…
                    </>
                  ) : (
                    <>
                      <Save size={16} />
                      Save changes
                    </>
                  )}
                </button>
              </div>
            </div>
          </div>

          {/* Danger Zone */}
          <div className="danger-zone">
            <h3>
              <Trash2 size={16} style={{ verticalAlign: 'middle', marginRight: '6px' }} />
              Danger Zone
            </h3>
            <p>
              Permanently delete this chatbot and all its associated data including documents,
              embeddings, and conversations. This action cannot be undone.
            </p>
            <button
              className="btn btn-danger btn-sm"
              onClick={() => setShowDelete(true)}
              id="delete-chatbot-btn"
            >
              <Trash2 size={15} />
              Delete chatbot
            </button>
          </div>
        </>
      )}

      {/* Knowledge Base Tab */}
      {activeTab === 'knowledge' && chatbot && (
        <KnowledgeBaseTab chatbotId={chatbotId} />
      )}

      {/* Embed Widget Tab */}
      {activeTab === 'embed' && chatbot && (
        <EmbedWidgetTab chatbot={chatbot} />
      )}

      {/* API Key Tab */}
      {activeTab === 'api' && chatbot && (
        <div className="settings-panel">
          <div className="settings-panel-header">
            <h3>API Key</h3>
            <p>Use this key to integrate your chatbot with external applications.</p>
          </div>

          <div className="api-key-display">
            <code className="api-key-text">{chatbot.api_key}</code>
            <button
              className="api-key-copy"
              onClick={handleCopyApiKey}
              aria-label="Copy API key"
              title="Copy to clipboard"
            >
              {copied ? <Check size={16} style={{ color: 'var(--color-success)' }} /> : <Copy size={16} />}
            </button>
          </div>

          <div className="form-hint" style={{ marginTop: 'var(--space-3)' }}>
            Keep this key secret. Anyone with this key can send messages to your chatbot.
          </div>
        </div>
      )}

      {/* Save Success Toast */}
      {showSaveToast && (
        <div className="save-toast">
          <div className="toast toast-success">
            <Check size={16} />
            Settings saved successfully
          </div>
        </div>
      )}

      {/* Delete Dialog */}
      {showDelete && (
        <DeleteChatbotDialog
          chatbot={chatbot}
          onClose={() => setShowDelete(false)}
          onSuccess={handleDeleteSuccess}
        />
      )}
    </AppLayout>
  );
}
