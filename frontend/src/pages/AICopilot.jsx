import React, { useState, useEffect, useRef } from 'react';
import { 
  Bot, 
  User, 
  Send, 
  Sparkles, 
  Quote, 
  Trash2, 
  HelpCircle, 
  ShieldCheck, 
  Layers, 
  CheckCircle2, 
  CornerDownLeft,
  ChevronRight,
  Database
} from 'lucide-react';
import { api } from '../services/api';

const DEFAULT_SUGGESTED_QUESTIONS = [
  "What are the biggest user complaints?",
  "What should we fix first?",
  "What features are users requesting?",
  "Why is negative sentiment increasing?",
  "Summarize the feedback about payment issues.",
  "What are the most common login problems?",
  "Which issue has the highest priority?"
];

export default function AICopilot() {
  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      text: "👋 Welcome to **FeedbackIQ Copilot**!\n\nI am your conversational product intelligence agent grounded strictly in your analyzed customer feedback records and identified themes.\n\nAsk me about priority bugs, feature demand, sentiment trends, or root causes.",
      sources: [],
      suggested_questions: [
        "What should we fix first?",
        "What are the biggest user complaints?",
        "What features are users requesting?"
      ]
    }
  ]);
  const [inputMessage, setInputMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const [activeAnalysis, setActiveAnalysis] = useState(null);
  const chatBottomRef = useRef(null);

  useEffect(() => {
    api.getHealth()
      .then(res => {
        setActiveAnalysis({
          mode: res.mode,
          records: res.records_count
        });
      })
      .catch(console.error);
  }, []);

  useEffect(() => {
    chatBottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  const handleSendMessage = async (textToSend) => {
    const query = textToSend || inputMessage;
    if (!query.trim() || loading) return;

    const newMsgs = [...messages, { role: 'user', text: query }];
    setMessages(newMsgs);
    setInputMessage('');
    setLoading(true);

    try {
      const res = await api.sendChat(query);
      const answerText = res.answer || "No response received.";
      const sources = res.sources || res.supporting_quotes || [];
      const suggested = res.suggested_questions || DEFAULT_SUGGESTED_QUESTIONS.slice(0, 3);
      const relevantThemes = res.relevant_themes || [];

      setMessages([
        ...newMsgs,
        {
          role: 'assistant',
          text: answerText,
          sources: sources,
          suggested_questions: suggested,
          relevant_themes: relevantThemes
        }
      ]);
    } catch (err) {
      setMessages([
        ...newMsgs,
        {
          role: 'assistant',
          text: `⚠️ Error retrieving insights: ${err.message}`,
          sources: [],
          suggested_questions: DEFAULT_SUGGESTED_QUESTIONS.slice(0, 3)
        }
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleClearChat = () => {
    setMessages([
      {
        role: 'assistant',
        text: "Conversation cleared. How can I help you analyze your customer feedback today?",
        sources: [],
        suggested_questions: DEFAULT_SUGGESTED_QUESTIONS.slice(0, 3)
      }
    ]);
  };

  // Simple Markdown renderer for bold, lists, and linebreaks
  const renderFormattedText = (text) => {
    const lines = text.split('\n');
    return lines.map((line, lIdx) => {
      // Check for bullet line
      const isBullet = line.trim().startsWith('•') || line.trim().startsWith('-') || line.trim().startsWith('* ');
      const cleanLine = isBullet ? line.replace(/^[•\-\*]\s*/, '') : line;

      // Parse bold **text**
      const parts = cleanLine.split(/(\*\*.*?\*\*)/g);
      const parsedParts = parts.map((part, pIdx) => {
        if (part.startsWith('**') && part.endsWith('**')) {
          return <strong key={pIdx} className="text-white font-semibold">{part.slice(2, -2)}</strong>;
        }
        return part;
      });

      if (isBullet) {
        return (
          <li key={lIdx} className="ml-4 list-disc text-slate-200 my-0.5">
            {parsedParts}
          </li>
        );
      }

      if (!line.trim()) {
        return <div key={lIdx} className="h-2" />;
      }

      return (
        <p key={lIdx} className="my-0.5 leading-relaxed text-slate-200">
          {parsedParts}
        </p>
      );
    });
  };

  return (
    <div className="space-y-4 max-w-5xl mx-auto h-[calc(100vh-120px)] flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between pb-3 hairline-b shrink-0">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-violet-600 to-indigo-600 flex items-center justify-center text-white shadow-sm">
            <Bot className="w-4 h-4" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-base font-bold tracking-tight text-white">AI Feedback Copilot</h1>
              <span className="px-2 py-0.2 text-[10px] font-mono uppercase tracking-wider rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                Grounded RAG Mode
              </span>
            </div>
            <p className="text-[11px] text-slate-400">
              Retrieval-augmented conversational agent citing real user feedback records.
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {activeAnalysis && (
            <div className="hidden sm:flex items-center gap-1.5 px-2.5 py-1 rounded bg-[#0E131F] border border-border-muted text-[11px] font-mono text-slate-400">
              <Database className="w-3 h-3 text-cyan-400" />
              <span>{activeAnalysis.records} items loaded</span>
            </div>
          )}

          <button
            onClick={handleClearChat}
            className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-[#0E131F] border border-border-muted hover:border-slate-700 text-slate-400 hover:text-slate-200 text-xs transition-colors"
            title="Clear current conversation"
          >
            <Trash2 className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">Clear Chat</span>
          </button>
        </div>
      </div>

      {/* Suggested Questions Ribbon */}
      <div className="p-2.5 rounded-xl surface-card shrink-0 space-y-1.5">
        <div className="flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-wider text-slate-400">
          <Sparkles className="w-3 h-3 text-cyan-400" />
          <span>Recommended Analytical Questions:</span>
        </div>
        <div className="flex flex-wrap gap-1.5">
          {DEFAULT_SUGGESTED_QUESTIONS.map((q, idx) => (
            <button
              key={idx}
              onClick={() => handleSendMessage(q)}
              className="text-[11px] px-2.5 py-1 rounded-md bg-[#080B11] hover:bg-white/[0.06] text-slate-300 hover:text-white border border-border-muted hover:border-violet-500/40 transition-all text-left"
            >
              {q}
            </button>
          ))}
        </div>
      </div>

      {/* Chat Messages Container */}
      <div className="flex-1 surface-card rounded-xl p-4 overflow-y-auto space-y-4">
        {messages.map((msg, idx) => {
          const isUser = msg.role === 'user';
          return (
            <div key={idx} className={`flex gap-3 ${isUser ? 'justify-end' : 'justify-start'}`}>
              {!isUser && (
                <div className="w-7 h-7 rounded-lg bg-violet-600/20 border border-violet-500/30 flex items-center justify-center shrink-0 mt-0.5 text-violet-300">
                  <Bot className="w-4 h-4" />
                </div>
              )}

              <div className={`max-w-[85%] rounded-xl p-3.5 text-xs ${
                isUser 
                  ? 'bg-violet-600 text-white rounded-tr-none' 
                  : 'bg-[#0E131F] border border-border-muted text-slate-200 rounded-tl-none shadow-sm'
              }`}>
                {/* Message Body */}
                <div className="space-y-1">
                  {isUser ? (
                    <p className="whitespace-pre-line font-medium">{msg.text}</p>
                  ) : (
                    renderFormattedText(msg.text)
                  )}
                </div>

                {/* Supporting Feedback Sources / Evidence */}
                {!isUser && msg.sources && msg.sources.length > 0 && (
                  <div className="mt-3 pt-2.5 border-t border-border-muted space-y-1.5">
                    <span className="text-[10px] font-bold uppercase tracking-wider text-cyan-400 flex items-center gap-1 font-mono">
                      <Quote className="w-3 h-3" /> Supporting Feedback Evidence ({msg.sources.length} quotes):
                    </span>
                    <div className="space-y-1">
                      {msg.sources.map((src, sIdx) => (
                        <div key={sIdx} className="p-2 rounded bg-[#080B11] border border-border-muted text-[11px] text-slate-300 italic font-mono">
                          "{src}"
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Suggested Follow-up Questions from Copilot */}
                {!isUser && msg.suggested_questions && msg.suggested_questions.length > 0 && (
                  <div className="mt-3 pt-2.5 border-t border-border-muted space-y-1.5">
                    <span className="text-[10px] font-bold uppercase tracking-wider text-violet-400 font-mono">
                      Follow-up Questions:
                    </span>
                    <div className="flex flex-wrap gap-1.5">
                      {msg.suggested_questions.map((sq, sqIdx) => (
                        <button
                          key={sqIdx}
                          onClick={() => handleSendMessage(sq)}
                          className="flex items-center gap-1 text-[10px] px-2 py-0.5 rounded bg-violet-500/10 hover:bg-violet-500/20 text-violet-300 border border-violet-500/20 transition-colors"
                        >
                          <span>{sq}</span>
                          <ChevronRight className="w-2.5 h-2.5 text-violet-400" />
                        </button>
                      ))}
                    </div>
                  </div>
                )}
              </div>

              {isUser && (
                <div className="w-7 h-7 rounded-lg bg-slate-800 flex items-center justify-center shrink-0 mt-0.5 text-slate-300">
                  <User className="w-4 h-4" />
                </div>
              )}
            </div>
          );
        })}

        {loading && (
          <div className="flex items-center gap-3">
            <div className="w-7 h-7 rounded-lg bg-violet-600/20 border border-violet-500/30 flex items-center justify-center text-cyan-400">
              <Bot className="w-4 h-4" />
            </div>
            <div className="p-3 rounded-xl bg-[#0E131F] border border-border-muted text-xs text-slate-400 flex items-center gap-2.5">
              <div className="flex space-x-1">
                <div className="w-1.5 h-1.5 bg-cyan-400 rounded-full animate-bounce" />
                <div className="w-1.5 h-1.5 bg-violet-400 rounded-full animate-bounce delay-100" />
                <div className="w-1.5 h-1.5 bg-indigo-400 rounded-full animate-bounce delay-200" />
              </div>
              <span className="font-mono text-[11px]">Searching feedback embeddings & synthesizing answer...</span>
            </div>
          </div>
        )}

        <div ref={chatBottomRef} />
      </div>

      {/* Input Bar */}
      <div className="p-3 surface-card rounded-xl shrink-0">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleSendMessage();
          }}
          className="flex items-center gap-2"
        >
          <input
            type="text"
            placeholder="Ask about recurring bugs, customer complaints, what to fix first, payment issues..."
            value={inputMessage}
            onChange={(e) => setInputMessage(e.target.value)}
            disabled={loading}
            className="flex-1 bg-[#080B11] border border-border-muted rounded-lg px-3.5 py-2 text-xs text-slate-100 placeholder-slate-500 focus:outline-none focus:border-violet-500/80 transition-colors"
          />
          <button
            type="submit"
            disabled={loading || !inputMessage.trim()}
            className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-violet-600 hover:bg-violet-500 disabled:opacity-40 text-white font-semibold text-xs transition-colors shrink-0 shadow-sm"
          >
            <span>Send</span>
            <Send className="w-3.5 h-3.5" />
          </button>
        </form>
      </div>
    </div>
  );
}
