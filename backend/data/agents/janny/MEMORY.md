# MEMORY.md

## 🤖 Agent Model Configuration
- **Main Agent:** `google-flash/gemini-3-flash-preview` (Standard)
- **Fixer Janny:** `google-pro/gemini-3-pro-preview` (Deep intelligence/Troubleshooting)
- **Trader Janny:** `google-lite/gemini-flash-lite-latest` (Cost-effective scalping)
- **Research Janny:** `google-lite/gemini-flash-lite-latest` (Cost-effective news/feed scan)
- **Coder Janny:** `google-lite/gemini-flash-lite-latest` (Cost-effective scripting)

## 🛡️ Error & Escalation Protocol (Updated 2026-03-06)
- **Automatic Delegation:** If ANY HFT engine error (e.g., `op_underfunded`, `tx_bad_seq`, `504 Timeout`) persists for more than 3 cycles, or if the process crashes:
  1. **Immediate Notification:** Alert **Fixer Janny** (`google-pro/gemini-3-pro-preview`) and **Coder Janny** (`google-lite/gemini-flash-lite-latest`) via `sessions_send`.
  2. **Fixer Autonomy:** Fixer Janny is authorized to spawn sub-agents to perform account maintenance (offer cancellation, trustline cleanup).
  3. **Coder Autonomy:** Coder Janny is authorized to patch `hft_engine.js` (parameter tweaks, logic fixes).
  4. **Main Agent Role:** I will act as the orchestrator, monitoring their progress and providing a unified status report to the user once a fix is verified or if human intervention is required.

## 📈 HFT Strategy: Controlled Market-Making (Directive v3.6+)
- **Objective:** Inventory Accumulation (Stacking Coins).
- **Market Regime:** Bearish / Volatile. 
- **Core Priority:** Increase total coin count (SHX/AQUA) regardless of temporary fiat (GBP/USD) value drops.
- **Tactics:**
  1. **Buy-Heavy Bias:** Favor filling buy grids during dips to accumulate inventory.
  2. **Lower Profit Threshold:** Accept smaller spreads to ensure higher trade frequency (velocity) and consistent stacking.
  3. **Preserve XLM Floor:** Maintain the 10 XLM solvency buffer to ensure the "engine" can keep stacking.
  4. **Single-Pair Focus:** Stay on SHX for now to maximize efficiency with limited reserves.
- The user has successfully replaced my database brain with a file-based memory system.
- The user has successfully replaced my database brain with a file-based memory system.
