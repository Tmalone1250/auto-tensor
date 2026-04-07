import { useState, useEffect } from 'react';
import axios from 'axios';
import Sidebar from './components/Sidebar';
import AuditTerminal from './components/AuditTerminal';
import GovernorGauge from './components/GovernorGauge';
import { Activity, ShieldCheck, Clock, UserCheck, ScrollText } from 'lucide-react';

const API_BASE = 'http://localhost:8000';

function App() {
  const [activeTab, setActiveTab] = useState('missions');
  const [status, setStatus] = useState<any>(null);
  const [audit, setAudit] = useState<string>('');
  const [logs, setLogs] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchData = async () => {
    try {
      const [statusRes, auditRes, logsRes] = await Promise.all([
        axios.get(`${API_BASE}/status`),
        axios.get(`${API_BASE}/audit`),
        axios.get(`${API_BASE}/logs`)
      ]);

      setStatus(statusRes.data);
      setAudit(auditRes.data.content);
      setLogs(logsRes.data.logs);
      setLoading(false);
    } catch (error) {
      console.error('Data fetch failed:', error);
    }
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 5000); // 5s Polling
    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-brand-bg text-brand-success font-mono">
        <div className="animate-pulse flex flex-col items-center">
          <Activity size={48} className="mb-4" />
          <span className="text-xl uppercase tracking-widest font-bold">INITIALIZING WAR ROOM...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-screen bg-brand-bg text-slate-100 overflow-hidden font-mono">
      <Sidebar activeTab={activeTab} setActiveTab={setActiveTab} />

      <main className="flex-1 flex flex-col overflow-hidden">
        {/* Header Stats */}
        <header className="h-20 border-b border-brand-accent flex items-center justify-between px-8 bg-slate-900/40 backdrop-blur-md sticky top-0 z-20">
          <div className="flex items-center gap-6">
            <div className="flex flex-col">
              <span className="text-[10px] text-slate-500 font-bold uppercase tracking-widest flex items-center gap-1">
                <Clock size={10} className="text-brand-success" /> Uptime
              </span>
              <span className="text-lg font-bold text-brand-success">{status?.miner_uptime || "00:00:00"}</span>
            </div>
            <div className="w-px h-8 bg-brand-accent/50" />
            <div className="flex flex-col">
              <span className="text-[10px] text-slate-500 font-bold uppercase tracking-widest flex items-center gap-1">
                <UserCheck size={10} className="text-brand-warning" /> Active Agent
              </span>
              <span className="text-lg font-bold text-brand-warning">{status?.active_agent || "None"}</span>
            </div>
          </div>

          <div className="hidden md:flex items-center gap-2 px-3 py-1.5 bg-brand-success/10 border border-brand-success/20 rounded-md">
            <ShieldCheck size={14} className="text-brand-success" />
            <span className="text-xs font-bold text-brand-success/80">Sovereign Protocol: Secure</span>
          </div>
        </header>

        {/* Content Area */}
        <div className="flex-1 overflow-auto p-8 custom-scrollbar">
          <div className="max-w-6xl mx-auto space-y-8">
            
            {/* Mission / Dashboard View */}
            {activeTab === 'missions' && (
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
                <div className="lg:col-span-2 space-y-8">
                  <AuditTerminal content={audit} />
                </div>
                <div className="space-y-8">
                  <GovernorGauge 
                    remaining={status?.github_status?.remaining || 0} 
                    limit={status?.github_status?.limit || 5000} 
                  />
                  
                  {/* Recent Logs Summary */}
                  <div className="bg-brand-bg/50 border border-brand-accent p-6 rounded-lg shadow-lg">
                    <div className="flex items-center gap-2 mb-4">
                      <ScrollText className="text-slate-500" size={18} />
                      <h3 className="text-[10px] uppercase font-bold text-slate-500 tracking-[0.2em]">Workflow Logs</h3>
                    </div>
                    <div className="space-y-2">
                      {logs.slice(-5).map((log, i) => (
                        <div key={i} className="text-[10px] border-l-2 border-brand-accent/50 pl-2 py-1 text-slate-400 font-mono truncate">
                          {log}
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Other views (Placeholders) */}
            {activeTab === 'status' && (
              <div className="text-center py-20 animate-in fade-in duration-500">
                <Activity size={64} className="mx-auto text-brand-warning/30 mb-6" />
                <h2 className="text-2xl font-bold tracking-tighter text-slate-500 uppercase">Miner Telemetry Offline</h2>
                <p className="text-sm text-slate-600 mt-2 italic">Connect to Gittensor pool to view metrics.</p>
              </div>
            )}

            {activeTab === 'health' && (
              <div className="text-center py-20 animate-in fade-in duration-500">
                <ShieldCheck size={64} className="mx-auto text-brand-success/30 mb-6" />
                <h2 className="text-2xl font-bold tracking-tighter text-slate-500 uppercase">All Systems Nominal</h2>
                <p className="text-sm text-slate-600 mt-2 italic">Governor shielding at 100% capacity.</p>
              </div>
            )}

          </div>
        </div>
      </main>
    </div>
  );
}

export default App;
