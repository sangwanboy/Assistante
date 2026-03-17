import asyncio
import json
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class ChatMessage:
    role: str
    content: str
    tool_calls: Optional[List[dict]] = None
    tool_call_id: Optional[str] = None

# Mock the parts of ContextPruner we need for testing
import sys
from pathlib import Path
sys.path.append(str(Path("d:/Projects/Assitance/backend")))

from app.services.context_pruner import ContextPruner

async def test_pruning_atomicity():
    # Mock providers manager
    class MockProviders:
        pass
    
    pruner = ContextPruner(MockProviders())
    
    # Create a conversation that will trigger pruning
    # We want a tool call + result to be right at the boundary
    messages = [
        ChatMessage(role="system", content="System prompt"),
    ]
    
    # Add many messages to exceed RECENT_TOKEN_BUDGET (10_000)
    for i in range(50):
        messages.append(ChatMessage(role="user", content=f"User message {i} " + "very long " * 20))
        messages.append(ChatMessage(role="assistant", content=f"Assistant response {i}"))

    # Now add the critical atomic block at the end
    messages.append(ChatMessage(role="user", content="Critical user message"))
    messages.append(ChatMessage(role="assistant", content="Assistant calling tool", tool_calls=[{"id": "call_1", "function": {"name": "test_tool"}}]))
    messages.append(ChatMessage(role="tool", content="Tool result output", tool_call_id="call_1"))
    
    # Total messages ~ 103
    print(f"Total messages before pruning: {len(messages)}")
    
    # Prune with a small max_tokens to force active pruning
    # Thresholds are 0.6, 0.8, 0.99
    # We want 'active' pruning (middle summary)
    pruned = await pruner.prune_context_if_needed(
        messages, 
        max_tokens=2000, # Small enough to trigger
        prune_trigger_ratio=0.1 # Force it
    )
    
    print(f"Total messages after pruning: {len(pruned)}")
    
    # Verify the last few messages
    # The last 3 should be User -> Assistant (call) -> Tool (result)
    # If it split them, we have a bug.
    
    last_three = pruned[-3:]
    roles = [m.role for m in last_three]
    print(f"Roles of last 3 messages: {roles}")
    
    if roles == ["user", "assistant", "tool"]:
        print("SUCCESS: Atomic block preserved!")
    else:
        print(f"FAILURE: Atomic block split! Expected ['user', 'assistant', 'tool'], got {roles}")
        # Debug: list last 10 roles
        print("Last 10 roles:", [m.role for m in pruned[-10:]])

if __name__ == "__main__":
    asyncio.run(test_pruning_atomicity())
