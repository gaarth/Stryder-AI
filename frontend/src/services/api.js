/**
 * STRYDER AI — API Service
 * Uses relative /api paths in production (triggers Vercel proxy → Render)
 * Uses VITE_BACKEND_URL in development (direct localhost:8000)
 */

// In production, use '' (empty) so requests go to /api/* → Vercel rewrites to Render
// In development, use the env var or fallback to localhost:8000
const BASE = import.meta.env.PROD
    ? ''
    : (import.meta.env.VITE_BACKEND_URL || 'http://localhost:8000');

let _connected = false;

async function request(path, options = {}) {
    const url = `${BASE}${path}`;
    const config = {
        headers: { 'Content-Type': 'application/json' },
        ...options,
    };
    if (config.body && typeof config.body === 'object') {
        config.body = JSON.stringify(config.body);
    }
    try {
        const res = await fetch(url, config);
        if (!res.ok) throw new Error(`API Error ${res.status}: ${path}`);

        // Log first successful connection
        if (!_connected) {
            _connected = true;
            console.log(
                `%c[STRYDER AI] SYSTEM CONNECTED — Backend: ${BASE || 'Vercel Proxy → Render'}`,
                'color: #22d3ee; font-weight: bold; font-size: 14px;'
            );
        }

        return res.json();
    } catch (err) {
        if (!_connected) {
            console.error(
                `%c[STRYDER AI] Connection to backend FAILED: ${err.message}`,
                'color: #ef4444; font-weight: bold;'
            );
        }
        throw err;
    }
}

const api = {
    // Health
    health: () => request('/health'),

    // Dashboard
    overview: () => request('/api/dashboard/overview'),
    mapHubs: () => request('/api/dashboard/map/hubs'),
    mapRoutes: () => request('/api/dashboard/map/routes'),
    mapNetwork: () => request('/api/dashboard/map/network'),

    // Agents
    agentStatuses: () => request('/api/agents/status'),
    agentStatus: (name) => request(`/api/agents/status/${name}`),
    runLoop: (limit = 50) => request('/api/agents/run-loop', { method: 'POST', body: { shipment_limit: limit } }),
    setMode: (auto) => request('/api/agents/mode', { method: 'POST', body: { auto_mode: auto } }),
    getMode: () => request('/api/agents/mode'),
    decisions: (limit = 20) => request(`/api/agents/decisions?limit=${limit}`),
    decisionStats: () => request('/api/agents/decisions/stats'),
    learning: () => request('/api/agents/learning'),
    summary: () => request('/api/agents/summary'),
    events: (limit = 20) => request(`/api/agents/events?limit=${limit}`),

    // Disruption + agent reasoning chain
    disruptAndReason: () => request('/api/agents/disrupt', { method: 'POST' }),

    // Chat
    chat: (message, context = {}) => request('/api/chat/send', { method: 'POST', body: { message, context } }),

    // Simulation
    simStats: () => request('/api/simulation/stats'),
    shipments: (limit = 100, status = '') => request(`/api/simulation/shipments?limit=${limit}${status ? `&status=${status}` : ''}`),
    shipment: (id) => request(`/api/simulation/shipments/${id}`),
    timeline: (id) => request(`/api/simulation/shipments/${id}/timeline`),
    activeChaos: () => request('/api/simulation/chaos/active'),

    // Sim Control
    tick: (mins = 30) => request('/api/simulation/control', { method: 'POST', body: { action: 'tick', value: mins } }),

    // Ops
    reset: () => request('/api/ops/reset', { method: 'POST' }),
    simControl: (data) => request('/api/ops/sim-control', { method: 'POST', body: data }),
};

export default api;
