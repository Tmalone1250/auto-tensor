import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { BrainCircuit, Search, Trash2, ArrowUpRight, Loader2, AlertCircle, ClipboardCheck } from 'lucide-react';
import AuditTerminal from '../components/AuditTerminal';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

const API_BASE = import.meta.env.VITE_API_URL || 'https://autotensor.duckdns.org';

interface Target {
  id: number;
  title: string;
  url: string;
  category: string;
  delta_score: number;
  repo: string;
  target_repo?: string;
  strategy?: string;
}

const Intelligence: React.FC = () => {
  const [targets, setTargets] = useState<Target[]>([]);
  const [scanUrl, setScanUrl] = useState('');
  const [loading, setLoading] = useState(true);
  const [scanning, setScanning] = useState(false);
  const [refining, setRefining] = useState(false);
  const [logs, setLogs] = useState<string[]>([]);
  
  // Provisioning States
  const [provisionedRepos, setProvisionedRepos] = useState<string[]>([]);
  const [provisioningFolders, setProvisioningFolders] = useState<Set<string>>(new Set());
  const [failedFolders, setFailedFolders] = useState<Set<string>>(new Set());
  const [pollInterval, setPollInterval] = useState(5000); // 5s heartbeat

  const fetchIntelligence = async () => {
    try {
      const [reportRes, logsRes, statusRes] = await Promise.all([
        axios.get(`${API_BASE}/scout/report`),
        axios.get(`${API_BASE}/logs?agent=scout`),
        axios.get(`${API_BASE}/status`)
      ]);

      if (reportRes.data && reportRes.data.top_targets) {
        setTargets(reportRes.data.top_targets);
      }

      setLogs(logsRes.data.logs);
      
      const provisioned = statusRes.data.provisioned_repos || [];
      setProvisionedRepos(provisioned.map((r: string) => r.toLowerCase()));
      
      // If none of the provisioning folders are missing anymore, we can stop fast polling
      if (provisioningFolders.size > 0) {
        const stillProvisioning = [...provisioningFolders].some(folder => !provisioned.map((r: string) => r.toLowerCase()).includes(folder));
        if (!stillProvisioning) {
          setProvisioningFolders(new Set());
          setPollInterval(5000);
        }
      }

      setLoading(false);
    } catch (err) {
      console.error("Fetch intelligence failed:", err);
    }
  };

  useEffect(() => {
    fetchIntelligence();
    const interval = setInterval(fetchIntelligence, pollInterval);
    return () => clearInterval(interval);
  }, [pollInterval]);

  // Adjust polling frequency based on active tasks
  useEffect(() => {
    if (provisioningFolders.size > 0) {
      setPollInterval(3000); // High frequency (3s) while provisioning
    } else {
      setPollInterval(5000); // Normal heartbeat (5s)
    }
  }, [provisioningFolders.size]);

  const handleScan = async () => {
    if (!scanUrl) return;
    setScanning(true);
    setTargets([]); 

    let finalUrl = scanUrl.trim();
    if (finalUrl && !finalUrl.startsWith('http')) {
      finalUrl = `https://github.com/${finalUrl}`;
    }

    try {
      await axios.post(`${API_BASE}/repo/scan`, { url: finalUrl });
    } catch (err) {
      alert("Scan failed to initiate.");
    } finally {
      setScanning(false);
    }
  };

  const handleRefine = async () => {
    setRefining(true);
    try {
      await axios.post(`${API_BASE}/scout/refine`);
      // Start polling for results
      setTimeout(fetchIntelligence, 2000);
    } catch (err) {
      console.error("Refinement failed:", err);
    } finally {
      setRefining(false);
    }
  };

  const promote = async (target: Target) => {
    try {
      await axios.post(`${API_BASE}/scout/promote`, target);
      alert("Target promoted to Engineering with Senior Dev Directive.");
    } catch (err) {
      alert("Promotion failed.");
    }
  };

  const handleClearLogs = async () => {
    try {
      await axios.post(`${API_BASE}/logs/clear`);
      setLogs([]);
    } catch (err) {
      console.error("Failed to clear logs:", err);
      setLogs([]); // Fallback to local clear
    }
  };

  const handleIgnore = async (targetId: number) => {
    // Optimistic Update: Remove from local state immediately
    setTargets(prev => prev.filter(t => t.id !== targetId));
    
    try {
      await axios.post(`${API_BASE}/scout/ignore`, { issue_id: targetId });
    } catch (err) {
      console.error("Failed to ignore issue:", err);
      // Optional: Refresh feed if server call fails
      fetchIntelligence();
    }
  };

  const getRepoFolder = (url: string | undefined): string => {
    if (!url) return "";
    const clean = url.rstrip ? url.rstrip("/").replace(".git", "") : url.replace(".git", "");
    if (clean.includes("/")) {
      return clean.split("/").pop()?.toLowerCase() || "";
    }
    return clean.toLowerCase();
  };

  const handleProvision = async (targetRepo: string) => {
    const folder = getRepoFolder(targetRepo);
    if (!folder) return;

    // Move to provisioning state (Global Sync: Affects all issues for this repo)
    setProvisioningFolders(prev => new Set(prev).add(folder));
    setFailedFolders(prev => {
      const next = new Set(prev);
      next.delete(folder);
      return next;
    });

    try {
      // Telemetry "Toast" (locally logged or displayed)
      console.log(`[PROVISION]: Initializing Fork & Branch on GitHub for ${folder}...`);
      
      await axios.post(`${API_BASE}/repo/provision`, { target_repo: targetRepo });
      
      // Success: fetchIntelligence will catch the transition soon due to 3s polling
      fetchIntelligence();
    } catch (err) {
      console.error("Provisioning failed:", err);
      setProvisioningFolders(prev => {
        const next = new Set(prev);
        next.delete(folder);
        return next;
      });
      setFailedFolders(prev => new Set(prev).add(folder));
    }
  };

  return (
    <div className="space-y-8 animate-in fade-in duration-500">
      {/* Mission Intake Bar */}
      <div className="bg-brand-bg/80 border border-brand-accent p-6 rounded-lg shadow-2xl backdrop-blur-md">
        <h3 className="text-xs font-black uppercase text-slate-500 tracking-[0.2em] mb-4">Mission Intake</h3>
        <div className="flex flex-col sm:flex-row gap-4">
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" size={16} />
            <input
              type="text"
              value={scanUrl}
              onChange={(e) => setScanUrl(e.target.value)}
              placeholder="Enter GitHub Link Here"
              className="w-full bg-black/40 border border-brand-accent p-3 pl-10 rounded text-sm font-mono text-brand-success placeholder:text-slate-600 focus:border-brand-success/50 outline-none transition-all"
            />
          </div>
          <button
            onClick={handleScan}
            disabled={scanning}
            className="px-8 py-3 bg-brand-success/10 hover:bg-brand-success/20 border border-brand-success/50 text-brand-success text-xs font-black uppercase tracking-widest transition-all disabled:opacity-30 flex items-center justify-center gap-2"
          >
            {scanning ? <Loader2 className="animate-spin" size={16} /> : <BrainCircuit size={16} />}
            Scan Repository
          </button>
        </div>
      </div>

      <div className="flex items-center justify-between border-b border-brand-accent/30 pb-4">
        <div className="flex items-center gap-3">
          <BrainCircuit className="text-brand-success" size={24} />
          <h2 className="text-xl font-bold tracking-tighter uppercase">Intelligence Agent</h2>
        </div>
        <div className="text-[10px] font-mono text-slate-500 uppercase tracking-widest">
          Status: {scanning ? 'Scanning Repository...' : 'Active Scouting'}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Target Queue */}
        <div className="space-y-4">
          <div className="flex items-center justify-between mb-6">
            <h3 className="text-xs font-black uppercase text-slate-500 tracking-[0.2em]">Target Queue</h3>
            <button
              onClick={handleRefine}
              disabled={loading || scanning || refining || targets.length === 0}
              className="flex items-center gap-1.5 text-[9px] font-black uppercase text-brand-success/60 hover:text-brand-success border border-brand-success/20 hover:border-brand-success/40 px-2 py-0.5 rounded transition-all bg-black/20 disabled:opacity-30"
              title="Refresh FAILED strategies"
            >
              {refining ? <Loader2 className="animate-spin" size={10} /> : <ArrowUpRight className="rotate-45" size={10} />}
              Refresh Blueprints
            </button>
          </div>
          {loading ? <Loader2 className="animate-spin text-brand-success" /> : targets.length === 0 && !scanning ? (
            <div className="text-center py-12 border border-dashed border-brand-accent/30 rounded-lg">
              <p className="text-[10px] text-slate-600 uppercase font-black tracking-widest leading-loose">
                No active intelligence. <br /> Use Mission Intake to scan a repository.
              </p>
            </div>
          ) : (
            <div className="space-y-4">
              {targets?.map((target, idx) => (
                <div key={idx} className="bg-brand-bg/50 border border-brand-accent p-5 rounded-lg group hover:border-brand-success/50 transition-all shadow-lg relative overflow-hidden">
                  <div className="absolute top-0 left-0 w-1 h-full bg-brand-success/20" />
                  <div className="flex items-start justify-between mb-4">
                    <span className="text-[10px] bg-brand-success/10 text-brand-success px-2 py-0.5 rounded border border-brand-success/20 font-bold uppercase">
                      DELTA SCORE: {target.delta_score}
                    </span>
                    <button 
                      onClick={() => handleIgnore(target.id)}
                      className="p-1.5 text-slate-600 hover:text-brand-danger transition-colors"
                      title="Dismiss Issue"
                    >
                      <Trash2 size={14} />
                    </button>
                  </div>
                  <h4 className="text-sm font-bold text-slate-200 mb-2 leading-tight">
                    {target.title}
                  </h4>
                  <p className="text-[10px] text-slate-500 font-mono mb-4">RE: {target.repo}</p>

                  <div className="mb-6 p-4 bg-black/60 border border-brand-accent/30 rounded text-[11px] font-sans leading-relaxed relative overflow-hidden">
                    <div className="absolute top-2 right-2 opacity-10 pointer-events-none">
                      <ClipboardCheck size={20} />
                    </div>
                    <span className="text-brand-success/50 font-black text-[9px] uppercase tracking-widest block mb-3 border-b border-brand-accent/20 pb-1">Architect Strategy</span>
                    <div className="prose prose-invert max-w-none prose-sm relative">
                      {refining && (target.strategy?.toLowerCase().includes('offline') || target.strategy?.toLowerCase().includes('failed')) && (
                        <div className="absolute inset-0 bg-black/40 backdrop-blur-sm flex items-center justify-center z-10 rounded">
                           <Loader2 className="animate-spin text-brand-success" size={20} />
                        </div>
                      )}
                      <ReactMarkdown 
                        remarkPlugins={[remarkGfm]}
                        components={{
                          h2: ({node, ...props}) => <h2 className="text-brand-success font-black border-b border-brand-accent/30 pb-1 mb-2 mt-4 text-[13px] uppercase tracking-widest" {...props} />,
                          h3: ({node, ...props}) => <h3 className="text-slate-100 font-bold mb-2 mt-3 text-[12px]" {...props} />,
                          p: ({node, ...props}) => <p className="text-slate-300 text-[11px] leading-relaxed mb-3 font-medium" {...props} />,
                          code: ({node, inline, ...props}: any) => (
                            inline 
                              ? <code className="bg-slate-900 text-brand-success px-1.5 py-0.5 rounded font-mono text-[10px] border border-brand-accent/30" {...props} />
                              : <code className="block bg-slate-950 p-3 rounded-md border border-brand-accent/50 my-3 overflow-x-auto font-mono text-[10px] text-brand-success custom-scrollbar" {...props} />
                          ),
                          pre: ({node, ...props}) => <pre className="bg-transparent p-0 m-0" {...props} />,
                          ul: ({node, ...props}) => <ul className="list-disc list-inside space-y-1 mb-4 ml-1 text-slate-400 text-[11px]" {...props} />,
                          li: ({node, ...props}) => <li className="mb-0.5" {...props} />,
                          strong: ({node, ...props}) => <strong className="text-brand-success font-bold" {...props} />
                        }}
                      >
                        {target.strategy || "_No strategy generated._"}
                      </ReactMarkdown>
                    </div>
                  </div>

                  {/* Dynamic Provisioning / Promote Button */}
                  {(() => {
                    const repoFolder = getRepoFolder(target.target_repo || target.repo);
                    const isProvisioned = provisionedRepos.includes(repoFolder);
                    const isProvisioning = provisioningFolders.has(repoFolder);
                    const isFailed = failedFolders.has(repoFolder);

                    if (isProvisioned) {
                      return (
                        <button
                          onClick={() => promote(target)}
                          className="w-full py-4 bg-brand-success/10 hover:bg-brand-success/20 border border-brand-success/50 text-brand-success text-[10px] font-mono font-black uppercase tracking-[0.1em] flex items-center justify-center gap-2 transition-all shadow-inner"
                        >
                          [PROMOTE TO CODER] <ArrowUpRight size={14} />
                        </button>
                      );
                    }

                    if (isProvisioning) {
                      return (
                        <button
                          disabled
                          className="w-full py-4 bg-brand-accent/10 border border-brand-accent/50 text-brand-accent text-[10px] font-mono font-black uppercase tracking-[0.1em] flex items-center justify-center gap-2 opacity-80 cursor-not-allowed"
                        >
                          <Loader2 className="animate-spin" size={14} />
                          [PROVISIONING...]
                        </button>
                      );
                    }

                    if (isFailed) {
                      return (
                        <button
                          onClick={() => handleProvision(target.target_repo || target.repo)}
                          className="w-full py-4 bg-brand-danger/10 hover:bg-brand-danger/20 border border-brand-danger/50 text-brand-danger text-[10px] font-mono font-black uppercase tracking-[0.1em] flex items-center justify-center gap-2 transition-all shadow-inner"
                        >
                          <AlertCircle size={14} />
                          [PROVISIONING FAILED - RETRY?]
                        </button>
                      );
                    }

                    return (
                      <button
                        onClick={() => handleProvision(target.target_repo || target.repo)}
                        className="w-full py-4 bg-brand-warning/10 hover:bg-brand-warning/30 border border-brand-warning/50 text-brand-warning text-[10px] font-mono font-black uppercase tracking-[0.1em] flex items-center justify-center gap-2 transition-all shadow-inner group-hover:bg-brand-warning/20"
                      >
                        [FORK & CLONE] <ArrowUpRight size={14} className="rotate-45" />
                      </button>
                    );
                  })()}
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Node Telemetry */}
        <div className="space-y-4">
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-xs font-black uppercase text-slate-500 tracking-[0.2em]">Agent Telemetry</h3>
            <button 
              onClick={handleClearLogs}
              className="text-[9px] font-black uppercase text-brand-success/60 hover:text-brand-success border border-brand-success/20 hover:border-brand-success/40 px-2 py-0.5 rounded transition-all bg-black/20"
            >
              Clear
            </button>
          </div>
          <div className="bg-black/40 border border-brand-accent rounded-lg p-4 h-[600px] font-mono text-[10px] overflow-y-auto space-y-1 custom-scrollbar">
            {logs?.map((log, i) => {
              const isError = log.includes("LLM Error") || log.includes("Exception");
              const isContinuation = log.startsWith("  ");
              return (
                <div key={i} className={`text-slate-400 border-l ${isError ? 'border-brand-danger/50 bg-brand-danger/5 text-brand-danger/90' : 'border-brand-accent/30'} ${isContinuation ? 'ml-4 border-l-0 opacity-80' : 'pl-2'} py-0.5`}>
                  {!isContinuation && <span className={`${isError ? 'text-brand-danger' : 'text-brand-success/40'} mr-2`}>{'>'}</span>}
                  {log}
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
};

export default Intelligence;
