import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Terminal, Cpu, Loader2, RotateCcw, AlertTriangle, CheckCircle } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

const API_BASE = 'http://localhost:8000';

const Engineering: React.FC = () => {
  const [diff, setDiff] = useState('');
  const [logs, setLogs] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [retrying, setRetrying] = useState(false);

  const fetchEngineering = async () => {
    try {
      const [diffRes, logsRes] = await Promise.all([
        axios.get(`${API_BASE}/coder/diff`),
        axios.get(`${API_BASE}/logs?agent=coder`)
      ]);
      setDiff(diffRes.data.diff);
      setLogs(logsRes.data.logs);
      setLoading(false);
    } catch (err) {
      console.error(err);
    }
  };

  useEffect(() => {
    fetchEngineering();
    const interval = setInterval(fetchEngineering, 5000);
    return () => clearInterval(interval);
  }, []);

  const retry = async () => {
    setRetrying(true);
    try {
      await axios.post(`${API_BASE}/agent/retry`);
      alert("Coder restarted.");
    } catch (err) {
      alert("Retry failed.");
    } finally {
      setRetrying(false);
    }
  };

  return (
    <div className="space-y-8 animate-in fade-in duration-500">
      <div className="flex items-center justify-between border-b border-brand-accent/30 pb-4">
        <div className="flex items-center gap-3">
          <Terminal className="text-slate-100" size={24} />
          <h2 className="text-xl font-bold tracking-tighter uppercase">Engineering Node</h2>
        </div>
        <div className="flex items-center gap-4">
          <div className="text-[10px] font-mono text-slate-500 uppercase tracking-widest bg-brand-accent/20 px-3 py-1 rounded border border-brand-accent">
            STATUS: Patches in Progress
          </div>
          <button 
            onClick={retry}
            disabled={retrying}
            className="flex items-center gap-2 px-4 py-1.5 bg-brand-accent hover:bg-brand-accent/70 border border-brand-accent/50 text-slate-200 text-[10px] uppercase font-black transition-all rounded"
          >
            {retrying ? <Loader2 size={12} className="animate-spin" /> : <RotateCcw size={12} />}
            Regenerate Fix
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Surgical Diff Viewer */}
        <div className="space-y-4">
          <h3 className="text-xs font-black uppercase text-slate-500 tracking-[0.2em] mb-6">Surgical Diff</h3>
          <div className="bg-brand-bg/50 border border-brand-accent rounded-lg p-6 font-mono text-[11px] h-[500px] overflow-auto custom-scrollbar shadow-2xl relative">
            <div className="absolute top-4 right-4 text-brand-success/20">
               <Cpu size={40} />
            </div>
            {loading ? <Loader2 className="animate-spin text-brand-success mx-auto mt-20" /> : (
              <div className="prose prose-invert max-w-none prose-pre:bg-slate-950 prose-pre:border prose-pre:border-brand-accent prose-sm">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                  {diff || "*No active Engineering mission. Awaiting Intelligence promotion.*"}
                </ReactMarkdown>
              </div>
            )}
          </div>
        </div>

        {/* Coder Telemetry */}
        <div className="space-y-4">
          <h3 className="text-xs font-black uppercase text-slate-500 tracking-[0.2em] mb-6">Coder Telemetry</h3>
          <div className="bg-black/40 border border-brand-accent rounded-lg p-4 h-[500px] font-mono text-[10px] overflow-y-auto space-y-1 custom-scrollbar">
            {logs.map((log, i) => (
              <div key={i} className="text-slate-400 border-l border-brand-accent/30 pl-2">
                <span className="text-slate-100/40 mr-2">{'>'}</span>
                {log}
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

export default Engineering;
