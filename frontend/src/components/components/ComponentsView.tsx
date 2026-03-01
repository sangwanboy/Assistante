import { useState } from 'react';
import { AnimatedSidebar } from '../sidebar/AnimatedSidebar';

export function ComponentsView() {
  const [activeView, setActiveView] = useState('components');

  const handleViewChange = (view: string) => {
    if (view !== 'components') {
      // Navigate to the main app for other views
      window.location.href = '/';
      return;
    }
    setActiveView(view);
  };

  return (
    <div className="h-screen flex bg-[#080810]">
      <AnimatedSidebar
        activeView={activeView}
        onViewChange={handleViewChange}
      />

      <div className="flex flex-col min-w-0 flex-1">
        <div className="flex-1 overflow-y-auto p-8">
          <div className="max-w-7xl mx-auto">
            <h1 className="text-4xl font-bold mb-8 text-gray-100">Components</h1>
            <p className="text-gray-400 mb-8">
              This is a separate components route, completely independent from the main application.
            </p>
            
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              <div className="bg-[#0a0a14] border border-[#1a1a2e] rounded-lg p-6">
                <h2 className="text-xl font-semibold mb-3 text-gray-200">Component Library</h2>
                <p className="text-gray-400 text-sm">
                  Browse and explore available UI components.
                </p>
              </div>
              
              <div className="bg-[#0a0a14] border border-[#1a1a2e] rounded-lg p-6">
                <h2 className="text-xl font-semibold mb-3 text-gray-200">Documentation</h2>
                <p className="text-gray-400 text-sm">
                  Learn how to use and customize components.
                </p>
              </div>
              
              <div className="bg-[#0a0a14] border border-[#1a1a2e] rounded-lg p-6">
                <h2 className="text-xl font-semibold mb-3 text-gray-200">Examples</h2>
                <p className="text-gray-400 text-sm">
                  See components in action with live examples.
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
