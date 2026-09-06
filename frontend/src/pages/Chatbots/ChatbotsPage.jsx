import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Bot,
  Plus,
  FileText,
  MessageSquare,
  MoreVertical,
  Trash2,
  Settings,
  Calendar,
} from 'lucide-react';
import AppLayout from '../../components/Layout/AppLayout';
import CreateChatbotModal from './CreateChatbotModal';
import DeleteChatbotDialog from './DeleteChatbotDialog';
import { chatbotsAPI } from '../../api/client';
import './Chatbots.css';

export default function ChatbotsPage() {
  const navigate = useNavigate();
  const [chatbots, setChatbots] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState(null);
  const [openMenuId, setOpenMenuId] = useState(null);

  const fetchChatbots = async () => {
    try {
      setError(null);
      const response = await chatbotsAPI.list();
      setChatbots(response.data);
    } catch (err) {
      setError('Failed to load chatbots. Please try again.');
      console.error('Failed to load chatbots:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchChatbots();
  }, []);

  // Close context menu on outside click
  useEffect(() => {
    const handleClick = () => setOpenMenuId(null);
    if (openMenuId) {
      document.addEventListener('click', handleClick);
      return () => document.removeEventListener('click', handleClick);
    }
  }, [openMenuId]);

  const handleCreateSuccess = (newChatbot) => {
    setChatbots((prev) => [newChatbot, ...prev]);
    setShowCreateModal(false);
  };

  const handleDeleteSuccess = (deletedId) => {
    setChatbots((prev) => prev.filter((bot) => bot.id !== deletedId));
    setDeleteTarget(null);
  };

  const handleMenuToggle = (e, chatbotId) => {
    e.stopPropagation();
    setOpenMenuId(openMenuId === chatbotId ? null : chatbotId);
  };

  const handleMenuAction = (e, action, chatbot) => {
    e.stopPropagation();
    setOpenMenuId(null);
    if (action === 'settings') {
      navigate(`/chatbots/${chatbot.id}`);
    } else if (action === 'delete') {
      setDeleteTarget(chatbot);
    }
  };

  const formatDate = (dateStr) => {
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    });
  };

  // Loading skeletons
  if (isLoading) {
    return (
      <AppLayout pageTitle="Chatbots">
        <div className="chatbots-header">
          <div>
            <h1>Chatbots</h1>
            <p>Manage your AI assistants</p>
          </div>
        </div>
        <div className="chatbots-grid">
          {[1, 2, 3].map((i) => (
            <div key={i} className="skeleton skeleton-card" />
          ))}
        </div>
      </AppLayout>
    );
  }

  return (
    <AppLayout pageTitle="Chatbots">
      <div className="chatbots-header">
        <div>
          <h1>Chatbots</h1>
          <p>Manage your AI assistants</p>
        </div>
        <button
          className="btn btn-primary"
          onClick={() => setShowCreateModal(true)}
          id="create-chatbot-btn"
        >
          <Plus size={18} />
          New chatbot
        </button>
      </div>

      {/* Error state */}
      {error && (
        <div className="toast toast-error" style={{ marginBottom: 'var(--space-6)' }}>
          {error}
        </div>
      )}

      {/* Empty state */}
      {!error && chatbots.length === 0 && (
        <div className="empty-state">
          <div className="empty-state-icon">
            <Bot size={28} />
          </div>
          <h3>No chatbots yet</h3>
          <p>Create your first AI chatbot to get started. Upload documents and start chatting.</p>
          <button
            className="btn btn-primary"
            onClick={() => setShowCreateModal(true)}
          >
            <Plus size={18} />
            Create your first chatbot
          </button>
        </div>
      )}

      {/* Chatbot grid */}
      {chatbots.length > 0 && (
        <div className="chatbots-grid">
          {chatbots.map((chatbot) => (
            <div
              key={chatbot.id}
              className="chatbot-card"
              onClick={() => navigate(`/chatbots/${chatbot.id}`)}
              id={`chatbot-card-${chatbot.id}`}
            >
              <div className="chatbot-card-header">
                <div className="chatbot-card-icon">
                  <Bot size={22} />
                </div>
                <div className="chatbot-card-menu">
                  <button
                    className="chatbot-card-menu-btn"
                    onClick={(e) => handleMenuToggle(e, chatbot.id)}
                    aria-label="Chatbot options"
                  >
                    <MoreVertical size={18} />
                  </button>
                  {openMenuId === chatbot.id && (
                    <div className="card-context-menu">
                      <button
                        className="card-context-menu-item"
                        onClick={(e) => handleMenuAction(e, 'settings', chatbot)}
                      >
                        <Settings size={15} />
                        <span>Settings</span>
                      </button>
                      <button
                        className="card-context-menu-item danger"
                        onClick={(e) => handleMenuAction(e, 'delete', chatbot)}
                      >
                        <Trash2 size={15} />
                        <span>Delete</span>
                      </button>
                    </div>
                  )}
                </div>
              </div>

              <div className="chatbot-card-name">{chatbot.name}</div>
              <div className="chatbot-card-desc">
                {chatbot.description || 'No description provided'}
              </div>

              <div className="chatbot-card-meta">
                <div className="chatbot-card-meta-item">
                  <FileText />
                  <span>{chatbot.document_count || 0} docs</span>
                </div>
                <div className="chatbot-card-meta-item">
                  <MessageSquare />
                  <span>{chatbot.model_name}</span>
                </div>
                <div className="chatbot-card-meta-item">
                  <Calendar />
                  <span>{formatDate(chatbot.created_at)}</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Create Modal */}
      {showCreateModal && (
        <CreateChatbotModal
          onClose={() => setShowCreateModal(false)}
          onSuccess={handleCreateSuccess}
        />
      )}

      {/* Delete Dialog */}
      {deleteTarget && (
        <DeleteChatbotDialog
          chatbot={deleteTarget}
          onClose={() => setDeleteTarget(null)}
          onSuccess={handleDeleteSuccess}
        />
      )}
    </AppLayout>
  );
}
