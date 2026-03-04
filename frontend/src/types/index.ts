export interface Message {
  id?: number;
  role: 'user' | 'assistant' | 'system' | 'tool';
  content: string;
  tool_calls_json?: string | null;
  tool_call_id?: string | null;
  agent_name?: string | null;
  created_at?: string;
}

export interface Channel {
  id: string;
  name: string;
  description: string | null;
  is_announcement: boolean;
  orchestration_mode: 'autonomous' | 'manual';
  created_at: string;
  updated_at: string;
}

export interface Conversation {
  id: string;
  title: string;
  model: string;
  system_prompt: string | null;
  is_group?: boolean;
  agent_id?: string | null;
  channel_id?: string | null;
  created_at: string;
  updated_at: string;
  messages?: Message[];
}

export interface ModelInfo {
  id: string;
  name: string;
  provider: string;
  supports_streaming: boolean;
  supports_tools: boolean;
  context_window: number;
}

export interface ToolInfo {
  name: string;
  description: string;
  parameters: Record<string, unknown>;
  is_builtin: boolean;
}

export interface StreamEvent {
  type: 'chunk' | 'tool_call' | 'tool_result' | 'done' | 'error' | 'agent_turn_start' | 'agent_turn_end'
    | 'chain_start' | 'chain_update' | 'chain_complete' | 'orchestration_plan' | 'task_progress';
  delta?: string;
  tool_name?: string;
  tool_args?: Record<string, unknown>;
  tool_result?: string;
  message_id?: number;
  conversation_id?: string;
  agent_name?: string;
  error?: string;
  // Chain/orchestration fields
  chain_id?: string;
  chain_state?: string;
  chain_depth?: number;
  chain_agents?: string[];
  current_agent?: string;
  current_task?: string;
  plan_summary?: string;
  steps?: Array<{ agent: string; task: string }>;
  // Task progress fields
  task_id?: string;
  progress?: number;
}

export interface AppSettings {
  openai_api_key_set: boolean;
  anthropic_api_key_set: boolean;
  gemini_api_key_set: boolean;
  ollama_base_url: string;
  default_model: string;
  default_temperature: number;
  default_system_prompt: string;
}

export interface Agent {
  id: string;
  name: string;
  description: string | null;
  provider: string;
  model: string;
  system_prompt: string | null;
  is_active: boolean;
  // Soul
  personality_tone: string | null;
  personality_traits: string | null;       // JSON list
  communication_style: string | null;
  // Mind
  enabled_tools: string | null;            // JSON list
  enabled_skills: string | null;           // JSON list
  reasoning_style: string | null;
  // Memory
  memory_context: string | null;
  memory_instructions: string | null;
  // Per-agent API key (masked in responses)
  api_key: string | null;
  is_system?: boolean;
  total_cost?: number;
  created_at: string;
  updated_at: string;
}

export interface Document {
  id: string;
  filename: string;
  file_type: string;
  size: number;
  content_hash: string;
  created_at: string;
  updated_at: string;
}

export interface CustomTool {
  id: string;
  name: string;
  description: string;
  parameters_schema: string;  // JSON string
  code: string;               // Python source
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface Skill {
  id: string;
  name: string;
  description: string | null;
  instructions: string;
  is_active: boolean;
  user_invocable: boolean;
  trigger_pattern: string | null;
  metadata_json: string | null;
  created_at: string;
  updated_at: string;
}

// ── Omnichannel Integrations ───────────────────────────────────────────────
export interface Integration {
  id: string;
  name: string;
  platform: 'telegram' | 'discord' | 'slack' | 'whatsapp';
  agent_id: string | null;
  is_active: boolean;
}

export interface IntegrationCreate {
  name: string;
  platform: 'telegram' | 'discord' | 'slack' | 'whatsapp';
  config: Record<string, string>;
  agent_id?: string | null;
  is_active?: boolean;
}

// ── Heartbeat Schedules ────────────────────────────────────────────────────
export interface AgentSchedule {
  id: string;
  agent_id: string;
  name: string;
  description: string;
  interval_minutes: number;
  is_active: boolean;
  last_run: string | null;
  created_at: string;
}

// ── Marketplace Skills ─────────────────────────────────────────────────────
export interface MarketplaceSkill {
  id: string;
  name: string;
  description: string;
  version: string;
  author: string;
  tags: string[];
  instructions: string;
}

// ── Task & Delegation Chain ───────────────────────────────────────────────
export interface TaskInfo {
  id: string;
  chain_id: string | null;
  assigned_agent_id: string;
  conversation_id: string | null;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';
  prompt: string;
  result: string | null;
  progress: number;
  checkpoint: string | null;
  timeout_seconds: number;
  retry_count: number;
  max_retries: number;
  created_at: string;
  updated_at: string;
  started_at: string | null;
  completed_at: string | null;
}

export interface ChainInfo {
  id: string;
  conversation_id: string | null;
  parent_task_id: string | null;
  state: 'active' | 'completed' | 'halted' | 'failed';
  depth: number;
  max_depth: number;
  agents_involved_json: string;
  plan_summary: string | null;
  total_tokens_used: number;
  max_token_budget: number;
  created_at: string;
  updated_at: string;
}

