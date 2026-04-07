import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Terminal } from 'lucide-react';

interface AuditTerminalProps {
  content: string;
}

const AuditTerminal: React.FC<AuditTerminalProps> = ({ content }) => {
  return (
    <div className="flex flex-col h-full bg-slate-900/50 rounded-lg border border-brand-accent overflow-hidden font-mono shadow-xl">
      <div className="flex items-center justify-between px-4 py-2 bg-brand-accent/50 border-b border-brand-accent">
        <div className="flex items-center gap-2">
          <Terminal size={14} className="text-brand-success" />
          <span className="text-[10px] uppercase font-bold tracking-widest text-slate-400">Simulation Audit (simulation_audit.md)</span>
        </div>
        <div className="flex gap-1.5">
          <div className="w-2.5 h-2.5 rounded-full bg-slate-700" />
          <div className="w-2.5 h-2.5 rounded-full bg-slate-700" />
          <div className="w-2.5 h-2.5 rounded-full bg-brand-success/50" />
        </div>
      </div>
      
      <div className="flex-1 overflow-auto p-6 custom-scrollbar bg-brand-bg/20">
        <div className="max-w-none prose prose-invert prose-brand prose-slate">
          <ReactMarkdown 
            remarkPlugins={[remarkGfm]}
            components={{
              h1: (props) => <h1 className="text-2xl font-black text-brand-success uppercase tracking-tighter mt-2 mb-6 border-b-2 border-brand-success/20 pb-2 flex items-center gap-2" {...props} />,
              h2: (props) => <h2 className="text-lg font-bold text-brand-success uppercase tracking-tighter mt-8 mb-4 flex items-center gap-2" {...props} />,
              h3: (props) => <h3 className="text-md font-bold text-slate-400 uppercase tracking-widest mt-6 mb-2" {...props} />,
              p: (props) => <p className="text-sm text-slate-300 leading-relaxed mb-4" {...props} />,
              strong: (props) => <strong className="text-brand-success font-bold" {...props} />,
              code: ({ inline, ...props }: { inline?: boolean } & React.HTMLAttributes<HTMLElement>) =>
                inline 
                  ? <code className="bg-brand-accent/40 px-1.5 py-0.5 rounded text-brand-success/90 text-[13px]" {...props} />
                  : <div className="relative group my-6">
                      <pre className="bg-slate-950 p-4 rounded-md border border-brand-accent/50 overflow-x-auto scrollbar-thin scrollbar-thumb-brand-accent shadow-inner">
                        <code className="text-xs text-brand-success/80 block leading-5" {...props} />
                      </pre>
                    </div>,
              table: (props) => (
                <div className="overflow-x-auto my-6 border border-brand-accent rounded-lg">
                  <table className="w-full border-collapse text-left" {...props} />
                </div>
              ),
              thead: (props) => <thead className="bg-brand-accent/30 text-brand-success uppercase text-[10px] font-black tracking-widest" {...props} />,
              th: (props) => <th className="p-3 border-b border-brand-accent" {...props} />,
              td: (props) => <td className="p-3 border-b border-brand-accent/30 text-sm text-slate-400 font-medium" {...props} />,
              hr: (props) => <hr className="border-brand-accent my-10 opacity-50" {...props} />,
              ul: (props) => <ul className="list-disc list-inside space-y-2 mb-4 text-slate-400 text-sm" {...props} />,
              li: (props) => <li className="hover:text-slate-200 transition-colors" {...props} />,
            }}
          >
            {content || "Reading simulation audit data..."}
          </ReactMarkdown>
        </div>
      </div>
    </div>
  );
};

export default AuditTerminal;
