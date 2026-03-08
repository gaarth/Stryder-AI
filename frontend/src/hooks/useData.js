import { useState, useEffect, useCallback, useRef } from 'react';
import api from '../services/api';

/** Poll an API endpoint at interval */
export function usePolling(fetcher, interval = 5000) {
    const [data, setData] = useState(null);
    const [error, setError] = useState(null);
    const [loading, setLoading] = useState(true);
    const ref = useRef(fetcher);
    ref.current = fetcher;

    const refresh = useCallback(async () => {
        try {
            const result = await ref.current();
            setData(result);
            setError(null);
        } catch (e) {
            setError(e.message);
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        refresh();
        const id = setInterval(refresh, interval);
        return () => clearInterval(id);
    }, [refresh, interval]);

    return { data, error, loading, refresh };
}

/** Global event bus for scan effect */
const listeners = new Set();
export function emitScan() { listeners.forEach(fn => fn()); }
export function useScanEffect() {
    const [active, setActive] = useState(false);
    useEffect(() => {
        const handler = () => { setActive(true); setTimeout(() => setActive(false), 1500); };
        listeners.add(handler);
        return () => listeners.delete(handler);
    }, []);
    return active;
}

/** Format timestamp */
export function fmtTime(iso) {
    if (!iso) return '--:--:--';
    const d = new Date(iso);
    return d.toLocaleTimeString('en-GB', { hour12: false });
}

export function fmtDate(iso) {
    if (!iso) return '--';
    return new Date(iso).toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' });
}

/** Short number */
export function shortNum(n) {
    if (n == null) return '--';
    if (n >= 1e6) return (n / 1e6).toFixed(1) + 'M';
    if (n >= 1e3) return (n / 1e3).toFixed(1) + 'K';
    return String(n);
}

/** Confidence to color */
export function confColor(c) {
    if (c >= 0.8) return 'var(--status-ok)';
    if (c >= 0.5) return 'var(--status-warning)';
    return 'var(--status-danger)';
}

/** Agent color map */
export const AGENT_COLORS = {
    Sentinel: 'var(--agent-sentinel)',
    Strategist: 'var(--agent-strategist)',
    Actuary: 'var(--agent-actuary)',
    Executor: 'var(--agent-executor)',
    Cascade: 'var(--agent-cascade)',
};
