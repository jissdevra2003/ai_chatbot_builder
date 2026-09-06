import { useState, useRef, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import {
  Code,
  Copy,
  Check,
  Sparkles,
  MessageSquare,
  Send,
  Bot,
  User,
  Globe,
  Settings,
  HelpCircle,
} from 'lucide-react';
import { widgetAPI } from '../../api/client';

const THEME_OPTIONS = [
  { id: 'dark', label: 'Slate Dark', primaryColor: '#191C1F', headerBg: '#191C1F' },
  { id: 'blue', label: 'Ocean Blue', primaryColor: '#2563EB', headerBg: '#2563EB' },
  { id: 'emerald', label: 'Emerald Green', primaryColor: '#059669', headerBg: '#059669' },
  { id: 'purple', label: 'Royal Purple', primaryColor: '#7C3AED', headerBg: '#7C3AED' },
  { id: 'rose', label: 'Rose Pink', primaryColor: '#E11D48', headerBg: '#E11D48' },
];

/**
 * EmbedWidgetTab — Interactive setup tab for generating website embed code,
 * customizing widget styling, and testing a live interactive widget preview.
 *
 * Props:
 *  - chatbot: Chatbot object
 */
export default function EmbedWidgetTab({ chatbot }) {
  const [theme, setTheme] = useState(THEME_OPTIONS[0]);
  const [position, setPosition] = useState('bottom-right');
  const [welcomeMsg, setWelcomeMsg] = useState(
    `Hi! I'm ${chatbot.name}. How can I help you today?`
  );
  const [copied, setCopied] = useState(false);

  // Live preview state
  const [isWidgetOpen, setIsWidgetOpen] = useState(true);
  const [previewMessages, setPreviewMessages] = useState([
    { id: 'welcome', sender: 'bot', text: welcomeMsg },
  ]);
  const [inputMsg, setInputMsg] = useState('');
  const [isSending, setIsSending] = useState(false);
  const [sessionId, setSessionId] = useState(null);
  const messagesAreaRef = useRef(null);

  // Auto-scroll internal message container ONLY (prevents main window jumping)
  useEffect(() => {
    if (messagesAreaRef.current) {
      messagesAreaRef.current.scrollTop = messagesAreaRef.current.scrollHeight;
    }
  }, [previewMessages, isSending]);

  // Generate HTML Embed Code Snippet
  const origin = window.location.origin;
  const embedCodeSnippet = `<script
  src="${origin}/widget.js"
  data-chatbot-id="${chatbot.id}"
  data-theme-color="${theme.primaryColor}"
  data-position="${position}"
  defer>
</script>`;

  const handleCopyCode = async () => {
    try {
      await navigator.clipboard.writeText(embedCodeSnippet);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Fallback
      const textarea = document.createElement('textarea');
      textarea.value = embedCodeSnippet;
      document.body.appendChild(textarea);
      textarea.select();
      document.execCommand('copy');
      document.body.removeChild(textarea);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  // Send message in live preview
  const handleSendMessage = async (e) => {
    e.preventDefault();
    if (!inputMsg.trim() || isSending) return;

    const userText = inputMsg.trim();
    setInputMsg('');
    const userMsgObj = { id: `user-${Date.now()}`, sender: 'user', text: userText };
    setPreviewMessages((prev) => [...prev, userMsgObj]);
    setIsSending(true);

    try {
      const response = await widgetAPI.sendMessage(chatbot.id, userText, sessionId);
      const data = response.data;
      if (data.session_id) setSessionId(data.session_id);

      const botMsgObj = {
        id: `bot-${Date.now()}`,
        sender: 'bot',
        text: data.message,
        sources: data.sources,
      };
      setPreviewMessages((prev) => [...prev, botMsgObj]);
    } catch (err) {
      console.error('Widget chat preview error:', err);
      const errorMsgObj = {
        id: `err-${Date.now()}`,
        sender: 'bot',
        text: 'Sorry, I ran into an error processing your request.',
      };
      setPreviewMessages((prev) => [...prev, errorMsgObj]);
    } finally {
      setIsSending(false);
    }
  };

  return (
    <div className="embed-widget-tab animate-fade-in">
      <div className="embed-grid">
        {/* Left Column: Embed Controls & Instructions */}
        <div className="embed-controls-col">
          {/* Panel 1: Code Generator */}
          <div className="settings-panel">
            <div className="settings-panel-header">
              <h3>
                <Code size={18} style={{ verticalAlign: 'middle', marginRight: '6px' }} />
                Embed Code Snippet
              </h3>
              <p>
                Paste this script tag before the closing <code>&lt;/body&gt;</code> tag on
                your website.
              </p>
            </div>

            <div className="embed-code-box">
              <pre><code>{embedCodeSnippet}</code></pre>
              <button
                className="btn btn-primary btn-sm embed-copy-btn"
                onClick={handleCopyCode}
                id="copy-embed-code-btn"
              >
                {copied ? (
                  <>
                    <Check size={14} /> Copied!
                  </>
                ) : (
                  <>
                    <Copy size={14} /> Copy snippet
                  </>
                )}
              </button>
            </div>
          </div>

          {/* Panel 2: Widget Customization */}
          <div className="settings-panel" style={{ marginTop: 'var(--space-6)' }}>
            <div className="settings-panel-header">
              <h3>
                <Settings size={18} style={{ verticalAlign: 'middle', marginRight: '6px' }} />
                Widget Customization
              </h3>
              <p>Customize how the widget looks and feels on your website.</p>
            </div>

            <div className="settings-form">
              {/* Theme Color Selection */}
              <div className="form-group">
                <label className="form-label">Theme Color</label>
                <div className="theme-swatch-list">
                  {THEME_OPTIONS.map((opt) => (
                    <button
                      key={opt.id}
                      className={`theme-swatch-btn ${theme.id === opt.id ? 'active' : ''}`}
                      onClick={() => setTheme(opt)}
                      type="button"
                    >
                      <span
                        className="theme-swatch-color"
                        style={{ backgroundColor: opt.primaryColor }}
                      />
                      <span>{opt.label}</span>
                    </button>
                  ))}
                </div>
              </div>

              {/* Position */}
              <div className="form-group">
                <label className="form-label">Widget Position</label>
                <div className="position-toggle-group">
                  <button
                    className={`btn btn-sm ${position === 'bottom-right' ? 'btn-primary' : 'btn-secondary'}`}
                    onClick={() => setPosition('bottom-right')}
                    type="button"
                  >
                    Bottom Right
                  </button>
                  <button
                    className={`btn btn-sm ${position === 'bottom-left' ? 'btn-primary' : 'btn-secondary'}`}
                    onClick={() => setPosition('bottom-left')}
                    type="button"
                  >
                    Bottom Left
                  </button>
                </div>
              </div>

              {/* Initial Welcome Message */}
              <div className="form-group">
                <label className="form-label">Welcome Message</label>
                <input
                  className="form-input"
                  type="text"
                  value={welcomeMsg}
                  onChange={(e) => {
                    setWelcomeMsg(e.target.value);
                    setPreviewMessages((prev) => [
                      { id: 'welcome', sender: 'bot', text: e.target.value },
                      ...prev.slice(1),
                    ]);
                  }}
                  placeholder="Initial message shown when widget opens"
                />
              </div>
            </div>
          </div>

          {/* Panel 3: Integration Guides */}
          <div className="settings-panel" style={{ marginTop: 'var(--space-6)' }}>
            <div className="settings-panel-header">
              <h3>
                <Globe size={18} style={{ verticalAlign: 'middle', marginRight: '6px' }} />
                Platform Integration Guides
              </h3>
              <p>Quick instructions for common web builders.</p>
            </div>

            <div className="platform-guides">
              <div className="platform-guide-item">
                <strong>HTML / Custom Site:</strong> Paste before <code>&lt;/body&gt;</code> in <code>index.html</code>.
              </div>
              <div className="platform-guide-item">
                <strong>WordPress:</strong> Use Header & Footer Scripts plugin or add to theme's <code>footer.php</code>.
              </div>
              <div className="platform-guide-item">
                <strong>Shopify:</strong> Go to Online Store → Edit Code → Add before <code>&lt;/body&gt;</code> in <code>theme.liquid</code>.
              </div>
              <div className="platform-guide-item">
                <strong>Webflow:</strong> Go to Site Settings → Custom Code → Footer Code.
              </div>
            </div>
          </div>
        </div>

        {/* Right Column: Live Interactive Widget Preview */}
        <div className="embed-preview-col">
          <div className="preview-container-card">
            <div className="preview-header-bar">
              <Sparkles size={16} />
              <span>Live Interactive Preview</span>
            </div>

            {/* Mock website background */}
            <div className="mock-website-stage">
              <div className="mock-website-header">
                <div className="mock-nav-dot" />
                <div className="mock-nav-dot" />
                <div className="mock-nav-dot" />
                <span className="mock-url-bar">https://yourwebsite.com</span>
              </div>
              <div className="mock-website-body">
                <h4>Your Website Content</h4>
                <p>This is a live preview of how your AI chatbot will look and respond to visitors on your site.</p>
              </div>

              {/* Floating Widget Mock inside stage */}
              <div className={`widget-mock-layer widget-pos-${position}`}>
                {/* Chat Drawer */}
                {isWidgetOpen && (
                  <div className="widget-drawer animate-slide-up">
                    <div
                      className="widget-drawer-header"
                      style={{ backgroundColor: theme.primaryColor }}
                    >
                      <div className="widget-avatar">
                        <Bot size={18} />
                      </div>
                      <div className="widget-header-title">
                        <h5>{chatbot.name}</h5>
                        <span>Online • AI Assistant</span>
                      </div>
                      <button
                        className="widget-close-btn"
                        onClick={() => setIsWidgetOpen(false)}
                        aria-label="Close widget"
                      >
                        ×
                      </button>
                    </div>

                    <div className="widget-messages-area" ref={messagesAreaRef}>
                      {previewMessages.map((msg) => (
                        <div
                          key={msg.id}
                          className={`widget-msg-bubble widget-msg-${msg.sender}`}
                        >
                          {msg.sender === 'bot' && (
                            <div className="widget-msg-avatar" style={{ backgroundColor: theme.primaryColor }}>
                              <Bot size={13} />
                            </div>
                          )}
                          <div
                            className="widget-msg-text"
                            style={msg.sender === 'user' ? { backgroundColor: theme.primaryColor } : {}}
                          >
                            {msg.sender === 'bot' ? (
                              <ReactMarkdown>{msg.text}</ReactMarkdown>
                            ) : (
                              msg.text
                            )}
                          </div>
                        </div>
                      ))}
                      {isSending && (
                        <div className="widget-msg-bubble widget-msg-bot">
                          <div className="widget-msg-avatar" style={{ backgroundColor: theme.primaryColor }}>
                            <Bot size={13} />
                          </div>
                          <div className="widget-msg-text typing-indicator">
                            <span /><span /><span />
                          </div>
                        </div>
                      )}
                    </div>

                    <form className="widget-input-bar" onSubmit={handleSendMessage}>
                      <input
                        type="text"
                        placeholder="Type a message…"
                        value={inputMsg}
                        onChange={(e) => setInputMsg(e.target.value)}
                        disabled={isSending}
                      />
                      <button
                        type="submit"
                        className="widget-send-btn"
                        style={{ backgroundColor: theme.primaryColor }}
                        disabled={!inputMsg.trim() || isSending}
                      >
                        <Send size={14} />
                      </button>
                    </form>
                  </div>
                )}

                {/* Bubble Button */}
                <button
                  className="widget-bubble-trigger"
                  style={{ backgroundColor: theme.primaryColor }}
                  onClick={() => setIsWidgetOpen(!isWidgetOpen)}
                  aria-label="Toggle chatbot"
                >
                  <MessageSquare size={22} />
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
