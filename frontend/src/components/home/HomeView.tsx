import { ActiveDialogue } from './ActiveDialogue';
import { ActiveTasks } from './ActiveTasks';

export function HomeView() {
  const handleAction = (message: string) => {
    // Action handler for child components
    console.log(message);
  };

  return (
    <div className="flex h-full bg-[#080810] gap-4 p-4">
      {/* Left: Active Dialogue - takes most of the space */}
      <div className="flex-1 min-w-0">
        <ActiveDialogue onAction={handleAction} />
      </div>

      {/* Right: Active Tasks and Quick Actions stacked */}
      <div className="w-80 flex flex-col gap-4 shrink-0">
        <ActiveTasks onAction={handleAction} />
      </div>
    </div>
  );
}
