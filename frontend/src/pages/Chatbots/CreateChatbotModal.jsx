import { useState } from 'react';
import { X, Bot, Sparkles, Plus } from 'lucide-react';
import { chatbotsAPI } from '../../api/client';

const MODEL_OPTIONS = [
  { value: 'gemini-3.6-flash', label: 'Gemini 3.6 Flash', desc: 'Fast & efficient' },
  { value: 'gemini-2.5-flash', label: 'Gemini 2.5 Flash', desc: 'Balanced performance' },
  { value: 'gemini-2.5-pro', label: 'Gemini 2.5 Pro', desc: 'Most capable' },
];

export default function CreateChatbotModal({ onClose, onSuccess }) {
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    system_prompt: 'You are a helpful AI assistant.',
    model_name: 'gemini-3.6-flash',
    temperature: 0.7,
  });
  const [errors, setErrors] = useState({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [apiError, setApiError] = useState(null);

  const validate = () => {
    const newErrors = {};
    if (!formData.name.trim()) {
      newErrors.name = 'Chatbot name is required';
    } else if (formData.name.length > 255) {
      newErrors.name = 'Name must be 255 characters or less';
    }
    if (!formData.system_prompt.trim()) {
      newErrors.system_prompt = 'System prompt is required';
    }
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
    // Clear field error on change
    if (errors[name]) {
      setErrors((prev) => {
        const next = { ...prev };
        delete next[name];
        return next;
      });
    }
  };

  const handleTemperatureChange = (e) => {
    const value = parseFloat(e.target.value);
    setFormData((prev) => ({ ...prev, temperature: value }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!validate()) return;

    setIsSubmitting(true);
    setApiError(null);

    try {
      const payload = {
        name: formData.name.trim(),
        description: formData.description.trim() || null,
        system_prompt: formData.system_prompt.trim(),
        model_name: formData.model_name,
        temperature: formData.temperature,
      };
      const response = await chatbotsAPI.create(payload);
      onSuccess(response.data);
    } catch (err) {
      const message =
        err.response?.data?.detail || 'Failed to create chatbot. Please try again.';
      setApiError(typeof message === 'string' ? message : JSON.stringify(message));
    } finally {
      setIsSubmitting(false);
    }
  };

  // Close on overlay click
  const handleOverlayClick = (e) => {
    if (e.target === e.currentTarget) {
      onClose();
    }
  };

  return (
    <div className="modal-overlay" onClick={handleOverlayClick}>
      <div className="modal" role="dialog" aria-labelledby="create-chatbot-title">
        {/* Header */}
        <div className="modal-header">
          <h2 id="create-chatbot-title">
            <Bot size={20} style={{ verticalAlign: 'middle', marginRight: '8px' }} />
            Create a new chatbot
          </h2>
          <button className="modal-close" onClick={onClose} aria-label="Close">
            <X size={20} />
          </button>
        </div>

        {/* Body */}
        <div className="modal-body">
          {apiError && (
            <div className="toast toast-error" style={{ marginBottom: 'var(--space-4)' }}>
              {apiError}
            </div>
          )}

          <form className="modal-form" onSubmit={handleSubmit}>
            {/* Name */}
            <div className="form-group">
              <label className="form-label" htmlFor="chatbot-name">
                Name <span style={{ color: 'var(--color-error)' }}>*</span>
              </label>
              <input
                id="chatbot-name"
                className={`form-input ${errors.name ? 'error' : ''}`}
                type="text"
                name="name"
                value={formData.name}
                onChange={handleChange}
                placeholder="e.g. Customer Support Bot"
                autoFocus
              />
              {errors.name && <div className="form-error">{errors.name}</div>}
            </div>

            {/* Description */}
            <div className="form-group">
              <label className="form-label" htmlFor="chatbot-description">
                Description
              </label>
              <input
                id="chatbot-description"
                className="form-input"
                type="text"
                name="description"
                value={formData.description}
                onChange={handleChange}
                placeholder="A brief description of what this chatbot does"
              />
            </div>

            {/* System Prompt */}
            <div className="form-group">
              <label className="form-label" htmlFor="chatbot-system-prompt">
                System prompt <span style={{ color: 'var(--color-error)' }}>*</span>
              </label>
              <textarea
                id="chatbot-system-prompt"
                className={`form-textarea ${errors.system_prompt ? 'error' : ''}`}
                name="system_prompt"
                value={formData.system_prompt}
                onChange={handleChange}
                placeholder="Define the chatbot's personality and behavior..."
                rows={4}
              />
              <div className="form-hint">
                Tell the AI how it should behave — its role, tone, and any rules to follow.
              </div>
              {errors.system_prompt && <div className="form-error">{errors.system_prompt}</div>}
            </div>

            {/* Model */}
            <div className="form-group">
              <label className="form-label" htmlFor="chatbot-model">
                <Sparkles size={14} style={{ verticalAlign: 'middle', marginRight: '4px' }} />
                AI Model
              </label>
              <select
                id="chatbot-model"
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

            {/* Temperature */}
            <div className="form-group">
              <label className="form-label" htmlFor="chatbot-temperature">
                Temperature: {formData.temperature.toFixed(1)}
              </label>
              <input
                id="chatbot-temperature"
                type="range"
                name="temperature"
                min="0"
                max="2"
                step="0.1"
                value={formData.temperature}
                onChange={handleTemperatureChange}
                className="form-range"
              />
              <div className="form-hint" style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span>Precise (0.0)</span>
                <span>Creative (2.0)</span>
              </div>
            </div>
          </form>
        </div>

        {/* Footer */}
        <div className="modal-footer">
          <button className="btn btn-secondary" onClick={onClose} disabled={isSubmitting}>
            Cancel
          </button>
          <button
            className="btn btn-primary"
            onClick={handleSubmit}
            disabled={isSubmitting}
            id="submit-create-chatbot"
          >
            {isSubmitting ? (
              <>
                <span className="spinner spinner-sm" />
                Creating…
              </>
            ) : (
              <>
                <Plus size={18} />
                Create chatbot
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}

