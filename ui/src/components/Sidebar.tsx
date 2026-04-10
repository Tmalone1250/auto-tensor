import React, { useState } from 'react';
import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  ShieldAlert,
  Activity,
  Menu,
  X,
  ChevronRight,
  ClipboardCheck,
  BrainCircuit,
  Terminal,
  TerminalSquare,
  Zap
} from 'lucide-react';

const Sidebar: React.FC = () => {
  const [isOpen, setIsOpen] = useState(false);

  const navItems = [
    { id: 'intelligence', label: 'Intelligence', icon: BrainCircuit, path: '/intelligence' },
    { id: 'engineering', label: 'Engineering', icon: Terminal, path: '/engineering' },
    { id: 'quality', label: 'Quality', icon: ClipboardCheck, path: '/quality' },
    { id: 'terminal', label: 'Shell', icon: TerminalSquare, path: '/terminal' },
  ];

  const toggleSidebar = () => setIsOpen(!isOpen);

  return (
    <>
      <button
        onClick={toggleSidebar}
        className="fixed top-4 left-4 z-50 p-2 bg-brand-accent rounded-md md:hidden"
      >
        {isOpen ? <X size={20} /> : <Menu size={20} />}
      </button>

      <aside className={`
        fixed inset-y-0 left-0 z-40 w-64 bg-brand-bg border-r border-brand-accent transform transition-transform duration-300 ease-in-out
        ${isOpen ? 'translate-x-0' : '-translate-x-full'}
        md:translate-x-0 md:static md:inset-0
      `}>
        <div className="flex flex-col h-full p-4">
          <NavLink to="/" className="flex items-center gap-2 mb-8 px-2">
            <div className="w-8 h-8 bg-brand-success rounded-sm flex items-center justify-center">
              <span className="text-brand-bg font-bold text-xs">AT</span>
            </div>
            <h1 className="text-xl font-bold tracking-tighter">AUTO-TENSOR</h1>
          </NavLink>

          <nav className="flex-1 space-y-2">
            {navItems.map((item) => (
              <NavLink
                key={item.id}
                to={item.path}
                onClick={() => setIsOpen(false)}
                className={({ isActive }) => `
                  w-full flex items-center justify-between px-3 py-3 rounded-md transition-all
                  ${isActive
                    ? 'bg-brand-accent/40 text-brand-success border-l-4 border-brand-success shadow-[0_0_15px_rgba(16,185,129,0.1)]'
                    : 'hover:bg-brand-accent/20 text-slate-400'}
                `}
              >
                <div className="flex items-center gap-3">
                  <item.icon size={18} />
                  <span className="text-xs font-black uppercase tracking-widest">{item.label}</span>
                </div>
                <ChevronRight size={14} className="opacity-30" />
              </NavLink>
            ))}
          </nav>

          <div className="mt-auto p-4 bg-brand-accent/10 rounded-lg border border-brand-accent/30">
            <div className="flex items-center gap-2 mb-2">
              <div className="w-2 h-2 rounded-full bg-brand-success animate-pulse" />
              <span className="text-[9px] uppercase font-black text-slate-500 tracking-[0.2em]">Sovereign Protocol</span>
            </div>
            <p className="text-[10px] text-slate-400 font-mono italic leading-tight">
              Awaiting Engineering Promotion...
            </p>
          </div>
        </div>
      </aside>

      {/* Mobile Overlay */}
      {isOpen && (
        <div
          onClick={toggleSidebar}
          className="fixed inset-0 bg-black/70 backdrop-blur-sm z-30 md:hidden"
        />
      )}
    </>
  );
};

export default Sidebar;
