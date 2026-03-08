import { usePolling, AGENT_COLORS, confColor } from '../hooks/useData';
import api from '../services/api';
import './AgentPanel.css';

const AGENT_ICONS = {
    Sentinel: '\u25C9',   // ◉
    Strategist: '\u2B23', // ⬣
    Actuary: '\u25B2',    // ▲
    Executor: '\u25A0',   // ■
    Cascade: '\u2B22',    // ⬢
};

const STATUS_MAP = {
    IDLE: { label: 'Monitoring', cls: 'ok' },
    OBSERVING: { label: 'Observing', cls: 'info' },
    REASONING: { label: 'Analyzing', cls: 'warning' },
    DECIDING: { label: 'Planning', cls: 'warning' },
    ACTING: { label: 'Executing', cls: 'ok' },
    LEARNING: { label: 'Learning', cls: 'info' },
    ERROR: { label: 'Error', cls: 'danger' },
};

export default function AgentPanel({ compact = false }) {
    const { data } = usePolling(() => api.agentStatuses(), 3000);
    const agents = data?.agents || [];

    return (
        <div className="panel agent-panel">
            <div className="panel-header">
                <span className="label"><span className="dot"></span>Agent Fleet</span>
                <span className="agent-count">{agents.length} ACTIVE</span>
            </div>
            <div className="panel-body">
                {agents.map(a => {
                    const st = STATUS_MAP[a.status] || STATUS_MAP.IDLE;
                    const color = AGENT_COLORS[a.name] || 'var(--accent)';
                    const isThinking = ['OBSERVING', 'REASONING', 'DECIDING', 'ACTING'].includes(a.status);
                    return (
                        <div key={a.name} className={`agent-card ${isThinking ? 'thinking' : ''}`} style={{ '--agent-color': color }}>
                            <div className="agent-icon">{AGENT_ICONS[a.name] || '\u25CF'}</div>
                            <div className="agent-info">
                                <div className="agent-name-row">
                                    <span className="agent-name">{a.name}</span>
                                    <span className={`status-badge ${st.cls}`}>{st.label}</span>
                                </div>
                                <div className="agent-role">{a.role || 'Agent'}</div>
                                {isThinking && <div className="thinking-bar"></div>}
                                {!compact && (
                                    <div className="agent-meta">
                                        <span>Conf: {((a.confidence || 0) * 100).toFixed(0)}%</span>
                                        <div className="confidence-bar">
                                            <div className="fill" style={{
                                                width: `${(a.confidence || 0) * 100}%`,
                                                background: confColor(a.confidence || 0),
                                            }}></div>
                                        </div>
                                    </div>
                                )}
                            </div>
                        </div>
                    );
                })}
            </div>
        </div>
    );
}
