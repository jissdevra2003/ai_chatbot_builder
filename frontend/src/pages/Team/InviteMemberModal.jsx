import { useState } from 'react';
import { X, UserPlus, Mail, Shield } from 'lucide-react';
import { invitationsAPI } from '../../api/client';

export default function InviteMemberModal({ onClose, onSuccess }) {
  const [email, setEmail] = useState('');
  const [role, setRole] = useState('member');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);

    if (!email.trim()) {
      setError('Please enter an email address.');
      return;
    }

    setIsSubmitting(true);
    try {
      const response = await invitationsAPI.create({
        email: email.trim(),
        role: role,
      });
      onSuccess(response.data);
    } catch (err) {
      const message =
        err.response?.data?.detail || 'Failed to send invitation. Please try again.';
      setError(typeof message === 'string' ? message : JSON.stringify(message));
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleOverlayClick = (e) => {
    if (e.target === e.currentTarget) {
      onClose();
    }
  };

  return (
    <div className="modal-overlay" onClick={handleOverlayClick}>
      <div className="modal" role="dialog" aria-labelledby="invite-modal-title">
        <div className="modal-header">
          <h2 id="invite-modal-title" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <UserPlus size={20} />
            Invite Team Member
          </h2>
          <button className="modal-close" onClick={onClose} aria-label="Close">
            <X size={20} />
          </button>
        </div>

        <div className="modal-body">
          {error && (
            <div className="toast toast-error" style={{ marginBottom: 'var(--space-4)' }}>
              {error}
            </div>
          )}

          <form className="modal-form" onSubmit={handleSubmit}>
            <div className="form-group">
              <label className="form-label" htmlFor="invite-email">
                Email Address <span style={{ color: 'var(--color-error)' }}>*</span>
              </label>
              <div style={{ position: 'relative' }}>
                <input
                  id="invite-email"
                  className="form-input"
                  type="email"
                  placeholder="colleague@company.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  autoFocus
                />
              </div>
            </div>

            <div className="form-group">
              <label className="form-label" htmlFor="invite-role">
                <Shield size={14} style={{ verticalAlign: 'middle', marginRight: '4px' }} />
                Role
              </label>
              <select
                id="invite-role"
                className="form-select"
                value={role}
                onChange={(e) => setRole(e.target.value)}
              >
                <option value="member">Member — Can manage chatbots & documents</option>
                <option value="admin">Admin — Can manage team & settings</option>
              </select>
              <div className="form-hint">
                Admins have full access to workspace settings and team invitations.
              </div>
            </div>
          </form>
        </div>

        <div className="modal-footer">
          <button className="btn btn-secondary" onClick={onClose} disabled={isSubmitting}>
            Cancel
          </button>
          <button
            className="btn btn-primary"
            onClick={handleSubmit}
            disabled={isSubmitting}
            id="send-invite-btn"
          >
            {isSubmitting ? (
              <>
                <span className="spinner spinner-sm" />
                Sending…
              </>
            ) : (
              <>
                <Mail size={16} />
                Send invitation
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
