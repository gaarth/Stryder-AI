import { usePolling, fmtTime, AGENT_COLORS } from '../hooks/useData';
import api from '../services/api';
import './DecisionHistory.css';

export default function DecisionHistory({ limit = 15, onSelect }) {
    const { data } = usePolling(() => api.decisions(limit), 4000);
    const decisions = data?.decisions || [];

    return (
        <div className="panel decision-panel">
            <div className="panel-header">
                <span className="label"><span className="dot"></span>Decision History</span>
                <span style={{ fontSize: 10, color: 'var(--text-muted)' }}>{decisions.length} ENTRIES</span>
            </div>
            <div className="panel-body">
                {decisions.length === 0 && (
                    <div className="no-data">No decisions yet. Run agent loop to generate.</div>
                )}
                {decisions.slice().reverse().map((d, i) => (
                    <div key={d.id || i} className="decision-row" onClick={() => onSelect?.(d)}>
                        <div className="d-time">{fmtTime(d.timestamp)}</div>
                        <div className="d-agent" style={{ color: AGENT_COLORS[d.agent] || 'var(--accent)' }}>
                            {d.agent}
                        </div>
                        <div className="d-type">{d.type?.replace(/_/g, ' ')}</div>
                        <div className="d-conf">{((d.confidence || 0) * 100).toFixed(0)}%</div>
                        <div className={`d-priority p${d.priority || 3}`}>P{d.priority || 3}</div>
                    </div>
                ))}
            </div>
        </div>
    );
}
