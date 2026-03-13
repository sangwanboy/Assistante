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
        const intId = setInterval(fetchMetrics, 5000); // 5s refresh
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
            icon: <Cpu className="w-4 h-4 text-indigo-400" />,
            color: 'bg-indigo-500',
            percent: data.total_agents > 0 ? (data.active_agents / data.total_agents) * 100 : 0,
        },
        {
            id: 'rpm_load',
            label: 'Global RPM Load',
            value: formatNumber(data.global_rpm),
            total: formatNumber(data.total_rpm_limit),
            icon: <Activity className="w-4 h-4 text-emerald-400" />,
            color: 'bg-emerald-500',
            percent: data.total_rpm_limit > 0 ? (data.global_rpm / data.total_rpm_limit) * 100 : 0,
        },
        {
            id: 'tpm_burn',
            label: 'Current TPM Burn',
            value: formatNumber(data.global_tpm),
            total: formatNumber(data.total_tpm_limit),
            icon: <Zap className="w-4 h-4 text-amber-400" />,
            color: 'bg-amber-500',
            percent: data.total_tpm_limit > 0 ? (data.global_tpm / data.total_tpm_limit) * 100 : 0,
        },
        {
            id: 'rate_limits',
            label: 'Rate Limit Blocks',
            value: data.rate_limit_blocks.toString(),
            total: '100',
            icon: <ShieldAlert className="w-4 h-4 text-red-400" />,
            color: 'bg-red-500',
            percent: Math.min(data.rate_limit_blocks, 100),
        }
    ];

    return (
        <div className="bg-[#0c0c1a] border border-[#1c1c30] rounded-xl overflow-hidden flex flex-col">
            <div className="px-5 py-4 border-b border-[#1c1c30] flex items-center justify-between bg-[#141426]">
                <h3 className="text-sm font-bold text-white flex items-center gap-2">
                    <Activity className="w-4 h-4 text-emerald-400" />
                    System Metrics
                </h3>
                <div className="flex items-center gap-2 text-xs font-semibold text-emerald-400 bg-emerald-500/10 px-2 py-1 rounded-full border border-emerald-500/20">
                    <span className="relative flex h-2 w-2">
                        <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                        <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
                    </span>
                    Gateway Active
                </div>
            </div>

            <div className="p-4 flex flex-col gap-4">
                {metrics.map((m, idx) => (
                    <motion.div
                        key={m.id}
                        initial={{ opacity: 0, x: -10 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: idx * 0.1 }}
                        className="flex flex-col gap-2"
                    >
                        <div className="flex items-center justify-between text-sm">
                            <div className="flex items-center gap-2 text-gray-300 font-medium">
                                {m.icon}
                                {m.label}
                            </div>
                            <div className="font-mono text-white text-xs">
                                {m.value} / <span className="text-gray-500">{m.total}</span>
                            </div>
                        </div>
                        {/* Progress Bar */}
                        <div className="h-1.5 w-full bg-[#1c1c30] rounded-full overflow-hidden">
                            <motion.div
                                initial={{ width: 0 }}
                                animate={{ width: `${m.percent}%` }}
                                transition={{ duration: 1, delay: 0.2 + (idx * 0.1), type: 'spring' }}
                                className={`h-full ${m.color}`}
                            />
                        </div>
                    </motion.div>
                ))}
            </div>
        </div>
    );
}
