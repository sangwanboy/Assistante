import { useState } from 'react';
import { ActiveDialogue } from './ActiveDialogue';
import { ActiveTasks } from './ActiveTasks';
import { QuickActions } from './QuickActions';
import { Clock, Bot, Zap, FileText } from 'lucide-react';

const recentEvents = [
  { icon: Bot, text: 'Analyst Agent completed data summary', time: '2m ago', color: 'text-blue-500' },
  { icon: Zap, text: 'Workflow "Daily Digest" triggered', time: '15m ago', color: 'text-orange-500' },
  { icon: FileText, text: 'Document "Q4 Report.pdf" indexed', time: '1h ago', color: 'text-emerald-500' },
  { icon: Bot, text: 'Support Bot responded to 3 queries', time: '2h ago', color: 'text-purple-500' },
];

export function HomeView() {
  const [lastAction, setLastAction] = useState<string>('Ready');

  return (
    <div className="flex-1 flex flex-col min-h-0 bg-[#f8f9fa] overflow-hidden">
      <div className="flex flex-col flex-1 min-h-0 max-w-[1400px] w-full mx-auto px-6 py-4 overflow-hidden">
        <h1 className="text-[28px] leading-none font-bold text-gray-900 mb-4 flex-shrink-0">Home</h1>

        <div className="grid grid-cols-1 lg:grid-cols-[1fr_340px] gap-5 flex-1 min-h-0">
          {/* Left: Active Dialogue (large canvas) */}
          <div className="min-h-0 flex flex-col">
            <ActiveDialogue onAction={setLastAction} />
          </div>

          {/* Right: Collapsible cards */}
          <div className="space-y-4 flex flex-col min-h-0 overflow-y-auto pr-1">
            <ActiveTasks onAction={setLastAction} />
            <QuickActions onAction={setLastAction} />
          </div>
        </div>

        {/* Activity Feed */}
        <div className="mt-3 bg-white rounded-2xl border border-gray-200 shadow-sm overflow-hidden flex-shrink-0">
          <div className="flex items-center gap-2 px-5 py-3 border-b border-gray-100">
            <Clock className="w-4 h-4 text-gray-400" />
            <h3 className="text-sm font-bold text-gray-700">Recent Events</h3>
          </div>
          <div className="flex items-center gap-6 px-5 py-3 overflow-x-auto">
            {recentEvents.map((event, i) => (
              <div key={i} className="flex items-center gap-2.5 min-w-[260px] px-3 py-2 rounded-xl hover:bg-gray-50 transition-colors cursor-pointer">
                <div className={`w-7 h-7 rounded-lg bg-gray-50 flex items-center justify-center flex-shrink-0 ${event.color}`}>
                  <event.icon className="w-3.5 h-3.5" />
                </div>
                <div className="min-w-0">
                  <p className="text-[12px] font-medium text-gray-800 truncate">{event.text}</p>
                  <p className="text-[10px] text-gray-400">{event.time}</p>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="mt-1.5 mb-1 text-xs text-center text-gray-400 flex-shrink-0">Switched to {lastAction}</div>
      </div>
    </div>
  );
}
