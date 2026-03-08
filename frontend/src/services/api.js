/**
 * STRYDER AI — API Service
 * Centralized API client for all backend endpoints
 */
const BASE = import.meta.env.VITE_BACKEND_URL || 'http://localhost:8000';

async function request(path, options = {}) {
    const url = `${BASE}${path}`;
    const config = {
        headers: { 'Content-Type': 'application/json' },
        ...options,
    };
    if (config.body && typeof config.body === 'object') {
        config.body = JSON.stringify(config.body);
    }
    const res = await fetch(url, config);
    if (!res.ok) throw new Error(`API Error ${res.status}: ${path}`);
    return res.json();
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
};

export default api;
