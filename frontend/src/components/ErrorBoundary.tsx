import { Component, type ReactNode } from 'react';

interface Props { children: ReactNode; }
interface State { error: Error | null; }

export class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error) {
    return { error };
  }

  render() {
    if (this.state.error) {
      return (
        <div className="flex flex-col items-center justify-center h-screen bg-[#080810] text-gray-200 p-8 gap-4">
          <div className="text-red-400 text-lg font-semibold">App crashed — runtime error</div>
          <pre className="bg-[#0e0e1c] border border-red-500/30 rounded-xl p-4 text-xs text-red-300 max-w-2xl w-full overflow-x-auto whitespace-pre-wrap">
            {this.state.error.message}{'\n\n'}{this.state.error.stack}
          </pre>
          <button
            onClick={() => this.setState({ error: null })}
            className="px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-sm"
          >
            Try Again
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}
