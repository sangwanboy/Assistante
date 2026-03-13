import { useState, useEffect } from 'react';
import { X } from 'lucide-react';
import { ICON_MAP } from './CustomNodes';
import { NODE_CATEGORY_COLORS } from '../../types/workflow';
import type { Agent } from '../../types';

interface NodeConfig {
    id: string;
    type: string;
    sub_type: string;
    label: string;
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    config: Record<string, any>;
}

interface NodeConfigPanelProps {
    node: NodeConfig | null;
    agents: Agent[];
    onClose: () => void;
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    onUpdate: (nodeId: string, label: string, config: Record<string, any>) => void;
}

export function NodeConfigPanel({ node, agents, onClose, onUpdate }: NodeConfigPanelProps) {
    const [label, setLabel] = useState('');
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const [config, setConfig] = useState<Record<string, any>>({});

    useEffect(() => {
        if (node) {
            // eslint-disable-next-line
            setLabel(node.label || node.sub_type);
            setConfig(node.config || {});
        }
    }, [node]);

    if (!node) return null;

    const color = NODE_CATEGORY_COLORS[node.type] || '#6366f1';
    const Icon = ICON_MAP[node.sub_type];

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const updateConfig = (key: string, value: any) => {
        const updated = { ...config, [key]: value };
        setConfig(updated);
        onUpdate(node.id, label, updated);
    };

    const handleLabelChange = (newLabel: string) => {
        setLabel(newLabel);
        onUpdate(node.id, newLabel, config);
    };

    // ─── Render Dynamic Fields ───────────────────────────────

    const renderFields = () => {
        switch (node.sub_type) {
            // Agent nodes
            case 'agent_call':
            case 'agent_delegate':
                return (
                    <>
                        <FieldLabel>Agent</FieldLabel>
                        <select
                            value={config.agent_id || ''}
                            onChange={e => updateConfig('agent_id', e.target.value)}
                            style={selectStyle}
                        >
                            <option value="">Select agent...</option>
                            {agents.map(a => (
                                <option key={a.id} value={a.id}>{a.name}</option>
                            ))}
                        </select>
                        <FieldLabel>Input Template</FieldLabel>
                        <textarea
                            value={config.input_template || '{{message}}'}
                            onChange={e => updateConfig('input_template', e.target.value)}
                            style={textareaStyle}
                            placeholder="{{message}}"
                            rows={3}
                        />
                        <FieldLabel>Model</FieldLabel>
                        <input
                            value={config.model || 'gemini/gemini-2.5-flash'}
                            onChange={e => updateConfig('model', e.target.value)}
                            style={inputStyle}
                        />

                        <div className="mt-4 pt-4 border-t border-[#1c1c30]">
                            <p className="text-xs text-indigo-400 font-semibold mb-3">Autonomous Guards</p>
                            <div className="grid grid-cols-2 gap-3">
                                <div>
                                    <FieldLabel>Max Steps</FieldLabel>
                                    <input
                                        type="number"
                                        value={config.max_steps || 40}
                                        onChange={e => updateConfig('max_steps', parseInt(e.target.value))}
                                        style={inputStyle}
                                        placeholder="40"
                                    />
                                </div>
                                <div>
                                    <FieldLabel>Max Tokens</FieldLabel>
                                    <input
                                        type="number"
                                        value={config.max_tokens || 200000}
                                        onChange={e => updateConfig('max_tokens', parseInt(e.target.value))}
                                        style={inputStyle}
                                        placeholder="200000"
                                    />
                                </div>
                            </div>
                        </div>
                    </>
                );

            // Tool nodes
            case 'http_request':
                return (
                    <>
                        <FieldLabel>URL</FieldLabel>
                        <input
                            value={config.url || ''}
                            onChange={e => updateConfig('url', e.target.value)}
                            style={inputStyle}
                            placeholder="https://api.example.com/data"
                        />
                        <FieldLabel>Method</FieldLabel>
                        <select
                            value={config.method || 'GET'}
                            onChange={e => updateConfig('method', e.target.value)}
                            style={selectStyle}
                        >
                            {['GET', 'POST', 'PUT', 'DELETE', 'PATCH'].map(m => (
                                <option key={m} value={m}>{m}</option>
                            ))}
                        </select>
                        <FieldLabel>Body (JSON template)</FieldLabel>
                        <textarea
                            value={config.body || ''}
                            onChange={e => updateConfig('body', e.target.value)}
                            style={textareaStyle}
                            rows={4}
                            placeholder='{"key": "{{value}}"}'
                        />
                    </>
                );

            case 'web_scrape':
                return (
                    <>
                        <FieldLabel>URL</FieldLabel>
                        <input
                            value={config.url || ''}
                            onChange={e => updateConfig('url', e.target.value)}
                            style={inputStyle}
                            placeholder="https://example.com"
                        />
                    </>
                );

            case 'file_read':
                return (
                    <>
                        <FieldLabel>File Path</FieldLabel>
                        <input
                            value={config.filepath || ''}
                            onChange={e => updateConfig('filepath', e.target.value)}
                            style={inputStyle}
                            placeholder="/path/to/file.txt"
                        />
                    </>
                );

            case 'db_query':
                return (
                    <>
                        <FieldLabel>Query</FieldLabel>
                        <textarea
                            value={config.query || ''}
                            onChange={e => updateConfig('query', e.target.value)}
                            style={textareaStyle}
                            rows={4}
                            placeholder="SELECT * FROM ..."
                        />
                    </>
                );

            // Data nodes
            case 'set_variable':
                return (
                    <>
                        <FieldLabel>Variable Name</FieldLabel>
                        <input
                            value={config.key || ''}
                            onChange={e => updateConfig('key', e.target.value)}
                            style={inputStyle}
                            placeholder="my_variable"
                        />
                        <FieldLabel>Value</FieldLabel>
                        <input
                            value={config.value || ''}
                            onChange={e => updateConfig('value', e.target.value)}
                            style={inputStyle}
                            placeholder="{{data.field}} or static value"
                        />
                    </>
                );

            case 'save_memory':
                return (
                    <>
                        <FieldLabel>Memory Key</FieldLabel>
                        <input
                            value={config.key || ''}
                            onChange={e => updateConfig('key', e.target.value)}
                            style={inputStyle}
                            placeholder="user_preference"
                        />
                        <FieldLabel>Value</FieldLabel>
                        <input
                            value={config.value || ''}
                            onChange={e => updateConfig('value', e.target.value)}
                            style={inputStyle}
                            placeholder="{{data.field}} or static value"
                        />
                    </>
                );

            case 'transform_json':
                return (
                    <>
                        <FieldLabel>Key Path</FieldLabel>
                        <input
                            value={config.key_path || ''}
                            onChange={e => updateConfig('key_path', e.target.value)}
                            style={inputStyle}
                            placeholder="data.results.0.name"
                        />
                    </>
                );

            case 'template':
                return (
                    <>
                        <FieldLabel>Template</FieldLabel>
                        <textarea
                            value={config.template || ''}
                            onChange={e => updateConfig('template', e.target.value)}
                            style={textareaStyle}
                            rows={5}
                            placeholder="Hello {{name}}, your order {{order_id}} is ready."
                        />
                    </>
                );

            // Logic nodes
            case 'condition':
            case 'branch':
                return (
                    <>
                        <FieldLabel>Field</FieldLabel>
                        <input
                            value={config.field || ''}
                            onChange={e => updateConfig('field', e.target.value)}
                            style={inputStyle}
                            placeholder="confidence"
                        />
                        <FieldLabel>Operator</FieldLabel>
                        <select
                            value={config.operator || 'equals'}
                            onChange={e => updateConfig('operator', e.target.value)}
                            style={selectStyle}
                        >
                            <option value="equals">Equals</option>
                            <option value="not_equals">Not Equals</option>
                            <option value="contains">Contains</option>
                            <option value="greater_than">Greater Than</option>
                            <option value="less_than">Less Than</option>
                            <option value="exists">Exists</option>
                        </select>
                        <FieldLabel>Value</FieldLabel>
                        <input
                            value={config.value || ''}
                            onChange={e => updateConfig('value', e.target.value)}
                            style={inputStyle}
                            placeholder="0.7"
                        />
                    </>
                );

            case 'switch':
                return (
                    <>
                        <FieldLabel>Field</FieldLabel>
                        <input
                            value={config.field || ''}
                            onChange={e => updateConfig('field', e.target.value)}
                            style={inputStyle}
                            placeholder="intent"
                        />
                        <FieldLabel>Cases (JSON)</FieldLabel>
                        <textarea
                            value={typeof config.cases === 'object' ? JSON.stringify(config.cases, null, 2) : (config.cases || '')}
                            onChange={e => {
                                try {
                                    updateConfig('cases', JSON.parse(e.target.value));
                                } catch { /* user still typing */ }
                            }}
                            style={textareaStyle}
                            rows={4}
                            placeholder='{"buy": "buy", "sell": "sell"}'
                        />
                    </>
                );

            case 'loop':
                return (
                    <>
                        <FieldLabel>Items Field</FieldLabel>
                        <input
                            value={config.items_field || 'items'}
                            onChange={e => updateConfig('items_field', e.target.value)}
                            style={inputStyle}
                            placeholder="items"
                        />
                    </>
                );

            case 'delay':
                return (
                    <>
                        <FieldLabel>Delay (seconds)</FieldLabel>
                        <input
                            type="number"
                            value={config.seconds || 1}
                            onChange={e => updateConfig('seconds', parseInt(e.target.value) || 1)}
                            style={inputStyle}
                            min={1}
                            max={300}
                        />
                    </>
                );

            // Human
            case 'human_approval':
                return (
                    <>
                        <FieldLabel>Approval Message</FieldLabel>
                        <textarea
                            value={config.message || ''}
                            onChange={e => updateConfig('message', e.target.value)}
                            style={textareaStyle}
                            rows={3}
                            placeholder="Please review and approve this action."
                        />
                    </>
                );

            // LLM actions
            case 'summarize':
                return (
                    <>
                        <FieldLabel>Model</FieldLabel>
                        <input
                            value={config.model || 'gemini/gemini-2.5-flash'}
                            onChange={e => updateConfig('model', e.target.value)}
                            style={inputStyle}
                        />
                    </>
                );

            // Trigger configs
            case 'schedule':
                return (
                    <>
                        <FieldLabel>Cron Expression</FieldLabel>
                        <input
                            value={config.cron || ''}
                            onChange={e => updateConfig('cron', e.target.value)}
                            style={inputStyle}
                            placeholder="0 */6 * * *"
                        />
                    </>
                );

            case 'webhook':
                return (
                    <>
                        <FieldLabel>Webhook Path</FieldLabel>
                        <input
                            value={config.path || ''}
                            onChange={e => updateConfig('path', e.target.value)}
                            style={inputStyle}
                            placeholder="/incoming/my-hook"
                        />
                    </>
                );

            case 'parallel':
                return (
                    <>
                        <FieldLabel>Branch Count</FieldLabel>
                        <input
                            type="number"
                            value={config.branch_count || 2}
                            onChange={e => updateConfig('branch_count', parseInt(e.target.value) || 2)}
                            style={inputStyle}
                            min={2}
                            max={10}
                            placeholder="2"
                        />
                        <FieldLabel>Merge Strategy</FieldLabel>
                        <select
                            value={config.merge_strategy || 'wait_all'}
                            onChange={e => updateConfig('merge_strategy', e.target.value)}
                            style={selectStyle}
                        >
                            <option value="wait_all">Wait for All</option>
                            <option value="first_completed">First Completed</option>
                            <option value="majority">Majority (50%+)</option>
                        </select>
                        <FieldLabel>Timeout (seconds)</FieldLabel>
                        <input
                            type="number"
                            value={config.timeout_seconds || 300}
                            onChange={e => updateConfig('timeout_seconds', parseInt(e.target.value) || 300)}
                            style={inputStyle}
                            min={10}
                            max={3600}
                            placeholder="300"
                        />
                    </>
                );

            default:
                return (
                    <div style={{ color: 'rgba(255,255,255,0.4)', fontSize: '13px', fontStyle: 'italic' }}>
                        No configuration needed for this node type.
                    </div>
                );
        }
    };

    return (
        <div style={{
            position: 'absolute',
            right: 0,
            top: 0,
            bottom: 0,
            width: '340px',
            background: 'rgba(15, 15, 25, 0.97)',
            borderLeft: `2px solid ${color}30`,
            zIndex: 20,
            padding: '20px',
            overflowY: 'auto',
            animation: 'slideInRight 0.2s ease',
        }}>
            {/* Header */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                    {Icon && <Icon size={18} color={color} />}
                    <span style={{ fontSize: '15px', fontWeight: 600, color: '#fff' }}>
                        Configure Node
                    </span>
                </div>
                <button onClick={onClose} style={{
                    background: 'none', border: 'none', cursor: 'pointer',
                    color: 'rgba(255,255,255,0.5)', padding: '4px',
                }}>
                    <X size={18} />
                </button>
            </div>

            {/* Category badge */}
            <div style={{
                fontSize: '10px', fontWeight: 700, textTransform: 'uppercase',
                letterSpacing: '1.2px', color: color, marginBottom: '16px',
            }}>
                {node.type} · {node.sub_type}
            </div>

            {/* Label */}
            <FieldLabel>Label</FieldLabel>
            <input
                value={label}
                onChange={e => handleLabelChange(e.target.value)}
                style={inputStyle}
            />

            {/* Dynamic fields */}
            <div style={{ marginTop: '8px' }}>
                {renderFields()}
            </div>
        </div>
    );
}

// ─── Reusable styled helpers ─────────────────────────────

function FieldLabel({ children }: { children: React.ReactNode }) {
    return (
        <div style={{
            fontSize: '11px',
            fontWeight: 600,
            color: 'rgba(255,255,255,0.5)',
            marginTop: '14px',
            marginBottom: '5px',
            textTransform: 'uppercase',
            letterSpacing: '0.8px',
        }}>
            {children}
        </div>
    );
}

const inputStyle: React.CSSProperties = {
    width: '100%',
    padding: '8px 12px',
    background: 'rgba(255,255,255,0.06)',
    border: '1px solid rgba(255,255,255,0.1)',
    borderRadius: '8px',
    color: '#fff',
    fontSize: '13px',
    outline: 'none',
    boxSizing: 'border-box',
    textOverflow: 'ellipsis',
    minWidth: 0,
};

const selectStyle: React.CSSProperties = {
    ...inputStyle,
    cursor: 'pointer',
};

const textareaStyle: React.CSSProperties = {
    ...inputStyle,
    resize: 'vertical',
    fontFamily: 'monospace',
    fontSize: '12px',
};

export default NodeConfigPanel;
