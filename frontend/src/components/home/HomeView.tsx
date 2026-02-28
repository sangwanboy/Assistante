import { useState } from 'react';
import { ActiveDialogue } from './ActiveDialogue';
import { ActiveTasks } from './ActiveTasks';
import { QuickActions } from './QuickActions';
import { Clock, Bot, Zap, FileText } from 'lucide-react';

const recentEvents = [
  { icon: Bot, text: 'Analyst Agent completed data summary', time: '2m ago', color: 'text-indigo-400', bg: 'bg-indigo-500/10' },
  { icon: Zap, text: 'Workflow "Daily Digest" triggered', time: '15m ago', color: 'text-orange-400', bg: 'bg-orange-500/10' },
  { icon: FileText, text: 'Document "Q4 Report.pdf" indexed', time: '1h ago', color: 'text-emerald-400', bg: 'bg-emerald-500/10' },
  { icon: Bot, text: 'Support Bot responded to 3 queries', time: '2h ago', color: 'text-purple-400', bg: 'bg-purple-500/10' },
];

export function HomeView() {
  const [lastAction, setLastAction] = useState<string>('Ready');

  return (
    <div className="flex-1 flex flex-col min-h-0 bg-[#080810] overflow-hidden">
      <div className="flex flex-col flex-1 min-h-0 max-w-[1440px] w-full mx-auto px-6 py-5 overflow-hidden">

        <div className="mb-5 flex-shrink-0">
          <h1 className="text-2xl font-bold text-gray-100 tracking-tight">Home</h1>
          <p className="text-sm text-gray-500 mt-0.5">Your AI command center</p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-[1fr_320px] gap-4 flex-1 min-h-0">
          {/* Left: Active Dialogue */}
          <div className="min-h-0 flex flex-col">
            <ActiveDialogue onAction={setLastAction} />
          </div>

          {/* Right: Collapsible cards */}
          <div className="space-y-3 flex flex-col min-h-0 overflow-y-auto pr-0.5">
            <ActiveTasks onAction={setLastAction} />
            <QuickActions onAction={setLastAction} />
          </div>
        </div>

        {/* Activity Feed */}
        <div className="mt-3 bg-[#0e0e1c] rounded-2xl border border-[#1c1c30] overflow-hidden flex-shrink-0">
          <div className="flex items-center gap-2 px-5 py-3 border-b border-[#1c1c30]">
            <Clock className="w-3.5 h-3.5 text-gray-600" />
            <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider">Recent Events</h3>
          </div>
          <div className="flex items-center gap-4 px-4 py-3 overflow-x-auto">
            {recentEvents.map((event, i) => (
              <div
                key={i}
                className="flex items-center gap-2.5 min-w-[240px] px-3 py-2 rounded-xl hover:bg-white/5 transition-colors cursor-pointer"
              >
                <div className={`w-7 h-7 rounded-lg ${event.bg} flex items-center justify-center flex-shrink-0`}>
                  <event.icon className={`w-3.5 h-3.5 ${event.color}`} />
                </div>
                <div className="min-w-0">
                  <p className="text-[12px] font-medium text-gray-300 truncate">{event.text}</p>
                  <p className="text-[10px] text-gray-600">{event.time}</p>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="mt-1.5 mb-0.5 text-[11px] text-center text-gray-700 flex-shrink-0 flex items-center justify-center gap-1.5">
          <span className="w-1 h-1 rounded-full bg-emerald-600"></span>
          Switched to {lastAction}
        </div>
      </div>
    </div>
  );
}
