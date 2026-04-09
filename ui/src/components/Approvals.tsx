import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Check, Code2, GitCommit, FileText, Send, Loader2, ShieldAlert } from 'lucide-react';

const API_BASE = import.meta.env.VITE_API_URL;

interface PendingApproval {
  id: string;
  repo: string;
  stage: 'diff' | 'draft' | 'publish';
  diff: string;
  draft_title: string;
  draft_body: string;
}

const Approvals: React.FC = () => {
  const [approvals, setApprovals] = useState<PendingApproval[]>([]);
  const [loading, setLoading] = useState(true);
  const [processing, setProcessing] = useState<string | null>(null);

  const fetchApprovals = async () => {
    try {
      const res = await axios.get(`${API_BASE}/approvals`);
      setApprovals(res.data.pending || []);
    } catch (err) {
      console.error('Failed to fetch approvals:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchApprovals();
    const interval = setInterval(fetchApprovals, 10000); // 10s check
    return () => clearInterval(interval);
  }, []);

  const takeAction = async (id: string, action: string) => {
    setProcessing(`${id}-${action}`);
    try {
      await axios.post(`${API_BASE}/approvals/action`, { id, action });
      await fetchApprovals();
    } catch (err) {
      alert("Action failed: " + err);
    } finally {
      setProcessing(null);
    }
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center py-20 text-brand-success font-mono">
        <Loader2 className="animate-spin mb-4" size={32} />
        <span className="text-xs uppercase tracking-widest font-bold">Scanning Registry...</span>
      </div>
    );
  }

  if (approvals.length === 0) {
    return (
      <div className="text-center py-20 border border-dashed border-brand-accent/50 rounded-lg bg-slate-900/20">
        <Check className="mx-auto text-brand-success/30 mb-4" size={48} />
        <h3 className="text-slate-500 uppercase font-black tracking-[0.2em] text-sm">Registry Clean</h3>
        <p className="text-[10px] text-slate-600 mt-2 font-mono italic">Waiting for agents to commit new findings.</p>
      </div>
    );
  }

  return (
    <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500 px-2 lg:px-0">
      {approvals.map((item) => (
        <div key={item.id} className="bg-brand-bg/60 border border-brand-accent rounded-lg shadow-2xl relative overflow-hidden group">
          {/* Subtle Repo Badge */}
          <div className="absolute top-0 right-0 bg-brand-accent/20 px-4 py-1 border-b border-l border-brand-accent rounded-bl-lg">
             <span className="text-[9px] font-black uppercase text-slate-500 tracking-tighter">REF: {item.id}</span>
          </div>

          <div className="p-6">
            <div className="flex items-center gap-3 mb-8">
              <Code2 className="text-brand-success" size={24} />
              <div>
                <h3 className="text-sm font-black text-slate-100 font-mono">{item.repo}</h3>
                <p className="text-[9px] text-slate-500 uppercase font-bold tracking-widest">Sovereign Operator Review Required</p>
              </div>
            </div>

            {/* 3-Stage Workflow Grid */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              
              {/* Stage 1: Diff Verification */}
              <div className={`flex flex-col p-5 rounded-md border transition-all ${item.stage === 'diff' ? 'border-brand-success/60 bg-brand-success/5 shadow-[0_0_20px_rgba(16,185,129,0.05)]' : 'border-brand-accent opacity-40 grayscale'}`}>
                <div className="flex items-center gap-2 mb-4">
                  <GitCommit size={18} className="text-brand-success" />
                  <h4 className="text-[11px] font-black uppercase tracking-widest text-slate-200">1. Commit & Push</h4>
                </div>
                <div className="flex-1">
                  <pre className="text-[10px] font-mono text-slate-400 bg-black/60 p-3 rounded border border-brand-accent/30 mb-4 overflow-x-auto max-h-48 custom-scrollbar">
                    {item.diff}
                  </pre>
                </div>
                <button 
                  onClick={() => takeAction(item.id, 'commit')}
                  disabled={item.stage !== 'diff' || !!processing}
                  className="h-12 flex items-center justify-center gap-2 bg-brand-success/10 hover:bg-brand-success/20 border border-brand-success/50 text-brand-success text-[10px] font-black uppercase tracking-widest transition-all active:scale-95 disabled:opacity-30"
                >
                  {processing === `${item.id}-commit` ? <Loader2 className="animate-spin" size={14} /> : <Check size={14} />}
                  Authorize Commit
                </button>
              </div>

              {/* Stage 2: PR Draft Review */}
              <div className={`flex flex-col p-5 rounded-md border transition-all ${item.stage === 'draft' ? 'border-brand-warning/60 bg-brand-warning/5 shadow-[0_0_20px_rgba(245,158,11,0.05)]' : 'border-brand-accent opacity-40 grayscale'}`}>
                <div className="flex items-center gap-2 mb-4">
                  <FileText size={18} className="text-brand-warning" />
                  <h4 className="text-[11px] font-black uppercase tracking-widest text-slate-200">2. Stylist Draft</h4>
                </div>
                <div className="flex-1 space-y-4 mb-6">
                   <div>
                     <span className="text-[8px] text-slate-500 uppercase font-black tracking-widest">PR Title</span>
                     <div className="text-[11px] font-bold text-slate-200 mt-1">{item.draft_title}</div>
                   </div>
                   <div>
                     <span className="text-[8px] text-slate-500 uppercase font-black tracking-widest">PR Body</span>
                     <div className="text-[10px] text-slate-400 font-mono mt-1 p-2 bg-black/40 rounded border border-brand-accent/20 leading-relaxed italic">
                       {item.draft_body}
                     </div>
                   </div>
                </div>
                <button 
                  onClick={() => takeAction(item.id, 'draft')}
                  disabled={item.stage !== 'draft' || !!processing}
                  className="h-12 flex items-center justify-center gap-2 bg-brand-warning/10 hover:bg-brand-warning/20 border border-brand-warning/50 text-brand-warning text-[10px] font-black uppercase tracking-widest transition-all active:scale-95 disabled:opacity-30"
                >
                  {processing === `${item.id}-draft` ? <Loader2 className="animate-spin" size={14} /> : <FileText size={14} />}
                  Authorize Draft
                </button>
              </div>

              {/* Stage 3: Final Publication */}
              <div className={`flex flex-col p-5 rounded-md border transition-all ${item.stage === 'publish' ? 'border-brand-danger/60 bg-brand-danger/5 shadow-[0_0_20px_rgba(244,63,94,0.05)]' : 'border-brand-accent opacity-40 grayscale'}`}>
                <div className="flex items-center gap-2 mb-4">
                  <Send size={18} className="text-brand-danger" />
                  <h4 className="text-[11px] font-black uppercase tracking-widest text-slate-200">3. Final Publish</h4>
                </div>
                <div className="flex-1 flex flex-col items-center justify-center text-center p-4">
                   <ShieldAlert size={32} className="text-brand-danger/30 mb-2" />
                   <p className="text-[10px] text-slate-500 italic max-w-[200px]">PR ready for maintainer ingestion. Final safety checks complete.</p>
                </div>
                <button 
                  onClick={() => takeAction(item.id, 'publish')}
                  disabled={item.stage !== 'publish' || !!processing}
                  className="h-12 flex items-center justify-center gap-2 bg-brand-danger/10 hover:bg-brand-danger/20 border border-brand-danger/50 text-brand-danger text-[10px] font-black uppercase tracking-widest transition-all active:scale-95 disabled:opacity-30"
                >
                  {processing === `${item.id}-publish` ? <Loader2 className="animate-spin" size={14} /> : <Send size={14} />}
                  Publish to Main
                </button>
              </div>

            </div>
          </div>
        </div>
      ))}
    </div>
  );
};

export default Approvals;
