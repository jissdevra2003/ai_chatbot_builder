import { useState, useEffect } from 'react';
import {
  Users,
  UserPlus,
  Mail,
  Shield,
  Copy,
  Check,
  Clock,
  CheckCircle2,
} from 'lucide-react';
import AppLayout from '../../components/Layout/AppLayout';
import InviteMemberModal from './InviteMemberModal';
import { invitationsAPI } from '../../api/client';
import { useAuth } from '../../contexts/AuthContext';
import '../Chatbots/Chatbots.css';

export default function TeamPage() {
  const { role } = useAuth();
  const [members, setMembers] = useState([]);
  const [invitations, setInvitations] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [showInviteModal, setShowInviteModal] = useState(false);
  const [copiedToken, setCopiedToken] = useState(null);

  const canManage = role === 'owner' || role === 'admin';

  const fetchData = async () => {
    try {
      setError(null);
      const membersRes = await invitationsAPI.listMembers();
      setMembers(membersRes.data);

      if (canManage) {
        const invitesRes = await invitationsAPI.list();
        setInvitations(invitesRes.data);
      }
    } catch (err) {
      console.error('Failed to load team data:', err);
      setError('Failed to load team members.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleInviteSuccess = (newInvite) => {
    setInvitations((prev) => [newInvite, ...prev]);
    setShowInviteModal(false);
  };

  const handleCopyLink = async (token) => {
    const inviteUrl = `${window.location.origin}/signup?invite=${token}`;
    try {
      await navigator.clipboard.writeText(inviteUrl);
      setCopiedToken(token);
      setTimeout(() => setCopiedToken(null), 2000);
    } catch {
      const textarea = document.createElement('textarea');
      textarea.value = inviteUrl;
      document.body.appendChild(textarea);
      textarea.select();
      document.execCommand('copy');
      document.body.removeChild(textarea);
      setCopiedToken(token);
      setTimeout(() => setCopiedToken(null), 2000);
    }
  };

  const getInitials = (name) => {
    if (!name) return '?';
    return name
      .split(' ')
      .map((n) => n[0])
      .join('')
      .toUpperCase()
      .slice(0, 2);
  };

  const formatDate = (dateStr) => {
    return new Date(dateStr).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    });
  };

  return (
    <AppLayout pageTitle="Team Management">
      <div className="team-page animate-fade-in">
        {/* Header */}
        <div className="chatbots-header">
          <div>
            <h1>Team Members</h1>
            <p>Manage users and invitations for your organization.</p>
          </div>
          {canManage && (
            <button
              className="btn btn-primary"
              onClick={() => setShowInviteModal(true)}
              id="invite-member-btn"
            >
              <UserPlus size={18} />
              Invite member
            </button>
          )}
        </div>

        {error && (
          <div className="toast toast-error" style={{ marginBottom: 'var(--space-6)' }}>
            {error}
          </div>
        )}

        {/* Active Members Table */}
        <div className="settings-panel">
          <div className="settings-panel-header">
            <h3>Active Members ({members.length})</h3>
            <p>People with active access to this organization.</p>
          </div>

          {isLoading ? (
            <div className="doc-table-loading">
              {[1, 2, 3].map((i) => (
                <div key={i} className="skeleton doc-table-skeleton" />
              ))}
            </div>
          ) : (
            <div className="doc-table-wrapper">
              <table className="doc-table">
                <thead>
                  <tr>
                    <th className="doc-table-th">Member</th>
                    <th className="doc-table-th">Email</th>
                    <th className="doc-table-th">Role</th>
                    <th className="doc-table-th">Joined</th>
                  </tr>
                </thead>
                <tbody>
                  {members.map((member) => (
                    <tr key={member.user_id} className="doc-table-row">
                      <td className="doc-table-cell">
                        <div className="doc-name-wrapper">
                          <div className="sidebar-avatar" style={{ width: 34, height: 34, fontSize: 13 }}>
                            {getInitials(member.full_name)}
                          </div>
                          <span className="doc-filename">{member.full_name}</span>
                        </div>
                      </td>
                      <td className="doc-table-cell doc-table-cell-size">{member.email}</td>
                      <td className="doc-table-cell doc-table-cell-status">
                        <span
                          className={`badge ${
                            member.role === 'owner'
                              ? 'badge-success'
                              : member.role === 'admin'
                              ? 'badge-info'
                              : 'badge-neutral'
                          }`}
                        >
                          <Shield size={12} style={{ marginRight: 4 }} />
                          {member.role.toUpperCase()}
                        </span>
                      </td>
                      <td className="doc-table-cell doc-table-cell-date">
                        {formatDate(member.joined_at)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Pending Invitations Table (Only visible to OWNER / ADMIN) */}
        {canManage && (
          <div className="settings-panel" style={{ marginTop: 'var(--space-6)' }}>
            <div className="settings-panel-header">
              <h3>Pending Invitations ({invitations.filter((i) => i.status === 'pending').length})</h3>
              <p>Sent invitations waiting to be accepted.</p>
            </div>

            {invitations.length === 0 ? (
              <div className="doc-table-empty">
                <Mail size={20} style={{ color: 'var(--color-text-tertiary)' }} />
                <span>No pending invitations</span>
              </div>
            ) : (
              <div className="doc-table-wrapper">
                <table className="doc-table">
                  <thead>
                    <tr>
                      <th className="doc-table-th">Invited Email</th>
                      <th className="doc-table-th">Role</th>
                      <th className="doc-table-th">Status</th>
                      <th className="doc-table-th">Sent Date</th>
                      <th className="doc-table-th">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {invitations.map((invite) => (
                      <tr key={invite.id} className="doc-table-row">
                        <td className="doc-table-cell">
                          <span className="doc-filename">{invite.email}</span>
                        </td>
                        <td className="doc-table-cell">
                          <span className="badge badge-neutral">
                            {invite.role.toUpperCase()}
                          </span>
                        </td>
                        <td className="doc-table-cell">
                          <span
                            className={`badge ${
                              invite.status === 'pending'
                                ? 'badge-warning'
                                : invite.status === 'accepted'
                                ? 'badge-success'
                                : 'badge-error'
                            }`}
                          >
                            {invite.status === 'pending' ? <Clock size={12} /> : <CheckCircle2 size={12} />}
                            {invite.status.toUpperCase()}
                          </span>
                        </td>
                        <td className="doc-table-cell doc-table-cell-date">
                          {formatDate(invite.created_at)}
                        </td>
                        <td className="doc-table-cell">
                          {invite.status === 'pending' && (
                            <button
                              className="btn btn-secondary btn-sm"
                              onClick={() => handleCopyLink(invite.token)}
                              title="Copy invitation link"
                            >
                              {copiedToken === invite.token ? (
                                <>
                                  <Check size={14} style={{ color: 'var(--color-success)' }} /> Copied
                                </>
                              ) : (
                                <>
                                  <Copy size={14} /> Copy link
                                </>
                              )}
                            </button>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}

        {/* Invite Modal */}
        {showInviteModal && (
          <InviteMemberModal
            onClose={() => setShowInviteModal(false)}
            onSuccess={handleInviteSuccess}
          />
        )}
      </div>
    </AppLayout>
  );
}
