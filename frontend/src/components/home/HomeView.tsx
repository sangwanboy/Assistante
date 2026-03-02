import { ActiveDialogue } from './ActiveDialogue';
import { ActiveTasks } from './ActiveTasks';
import { QuickActions } from './QuickActions';

interface HomeViewProps {
  onViewChange?: (view: string) => void;
}

export function HomeView({ onViewChange }: HomeViewProps = {}) {
  const handleAction = (message: string) => {
    if (message === 'View All Agents' && onViewChange) onViewChange('agents');
  };

  return (
    <div className="flex h-full bg-[#080810] gap-4 p-4">
      {/* Left: Active Dialogue - takes most of the space */}
      <div className="flex-1 min-w-0">
        <ActiveDialogue onAction={() => {}} />
      </div>

      {/* Right: Active Tasks and Quick Actions stacked */}
      <div className="w-80 flex flex-col gap-4 shrink-0">
        <ActiveTasks onAction={handleAction} />
        <QuickActions onAction={() => {}} />
      </div>
    </div>
  );
}
