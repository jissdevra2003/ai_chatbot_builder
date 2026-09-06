import { useState, useEffect } from 'react';
import {
  Building,
  Save,
  Check,
  Shield,
  Zap,
  Sparkles,
  HardDrive,
  Bot,
} from 'lucide-react';
import AppLayout from '../../components/Layout/AppLayout';
import { useAuth } from '../../contexts/AuthContext';
import { authAPI } from '../../api/client';
import '../Chatbots/Chatbots.css';

export default function SettingsPage() {
  const { organization, role, refreshUser } = useAuth();
  const [orgName, setOrgName] = useState(organization?.name || '');
  const [isSaving, setIsSaving] = useState(false);
  const [saveError, setSaveError] = useState(null);
  const [showSaveToast, setShowSaveToast] = useState(false);

  const canEdit = role === 'owner' || role === 'admin';

  useEffect(() => {
    if (organization?.name) {
      setOrgName(organization.name);
    }
  }, [organization]);

  const handleSave = async (e) => {
    e.preventDefault();
    if (!orgName.trim() || isSaving) return;

    setIsSaving(true);
    setSaveError(null);

    try {
      await authAPI.updateOrg({ name: orgName.trim() });
      await refreshUser(); // Update AuthContext & sidebar in real time!
      setShowSaveToast(true);
      setTimeout(() => setShowSaveToast(false), 3000);
    } catch (err) {
      const message =
        err.response?.data?.detail || 'Failed to update organization name.';
      setSaveError(typeof message === 'string' ? message : JSON.stringify(message));
    } finally {
      setIsSaving(false);
    }
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return 'N/A';
    return new Date(dateStr).toLocaleDateString('en-US', {
      month: 'long',
      day: 'numeric',
      year: 'numeric',
    });
  };

  return (
    <AppLayout pageTitle="Organization Settings">
      <div className="settings-page animate-fade-in" style={{ maxWidth: 800 }}>
        {/* Header */}
        <div className="chatbots-header">
          <div>
            <h1>Organization Settings</h1>
            <p>Manage workspace configuration and active plan details.</p>
          </div>
        </div>

        {/* Panel 1: General Workspace Settings */}
        <div className="settings-panel">
          <div className="settings-panel-header">
            <h3>
              <Building size={18} style={{ verticalAlign: 'middle', marginRight: '6px' }} />
              Workspace Identity
            </h3>
            <p>General information about your organization tenant.</p>
          </div>

          {saveError && (
            <div className="toast toast-error" style={{ marginBottom: 'var(--space-4)' }}>
              {saveError}
            </div>
          )}

          <form onSubmit={handleSave} className="settings-form">
            <div className="form-group">
              <label className="form-label" htmlFor="org-name-input">
                Organization Name
              </label>
              <input
                id="org-name-input"
                className="form-input"
                type="text"
                value={orgName}
                onChange={(e) => setOrgName(e.target.value)}
                disabled={!canEdit || isSaving}
                placeholder="Enter organization name"
              />
            </div>

            <div className="settings-form-row" style={{ marginTop: 'var(--space-2)' }}>
              <div className="form-group">
                <label className="form-label">Organization ID</label>
                <input
                  className="form-input"
                  type="text"
                  value={organization?.id || ''}
                  disabled
                  style={{ background: 'var(--color-bg-secondary)', fontFamily: 'monospace' }}
                />
              </div>
              <div className="form-group">
                <label className="form-label">Created Date</label>
                <input
                  className="form-input"
                  type="text"
                  value={formatDate(organization?.created_at)}
                  disabled
                  style={{ background: 'var(--color-bg-secondary)' }}
                />
              </div>
            </div>

            {canEdit && (
              <div className="settings-form-actions">
                <button
                  className="btn btn-primary"
                  type="submit"
                  disabled={isSaving || orgName.trim() === organization?.name}
                  id="save-org-name-btn"
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
            )}
          </form>
        </div>

        {/* Panel 2: Active Plan & Limits Overview */}
        <div className="settings-panel" style={{ marginTop: 'var(--space-6)' }}>
          <div className="settings-panel-header">
            <h3>
              <Zap size={18} style={{ verticalAlign: 'middle', marginRight: '6px' }} />
              Workspace Plan & Limits
            </h3>
            <p>Active tier capabilities and system parameters.</p>
          </div>

          <div className="quick-actions" style={{ gridTemplateColumns: '1fr 1fr' }}>
            <div className="card" style={{ padding: 'var(--space-4)' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
                <Sparkles size={16} style={{ color: 'var(--color-warning)' }} />
                <span style={{ fontWeight: 600 }}>Pro Engine Tier</span>
              </div>
              <p style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-secondary)', margin: 0 }}>
                Powered by Gemini 2.0 & 3.6 Flash LLM models with RAG Vector search.
              </p>
            </div>

            <div className="card" style={{ padding: 'var(--space-4)' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
                <HardDrive size={16} style={{ color: 'var(--color-info)' }} />
                <span style={{ fontWeight: 600 }}>File Limits</span>
              </div>
              <p style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-secondary)', margin: 0 }}>
                Up to 10 MB per file (PDF, DOCX, TXT, CSV) with auto-chunking.
              </p>
            </div>
          </div>
        </div>

        {/* Panel 3: Roles & Permissions Matrix */}
        <div className="settings-panel" style={{ marginTop: 'var(--space-6)' }}>
          <div className="settings-panel-header">
            <h3>
              <Shield size={18} style={{ verticalAlign: 'middle', marginRight: '6px' }} />
              Your Role: <span style={{ color: 'var(--color-accent)', textTransform: 'uppercase' }}>{role}</span>
            </h3>
            <p>Access control summary for your role in this organization.</p>
          </div>

          <ul style={{
            listStyle: 'none',
            padding: 0,
            display: 'flex',
            flexDirection: 'column',
            gap: 'var(--space-2)',
            fontSize: 'var(--font-size-sm)',
            color: 'var(--color-text-secondary)'
          }}>
            <li style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Check size={16} style={{ color: 'var(--color-success)' }} />
              Create, edit, and delete AI chatbots & settings
            </li>
            <li style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Check size={16} style={{ color: 'var(--color-success)' }} />
              Upload, preview chunks, and delete knowledge base documents
            </li>
            <li style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Check size={16} style={{ color: 'var(--color-success)' }} />
              Generate API keys and configure website embed widget
            </li>
            {canEdit && (
              <li style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Check size={16} style={{ color: 'var(--color-success)' }} />
                Invite team members and manage organization settings
              </li>
            )}
          </ul>
        </div>

        {/* Save Toast */}
        {showSaveToast && (
          <div className="save-toast">
            <div className="toast toast-success">
              <Check size={16} />
              Organization name updated successfully
            </div>
          </div>
        )}
      </div>
    </AppLayout>
  );
}
