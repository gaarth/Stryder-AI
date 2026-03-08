import { useState } from 'react';
import { usePolling } from '../hooks/useData';
import { emitScan } from '../hooks/useData';
import api from '../services/api';
import './ChaosPanel.css';

const CHAOS_BUTTONS = [
    { key: 'truck_breakdown', label: 'TRUCK BREAKDOWN', icon: '\u2716' },
    { key: 'warehouse_overload', label: 'WAREHOUSE OVERLOAD', icon: '\u25A6' },
    { key: 'carrier_failure', label: 'CARRIER FAILURE', icon: '\u25CE' },
    { key: 'route_closure', label: 'ROUTE CLOSURE', icon: '\u2573' },
    { key: 'weather_disruption', label: 'WEATHER', icon: '\u2601' },
    { key: 'demand_spike', label: 'DEMAND SPIKE', icon: '\u25B2' },
    { key: 'port_congestion', label: 'PORT CONGESTION', icon: '\u2693' },
];

export default function ChaosPanel() {
    const [injecting, setInjecting] = useState(null);
    const [lastEvent, setLastEvent] = useState(null);
    const { data: activeData, refresh } = usePolling(() => api.activeChaos(), 5000);
    const activeEvents = activeData?.events || [];

    const inject = async (type) => {
        setInjecting(type);
        try {
            const result = await api.injectChaos(type);
            setLastEvent(result);
            emitScan();
            refresh();
        } catch (e) {
            console.error(e);
        } finally {
            setTimeout(() => setInjecting(null), 600);
        }
    };

    return (
        <div className="panel chaos-panel">
            <div className="panel-header">
                <span className="label"><span className="dot" style={{ background: 'var(--status-danger)', boxShadow: '0 0 6px var(--status-danger)' }}></span>Inject Disruption</span>
                <span className="active-count">{activeEvents.length} ACTIVE</span>
            </div>
            <div className="panel-body">
                <div className="chaos-grid">
                    {CHAOS_BUTTONS.map(b => (
                        <button key={b.key} className={`chaos-btn ${injecting === b.key ? 'injecting' : ''}`}
                            onClick={() => inject(b.key)} disabled={!!injecting}>
                            <span className="chaos-icon">{b.icon}</span>
                            <span className="chaos-label">{b.label}</span>
                        </button>
                    ))}
                </div>
                {lastEvent && (
                    <div className="last-event">
                        <span className="le-label">LAST:</span>
                        <span className="le-name">{lastEvent.name}</span>
                        <span className={`le-sev sev-${(lastEvent.severity || '').toLowerCase()}`}>{lastEvent.severity}</span>
                    </div>
                )}
                {activeEvents.length > 0 && (
                    <div className="active-list">
                        {activeEvents.slice(0, 4).map(e => (
                            <div key={e.chaos_id} className="active-event">
                                <span className="ae-id">{e.chaos_id}</span>
                                <span className="ae-name">{e.name}</span>
                                <span className={`ae-sev sev-${(e.severity || '').toLowerCase()}`}>{e.severity}</span>
                            </div>
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
}
