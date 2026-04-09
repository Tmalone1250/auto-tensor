import { useState, useEffect } from 'react';
import axios from 'axios';
import { Routes, Route, useLocation, Navigate } from 'react-router-dom';
import Sidebar from './components/Sidebar';
import Intelligence from './pages/Intelligence';
import Engineering from './pages/Engineering';
import Quality from './pages/Quality';
import { 
  ShieldCheck, 
  Clock, 
  UserCheck, 
  Cpu,
  ChevronRight,
  Database
} from 'lucide-react';

const API_BASE = import.meta.env.VITE_API_URL || 'https://autotensor.duckdns.org';

interface MinerStatus {
  github_status: {
    remaining: number;
    limit: number;
    reset: number;
  };
  miner_uptime: string;
  active_agent: string;
  is_running: boolean;
  current_task: string;
  timestamp: string;
}

function App() {
  const [status, setStatus] = useState<MinerStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const location = useLocation();

  const fetchData = async () => {
    try {
      const res = await axios.get(`${API_BASE}/status`);
      setStatus(res.data);
      setLoading(false);
    } catch (error) {
      console.error('Status fetch failed:', error);
    }
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 5000); 
    return () => clearInterval(interval);
  }, []);

  // Breadcrumb mapping
  const getBreadcrumb = () => {
    const path = location.pathname.substring(1);
    if (!path) return 'NOC Dashboard';
    return path.charAt(0).toUpperCase() + path.slice(1) + ' Node';
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-brand-bg text-brand-success font-mono">
        <div className="animate-pulse flex flex-col items-center">
          <Cpu size={48} className="mb-4" />
          <span className="text-xl uppercase tracking-widest font-bold">BOOTING NOC ENVIRONMENT...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-screen bg-brand-bg text-slate-100 overflow-hidden font-mono">
      <Sidebar />

      <main className="flex-1 flex flex-col overflow-hidden">
        {/* NOC Unified Header */}
        <header className="h-20 border-b border-brand-accent flex items-center justify-between px-8 bg-slate-900/40 backdrop-blur-md sticky top-0 z-20">
          <div className="flex items-center gap-4">
            <div className="flex flex-col">
               <div className="flex items-center gap-2 text-slate-500 text-[10px] uppercase font-black tracking-widest">
                  <Database size={12} />
                  <span>AT-MAIN</span>
                  <ChevronRight size={10} />
                  <span className="text-brand-success">{getBreadcrumb()}</span>
               </div>
               <h2 className="text-sm font-bold text-slate-200 mt-1 uppercase tracking-tighter">
                 {status?.current_task || "System Nominal"}
               </h2>
            </div>
          </div>

          <div className="flex items-center gap-8">
            <div className="flex flex-col items-end">
              <span className="text-[10px] text-slate-500 font-bold uppercase tracking-widest flex items-center gap-1">
                <Clock size={10} className="text-brand-success" /> Uptime
              </span>
              <span className="text-md font-bold text-brand-success leading-tight">{status?.miner_uptime || "00:00:00"}</span>
            </div>
            
            <div className="flex flex-col items-end">
              <span className="text-[10px] text-slate-500 font-bold uppercase tracking-widest">Agent State</span>
              <div className="flex items-center gap-2">
                <div className={`w-1.5 h-1.5 rounded-full ${status?.is_running ? 'bg-brand-success animate-pulse' : 'bg-slate-700'}`} />
                <span className="text-xs font-bold uppercase">{status?.active_agent || "IDLE"}</span>
              </div>
            </div>

            <div className="hidden lg:flex items-center gap-2 px-3 py-1.5 bg-brand-success/10 border border-brand-success/20 rounded-md">
              <ShieldCheck size={14} className="text-brand-success" />
              <span className="text-[10px] font-black tracking-widest uppercase text-brand-success/80">Sovereign Protocol</span>
            </div>
          </div>
        </header>

        {/* Dynamic Node Content Area */}
        <div className="flex-1 overflow-auto p-4 sm:p-8 custom-scrollbar">
          <div className="max-w-6xl mx-auto">
            <Routes>
              <Route path="/" element={<Navigate to="/intelligence" replace />} />
              <Route path="/intelligence" element={<Intelligence />} />
              <Route path="/engineering" element={<Engineering />} />
              <Route path="/quality" element={<Quality />} />
            </Routes>
          </div>
        </div>
      </main>
    </div>
  );
}

export default App;
