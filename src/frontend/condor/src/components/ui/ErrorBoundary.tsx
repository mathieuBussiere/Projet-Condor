import React from "react";
import Alert from "./Alert";

type Props = { children: React.ReactNode };

type State = { hasError: boolean; error: Error | null };

class ErrorBoundary extends React.Component<Props, State> {
  state: State = { hasError: false, error: null };

  static getDerivedStateFromError(error: Error) {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    // Prefer console for now — replace with remote logging (Sentry) if available
    console.error("Uncaught error in component tree:", error, info);
  }

  handleReload = () => {
    // Hard reload is the safest way to recover from unknown render errors
    window.location.reload();
  };

  render() {
    if (this.state.hasError) {
      const message = this.state.error?.message ?? "Une erreur est survenue.";
      return (
        <div className="fixed inset-0 z-[2000] flex items-center justify-center bg-black/60 p-4">
          <div className="bg-slate-900 text-slate-200 rounded-lg shadow-lg p-6 max-w-lg w-full">
            <h2 className="text-lg font-bold mb-2">Oups — quelque chose s'est mal passé</h2>
            <p className="mb-4 text-sm">{message}</p>
            <div className="flex gap-2">
              <button
                onClick={this.handleReload}
                className="px-3 py-1.5 bg-sky-600 rounded hover:bg-sky-500"
              >
                Reload
              </button>
              <button
                onClick={() => this.setState({ hasError: false, error: null })}
                className="px-3 py-1.5 bg-zinc-700 rounded hover:bg-zinc-600"
              >
                Try again
              </button>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children as React.ReactElement;
  }
}

export default ErrorBoundary;
