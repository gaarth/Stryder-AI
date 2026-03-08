import { useState, useEffect } from 'react';
import api from '../services/api';
import './StatusStrip.css';

export default function StatusStrip() {
    const [data, setData] = useState(null);
    const [mode, setMode] = useState(true);
    const [time, setTime] = useState(new Date());

    useEffect(() => {
        const load = () => {
            api.health().then(r => setData(r)).catch(() => { });
            api.getMode().then(r => setMode(r.auto_mode)).catch(() => { });
        };
        load();
        const id = setInterval(load, 4000);
        const tid = setInterval(() => setTime(new Date()), 1000);
        return () => { clearInterval(id); clearInterval(tid); };
    }, []);

    const sim = data?.simulation || {};

    return (
        <div className="status-strip">
            <div className="ss-left">
                <span className="ss-brand">STRYDER</span>
                <span className="ss-tag">AI OPS</span>
                <span className="ss-sep">│</span>
                <span className="ss-item">SIM: {sim.sim_time?.split('T')[1]?.slice(0, 8) || '00:00:00'}</span>
                <span className="ss-sep">│</span>
                <span className="ss-item">TICK: {sim.tick_count || 0}</span>
                <span className="ss-sep">│</span>
                <span className="ss-item">SHIPMENTS: {sim.shipments || 0}</span>
                <span className="ss-sep">│</span>
                <span className="ss-item">{'CHAOS: '}{sim.active_chaos || 0}</span>
            </div>
            <div className="ss-right">
                <span className={`ss-mode ${mode ? 'auto' : 'manual'}`}>{mode ? 'AUTO' : 'MANUAL'}</span>
                <span className="ss-clock">{time.toLocaleTimeString('en-GB', { hour12: false })}</span>
            </div>
        </div>
    );
}
