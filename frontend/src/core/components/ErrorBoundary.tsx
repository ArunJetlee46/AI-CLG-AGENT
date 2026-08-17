import { Component, type ReactNode } from "react";
import { AlertTriangle, RefreshCw } from "lucide-react";
import { Button } from "@/core/components/ui/button";

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false, error: null };

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    console.error("[ErrorBoundary]", error, info.componentStack);
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null });
  };

  render() {
    if (this.state.hasError) {
      return (
        <div className="flex min-h-screen items-center justify-center bg-[var(--background)] p-6">
          <div className="w-full max-w-md rounded-xl border border-[var(--border)] bg-[var(--card)] p-8 text-center shadow-lg">
            <div className="mx-auto mb-4 grid h-14 w-14 place-items-center rounded-full bg-[var(--destructive)]/10">
              <AlertTriangle className="h-7 w-7 text-[var(--destructive)]" />
            </div>
            <h2 className="mb-2 text-lg font-bold text-[var(--foreground)]">Something went wrong</h2>
            <p className="mb-1 text-sm text-[var(--muted-foreground)]">
              The app encountered an unexpected error. You can try reloading or continue using other pages.
            </p>
            {this.state.error && (
              <p className="mb-6 max-h-24 overflow-auto rounded-lg bg-[var(--muted)] p-3 text-left font-mono text-xs text-[var(--muted-foreground)]">
                {this.state.error.message}
              </p>
            )}
            <div className="flex gap-3 justify-center">
              <Button variant="outline" onClick={this.handleReset}>
                <RefreshCw className="mr-2 h-4 w-4" />
                Try Again
              </Button>
              <Button onClick={() => window.location.assign("/")}>
                Go Home
              </Button>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
