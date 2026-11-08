import React, { useState, useEffect } from 'react';
import { 
  LayoutDashboard, 
  UploadCloud, 
  TableProperties, 
  Sparkles, 
  TrendingUp, 
  Settings as SettingsIcon,
  Search,
  Bell,
  Command,
  ChevronDown,
  Menu,
  X,
  Bot,
  FolderGit2,
  LogIn,
  LogOut,
  User,
  ShieldCheck,
  BrainCircuit,
  History
} from 'lucide-react';
import { api } from '../services/api';
import { useAuth } from '../context/AuthContext';
import AuthModal from '../components/AuthModal';

export default function MainLayout({ currentTab, onTabChange, children }) {
  const { user, signOut, isConfigured } = useAuth();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [notificationsOpen, setNotificationsOpen] = useState(false);
  const [authModalOpen, setAuthModalOpen] = useState(false);
  const [systemHealth, setSystemHealth] = useState({ online: true, mode: 'Local Storage (JSON)', records: 0, connected: false });
  const [searchQuery, setSearchQuery] = useState('');

  useEffect(() => {
    api.getSystemStatus()
      .then(res => {
        setSystemHealth({
          online: true,
          mode: res.connected ? 'Supabase PostgreSQL' : (res.mode || 'Local Storage (JSON)'),
          records: res.records_count || 0,
          connected: Boolean(res.connected)
        });
      })
      .catch(() => {
        setSystemHealth(prev => ({ ...prev, online: false }));
      });
  }, [currentTab]);

  const navSections = [
    {
      title: 'CORE',
      items: [
        { id: 'dashboard', label: 'Overview', icon: LayoutDashboard },
        { id: 'analyze', label: 'Ingest Feedback', icon: UploadCloud, badge: 'New' },
      ]
    },
    {
      title: 'EXPLORE',
      items: [
        { 
          id: 'explorer', 
          label: 'Feedback Records', 
          icon: TableProperties, 
          count: systemHealth.records > 0 ? systemHealth.records : null 
        },
        { id: 'trends', label: 'Temporal Velocity', icon: TrendingUp },
        { id: 'history', label: 'Analysis History', icon: FolderGit2 },
      ]
    },
    {
      title: 'INTELLIGENCE',
      items: [
        { 
          id: 'insights', 
          label: 'AI Summaries', 
          icon: Sparkles, 
          alertBadge: 'P0 Alert' 
        },
        { 
          id: 'copilot', 
          label: 'AI Copilot Chat', 
          icon: Bot, 
          badge: 'RAG' 
        },
        { 
          id: 'historical', 
          label: 'Historical Intelligence', 
          icon: History, 
          badge: 'Hindsight' 
        },
      ]
    },
    {
      title: 'MACHINE LEARNING',
      items: [
        { 
          id: 'ml-lab', 
          label: 'ML Model Lab', 
          icon: BrainCircuit, 
          badge: 'Train & Eval' 
        },
      ]
    },
    {
      title: 'SYSTEM',
      items: [
        { id: 'settings', label: 'Database & Models', icon: SettingsIcon },
      ]
    }
  ];

  return (
    <div className="min-h-screen flex flex-col md:flex-row bg-[#080B11] text-slate-100 font-sans selection:bg-violet-600/30">
      {/* Auth Modal */}
      <AuthModal isOpen={authModalOpen} onClose={() => setAuthModalOpen(false)} />

      {/* Mobile Top Header */}
      <div className="md:hidden flex items-center justify-between px-4 py-3 hairline-b bg-[#0B0F17]/95 backdrop-blur-md sticky top-0 z-50">
        <div className="flex items-center gap-2.5">
          <div className="w-7 h-7 rounded-lg bg-violet-600 flex items-center justify-center font-bold text-xs text-white shadow-sm">
            F
          </div>
          <span className="font-semibold text-sm tracking-tight text-white">
            Feedback<span className="text-cyan-400">IQ</span>
          </span>
        </div>
        <button 
          onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
          className="p-1.5 text-slate-400 hover:text-white rounded-lg bg-slate-900 border border-slate-800"
        >
          {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
        </button>
      </div>

      {/* Sidebar Navigation */}
      <aside className={`
        fixed md:sticky top-0 left-0 z-40 h-screen w-60 flex flex-col justify-between
        bg-[#090D15] hairline-r shrink-0
        transition-transform duration-200 ease-out
        ${mobileMenuOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0'}
      `}>
        {/* Workspace Switcher Header */}
        <div>
          <div className="p-3.5 hairline-b">
            <div className="w-full flex items-center justify-between p-1.5 rounded-lg text-left">
              <div className="flex items-center gap-2.5 min-w-0">
                <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-violet-600 to-indigo-700 flex items-center justify-center text-white text-xs font-bold shadow-sm">
                  IQ
                </div>
                <div className="min-w-0">
                  <div className="flex items-center gap-1.5">
                    <span className="font-semibold text-xs text-white truncate">FeedbackIQ</span>
                    <span className="text-[10px] font-mono text-cyan-400 font-medium">v1.2</span>
                  </div>
                  <p className="text-[10px] text-slate-500 truncate">Customer Intelligence SaaS</p>
                </div>
              </div>
            </div>
          </div>

          {/* Categorized Nav Sections */}
          <div className="px-3 py-3 space-y-4 overflow-y-auto max-h-[calc(100vh-190px)]">
            {navSections.map((section) => (
              <div key={section.title} className="space-y-0.5">
                <div className="px-2.5 pb-1 text-[10px] font-bold tracking-wider text-slate-500">
                  {section.title}
                </div>
                {section.items.map((item) => {
                  const Icon = item.icon;
                  const active = currentTab === item.id;
                  return (
                    <button
                      key={item.id}
                      onClick={() => {
                        onTabChange(item.id);
                        setMobileMenuOpen(false);
                      }}
                      className={`
                        w-full flex items-center justify-between px-2.5 py-1.5 rounded-lg text-xs font-medium transition-all
                        ${active 
                          ? 'bg-white/[0.08] text-white font-semibold shadow-sm' 
                          : 'text-slate-400 hover:text-slate-200 hover:bg-white/[0.03]'}
                      `}
                    >
                      <div className="flex items-center gap-2.5">
                        <Icon className={`w-3.5 h-3.5 ${active ? 'text-violet-400' : 'text-slate-400'}`} />
                        <span>{item.label}</span>
                      </div>

                      {item.count && (
                        <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-slate-800 text-slate-300">
                          {item.count}
                        </span>
                      )}

                      {item.alertBadge && (
                        <span className="text-[9px] font-mono px-1.5 py-0.5 rounded bg-rose-500/10 text-rose-400 border border-rose-500/20 font-semibold">
                          {item.alertBadge}
                        </span>
                      )}

                      {item.badge && (
                        <span className="text-[9px] font-mono px-1.5 py-0.2 rounded bg-cyan-500/10 text-cyan-300 border border-cyan-500/20">
                          {item.badge}
                        </span>
                      )}
                    </button>
                  );
                })}
              </div>
            ))}
          </div>
        </div>

        {/* Bottom Status & Profile */}
        <div className="p-3 hairline-t bg-[#080B12] space-y-2">
          {/* Active Model Indicator */}
          <div className="px-2.5 py-1.5 rounded-lg bg-white/[0.02] border border-white/[0.04] flex items-center justify-between text-[11px]">
            <div className="flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
              <span className="text-slate-400">MiniLM-L6-v2</span>
            </div>
            <span className="font-mono text-[10px] text-cyan-400 font-medium">NLP AI</span>
          </div>

          {/* User profile / Auth button */}
          <div className="flex items-center justify-between px-1 pt-1">
            <div className="flex items-center gap-2 min-w-0">
              <div className="w-6 h-6 rounded-md bg-gradient-to-tr from-violet-600 to-indigo-600 flex items-center justify-center font-bold text-[10px] text-white shrink-0">
                {user ? user.email?.slice(0, 2).toUpperCase() : 'AK'}
              </div>
              <div className="leading-none min-w-0">
                <p className="text-xs font-semibold text-slate-200 truncate">
                  {user ? (user.user_metadata?.full_name || user.email?.split('@')[0]) : 'Guest Analyst'}
                </p>
                <p className="text-[10px] text-slate-500 mt-0.5 truncate">
                  {user ? user.email : 'Local Dev Mode'}
                </p>
              </div>
            </div>

            {user ? (
              <button
                onClick={signOut}
                title="Sign out of Supabase"
                className="p-1 rounded text-slate-500 hover:text-rose-400 transition-colors"
              >
                <LogOut className="w-3.5 h-3.5" />
              </button>
            ) : (
              <button
                onClick={() => setAuthModalOpen(true)}
                className="text-[10px] font-semibold text-cyan-400 hover:text-cyan-300 bg-cyan-500/10 px-2 py-0.5 rounded border border-cyan-500/20 transition-colors"
              >
                Auth
              </button>
            )}
          </div>
        </div>
      </aside>

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Top Navbar */}
        <header className="hidden md:flex items-center justify-between px-8 py-3 hairline-b bg-[#080B11]/90 backdrop-blur-md sticky top-0 z-30">
          {/* Command / Search Bar */}
          <div className="relative w-80">
            <Search className="w-3.5 h-3.5 text-slate-500 absolute left-3 top-1/2 -translate-y-1/2" />
            <input 
              type="text" 
              placeholder="Search feedback, issues, or clusters..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full bg-[#0E131F] border border-border-muted rounded-lg pl-8 pr-12 py-1.5 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-violet-500/70 transition-colors"
            />
            <div className="absolute right-2.5 top-1/2 -translate-y-1/2 flex items-center gap-1 text-[10px] text-slate-500 font-mono">
              <span className="bg-slate-800 px-1 py-0.5 rounded border border-slate-700/60">/</span>
            </div>
          </div>

          {/* Right Header Actions */}
          <div className="flex items-center gap-3">
            {/* Database / Environment Badge */}
            <div 
              title={systemHealth.connected ? 'Active database: Supabase PostgreSQL (Remote Cloud)' : 'Active database: Local JSON storage (Local Dev Mode)'}
              className="flex items-center gap-2 px-2.5 py-1 rounded-md bg-[#0E131F] border border-border-muted text-xs cursor-default"
            >
              <span className={`w-1.5 h-1.5 rounded-full ${
                !systemHealth.online ? 'bg-rose-400' :
                systemHealth.connected ? 'bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.6)]' : 'bg-amber-400'
              }`} />
              <span className="text-slate-300 font-medium text-[11px]">{systemHealth.mode}</span>
              <span className="text-slate-600">|</span>
              <span className="text-slate-400 font-mono text-[11px]">{systemHealth.records} items</span>
            </div>

            {/* Ingest Action Button */}
            <button
              onClick={() => onTabChange('analyze')}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-violet-600 hover:bg-violet-500 text-white text-xs font-semibold shadow-sm transition-colors"
            >
              <UploadCloud className="w-3.5 h-3.5" />
              <span>Ingest Feedback</span>
            </button>

            {/* AI Copilot Shortcut */}
            <button
              onClick={() => onTabChange('copilot')}
              className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-[#0E131F] border border-border-muted hover:border-violet-500/40 text-xs font-medium text-slate-300 hover:text-white transition-colors"
            >
              <Bot className="w-3.5 h-3.5 text-cyan-400" />
              <span>Copilot</span>
            </button>

            {/* Notifications */}
            <div className="relative">
              <button 
                onClick={() => setNotificationsOpen(!notificationsOpen)}
                className="relative p-1.5 rounded-lg text-slate-400 hover:text-white bg-[#0E131F] border border-border-muted hover:border-slate-700 transition-colors"
              >
                <Bell className="w-3.5 h-3.5" />
                <span className="absolute top-1 right-1 w-1.5 h-1.5 rounded-full bg-cyan-400" />
              </button>

              {notificationsOpen && (
                <div className="absolute right-0 mt-2 w-72 rounded-xl surface-card p-3 shadow-xl z-50 animate-in fade-in duration-150">
                  <div className="flex items-center justify-between pb-2 hairline-b">
                    <span className="text-[11px] font-bold text-slate-200 uppercase tracking-wider">Operational Alerts</span>
                    <span className="text-[10px] text-cyan-400 font-mono">2 P0</span>
                  </div>
                  <div className="space-y-2 mt-2 text-xs">
                    <div className="p-2 rounded-lg bg-rose-500/10 border border-rose-500/20">
                      <p className="font-semibold text-rose-300 text-[11px]">Authentication Stability</p>
                      <p className="text-[10px] text-slate-400 mt-0.5">Crash rate on iOS 18 flagged as P0 critical blocker.</p>
                    </div>
                    <div className="p-2 rounded-lg bg-violet-500/10 border border-violet-500/20">
                      <p className="font-semibold text-violet-300 text-[11px]">K-Means Clustered</p>
                      <p className="text-[10px] text-slate-400 mt-0.5">5 distinct clusters verified with all-MiniLM-L6-v2.</p>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        </header>

        {/* Main Content Area */}
        <main className="flex-1 p-6 md:p-8 max-w-7xl mx-auto w-full">
          {children}
        </main>
      </div>
    </div>
  );
}
