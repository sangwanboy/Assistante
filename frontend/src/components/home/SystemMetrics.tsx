import { Activity, Zap, ShieldAlert, Cpu } from 'lucide-react';
import { motion } from 'framer-motion';
import { useState, useEffect } from 'react';
import { api } from '../../services/api';

export function SystemMetrics() {
    const [data, setData] = useState({
        active_agents: 0,
        total_agents: 25,
        global_rpm: 0,
        total_rpm_limit: 1000,
        global_tpm: 0,
        total_tpm_limit: 4000000,
        rate_limit_blocks: 0
    });

    useEffect(() => {
        let isMounted = true;
        const fetchMetrics = async () => {
            try {
                const res = await api.getSystemMetrics();
                if (isMounted && res) {
                    setData(res);
                }
            } catch (err) {
                console.error("Failed to load metrics:", err);
            }
        };
        fetchMetrics();
        const intId = setInterval(fetchMetrics, 5000);
        return () => {
            isMounted = false;
            clearInterval(intId);
        };
    }, []);

    const formatNumber = (num: number) => {
        if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M';
        if (num >= 1000) return (num / 1000).toFixed(1) + 'k';
        return num.toString();
    };

    const metrics = [
        {
            id: 'active_agents',
            label: 'Autonomous Agents',
            value: data.active_agents.toString(),
            total: data.total_agents.toString(),
            icon: <Cpu className="w-4 h-4" />,
            color: '#6366f1',
            percent: data.total_agents > 0 ? (data.active_agents / data.total_agents) * 100 : 0,
        },
        {
            id: 'rpm_load',
            label: 'Global RPM Load',
            value: formatNumber(data.global_rpm),
            total: formatNumber(data.total_rpm_limit),
            icon: <Activity className="w-4 h-4" />,
            color: '#10b981',
            percent: data.total_rpm_limit > 0 ? (data.global_rpm / data.total_rpm_limit) * 100 : 0,
        },
        {
            id: 'tpm_burn',
            label: 'Current TPM Burn',
            value: formatNumber(data.global_tpm),
            total: formatNumber(data.total_tpm_limit),
            icon: <Zap className="w-4 h-4" />,
            color: '#f59e0b',
            percent: data.total_tpm_limit > 0 ? (data.global_tpm / data.total_tpm_limit) * 100 : 0,
        },
        {
            id: 'rate_limits',
            label: 'Rate Limit Blocks',
            value: data.rate_limit_blocks.toString(),
            total: '100',
            icon: <ShieldAlert className="w-4 h-4" />,
            color: '#f43f5e',
            percent: Math.min(data.rate_limit_blocks, 100),
        }
    ];

    return (
        <section className="liquid-panel overflow-hidden flex flex-col">
            <div className="px-5 py-4 flex items-center justify-between">
                <h3 className="text-[10px] font-semibold text-white/40 uppercase tracking-[1.5px]">
                    System Metrics
                </h3>
                <div className="flex items-center gap-1.5 text-[9px] font-semibold text-emerald-400/80 bg-emerald-500/10 px-2 py-0.5 rounded-full border border-emerald-500/15">
                    <span className="relative flex h-1.5 w-1.5">
                        <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                        <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-emerald-500"></span>
                    </span>
                    LIVE
                </div>
            </div>

            <div className="px-5 pb-5 flex flex-col gap-5">
                {metrics.map((m, idx) => (
                    <motion.div
                        key={m.id}
                        initial={{ opacity: 0, x: -10 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: idx * 0.08 }}
                        className="flex flex-col gap-2"
                    >
                        <div className="flex items-center justify-between">
                            <div className="flex items-center gap-2">
                                <span style={{ color: m.color, opacity: 0.7 }}>{m.icon}</span>
                                <span className="text-[11px] text-white/35 font-medium">{m.label}</span>
                            </div>
                            <div className="text-[11px] font-semibold text-white/70 tabular-nums">
                                {m.value} <span className="text-white/15">/</span> {m.total}
                            </div>
                        </div>
                        {/* Progress Bar */}
                        <div className="h-1 w-full bg-white/[0.04] rounded-full overflow-hidden">
                            <motion.div
                                initial={{ width: 0 }}
                                animate={{ width: `${m.percent}%` }}
                                transition={{ duration: 1.2, delay: 0.1 + (idx * 0.08), ease: [0.22, 1, 0.36, 1] }}
                                className="h-full rounded-full"
                                style={{ backgroundColor: m.color, boxShadow: `0 0 10px ${m.color}40` }}
                            />
                        </div>
                    </motion.div>
                ))}
            </div>
        </section>
    );
}
