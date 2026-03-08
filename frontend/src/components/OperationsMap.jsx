import { useEffect, useState, useRef } from 'react';
import api from '../services/api';
import ErrorBoundary from './ErrorBoundary';
import './OperationsMap.css';

const STATUS_CLS = {
    DELIVERED: 'ok', IN_TRANSIT: 'ok', PENDING: 'ok',
    AT_RISK: 'warning', DELAYED: 'danger', REROUTED: 'info',
};

export default function OperationsMap({ onSelectShipment }) {
    const [hubs, setHubs] = useState({});
    const [routes, setRoutes] = useState(null);
    const [shipments, setShipments] = useState([]);
    const mapRef = useRef(null);
    const containerRef = useRef(null);
    const layersRef = useRef({ hubs: [], ships: [], routes: [] });

    // Init map
    useEffect(() => {
        let L;
        const init = async () => {
            L = await import('leaflet');
            await import('leaflet/dist/leaflet.css');

            if (mapRef.current || !containerRef.current) return;

            const map = L.map(containerRef.current, {
                center: [22.5, 79],
                zoom: 5,
                zoomControl: true,
                attributionControl: false,
            });

            // Better styled tile layer
            L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
                maxZoom: 18,
                subdomains: 'abcd',
            }).addTo(map);

            mapRef.current = map;
        };
        init();
        return () => { if (mapRef.current) { mapRef.current.remove(); mapRef.current = null; } };
    }, []);

    // Load hubs + routes once
    useEffect(() => {
        api.mapHubs().then(r => setHubs(r.hubs || {})).catch(() => { });
        api.mapRoutes().then(r => setRoutes(r)).catch(() => { });
    }, []);

    // Poll shipments
    useEffect(() => {
        const load = () => api.shipments(100).then(r => setShipments(r.shipments || [])).catch(() => { });
        load();
        const id = setInterval(load, 6000);
        return () => clearInterval(id);
    }, []);

    // Draw routes
    useEffect(() => {
        const map = mapRef.current;
        if (!map || !routes?.features) return;
        import('leaflet').then(L => {
            layersRef.current.routes.forEach(l => l.remove());
            layersRef.current.routes = [];
            routes.features.forEach(f => {
                if (!f.geometry?.coordinates) return;
                const pos = f.geometry.coordinates.map(c => [c[1], c[0]]);
                const line = L.polyline(pos, { color: '#00ff4120', weight: 1.5, dashArray: '6 10' }).addTo(map);
                layersRef.current.routes.push(line);
            });
        });
    }, [routes]);

    // Draw hubs + shipments
    useEffect(() => {
        const map = mapRef.current;
        if (!map) return;
        import('leaflet').then(L => {
            // Clear old markers
            layersRef.current.hubs.forEach(m => m.remove());
            layersRef.current.ships.forEach(m => m.remove());
            layersRef.current.hubs = [];
            layersRef.current.ships = [];

            // Hub markers (diamond shape via DivIcon)
            Object.entries(hubs).forEach(([id, hub]) => {
                const icon = L.divIcon({ className: '', html: '<div class="hub-pin"></div>', iconSize: [12, 12], iconAnchor: [6, 6] });
                const marker = L.marker([hub.lat, hub.lon], { icon }).addTo(map);
                marker.bindPopup(`<div style="color:#000;font-family:monospace;font-size:11px"><b>${id}</b><br/>${hub.city}<br/>Type: ${hub.type}</div>`);
                layersRef.current.hubs.push(marker);
            });

            // Shipment pins (tear-drop via DivIcon)
            shipments.slice(0, 100).forEach((s) => {
                const lat = s.current_lat || s.origin_lat || (18 + Math.random() * 12);
                const lon = s.current_lon || s.origin_lon || (72 + Math.random() * 15);
                const cls = STATUS_CLS[s.status] || 'ok';
                const icon = L.divIcon({ className: '', html: `<div class="shipment-pin ${cls}"></div>`, iconSize: [10, 10], iconAnchor: [5, 10] });
                const marker = L.marker([lat, lon], { icon }).addTo(map);
                marker.on('click', () => onSelectShipment?.(s));
                marker.bindPopup(`<div style="color:#000;font-family:monospace;font-size:11px">
          <b>${s.shipment_id}</b><br/>
          Status: ${s.status}<br/>
          ${s.carrier_name ? `Carrier: ${s.carrier_name}<br/>` : ''}
          ${s.eta_hours ? `ETA: ${s.eta_hours}h<br/>` : ''}
          ${s.risk_level ? `Risk: ${s.risk_level}` : ''}
        </div>`);
                layersRef.current.ships.push(marker);
            });
        });
    }, [hubs, shipments, onSelectShipment]);

    return (
        <div className="ops-map">
            <ErrorBoundary>
                <div ref={containerRef} style={{ width: '100%', height: '100%' }} />
            </ErrorBoundary>
        </div>
    );
}
