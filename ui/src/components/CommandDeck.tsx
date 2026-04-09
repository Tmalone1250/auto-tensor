import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Square, Search, Terminal, ShieldAlert, Cpu, Plus, Loader2, Globe } from 'lucide-react';

const API_BASE = import.meta.env.VITE_API_URL || 'https://autotensor.duckdns.org';

interface Repo {
  id: string;
  full_name: string;
  html_url: string;
}

const CommandDeck: React.FC = () => {
  const [target, setTarget] = useState('');
  const [managedRepos, setManagedRepos] = useState<Repo[]>([]);
  const [selectedRepo, setSelectedRepo] = useState('');
  const [loading, setLoading] = useState(false);
  const [fetchingRepos, setFetchingRepos] = useState(true);

  const fetchRepos = async () => {
    try {
      const res = await axios.get(`${API_BASE}/repos`);
      setManagedRepos(res.data.repos || []);
    } catch (err) {
      console.error('Failed to fetch repos:', err);
    } finally {
      setFetchingRepos(false);
    }
  };

  useEffect(() => {
    fetchRepos();
  }, []);

  const addRepo = async () => {
    if (!target.includes('github.com')) {
      alert('Please enter a valid GitHub URL');
      return;
    }
    setLoading(true);
    try {
      await axios.post(`${API_BASE}/repo/add`, { url: target });
      await fetchRepos();
      setTarget('');
      alert('Repo added to registry.');
    } catch (err: any) {
      alert('Failed to add repo: ' + (err.response?.data?.detail || err.message));
    } finally {
      setLoading(false);
    }
  };

  const runAgent = async (agentName: string) => {
    const finalTarget = selectedRepo || target;
    if (!finalTarget) {
      alert('Please select a repo or enter a target.');
      return;
    }

    setLoading(true);
    try {
      await axios.post(`${API_BASE}/agent/run`, {
        agent_name: agentName,
        target: finalTarget
      });
    } catch (error) {
      console.error('Agent run failed:', error);
      alert('Command failed: Ensure backend is reachable.');
    }
    setLoading(false);
  };

  const stopAgent = async () => {
    setLoading(true);
    try {
      await axios.post(`${API_BASE}/agent/stop`);
    } catch (error) {
      console.error('Agent stop failed:', error);
    }
    setLoading(false);
  };

  return (
    <div className="bg-brand-bg/50 border border-brand-accent p-6 rounded-lg shadow-lg relative overflow-hidden">
      <Cpu className="absolute -right-4 -bottom-4 text-brand-accent/10 w-32 h-32 rotate-12" />

      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-2">
          <ShieldAlert className="text-brand-warning" size={18} />
          <h3 className="text-[10px] uppercase font-bold text-slate-500 tracking-[0.2em]">Mission Command Deck</h3>
        </div>
        {fetchingRepos && <Loader2 className="animate-spin text-brand-success" size={14} />}
      </div>

      <div className="space-y-6 relative z-10">
        
        {/* Repo Selection / Add */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          
          {/* Dropdown for Managed Repos */}
          <div className="relative group">
            <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
              <Globe size={16} className="text-slate-500 group-focus-within:text-brand-success transition-colors" />
            </div>
            <select
              value={selectedRepo}
              onChange={(e) => setSelectedRepo(e.target.value)}
              className="w-full bg-slate-950 border border-brand-accent rounded-md py-4 pl-12 pr-4 text-sm font-mono text-slate-200 focus:outline-none focus:ring-1 focus:ring-brand-success/50 transition-all shadow-inner appearance-none"
            >
              <option value="">SELECT MANAGED REPO</option>
              {managedRepos?.map((repo) => (
                <option key={repo.id} value={repo.full_name}>
                  {repo.full_name}
                </option>
              ))}
            </select>
            <div className="absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none text-slate-600 font-bold text-[8px] uppercase tracking-widest">
                Registry
            </div>
          </div>

          {/* Input for Manual New Repo */}
          <div className="relative group flex gap-2">
            <div className="relative flex-1">
              <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                <Plus size={16} className="text-slate-500 group-focus-within:text-brand-success transition-colors" />
              </div>
              <input
                type="text"
                value={target}
                onChange={(e) => setTarget(e.target.value)}
                placeholder="ADD NEW GITHUB URL"
                className="w-full bg-slate-950 border border-brand-accent rounded-md py-4 pl-12 pr-4 text-sm font-mono placeholder:text-slate-700 focus:outline-none focus:ring-1 focus:ring-brand-success/50 transition-all shadow-inner"
              />
            </div>
            <button
              onClick={addRepo}
              disabled={loading || !target}
              className="px-4 bg-brand-accent/30 hover:bg-brand-accent/50 border border-brand-accent rounded-md transition-all active:scale-95 text-slate-300 disabled:opacity-30"
            >
              {loading ? <Loader2 className="animate-spin" size={16} /> : <Plus size={16} />}
            </button>
          </div>

        </div>

        {/* Control Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 border-t border-brand-accent/30 pt-6">
          <button
            onClick={() => runAgent('scout')}
            disabled={loading}
            className="h-16 sm:h-14 flex items-center justify-center gap-3 bg-brand-success/10 hover:bg-brand-success/20 border border-brand-success/40 text-brand-success rounded-md transition-all active:scale-95 disabled:opacity-50 group"
          >
            <Search size={20} className="group-hover:scale-110 transition-transform" />
            <span className="font-black text-xs uppercase tracking-[0.15em]">Run Scout</span>
          </button>

          <button
            onClick={() => runAgent('coder')}
            disabled={loading}
            className="h-16 sm:h-14 flex items-center justify-center gap-3 bg-brand-accent/30 hover:bg-brand-accent/50 border border-brand-accent text-slate-200 rounded-md transition-all active:scale-95 disabled:opacity-50 group"
          >
            <Terminal size={20} className="group-hover:scale-110 transition-transform" />
            <span className="font-black text-xs uppercase tracking-[0.15em]">Run Coder</span>
          </button>

          <button
            onClick={stopAgent}
            disabled={loading}
            className="h-16 sm:h-14 flex items-center justify-center gap-3 bg-brand-danger/10 hover:bg-brand-danger/20 border border-brand-danger/40 text-brand-danger rounded-md transition-all active:scale-95 disabled:opacity-50 group"
          >
            <Square size={20} fill="currentColor" className="group-hover:scale-110 transition-transform" />
            <span className="font-black text-xs uppercase tracking-[0.15em]">Stop Agent</span>
          </button>
        </div>
      </div>
    </div>
  );
};

export default CommandDeck;
