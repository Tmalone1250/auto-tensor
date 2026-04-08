import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Check, Code2, GitCommit, FileText, Send, Loader2, ShieldAlert, ClipboardCheck } from 'lucide-react';

const API_BASE = 'http://localhost:8000';

interface PendingApproval {
  id: string;
  repo: string;
  stage: 'diff' | 'draft' | 'publish';
  diff: string;
  draft_title: string;
  draft_body: string;
}

const Quality: React.FC = () => {
  const [approvals, setApprovals] = useState<PendingApproval[]>([]);
  const [loading, setLoading] = useState(true);
  const [logs, setLogs] = useState<string[]>([]);
  const [processing, setProcessing] = useState<string | null>(null);

  const fetchQuality = async () => {
    try {
      const [res, logsRes] = await Promise.all([
        axios.get(`${API_BASE}/approvals`),
        axios.get(`${API_BASE}/logs?agent=reviewer`)
      ]);
      setApprovals(res.data.pending || []);
      setLogs(logsRes.data.logs);
    } catch (err) {
      console.error('Failed to fetch quality data:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchQuality();
    const interval = setInterval(fetchQuality, 10000);
    return () => clearInterval(interval);
  }, []);

  const takeAction = async (id: string, action: string) => {
    setProcessing(`${id}-${action}`);
    try {
      await axios.post(`${API_BASE}/approvals/action`, { id, action });
      await fetchQuality();
    } catch (err) {
      alert("Action failed: " + err);
    } finally {
      setProcessing(null);
    }
  };

  return (
    <div className="space-y-8 animate-in fade-in duration-500">
      <div className="flex items-center justify-between border-b border-brand-accent/30 pb-4">
        <div className="flex items-center gap-3">
          <ClipboardCheck className="text-brand-warning" size={24} />
          <h2 className="text-xl font-bold tracking-tighter uppercase">Quality Agent</h2>
        </div>
        <div className="text-[10px] font-mono text-slate-500 uppercase tracking-widest bg-brand-warning/10 px-3 py-1 rounded border border-brand-warning/20 text-brand-warning">
          SOVEREIGN GATE ACTIVE
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">

        {/* Sovereign Gate Column */}
        <div className="lg:col-span-3 space-y-6">
          <h3 className="text-xs font-black uppercase text-slate-500 tracking-[0.2em] mb-6">Approvals</h3>

          {loading ? (
            <div className="flex justify-center py-20"><Loader2 className="animate-spin text-brand-warning" /></div>
          ) : approvals.length === 0 ? (
            <div className="text-center py-20 border border-dashed border-brand-accent/30 rounded-lg bg-slate-900/10">
              <Check className="mx-auto text-brand-success/20 mb-4" size={48} />
              <p className="text-[10px] text-slate-600 font-mono uppercase tracking-widest">Queue Clear. Awaiting Engineering Artifacts.</p>
            </div>
          ) : (
            <div className="space-y-8">
              {approvals.map((item) => (
                <div key={item.id} className="bg-brand-bg/60 border border-brand-accent rounded-lg shadow-2xl relative overflow-hidden">
                  <div className="absolute top-0 left-0 w-1 h-full bg-brand-warning" />
                  <div className="p-6">
                    <div className="flex items-center justify-between mb-8">
                      <div className="flex items-center gap-3">
                        <Code2 className="text-brand-success" size={20} />
                        <h4 className="text-sm font-black text-slate-200 font-mono">{item.repo}</h4>
                      </div>
                      <span className="text-[9px] font-black uppercase text-slate-500 tracking-tighter opacity-50">REF: {item.id}</span>
                    </div>

                    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                      {/* Step 1: Diff */}
                      <div className={`p-4 rounded border ${item.stage === 'diff' ? 'border-brand-success/40 bg-brand-success/5' : 'border-brand-accent/30 opacity-40'}`}>
                        <div className="flex items-center gap-2 mb-3">
                          <GitCommit size={14} className="text-brand-success" />
                          <span className="text-[10px] font-black uppercase tracking-widest">1. Audit Diff</span>
                        </div>
                        <pre className="text-[9px] font-mono text-slate-400 bg-black/40 p-2 rounded mb-4 max-h-32 overflow-auto">
                          {item.diff}
                        </pre>
                        <button
                          disabled={item.stage !== 'diff' || !!processing}
                          onClick={() => takeAction(item.id, 'commit')}
                          className="w-full py-2 bg-brand-success/10 border border-brand-success/40 text-brand-success text-[9px] font-black uppercase tracking-widest disabled:opacity-20"
                        >
                          Authorize Commit
                        </button>
                      </div>

                      {/* Step 2: PR Draft */}
                      <div className={`p-4 rounded border ${item.stage === 'draft' ? 'border-brand-warning/40 bg-brand-warning/5' : 'border-brand-accent/30 opacity-40'}`}>
                        <div className="flex items-center gap-2 mb-3">
                          <FileText size={14} className="text-brand-warning" />
                          <span className="text-[10px] font-black uppercase tracking-widest">2. Review Draft</span>
                        </div>
                        <div className="space-y-2 mb-4">
                          <div className="text-[10px] font-bold text-slate-200 truncate">{item.draft_title}</div>
                          <div className="text-[9px] text-slate-500 italic line-clamp-3">{item.draft_body}</div>
                        </div>
                        <button
                          disabled={item.stage !== 'draft' || !!processing}
                          onClick={() => takeAction(item.id, 'draft')}
                          className="w-full py-2 bg-brand-warning/10 border border-brand-warning/40 text-brand-warning text-[9px] font-black uppercase tracking-widest disabled:opacity-20"
                        >
                          Authorize Draft
                        </button>
                      </div>

                      {/* Step 3: Final Publish */}
                      <div className={`p-4 rounded border ${item.stage === 'publish' ? 'border-brand-danger/40 bg-brand-danger/5' : 'border-brand-accent/30 opacity-40'}`}>
                        <div className="flex items-center gap-2 mb-3">
                          <Send size={14} className="text-brand-danger" />
                          <span className="text-[10px] font-black uppercase tracking-widest">3. Final Publish</span>
                        </div>
                        <div className="h-16 flex items-center justify-center mb-4">
                          <ShieldAlert size={24} className="text-brand-danger/20" />
                        </div>
                        <button
                          disabled={item.stage !== 'publish' || !!processing}
                          onClick={() => takeAction(item.id, 'publish')}
                          className="w-full py-2 bg-brand-danger/10 border border-brand-danger/40 text-brand-danger text-[9px] font-black uppercase tracking-widest disabled:opacity-20"
                        >
                          Publish
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Quality Telemetry */}
        <div className="space-y-4">
          <h3 className="text-xs font-black uppercase text-slate-500 tracking-[0.2em] mb-6">Reviewer Logs</h3>
          <div className="bg-black/40 border border-brand-accent rounded-lg p-4 h-[600px] font-mono text-[10px] overflow-y-auto space-y-1 custom-scrollbar">
            {logs.map((log, i) => (
              <div key={i} className="text-slate-400 border-l border-brand-accent/30 pl-2">
                <span className="text-brand-warning/40 mr-2">{'>'}</span>
                {log}
              </div>
            ))}
          </div>
        </div>

      </div>
    </div>
  );
};

export default Quality;
