import { usePolling, shortNum } from '../hooks/useData';
import api from '../services/api';
import './SLAMetrics.css';

export default function SLAMetrics() {
    const { data } = usePolling(() => api.simStats(), 4000);
    const { data: overview } = usePolling(() => api.overview(), 5000);

    const stats = data || {};
    const statuses = stats.shipment_statuses || {};
    const total = stats.total_shipments || 0;
    const atRisk = (statuses.DELAYED || 0) + (statuses.AT_RISK || 0);
    const delivered = statuses.DELIVERED || 0;
    const inTransit = statuses.IN_TRANSIT || 0;

    const metrics = [
        { label: 'ACTIVE SHIPMENTS', value: shortNum(total), accent: true },
        { label: 'IN TRANSIT', value: shortNum(inTransit), accent: false },
        { label: 'DELIVERED', value: shortNum(delivered), accent: false },
        { label: 'AT RISK', value: shortNum(atRisk), cls: atRisk > 0 ? 'danger' : '' },
        { label: 'CARRIERS', value: stats.total_carriers || '--' },
        { label: 'WAREHOUSES', value: stats.total_warehouses || '--' },
        { label: 'CHAOS EVENTS', value: stats.total_chaos_events || 0, cls: stats.total_chaos_events > 0 ? 'warning' : '' },
        { label: 'SIM TICK', value: stats.tick_count || 0 },
    ];

    return (
        <div className="panel sla-panel">
            <div className="panel-header">
                <span className="label"><span className="dot"></span>SLA Health Metrics</span>
                <span style={{ fontSize: 10, color: 'var(--text-muted)' }}>LIVE</span>
            </div>
            <div className="panel-body">
                <div className="metrics-grid">
                    {metrics.map(m => (
                        <div key={m.label} className="metric-cell">
                            <div className={`metric-value ${m.accent ? 'accent' : ''} ${m.cls || ''}`}>
                                {m.value}
                            </div>
                            <div className="metric-label">{m.label}</div>
                        </div>
                    ))}
                </div>
            </div>
        </div>
    );
}
