import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { BrainCircuit, Search, Trash2, ArrowUpRight, Loader2, AlertCircle } from 'lucide-react';
import AuditTerminal from '../components/AuditTerminal';

const API_BASE = 'http://localhost:8000';

interface Target {
  title: string;
  url: string;
  category: string;
  delta_score: number;
  repo: string;
}

const Intelligence: React.FC = () => {
  const [targets, setTargets] = useState<Target[]>([]);
  const [loading, setLoading] = useState(true);
  const [logs, setLogs] = useState<string[]>([]);

  const fetchIntelligence = async () => {
    try {
      const [reportRes, logsRes] = await Promise.all([
        axios.get(`${API_BASE}/audit`), // Assuming we might want a specific scout-report endpoint soon, but audit has it for now
        axios.get(`${API_BASE}/logs?agent=scout`)
      ]);
      
      // In a real scenario, we'd have a /scout/report endpoint. 
      // For now, let's mock it if the file doesn't exist or fetch from the known location.
      const scoutReportPath = 'logs/scout_report.json';
      const reportData = await axios.get(`${API_BASE}/audit`); // This is actually logs/simulation_audit.md. 
      // I'll assume the backend provides the scout_report.json data via a new endpoint soon.
      // For the sake of scaffolding, I'll fetch /logs?agent=scout and use state.
      
      setLogs(logsRes.data.logs);
      setLoading(false);
    } catch (err) {
      console.error(err);
    }
  };

  useEffect(() => {
    fetchIntelligence();
    const interval = setInterval(fetchIntelligence, 5000);
    return () => clearInterval(interval);
  }, []);

  const promote = async (target: Target) => {
    try {
      await axios.post(`${API_BASE}/scout/promote`, target);
      alert("Target promoted to Engineering.");
    } catch (err) {
      alert("Promotion failed.");
    }
  };

  return (
    <div className="space-y-8 animate-in fade-in duration-500">
      <div className="flex items-center justify-between border-b border-brand-accent/30 pb-4">
        <div className="flex items-center gap-3">
          <BrainCircuit className="text-brand-success" size={24} />
          <h2 className="text-xl font-bold tracking-tighter uppercase">Intelligence Node</h2>
        </div>
        <div className="text-[10px] font-mono text-slate-500 uppercase tracking-widest">
           Status: Active Scouting
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Target Queue */}
        <div className="space-y-4">
          <h3 className="text-xs font-black uppercase text-slate-500 tracking-[0.2em] mb-6">Target Queue</h3>
          {loading ? <Loader2 className="animate-spin text-brand-success" /> : (
            <div className="space-y-3">
              {/* Mocking a card for now since I can't easily fetch local json files directly via axios without a dedicated endpoint */}
              <div className="bg-brand-bg/50 border border-brand-accent p-5 rounded-lg group hover:border-brand-success/50 transition-all">
                <div className="flex items-start justify-between mb-4">
                  <span className="text-[10px] bg-brand-success/10 text-brand-success px-2 py-0.5 rounded border border-brand-success/20 font-bold uppercase">
                    P1 ISSUE
                  </span>
                  <div className="flex gap-2">
                    <button className="p-1.5 text-slate-600 hover:text-brand-danger transition-colors">
                      <Trash2 size={14} />
                    </button>
                  </div>
                </div>
                <h4 className="text-sm font-bold text-slate-200 mb-2 leading-tight">
                  bug(kona): kona-host-client-offline-cannon test crashes due to wrong target spec
                </h4>
                <p className="text-[10px] text-slate-500 font-mono mb-6">RE: ethereum-optimism/optimism</p>
                <button 
                  onClick={() => promote({
                    title: "bug(kona): ...",
                    repo: "ethereum-optimism/optimism",
                    url: "",
                    category: "DX",
                    delta_score: 6
                  })}
                  className="w-full py-3 bg-brand-success/10 hover:bg-brand-success/20 border border-brand-success/50 text-brand-success text-[10px] font-black uppercase tracking-[0.1em] flex items-center justify-center gap-2 group-hover:bg-brand-success/20 transition-all"
                >
                  Promote to Coder <ArrowUpRight size={14} />
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Node Telemetry */}
        <div className="space-y-4">
          <h3 className="text-xs font-black uppercase text-slate-500 tracking-[0.2em] mb-6">Node Telemetry</h3>
          <div className="bg-black/40 border border-brand-accent rounded-lg p-4 h-[400px] font-mono text-[10px] overflow-y-auto overflow-x-hidden space-y-1 custom-scrollbar">
            {logs.map((log, i) => (
              <div key={i} className="text-slate-400 border-l border-brand-accent/30 pl-2">
                <span className="text-brand-success/40 mr-2">{'>'}</span>
                {log}
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

export default Intelligence;
