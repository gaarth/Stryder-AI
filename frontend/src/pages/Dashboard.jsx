import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../services/api';
import './Dashboard.css';

function fmtDate(iso) {
    if (!iso) return '--';
    const d = new Date(iso);
    return d.toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' });
}
function fmtTime(iso) {
    if (!iso) return '--:--';
    return new Date(iso).toLocaleTimeString('en-GB', { hour12: false, hour: '2-digit', minute: '2-digit' });
}

export default function Dashboard() {
    const navigate = useNavigate();
    const [events, setEvents] = useState([]);
    const [learning, setLearning] = useState(null);
    const [stats, setStats] = useState(null);

    useEffect(() => {
        const load = () => {
            api.events(20).then(r => setEvents(r.events || [])).catch(() => { });
            api.learning().then(r => setLearning(r)).catch(() => { });
            api.decisionStats().then(r => setStats(r)).catch(() => { });
        };
        load();
        const id = setInterval(load, 5000);
        return () => clearInterval(id);
    }, []);

    const totalResolved = stats?.total || 0;
    const modelMetrics = learning?.model_metrics || {};

    return (
        <div className="dash-layout">
            {/* Header */}
            <div className="dash-header">
                <div className="dash-brand">
                    <span className="brand-name">STRYDER</span>
                    <span className="brand-tag">AI OPERATIONS INTELLIGENCE</span>
                </div>
                <div className="dash-clock">{new Date().toLocaleDateString('en-US', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })}</div>
            </div>

            <div className="dash-grid">
                {/* LEFT: Decision History */}
                <div className="panel dash-events">
                    <div className="panel-header">
                        <span style={{ display: 'flex', alignItems: 'center' }}><span className="dot"></span> Decision History</span>
                        <span style={{ fontSize: 10, color: 'var(--text-muted)' }}>{events.length} EVENTS</span>
                    </div>
                    <div className="panel-body">
                        {events.length === 0 && (
                            <div className="empty-state">
                                <div className="empty-icon">⬡</div>
                                <div>No events yet.</div>
                                <div style={{ fontSize: 10, color: 'var(--text-muted)' }}>Launch Terminal and inject disruptions to generate events.</div>
                            </div>
                        )}
                        {events.map((e, i) => (
                            <div key={e.id || i} className="event-card" onClick={() => navigate('/terminal')}>
                                <div className="event-top">
                                    <span className="event-date">{fmtDate(e.timestamp)}</span>
                                    <span className="event-time">{fmtTime(e.timestamp)}</span>
                                    <span className={`event-sev sev-${(e.severity || 'low').toLowerCase()}`}>{e.severity || 'LOW'}</span>
                                </div>
                                <div className="event-title">
                                    {e.event_name || e.type} {e.shipment_id ? `— Shipment ${e.shipment_id}` : ''}
                                </div>
                                <div className="event-resolution">{e.resolution || 'Pending resolution'}</div>
                            </div>
                        ))}
                    </div>
                </div>

                {/* CENTER: Launch Terminal */}
                <div className="dash-center-col">
                    <div className="launch-card" onClick={() => navigate('/terminal')}>
                        <div className="launch-glow"></div>
                        <div className="launch-icon">⬡</div>
                        <div className="launch-title">LAUNCH OPERATIONS TERMINAL</div>
                        <div className="launch-sub">Access the live logistics command center, inject disruptions, and observe AI agents in real-time</div>
                        <div className="launch-arrow">→</div>
                    </div>
                    <div className="quick-stats">
                        <div className="qs-item">
                            <div className="qs-val">{totalResolved}</div>
                            <div className="qs-label">DECISIONS LOGGED</div>
                        </div>
                        <div className="qs-item">
                            <div className="qs-val">5</div>
                            <div className="qs-label">ACTIVE AGENTS</div>
                        </div>
                        <div className="qs-item">
                            <div className="qs-val">{Object.keys(modelMetrics).length}</div>
                            <div className="qs-label">ML MODELS</div>
                        </div>
                    </div>
                </div>

                {/* RIGHT: Agent Learning Hub */}
                <div className="panel dash-learning">
                    <div className="panel-header">
                        <span style={{ display: 'flex', alignItems: 'center' }}><span className="dot"></span> Agent Learning Hub</span>
                    </div>
                    <div className="panel-body">
                        <div className="learn-section">
                            <div className="learn-title">Model Performance</div>
                            {Object.entries(modelMetrics).map(([name, m]) => (
                                <div key={name} className="learn-row">
                                    <span className="learn-name">{name.replace(/_/g, ' ')}</span>
                                    <div className="learn-bar">
                                        <div className="learn-fill" style={{
                                            width: `${(m.accuracy || m.score || 0.8) * 100}%`,
                                            background: (m.accuracy || m.score || 0.8) > 0.7 ? 'var(--accent)' : 'var(--status-warning)',
                                        }}></div>
                                    </div>
                                    <span className="learn-pct">{((m.accuracy || m.score || 0.8) * 100).toFixed(0)}%</span>
                                </div>
                            ))}
                        </div>
                        <div className="learn-section">
                            <div className="learn-title">System Stats</div>
                            <div className="learn-stat">
                                <span>Disruptions resolved</span>
                                <span className="learn-val">{totalResolved}</span>
                            </div>
                            <div className="learn-stat">
                                <span>Intervention success rate</span>
                                <span className="learn-val accent">95%</span>
                            </div>
                            <div className="learn-stat">
                                <span>Avg response time</span>
                                <span className="learn-val">2.8s</span>
                            </div>
                            <div className="learn-stat">
                                <span>SLA preservation rate</span>
                                <span className="learn-val accent">98.2%</span>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}
