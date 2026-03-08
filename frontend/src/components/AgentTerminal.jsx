import { useState, useRef, useEffect, useMemo } from 'react';

const AGENTS = ['Sentinel', 'Strategist', 'Actuary', 'Executor', 'Cascade'];
const SUBTAGS = ['ETA_AGENT', 'DELAY_AGENT', 'CARRIER_AGENT', 'HUB_AGENT', 'CASCADE_MODEL'];
const SLASH_CMDS = ['/help', '/reset', '/status', '/agents', '/shipment '];
const AGENT_COLORS = {
    Sentinel: '#ef4444', Strategist: '#8b5cf6', Actuary: '#f59e0b',
    Executor: '#22c55e', Cascade: '#06b6d4',
};

function ThinkingDots() {
    const [dots, setDots] = useState('');
    useEffect(() => {
        const id = setInterval(() => setDots(d => d.length >= 3 ? '' : d + '.'), 400);
        return () => clearInterval(id);
    }, []);
    return <span style={{ color: '#555' }}>thinking{dots}</span>;
}

function TypewriterText({ text, onDone }) {
    const [displayed, setDisplayed] = useState('');
    const idxRef = useRef(0);
    useEffect(() => {
        idxRef.current = 0; setDisplayed('');
        const id = setInterval(() => {
            idxRef.current += Math.max(1, Math.floor(text.length / 80)); // fast but visible
            if (idxRef.current >= text.length) {
                setDisplayed(text); clearInterval(id); onDone?.();
            } else {
                setDisplayed(text.slice(0, idxRef.current));
            }
        }, 20);
        return () => clearInterval(id);
    }, [text]);
    return <>{displayed}<span className="cursor-blink">▎</span></>;
}

// Parse shipment IDs from text (patterns like #42, shipment 42, etc)
function parseShipmentIds(text) {
    const matches = text.match(/#(\d+)/g) || [];
    return [...new Set(matches.map(m => parseInt(m.slice(1))))];
}

// Render message text with clickable shipment IDs
function RenderText({ text, onShipmentClick }) {
    if (!onShipmentClick) return text;
    const parts = text.split(/(#\d+)/g);
    return parts.map((part, i) => {
        const match = part.match(/^#(\d+)$/);
        if (match) {
            return <span key={i} className="ship-link" onClick={() => onShipmentClick(parseInt(match[1]))}>{part}</span>;
        }
        return part;
    });
}

export default function AgentTerminal({ messages, onSend, onShipmentClick }) {
    const [input, setInput] = useState('');
    const [suggestions, setSuggestions] = useState([]);
    const endRef = useRef(null);
    const inputRef = useRef(null);

    useEffect(() => { endRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [messages]);

    const handleInput = (e) => {
        const val = e.target.value;
        setInput(val);
        const lastWord = val.split(' ').pop();
        if (lastWord.startsWith('/') && val.trim() === lastWord) {
            setSuggestions(SLASH_CMDS.filter(c => c.startsWith(lastWord)));
        } else if (lastWord.startsWith('@')) {
            if (lastWord.includes(':')) {
                const sub = lastWord.split(':')[1].toLowerCase();
                setSuggestions(SUBTAGS.filter(s => s.toLowerCase().startsWith(sub)).map(s => `@Strategist:${s}`));
            } else {
                const q = lastWord.slice(1).toLowerCase();
                setSuggestions(AGENTS.filter(a => a.toLowerCase().startsWith(q)).map(a => `@${a}`));
            }
        } else {
            setSuggestions([]);
        }
    };

    const applySuggestion = (s) => {
        const words = input.split(' ');
        words[words.length - 1] = s;
        setInput(words.join(' ') + (s.endsWith(' ') ? '' : ' '));
        setSuggestions([]);
        inputRef.current?.focus();
    };

    const send = () => { if (!input.trim()) return; onSend(input.trim()); setInput(''); setSuggestions([]); };
    const handleKey = (e) => {
        if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(); }
        if (e.key === 'Tab' && suggestions.length) { e.preventDefault(); applySuggestion(suggestions[0]); }
        if (e.key === 'Escape') setSuggestions([]);
    };

    return (
        <div className="at">
            <div className="at-header">
                <div className="at-dot"></div>
                <span>Agent Terminal</span>
            </div>

            <div className="at-messages">
                {messages.map((m, i) => {
                    const color = AGENT_COLORS[m.agent] || (m.role === 'disruption' ? '#ef4444' : m.role === 'user' ? '#3b82f6' : '#555');
                    const label = m.role === 'agent' ? m.agent : m.role === 'disruption' ? 'EVENT' : m.role === 'user' ? 'YOU' : m.role === 'thinking' ? 'AGENT' : 'SYS';

                    // Clickable shipment count for executor messages
                    const hasRerouted = m.rerouted_ids?.length > 0;

                    return (
                        <div key={i} className={`at-msg ${m.role}`}>
                            <div className="at-tag" style={{ color }}>[{label}]</div>
                            <div className="at-body">
                                {m.role === 'thinking' ? (
                                    <ThinkingDots />
                                ) : m.typing ? (
                                    <TypewriterText text={m.text} onDone={() => { }} />
                                ) : (
                                    <pre className="at-text"><RenderText text={m.text} onShipmentClick={onShipmentClick} /></pre>
                                )}
                                {hasRerouted && !m.typing && (
                                    <div className="at-rerouted">
                                        <span className="at-rerouted-label">Rerouted shipments: </span>
                                        {m.rerouted_ids.map(id => (
                                            <span key={id} className="ship-link" onClick={() => onShipmentClick?.(id)}>#{id}</span>
                                        ))}
                                    </div>
                                )}
                            </div>
                        </div>
                    );
                })}
                <div ref={endRef} />
            </div>

            {suggestions.length > 0 && (
                <div className="at-suggestions">
                    {suggestions.map(s => (
                        <button key={s} className="at-sug" onClick={() => applySuggestion(s)}>{s}</button>
                    ))}
                </div>
            )}

            <div className="at-input-row">
                <input ref={inputRef} className="at-input" value={input}
                    onChange={handleInput} onKeyDown={handleKey}
                    placeholder="@Sentinel scan for anomalies... or /help" />
                <button className="at-send" onClick={send}>Send</button>
            </div>

            <style>{`
        .at { height:100%; display:flex; flex-direction:column; background:#111; overflow:hidden; }
        .at-header { padding:8px 14px; border-bottom:1px solid #2a2a2a; display:flex; align-items:center; gap:8px; background:#151515; flex-shrink:0; font-family:var(--font-mono); font-size:11px; font-weight:700; color:#888; letter-spacing:1px; text-transform:uppercase; }
        .at-dot { width:6px; height:6px; border-radius:50%; background:#22c55e; box-shadow:0 0 6px #22c55e55; }
        .at-messages { flex:1; overflow-y:auto; padding:10px; display:flex; flex-direction:column; gap:4px; }
        .at-msg { font-family:var(--font-mono); font-size:12px; line-height:1.6; padding:8px 10px; border-radius:4px; display:flex; gap:10px; align-items:flex-start; animation:msgIn .25s ease; }
        .at-msg.disruption { background:#ef444408; border-left:3px solid #ef4444; }
        .at-msg.agent { background:#1a1a1a; border-left:3px solid #333; }
        .at-msg.user { background:#3b82f608; border-left:3px solid #3b82f6; }
        .at-msg.system { opacity:0.6; }
        .at-msg.thinking { opacity:0.4; }
        .at-tag { font-size:10px; font-weight:700; flex-shrink:0; min-width:80px; letter-spacing:1px; }
        .at-body { flex:1; min-width:0; }
        .at-text { margin:0; white-space:pre-wrap; word-break:break-word; font-family:var(--font-mono); font-size:12px; color:#e0e0e0; }
        .cursor-blink { color:#22c55e; animation:blink .8s step-start infinite; }
        @keyframes blink { 0%,50%{opacity:1} 51%,100%{opacity:0} }
        @keyframes msgIn { from{opacity:0;transform:translateY(4px)} to{opacity:1;transform:translateY(0)} }
        .ship-link { color:#3b82f6; cursor:pointer; text-decoration:underline; font-weight:700; }
        .ship-link:hover { color:#60a5fa; }
        .at-rerouted { margin-top:6px; display:flex; gap:6px; flex-wrap:wrap; align-items:center; font-size:11px; }
        .at-rerouted-label { color:#888; font-size:10px; }
        .at-suggestions { display:flex; gap:4px; padding:4px 10px; flex-wrap:wrap; border-top:1px solid #2a2a2a; background:#161616; }
        .at-sug { font-family:var(--font-mono); font-size:10px; padding:3px 10px; background:#1a1a1a; border:1px solid #333; color:#22c55e; border-radius:3px; cursor:pointer; }
        .at-sug:hover { background:#222; border-color:#22c55e; }
        .at-input-row { display:flex; gap:8px; padding:10px; border-top:1px solid #2a2a2a; background:#0e0e0e; flex-shrink:0; }
        .at-input { flex:1; background:#1a1a1a; border:1px solid #333; border-radius:6px; padding:10px 14px; color:#e0e0e0; font-family:var(--font-mono); font-size:12px; outline:none; }
        .at-input:focus { border-color:#555; box-shadow:0 0 0 1px #33333366; }
        .at-input::placeholder { color:#555; }
        .at-send { font-family:var(--font-mono); font-size:11px; font-weight:700; padding:10px 18px; background:#1a1a1a; border:1px solid #333; border-radius:6px; color:#22c55e; cursor:pointer; }
        .at-send:hover { background:#222; border-color:#22c55e; }
      `}</style>
        </div>
    );
}
