import React, { useState, useEffect } from 'react';
import { 
  TrendingUp, 
  Smartphone, 
  Globe, 
  Headphones, 
  PieChart as PieIcon, 
  Calendar,
  Layers,
  ArrowUpRight
} from 'lucide-react';
import { 
  ResponsiveContainer, 
  AreaChart, 
  Area, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip 
} from 'recharts';
import { api } from '../services/api';

export default function Trends() {
  const [analytics, setAnalytics] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.getAnalytics()
      .then(res => setAnalytics(res))
      .catch(err => console.error(err))
      .finally(() => setLoading(false));
  }, []);

  if (loading || !analytics) {
    return (
      <div className="flex items-center justify-center min-h-[50vh]">
        <div className="w-6 h-6 rounded-full border-2 border-cyan-400 border-t-transparent animate-spin"></div>
      </div>
    );
  }

  const { sentiment_trend, top_themes, recent_feedback } = analytics;

  return (
    <div className="space-y-6 animate-in fade-in duration-200">
      {/* Header */}
      <div className="pb-3 hairline-b">
        <div className="flex items-center gap-2">
          <h1 className="text-xl font-bold tracking-tight text-white">Longitudinal Feedback Sentiment Trends</h1>
          <span className="px-2 py-0.5 text-[10px] font-mono uppercase tracking-wider rounded bg-violet-500/10 text-violet-400 border border-violet-500/20">
            Temporal Analysis
          </span>
        </div>
        <p className="text-xs text-slate-400 mt-0.5">
          Longitudinal trajectory of customer sentiment velocity, issue resolution rates, and touchpoint distribution.
        </p>
      </div>

      {/* Main Area Chart: Sentiment Velocity */}
      <div className="p-5 rounded-xl surface-card space-y-3">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-xs font-bold uppercase tracking-wider text-slate-200">Cumulative Sentiment Velocity Trajectory</h2>
            <p className="text-[11px] text-slate-400 mt-0.5">Daily volume stacked by positive, negative, and neutral mentions</p>
          </div>
          <div className="flex items-center gap-3 text-xs">
            <span className="flex items-center gap-1.5 text-emerald-400 text-[11px]">
              <span className="w-2 h-2 rounded-sm bg-emerald-500"></span> Positive
            </span>
            <span className="flex items-center gap-1.5 text-rose-400 text-[11px]">
              <span className="w-2 h-2 rounded-sm bg-rose-500"></span> Negative
            </span>
            <span className="flex items-center gap-1.5 text-indigo-400 text-[11px]">
              <span className="w-2 h-2 rounded-sm bg-indigo-500"></span> Neutral
            </span>
          </div>
        </div>

        <div className="h-64 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={sentiment_trend} margin={{ top: 10, right: 10, left: -25, bottom: 0 }}>
              <defs>
                <linearGradient id="gradPos" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#10B981" stopOpacity={0.3}/>
                  <stop offset="95%" stopColor="#10B981" stopOpacity={0.0}/>
                </linearGradient>
                <linearGradient id="gradNeg" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#F43F5E" stopOpacity={0.3}/>
                  <stop offset="95%" stopColor="#F43F5E" stopOpacity={0.0}/>
                </linearGradient>
                <linearGradient id="gradNeu" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#6366F1" stopOpacity={0.3}/>
                  <stop offset="95%" stopColor="#6366F1" stopOpacity={0.0}/>
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="2 2" stroke="#1E2638" opacity={0.6} />
              <XAxis dataKey="date" stroke="#475569" fontSize={10} tickLine={false} tickFormatter={(v) => v.slice(5)} />
              <YAxis stroke="#475569" fontSize={10} tickLine={false} />
              <Tooltip 
                contentStyle={{ 
                  backgroundColor: '#0E131F', 
                  borderColor: '#1E2638', 
                  borderRadius: '8px', 
                  fontSize: '11px', 
                  color: '#FFF' 
                }} 
              />
              <Area type="monotone" dataKey="positive" stroke="#10B981" strokeWidth={1.5} fillOpacity={1} fill="url(#gradPos)" />
              <Area type="monotone" dataKey="negative" stroke="#F43F5E" strokeWidth={1.5} fillOpacity={1} fill="url(#gradNeg)" />
              <Area type="monotone" dataKey="neutral" stroke="#6366F1" strokeWidth={1} fillOpacity={1} fill="url(#gradNeu)" />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Channel Comparison & Thematic Weight */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        {/* Source Channels */}
        <div className="p-5 rounded-xl surface-card space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-xs font-bold uppercase tracking-wider text-slate-200">Channel Distribution</h2>
            <span className="text-[10px] text-slate-500 font-mono">Touchpoints</span>
          </div>

          <div className="space-y-2.5">
            {[
              { label: 'Web Application', share: 45, color: 'bg-cyan-500', count: '14 reports' },
              { label: 'Mobile App (iOS)', share: 22, color: 'bg-violet-500', count: '7 reports' },
              { label: 'Mobile App (Android)', share: 15, color: 'bg-indigo-500', count: '4 reports' },
              { label: 'Support Tickets & Zendesk', share: 18, color: 'bg-rose-500', count: '5 reports' },
            ].map((ch, idx) => (
              <div key={idx} className="p-2.5 rounded-lg bg-[#111726] border border-border-muted space-y-1">
                <div className="flex items-center justify-between text-xs">
                  <span className="font-medium text-slate-200">{ch.label}</span>
                  <span className="text-slate-400 font-mono text-[10px]">{ch.count}</span>
                </div>
                <div className="w-full bg-slate-800 rounded-full h-1.5 overflow-hidden">
                  <div className={`${ch.color} h-full rounded-full`} style={{ width: `${ch.share}%` }}></div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Action Readiness Metric */}
        <div className="p-5 rounded-xl surface-card flex flex-col justify-between">
          <div>
            <h2 className="text-xs font-bold uppercase tracking-wider text-slate-200 mb-0.5">Projected CSAT Impact</h2>
            <p className="text-[11px] text-slate-400 mb-3">Model-forecasted satisfaction increase upon mitigating P0 issues</p>

            <div className="p-3.5 rounded-lg bg-[#111726] border border-border-muted space-y-2 font-sans">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-cyan-300">Engineering Health Index</span>
                <span className="text-xs font-mono font-bold text-emerald-400">82/100</span>
              </div>
              <p className="text-[11px] text-slate-300 leading-relaxed">
                By addressing <span className="font-semibold text-white">Authentication & Login Stability</span>, overall user satisfaction is projected to increase from 20.0% to 68.4%.
              </p>
            </div>
          </div>

          <div className="pt-3 hairline-t flex items-center justify-between text-[11px] text-slate-500 font-mono">
            <span>Model confidence: 92%</span>
            <span className="text-cyan-400">Auto-synchronized</span>
          </div>
        </div>
      </div>
    </div>
  );
}
