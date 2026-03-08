import { Component } from 'react';

export default class ErrorBoundary extends Component {
    constructor(props) {
        super(props);
        this.state = { hasError: false, error: null };
    }
    static getDerivedStateFromError(error) {
        return { hasError: true, error };
    }
    render() {
        if (this.state.hasError) {
            return (
                <div style={{
                    padding: 16, color: '#ff3333', background: '#0a0a0a',
                    border: '1px solid #ff333333', borderRadius: 4,
                    fontFamily: 'monospace', fontSize: 11,
                }}>
                    <div style={{ fontWeight: 700, marginBottom: 4 }}>Component Error</div>
                    <div style={{ color: '#8a8a8a' }}>{this.state.error?.message || 'Unknown error'}</div>
                </div>
            );
        }
        return this.props.children;
    }
}
