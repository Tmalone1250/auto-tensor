import { useEffect, useRef, useState } from 'react';
import { Terminal } from '@xterm/xterm';
import { FitAddon } from '@xterm/addon-fit';
import { Lock, Unlock, TerminalSquare, Wifi, WifiOff, Trash2, RefreshCw } from 'lucide-react';
import { useTerminal, ConnState } from '../context/TerminalContext';
import '@xterm/xterm/css/xterm.css';

export default function TerminalPage() {
  const containerRef = useRef<HTMLDivElement>(null);
  const termRef = useRef<Terminal | null>(null);
  const fitRef = useRef<FitAddon | null>(null);
  const resizeObserverRef = useRef<ResizeObserver | null>(null);

  const { connState, attachTerminal, sendResize, clearBuffer, reconnect } = useTerminal();
  const [locked, setLocked] = useState(false);

  // --- Bootstrap xterm ---
  useEffect(() => {
    if (!containerRef.current) return;

    // Instantiate xterm
    const term = new Terminal({
      cursorBlink: true,
      fontFamily: '"JetBrains Mono", "Fira Code", "Courier New", monospace',
      fontSize: 14,
      lineHeight: 1.4,
      theme: {
        background:  '#0a0f1a',   // brand-bg
        foreground:  '#e2e8f0',   // slate-200
        cursor:      '#10b981',   // brand-success
        cursorAccent:'#0a0f1a',
        black:       '#1e293b',
        red:         '#f87171',
        green:       '#10b981',
        yellow:      '#fbbf24',
        blue:        '#60a5fa',
        magenta:     '#a78bfa',
        cyan:        '#22d3ee',
        white:       '#e2e8f0',
        brightBlack: '#334155',
        brightRed:   '#fc8181',
        brightGreen: '#34d399',
        brightYellow:'#fcd34d',
        brightBlue:  '#93c5fd',
        brightMagenta:'#c4b5fd',
        brightCyan:  '#67e8f9',
        brightWhite: '#f8fafc',
        selectionBackground: '#10b98133',
      },
      scrollback: 5000,
    });

    const fitAddon = new FitAddon();
    term.loadAddon(fitAddon);
    
    termRef.current = term;
    fitRef.current = fitAddon;

    // Attach to global context
    const detach = attachTerminal(containerRef.current, term);
    
    // Initial focus
    term.focus();

    // --- ResizeObserver ---
    const observer = new ResizeObserver(() => {
      try {
        fitAddon.fit();
        sendResize(term.cols, term.rows);
      } catch {
        // Ignore fit errors during teardown
      }
    });
    if (containerRef.current) observer.observe(containerRef.current);
    resizeObserverRef.current = observer;

    return () => {
      detach();
      observer.disconnect();
      term.dispose();
      termRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [attachTerminal]);

  // --- Terminal Lock: toggle stdin ---
  useEffect(() => {
    if (termRef.current) {
      termRef.current.options.disableStdin = locked;
    }
  }, [locked]);

  // --- Connection status badge ---
  const statusConfig: Record<ConnState, { label: string; color: string; icon: React.ReactNode }> = {
    connecting:   { label: 'Connecting…', color: 'text-yellow-400 border-yellow-400/30 bg-yellow-400/10', icon: <Wifi size={12} className="animate-pulse" /> },
    connected:    { label: 'Live Shell',  color: 'text-brand-success border-brand-success/30 bg-brand-success/10', icon: <Wifi size={12} /> },
    disconnected: { label: 'Disconnected', color: 'text-red-400 border-red-400/30 bg-red-400/10', icon: <WifiOff size={12} /> },
    auth_error:   { label: 'Auth Error',  color: 'text-red-400 border-red-400/30 bg-red-400/10', icon: <WifiOff size={12} /> },
  };
  const status = statusConfig[connState];

  return (
    <div className="flex flex-col h-full" style={{ minHeight: 'calc(100vh - 80px)' }}>
      {/* ─── Toolbar ─── */}
      <div className="flex items-center justify-between px-4 py-2.5 border-b border-brand-accent bg-slate-900/60 flex-shrink-0">
        <div className="flex items-center gap-3">
          <TerminalSquare size={16} className="text-brand-success" />
          <span className="text-xs font-black uppercase tracking-widest text-slate-300">Direct Shell</span>
          <span className="text-slate-600 text-xs hidden sm:inline">Persisted @ trevor-main</span>
        </div>

        <div className="flex items-center gap-2 sm:gap-3">
          {/* Connection badge */}
          <div className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full border text-[10px] font-bold uppercase tracking-widest ${status.color}`}>
            {status.icon}
            {status.label}
          </div>

          <div className="flex items-center gap-1.5 border-l border-brand-accent ml-1 pl-3">
            {/* Reconnect button */}
            {(connState === 'disconnected' || connState === 'auth_error') && (
              <button
                onClick={() => reconnect()}
                className="p-1.5 rounded-md bg-brand-accent/20 border border-brand-accent/40 text-slate-400 hover:text-brand-success transition-colors"
                title="Reconnect Shell"
              >
                <RefreshCw size={14} />
              </button>
            )}

            {/* Clear Buffer */}
            <button
              onClick={() => clearBuffer()}
              className="p-1.5 rounded-md bg-brand-accent/20 border border-brand-accent/40 text-slate-400 hover:text-red-400 transition-colors"
              title="Clear Terminal Buffer"
            >
              <Trash2 size={14} />
            </button>

            {/* Terminal Lock toggle */}
            <button
              id="terminal-lock-toggle"
              onClick={() => setLocked((l) => !l)}
              title={locked ? 'Unlock terminal input' : 'Lock terminal input (safe scroll)'}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md border text-[10px] font-black uppercase tracking-widest transition-all duration-200 ${
                locked
                  ? 'bg-red-500/20 border-red-500/40 text-red-400 shadow-[0_0_12px_rgba(239,68,68,0.2)]'
                  : 'bg-brand-accent/20 border-brand-accent/40 text-slate-400 hover:text-slate-200'
              }`}
            >
              {locked ? <Lock size={12} /> : <Unlock size={12} />}
              <span className="hidden xs:inline">{locked ? 'Locked' : 'Lock'}</span>
            </button>
          </div>
        </div>
      </div>

      {/* ─── Terminal canvas ─── */}
      <div className="relative flex-1 min-h-0 bg-[#0a0f1a]">
        {/* Lock overlay */}
        {locked && (
          <div className="absolute inset-0 z-10 flex items-center justify-center pointer-events-none">
            <div className="flex flex-col items-center gap-2 opacity-30">
              <Lock size={48} className="text-red-400" />
              <span className="text-red-400 text-xs font-black uppercase tracking-widest">Input Locked</span>
            </div>
          </div>
        )}

        <div
          ref={containerRef}
          id="xterm-container"
          className="w-full h-full p-2"
          style={{ opacity: locked ? 0.7 : 1, transition: 'opacity 0.2s ease' }}
        />
      </div>
    </div>
  );
}
