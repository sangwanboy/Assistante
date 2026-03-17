import sys
import os
import time

# Mock ChatMessage
class ChatMessage:
    def __init__(self, role, content, tool_calls=None):
        self.role = role
        self.content = content
        self.tool_calls = tool_calls or []

# Mock ContextPruner dependencies
class MockContextPruner:
    def __init__(self):
        self.RECENT_TOKEN_BUDGET = 2000
        self.RECENT_FLOOR = 10
        self.RECENT_CEILING = 50

    def estimate_tokens(self, messages):
        return sum(len(m.content) // 4 + 10 for m in messages)

    # Copy updated methods from context_pruner.py
    def _group_atomic_blocks(self, messages: list[ChatMessage], limit: int | None = None) -> list[list[ChatMessage]]:
        if limit and len(messages) > limit:
            messages = messages[-limit:]
            
        blocks: list[list[ChatMessage]] = []
        current_block: list[ChatMessage] = []
        
        for msg in messages:
            if msg.role == "user":
                if current_block:
                    blocks.append(current_block)
                current_block = [msg]
            elif msg.role == "assistant":
                if not current_block or current_block[-1].role not in ["user", "assistant"]:
                    if current_block:
                        blocks.append(current_block)
                    current_block = [msg]
                else:
                    current_block.append(msg)
            elif msg.role == "tool":
                if not current_block:
                    current_block = [msg]
                else:
                    current_block.append(msg)
            else:
                if current_block:
                    blocks.append(current_block)
                blocks.append([msg])
                current_block = []
                
        if current_block:
            blocks.append(current_block)
        return blocks

    def _calculate_keep_recent(self, messages: list[ChatMessage]) -> int:
        blocks = self._group_atomic_blocks(messages, limit=100)
        kept_count = 0
        budget_used = 0
        for block in reversed(blocks):
            block_tokens = self.estimate_tokens(block)
            if budget_used + block_tokens > self.RECENT_TOKEN_BUDGET and kept_count >= self.RECENT_FLOOR:
                break
            budget_used += block_tokens
            kept_count += len(block)
            if kept_count >= self.RECENT_CEILING:
                break
        return max(self.RECENT_FLOOR, kept_count)

def test_performance():
    pruner = MockContextPruner()
    print("Generating 10,000 messages...")
    msgs = []
    for i in range(5000):
        msgs.append(ChatMessage("user", f"Hi {i}"))
        msgs.append(ChatMessage("assistant", f"Hello {i}", tool_calls=[{"id": f"tc{i}"}] if i % 10 == 0 else []))
        if i % 10 == 0:
            msgs.append(ChatMessage("tool", f"Result {i}"))

    print(f"Total messages: {len(msgs)}")
    
    start = time.time()
    keep = pruner._calculate_keep_recent(msgs)
    end = time.time()
    
    print(f"Kept count: {keep}")
    print(f"Time taken for 10k messages: {(end - start)*1000:.2f}ms")
    
    assert keep >= pruner.RECENT_FLOOR
    assert keep <= len(msgs)
    print("Performance test passed.")

def test_atomicity_at_boundary():
    pruner = MockContextPruner()
    # Create pattern: [User, Assistant+ToolCall, ToolResult] at the boundary
    msgs = [ChatMessage("user", "old")] * 100
    msgs.append(ChatMessage("user", "target start"))
    msgs.append(ChatMessage("assistant", "calling tool", tool_calls=[{"id": "1"}]))
    msgs.append(ChatMessage("tool", "result"))
    
    # If the boundary falls inside [Assistant, Tool], it should keep both.
    # Total messages: 103. RECENT_CEILING is 50. Floor is 10.
    # The last 3 messages are one block.
    
    keep = pruner._calculate_keep_recent(msgs)
    print(f"Kept count (atomicity test): {keep}")
    
    # Check if the block is kept whole
    last_msgs = msgs[-keep:]
    roles = [m.role for m in last_msgs]
    print(f"Roles kept: {roles}")
    
    # If the last block is [User, Assistant, Tool], it should be kept whole.
    # Our _group_atomic_blocks groups User, Assistant, Tool if assistant follows user.
    # Let's see how they are grouped.
    blocks = pruner._group_atomic_blocks(msgs)
    print(f"Last block size: {len(blocks[-1])}")
    assert len(blocks[-1]) >= 3 # User + Assistant + Tool
    
    print("Atomicity test passed.")

if __name__ == "__main__":
    test_performance()
    test_atomicity_at_boundary()
