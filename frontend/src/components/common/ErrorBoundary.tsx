import { Component, ErrorInfo, ReactNode } from 'react';

interface Props {
  children: ReactNode;
  fallbackTitle?: string;
}

interface State {
  hasError: boolean;
  message: string;
}

/**
 * Per-section error boundary. A single failing component shouldn't
 * blank the dashboard — the rest of the page keeps rendering, the
 * broken section degrades gracefully with an inline error card.
 */
class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false, message: '' };

  static getDerivedStateFromError(err: Error): State {
    return { hasError: true, message: err.message || 'Unknown error' };
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    // eslint-disable-next-line no-console
    console.error('Section error:', error, info.componentStack);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div
          className="card"
          style={{ borderColor: '#FBBFBA', background: 'var(--red-50)' }}
        >
          <div className="eyebrow" style={{ color: 'var(--red-600)' }}>
            {this.props.fallbackTitle ?? 'Section unavailable'}
          </div>
          <div className="body-sm" style={{ marginTop: 4 }}>
            {this.state.message}
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}

export default ErrorBoundary;
