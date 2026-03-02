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
  type: 'chunk' | 'tool_call' | 'tool_result' | 'done' | 'error' | 'agent_turn_start' | 'agent_turn_end';
  delta?: string;
  tool_name?: string;
  tool_args?: Record<string, unknown>;
  tool_result?: string;
  message_id?: number;
  conversation_id?: string;
  agent_name?: string;
  error?: string;
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
  reasoning_style: string | null;
  // Memory
  memory_context: string | null;
  memory_instructions: string | null;
  // Per-agent API key (masked in responses)
  api_key: string | null;
  is_system?: boolean;
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

