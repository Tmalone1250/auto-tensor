import React, { useState } from 'react';
import { LayoutDashboard, ShieldAlert, Activity, Menu, X, ChevronRight } from 'lucide-react';

interface SidebarProps {
  activeTab: string;
  setActiveTab: (tab: string) => void;
}

const Sidebar: React.FC<SidebarProps> = ({ activeTab, setActiveTab }) => {
  const [isOpen, setIsOpen] = useState(false);

  const navItems = [
    { id: 'missions', label: 'Missions', icon: LayoutDashboard },
    { id: 'status', label: 'Miner Status', icon: Activity },
    { id: 'health', label: 'System Health', icon: ShieldAlert },
  ];

  const toggleSidebar = () => setIsOpen(!isOpen);

  return (
    <>
      {/* Mobile Toggle */}
      <button 
        onClick={toggleSidebar}
        className="fixed top-4 left-4 z-50 p-2 bg-brand-accent rounded-md md:hidden"
      >
        {isOpen ? <X size={20} /> : <Menu size={20} />}
      </button>

      {/* Sidebar Container */}
      <aside className={`
        fixed inset-y-0 left-0 z-40 w-64 bg-brand-bg border-r border-brand-accent transform transition-transform duration-300 ease-in-out
        ${isOpen ? 'translate-x-0' : '-translate-x-full'}
        md:translate-x-0 md:static md:inset-0
      `}>
        <div className="flex flex-col h-full p-4">
          <div className="flex items-center gap-2 mb-8 px-2">
            <div className="w-8 h-8 bg-brand-success rounded-sm flex items-center justify-center">
              <span className="text-brand-bg font-bold text-xs">AT</span>
            </div>
            <h1 className="text-xl font-bold tracking-tighter">AUTO-TENSOR</h1>
          </div>

          <nav className="flex-1 space-y-1">
            {navItems.map((item) => (
              <button
                key={item.id}
                onClick={() => {
                  setActiveTab(item.id);
                  setIsOpen(false);
                }}
                className={`
                  w-full flex items-center justify-between px-3 py-2.5 rounded-md transition-colors
                  ${activeTab === item.id 
                    ? 'bg-brand-accent text-brand-success border-l-2 border-brand-success' 
                    : 'hover:bg-brand-accent/50 text-slate-400'}
                `}
              >
                <div className="flex items-center gap-3">
                  <item.icon size={18} />
                  <span className="text-sm font-medium">{item.label}</span>
                </div>
                {activeTab === item.id && <ChevronRight size={14} />}
              </button>
            ))}
          </nav>

          <div className="mt-auto p-3 bg-brand-accent/30 rounded-lg border border-brand-accent/50">
            <div className="flex items-center gap-2 mb-1">
              <div className="w-2 h-2 rounded-full bg-brand-success animate-pulse" />
              <span className="text-[10px] uppercase font-bold text-slate-500">Node Sync</span>
            </div>
            <p className="text-xs text-slate-300">Sovereign Layer Active</p>
          </div>
        </div>
      </aside>

      {/* Mobile Overlay */}
      {isOpen && (
        <div 
          onClick={toggleSidebar}
          className="fixed inset-0 bg-black/50 backdrop-blur-sm z-30 md:hidden"
        />
      )}
    </>
  );
};

export default Sidebar;
