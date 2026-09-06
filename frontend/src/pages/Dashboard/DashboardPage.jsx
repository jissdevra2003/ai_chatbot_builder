import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Bot, FileText, MessageSquare, Plus, Upload, ArrowRight } from 'lucide-react';
import AppLayout from '../../components/Layout/AppLayout';
import { useAuth } from '../../contexts/AuthContext';
import { chatbotsAPI } from '../../api/client';

export default function DashboardPage() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [chatbots, setChatbots] = useState([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const response = await chatbotsAPI.list();
        setChatbots(response.data);
      } catch (error) {
        console.error('Failed to load chatbots:', error);
      } finally {
        setIsLoading(false);
      }
    };
    fetchData();
  }, []);

  const firstName = user?.full_name?.split(' ')[0] || 'there';

  return (
    <AppLayout pageTitle="Dashboard">
      <div className="dashboard-welcome">
        <h1>Welcome back, {firstName}</h1>
        <p>Here's an overview of your AI chatbot workspace.</p>

        {/* Stats */}
        <div className="dashboard-stats">
          <div
            className="stat-card stat-card-interactive"
            onClick={() => navigate('/chatbots')}
            role="button"
            tabIndex={0}
            aria-label="View all chatbots"
          >
            <div className="stat-card-label">Total Chatbots</div>
            <div className="stat-card-value">
              {isLoading ? '—' : chatbots.length}
            </div>
            <div className="stat-card-hint">Active AI assistants</div>
          </div>
          <div
            className="stat-card stat-card-interactive"
            onClick={() => navigate('/chatbots')}
            role="button"
            tabIndex={0}
            aria-label="View documents"
          >
            <div className="stat-card-label">Documents</div>
            <div className="stat-card-value">
              {isLoading ? '—' : chatbots.reduce((sum, bot) => sum + (bot.document_count || 0), 0) || '0'}
            </div>
            <div className="stat-card-hint">Uploaded knowledge files</div>
          </div>
          <div className="stat-card">
            <div className="stat-card-label">Status</div>
            <div className="stat-card-value" style={{ fontSize: 'var(--font-size-xl)' }}>
              {chatbots.length > 0 ? '🟢 Active' : '⚪ Setup needed'}
            </div>
            <div className="stat-card-hint">System health</div>
          </div>
        </div>

        {/* Quick Actions */}
        <div style={{ marginBottom: 'var(--space-6)' }}>
          <h2 style={{
            fontSize: 'var(--font-size-lg)',
            fontWeight: 'var(--font-weight-semibold)',
            marginBottom: 'var(--space-4)',
            color: 'var(--color-text-primary)',
          }}>
            Quick actions
          </h2>
        </div>

        <div className="quick-actions">
          <div className="quick-action-card" onClick={() => navigate('/chatbots')}>
            <div className="quick-action-icon">
              <Plus size={20} />
            </div>
            <h3>Create a chatbot</h3>
            <p>Set up a new AI assistant with custom instructions and knowledge base.</p>
          </div>

          <div className="quick-action-card" onClick={() => navigate('/chatbots')}>
            <div className="quick-action-icon">
              <Upload size={20} />
            </div>
            <h3>Upload documents</h3>
            <p>Add PDF, DOCX, TXT, or CSV files to train your chatbot.</p>
          </div>

          <div className="quick-action-card" onClick={() => navigate('/chatbots')}>
            <div className="quick-action-icon">
              <MessageSquare size={20} />
            </div>
            <h3>Test your chatbot</h3>
            <p>Send messages and see how your AI responds with your data.</p>
          </div>
        </div>
      </div>
    </AppLayout>
  );
}
