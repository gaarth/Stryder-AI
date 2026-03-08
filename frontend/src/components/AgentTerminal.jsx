import { useState, useRef, useEffect, useMemo } from 'react';

const AGENTS = ['Sentinel', 'Strategist', 'Actuary', 'Executor', 'Cascade'];
const SUBTAGS = ['ETA_AGENT', 'DELAY_AGENT', 'CARRIER_AGENT', 'HUB_AGENT', 'CASCADE_MODEL'];
const SLASH_CMDS = ['/help', '/reset', '/status', '/agents', '/shipment '];
const AGENT_COLORS = {
    Sentinel: '#888888', Strategist: '#aaaaaa', Actuary: '#cccccc',
    Executor: '#22c55e', Cascade: '#dddddd',
};

// ── Single line thinking animation ──
function ThinkingChainAnimation({ steps }) {
    const thoughts = useMemo(() => steps.map(s => s.text.replace(/\n/g, ' ')), [steps]);
    const [currentIndex, setCurrentIndex] = useState(0);

    useEffect(() => {
        const id = setInterval(() => {
            setCurrentIndex(prev => {
                if (prev >= thoughts.length - 1) {
                    clearInterval(id);
                    return prev;
                }
                return prev + 1;
            });
        }, 1800); // 1.8 seconds per thought change

        return () => clearInterval(id);
    }, [thoughts.length]);

    return (
        <div className="terminal-log-stream" style={{
            color: '#888888', // Dim gray, significantly lighter than standard terminal white/green
            fontStyle: 'italic',
            fontSize: '13px',
            whiteSpace: 'nowrap',
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            fontFamily: 'var(--font-sans)',
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            width: '100%',
            opacity: 0.8
        }}>
            <span style={{ fontSize: '10px', flexShrink: 0 }}>◆</span>
            <span style={{ overflow: 'hidden', textOverflow: 'ellipsis' }}>{thoughts[currentIndex] || ""}</span>
        </div>
    );
}

// ── Expandable Thought Process Panel ──
function ThoughtProcessPanel({ steps, onClose }) {
    return (
        <div className="thought-panel">
            <div className="thought-panel-header">
                <span>[AI] THOUGHT PROCESS</span>
                <button onClick={onClose} className="thought-close">X</button>
            </div>
            <div className="thought-panel-body">
                {steps.map((step, i) => (
                    <div key={i} className="thought-step-detail">
                        <div className="thought-step-num">{i + 1}</div>
                        <div className="thought-step-content">
                            <div className="thought-step-agent">
                                <span className="thought-agent-name">{step.agent}</span>
                                <span className="thought-agent-role">({step.role})</span>
                            </div>
                            <div className="thought-step-desc">{step.text}</div>
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
}

function GeneratingStars() {
    return (
        <div style={{ display: 'flex', alignItems: 'center', gap: 4, padding: '4px 0', fontFamily: 'var(--font-mono)', fontSize: 16, color: 'var(--accent)' }}>
            <span className="star-pulse" style={{ animationDelay: '0s' }}>*</span>
            <span className="star-pulse" style={{ animationDelay: '0.2s' }}>*</span>
            <span className="star-pulse" style={{ animationDelay: '0.4s' }}>*</span>
        </div>
    );
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
    return <>{displayed}<span className="cursor-blink">|</span></>;
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
    const [expandedThought, setExpandedThought] = useState(null);
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
                    // ── Thinking chain animation ──
                    if (m.role === 'thinking-chain') {
                        return (
                            <div key={i} className="at-msg thinking-chain-container">
                                <ThinkingChainAnimation steps={m.steps} />
                            </div>
                        );
                    }

                    const color = AGENT_COLORS[m.agent] || (m.role === 'disruption' ? '#cccccc' : m.role === 'user' ? '#888888' : '#555');
                    const label = m.role === 'agent' ? m.agent : m.role === 'disruption' ? 'EVENT' : m.role === 'user' ? 'YOU' : m.role === 'thinking' ? 'AGENT' : 'SYS';

                    // Clickable shipment count for executor messages
                    const hasRerouted = m.rerouted_ids?.length > 0;
                    const hasThinking = m.thinkingSteps?.length > 0;

                    return (
                        <div key={i} className={`at-msg ${m.role}`}>
                            <div className="at-tag" style={{ color }}>[{label}]</div>
                            <div className="at-body">
                                {m.role === 'thinking' ? (
                                    <GeneratingStars />
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
                                {/* See Thought Process Button */}
                                {hasThinking && !m.typing && (
                                    <button
                                        className="see-thought-btn"
                                        onClick={() => setExpandedThought(expandedThought === m.thoughtId ? null : m.thoughtId)}
                                    >
                                        [AI] {expandedThought === m.thoughtId ? 'Hide' : 'See'} Thought Process
                                    </button>
                                )}
                                {hasThinking && expandedThought === m.thoughtId && !m.typing && (
                                    <ThoughtProcessPanel steps={m.thinkingSteps} onClose={() => setExpandedThought(null)} />
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
                <div style={{ flex: 1, position: 'relative' }}>
                    <input ref={inputRef} className="at-input" value={input} style={{ width: '100%' }}
                        onChange={handleInput} onKeyDown={handleKey}
                        placeholder="@Sentinel scan for anomalies... or /help" />
                    {messages.some(m => m.role === 'thinking' || m.role === 'thinking-chain') && (
                        <div style={{ position: 'absolute', right: 12, top: '50%', transform: 'translateY(-50%)', display: 'flex' }}>
                            <GeneratingStars />
                        </div>
                    )}
                </div>
                <button className="at-send" onClick={send} disabled={messages.some(m => m.role === 'thinking' || m.role === 'thinking-chain')} style={{ opacity: messages.some(m => m.role === 'thinking' || m.role === 'thinking-chain') ? 0.5 : 1 }}>Send</button>
            </div>

            <style>{`
        .at { height:100%; display:flex; flex-direction:column; background:#111; overflow:hidden; }
        .at-header { padding:8px 14px; border-bottom:1px solid #2a2a2a; display:flex; align-items:center; gap:8px; background:#151515; flex-shrink:0; font-family:var(--font-display); font-size:12px; font-weight:700; color:#888; letter-spacing:1px; text-transform:uppercase; }
        .at-dot { width:6px; height:6px; border-radius:50%; background:#22c55e; box-shadow:0 0 6px #22c55e55; }
        .at-messages { flex:1; overflow-y:auto; padding:10px; display:flex; flex-direction:column; gap:4px; }
        .at-msg { font-family:var(--font-body); font-size:12px; line-height:1.6; padding:8px 10px; border-radius:4px; display:flex; gap:10px; align-items:flex-start; animation:msgIn .25s ease; }
        .at-msg.disruption { background:#ffffff05; border-left:3px solid #666; }
        .at-msg.agent { background:#1a1a1a; border-left:3px solid #333; }
        .at-msg.user { background:#ffffff05; border-left:3px solid #888; }
        .at-msg.system { opacity:0.6; }
        .at-msg.thinking { opacity:0.4; }
        .at-tag { font-size:10px; font-weight:700; flex-shrink:0; min-width:80px; letter-spacing:1px; }
        .at-body { flex:1; min-width:0; }
        .at-text { margin:0; white-space:pre-wrap; word-break:break-word; font-family:var(--font-body); font-size:12px; color:#e0e0e0; }
        .cursor-blink { color:#22c55e; animation:blink .8s step-start infinite; }
        @keyframes blink { 0%,50%{opacity:1} 51%,100%{opacity:0} }
        @keyframes msgIn { from{opacity:0;transform:translateY(4px)} to{opacity:1;transform:translateY(0)} }
        @keyframes starPulse { 0%, 100% { opacity: 0.3; transform: scale(0.8); } 50% { opacity: 1; transform: scale(1.1); text-shadow: 0 0 8px var(--accent); } }
        .star-pulse { animation: starPulse 1s ease-in-out infinite; }
        .ship-link { color:#888; cursor:pointer; text-decoration:underline; font-weight:700; }
        .ship-link:hover { color:#aaa; }
        .at-rerouted { margin-top:6px; display:flex; gap:6px; flex-wrap:wrap; align-items:center; font-size:11px; }
        .at-rerouted-label { color:#888; font-size:10px; }
        .at-suggestions { display:flex; gap:4px; padding:4px 10px; flex-wrap:wrap; border-top:1px solid #2a2a2a; background:#161616; }
        .at-sug { font-family:var(--font-body); font-size:11px; padding:4px 12px; background:#1a1a1a; border:1px solid #333; color:#22c55e; border-radius:3px; cursor:pointer; }
        .at-sug:hover { background:#222; border-color:#22c55e; }
        .at-input-row { display:flex; gap:8px; padding:10px; border-top:1px solid #2a2a2a; background:#0e0e0e; flex-shrink:0; }
        .at-input { flex:1; background:#1a1a1a; border:1px solid #333; border-radius:6px; padding:10px 14px; color:#e0e0e0; font-family:var(--font-body); font-size:12px; outline:none; }
        .at-input:focus { border-color:#555; box-shadow:0 0 0 1px #33333366; }
        .at-input::placeholder { color:#555; }
        .at-send { font-family:var(--font-body); font-size:12px; font-weight:700; padding:10px 18px; background:#1a1a1a; border:1px solid #333; border-radius:6px; color:#22c55e; cursor:pointer; }
        .at-send:hover { background:#222; border-color:#22c55e; }

        /* ── Thinking Chain Animation ── */
        .terminal-log-stream { border-left: 2px solid #555; padding-left: 10px; margin-top: 4px; }

        /* ── See Thought Process Button ── */
        .see-thought-btn {
            margin-top: 8px;
            padding: 5px 14px;
            font-family: var(--font-sans);
            font-size: 10px;
            font-weight: 700;
            color: #00ff87;
            background: rgba(0, 255, 135, 0.05);
            border: 1px solid rgba(0, 255, 135, 0.2);
            border-radius: 4px;
            cursor: pointer;
            transition: all 0.2s ease;
            letter-spacing: 0.5px;
        }
        .see-thought-btn:hover {
            background: rgba(0, 255, 135, 0.12);
            border-color: rgba(0, 255, 135, 0.4);
            box-shadow: 0 0 12px rgba(0, 255, 135, 0.15);
        }

        /* ── Thought Process Panel ── */
        .thought-panel {
            margin-top: 10px;
            background: rgba(10, 10, 10, 0.9);
            border: 1px solid rgba(0, 255, 135, 0.15);
            border-radius: 8px;
            overflow: hidden;
            animation: msgIn 0.3s ease;
        }
        .thought-panel-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 10px 14px;
            border-bottom: 1px solid rgba(0, 255, 135, 0.1);
            font-family: var(--font-display);
            font-size: 11px;
            font-weight: 800;
            color: #00ff87;
            letter-spacing: 1px;
        }
        .thought-close {
            background: none;
            border: none;
            color: #666;
            font-size: 14px;
            cursor: pointer;
        }
        .thought-close:hover { color: #aaa; }
        .thought-panel-body {
            padding: 12px;
            display: flex;
            flex-direction: column;
            gap: 12px;
            max-height: 350px;
            overflow-y: auto;
        }
        .thought-step-detail {
            display: flex;
            gap: 12px;
            align-items: flex-start;
        }
        .thought-step-num {
            width: 22px;
            height: 22px;
            border-radius: 50%;
            background: rgba(0, 255, 135, 0.1);
            border: 1px solid rgba(0, 255, 135, 0.3);
            display: flex;
            align-items: center;
            justify-content: center;
            font-family: var(--font-mono);
            font-size: 9px;
            color: #00ff87;
            font-weight: 700;
            flex-shrink: 0;
        }
        .thought-step-content { flex: 1; }
        .thought-step-agent {
            display: flex;
            align-items: center;
            gap: 6px;
            margin-bottom: 4px;
        }
        .thought-agent-name {
            font-family: var(--font-sans);
            font-weight: 800;
            font-style: italic;
            font-size: 12px;
            color: var(--text-primary, #fff);
        }
        .thought-agent-role {
            font-family: var(--font-sans);
            font-size: 10px;
            color: #666;
        }
        .thought-step-desc {
            font-family: var(--font-sans);
            font-size: 11px;
            color: #999;
            line-height: 1.6;
        }
      `}</style>
        </div>
    );
}
