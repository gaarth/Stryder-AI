/**
 * STRYDER AI — Supabase Realtime Manager
 * ========================================
 * Subscribes to Supabase Realtime channels for live updates.
 * Falls back to polling if connection drops.
 * Gracefully disables if Supabase env vars are not configured.
 *
 * Usage:
 *   import { useRealtimeStore } from '../lib/realtime';
 *   const { shipments, events, learningLogs, cascadeAlerts, metrics, connected } = useRealtimeStore();
 */
import { useEffect, useRef, useState, useCallback } from 'react';
import { supabase } from './supabaseClient';

/**
 * Custom hook that subscribes to all realtime tables.
 * Returns live data + connection status.
 * Falls back to polling every 10s if realtime drops.
 * Returns empty state if Supabase is not configured.
 */
export function useRealtimeStore() {
    const [shipments, setShipments] = useState([]);
    const [events, setEvents] = useState([]);
    const [scenarioHistory, setScenarioHistory] = useState([]);
    const [learningLogs, setLearningLogs] = useState([]);
    const [cascadeAlerts, setCascadeAlerts] = useState([]);
    const [metrics, setMetrics] = useState([]);
    const [connected, setConnected] = useState(false);
    const channelsRef = useRef([]);
    const pollTimerRef = useRef(null);

    // ─── INITIAL FETCH ───
    const fetchAll = useCallback(async () => {
        if (!supabase) return;
        try {
            const [shipRes, evtRes, scnRes, lrnRes, casRes, metRes] = await Promise.all([
                supabase.from('shipments').select('*').order('id'),
                supabase.from('simulation_events').select('*').order('id', { ascending: false }).limit(50),
                supabase.from('scenario_history').select('*').order('id', { ascending: false }).limit(20),
                supabase.from('agent_learning_logs').select('*').order('id', { ascending: false }).limit(50),
                supabase.from('cascade_alerts').select('*').order('id', { ascending: false }).limit(20),
                supabase.from('system_metrics').select('*').order('id', { ascending: false }).limit(100),
            ]);
            if (shipRes.data) setShipments(shipRes.data);
            if (evtRes.data) setEvents(evtRes.data);
            if (scnRes.data) setScenarioHistory(scnRes.data);
            if (lrnRes.data) setLearningLogs(lrnRes.data);
            if (casRes.data) setCascadeAlerts(casRes.data);
            if (metRes.data) setMetrics(metRes.data);
        } catch (e) {
            console.error('[REALTIME] Fetch error:', e);
        }
    }, []);

    // ─── SUBSCRIBE ───
    useEffect(() => {
        if (!supabase) {
            console.info('[REALTIME] Supabase not configured — realtime disabled');
            return;
        }

        fetchAll();

        // Shipments channel
        const shipCh = supabase
            .channel('shipments-changes')
            .on('postgres_changes', { event: '*', schema: 'public', table: 'shipments' }, (payload) => {
                if (payload.eventType === 'INSERT') {
                    setShipments(prev => [...prev, payload.new]);
                } else if (payload.eventType === 'UPDATE') {
                    setShipments(prev => prev.map(s => s.id === payload.new.id ? payload.new : s));
                } else if (payload.eventType === 'DELETE') {
                    setShipments(prev => prev.filter(s => s.id !== payload.old.id));
                }
            })
            .subscribe((status) => {
                setConnected(status === 'SUBSCRIBED');
            });

        // Events channel
        const evtCh = supabase
            .channel('events-changes')
            .on('postgres_changes', { event: 'INSERT', schema: 'public', table: 'simulation_events' }, (payload) => {
                setEvents(prev => [payload.new, ...prev].slice(0, 50));
            })
            .subscribe();

        // Scenario history channel
        const scnCh = supabase
            .channel('scenarios-changes')
            .on('postgres_changes', { event: 'INSERT', schema: 'public', table: 'scenario_history' }, (payload) => {
                setScenarioHistory(prev => [payload.new, ...prev].slice(0, 20));
            })
            .subscribe();

        // Learning logs channel
        const lrnCh = supabase
            .channel('learning-changes')
            .on('postgres_changes', { event: 'INSERT', schema: 'public', table: 'agent_learning_logs' }, (payload) => {
                setLearningLogs(prev => [payload.new, ...prev].slice(0, 50));
            })
            .subscribe();

        // Cascade alerts channel
        const casCh = supabase
            .channel('cascade-changes')
            .on('postgres_changes', { event: '*', schema: 'public', table: 'cascade_alerts' }, (payload) => {
                if (payload.eventType === 'INSERT') {
                    setCascadeAlerts(prev => [payload.new, ...prev].slice(0, 20));
                } else if (payload.eventType === 'UPDATE') {
                    setCascadeAlerts(prev => prev.map(a => a.id === payload.new.id ? payload.new : a));
                }
            })
            .subscribe();

        // Metrics channel
        const metCh = supabase
            .channel('metrics-changes')
            .on('postgres_changes', { event: 'INSERT', schema: 'public', table: 'system_metrics' }, (payload) => {
                setMetrics(prev => [payload.new, ...prev].slice(0, 100));
            })
            .subscribe();

        channelsRef.current = [shipCh, evtCh, scnCh, lrnCh, casCh, metCh];

        // ─── FALLBACK POLLING (every 10s if connection drops) ───
        pollTimerRef.current = setInterval(() => {
            const anyDisconnected = channelsRef.current.some(ch => ch.state !== 'joined');
            if (anyDisconnected) {
                console.warn('[REALTIME] Connection lost, polling fallback...');
                fetchAll();
            }
        }, 10000);

        // ─── CLEANUP ───
        return () => {
            channelsRef.current.forEach(ch => supabase.removeChannel(ch));
            channelsRef.current = [];
            if (pollTimerRef.current) clearInterval(pollTimerRef.current);
        };
    }, [fetchAll]);

    return {
        shipments,
        events,
        scenarioHistory,
        learningLogs,
        cascadeAlerts,
        metrics,
        connected,
        refetch: fetchAll,
    };
}

/**
 * Hook to subscribe to a single table for simpler use cases.
 * Returns empty data if Supabase is not configured.
 */
export function useRealtimeTable(tableName, options = {}) {
    const [data, setData] = useState([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        if (!supabase) { setLoading(false); return; }

        const fetchData = async () => {
            const { data: rows, error } = await supabase
                .from(tableName)
                .select('*')
                .order('id', { ascending: options.ascending ?? false })
                .limit(options.limit ?? 50);
            if (!error && rows) setData(rows);
            setLoading(false);
        };
        fetchData();

        const ch = supabase
            .channel(`rt-${tableName}`)
            .on('postgres_changes', { event: '*', schema: 'public', table: tableName }, (payload) => {
                if (payload.eventType === 'INSERT') {
                    setData(prev => options.ascending !== false ? [...prev, payload.new] : [payload.new, ...prev]);
                } else if (payload.eventType === 'UPDATE') {
                    setData(prev => prev.map(r => r.id === payload.new.id ? payload.new : r));
                } else if (payload.eventType === 'DELETE') {
                    setData(prev => prev.filter(r => r.id !== payload.old.id));
                }
            })
            .subscribe();

        return () => supabase.removeChannel(ch);
    }, [tableName]);

    return { data, loading };
}
