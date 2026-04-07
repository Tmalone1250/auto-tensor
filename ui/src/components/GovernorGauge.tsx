import React from 'react';
import { ShieldCheck, ShieldAlert } from 'lucide-react';

interface GovernorGaugeProps {
  remaining: number;
  limit: number;
}

const GovernorGauge: React.FC<GovernorGaugeProps> = ({ remaining, limit }) => {
  const percentage = Math.min(100, (remaining / limit) * 100);
  const isCritical = remaining < 750; // Safety floor

  const getColor = () => {
    if (remaining < 750) return 'text-brand-danger';
    if (remaining < 1500) return 'text-brand-warning';
    return 'text-brand-success';
  };

  const getBgColor = () => {
    if (remaining < 750) return 'stroke-brand-danger';
    if (remaining < 1500) return 'stroke-brand-warning';
    return 'stroke-brand-success';
  };

  return (
    <div className="bg-brand-bg/50 border border-brand-accent p-6 rounded-lg shadow-lg relative overflow-hidden group">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-[10px] uppercase font-bold text-slate-500 tracking-[0.2em]">GitHub Governor</h3>
          <p className="text-xl font-bold font-mono tracking-tighter">SAFETY FLOOR</p>
        </div>
        {isCritical ? (
          <ShieldAlert className="text-brand-danger animate-pulse" size={24} />
        ) : (
          <ShieldCheck className="text-brand-success" size={24} />
        )}
      </div>

      <div className="flex flex-col items-center justify-center py-6 relative">
        {/* Simple Progress Bar for Industrial Look */}
        <div className="w-full bg-slate-900 h-3 rounded-full overflow-hidden border border-brand-accent/50 mb-4">
          <div 
            className={`h-full transition-all duration-1000 ease-out ${getBgColor().replace('stroke-', 'bg-')}`}
            style={{ width: `${percentage}%` }}
          />
        </div>

        <div className="flex justify-between w-full mb-1">
          <span className="text-[10px] text-slate-500 font-bold uppercase">Requests Remaining</span>
          <span className={`text-lg font-mono font-bold ${getColor()}`}>
            {remaining.toLocaleString()}
          </span>
        </div>
        <div className="flex justify-between w-full border-t border-brand-accent/30 pt-1">
          <span className="text-[10px] text-slate-500 font-bold uppercase transition-colors group-hover:text-amber-500">Floor Threshold</span>
          <span className="text-xs font-mono font-bold text-slate-400">750 (15%)</span>
        </div>
      </div>

      {isCritical && (
        <div className="absolute inset-0 bg-brand-danger/5 pointer-events-none animate-pulse" />
      )}
    </div>
  );
};

export default GovernorGauge;
