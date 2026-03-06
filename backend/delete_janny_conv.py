"""Find and delete conversations with workflow error messages."""
import asyncio
from app.db.engine import async_session
from sqlalchemy import select, func, delete, or_
from app.models.conversation import Conversation, Message

async def find_and_clean():
    async with async_session() as session:
        # Search for messages mentioning workflow error keywords
        error_result = await session.execute(
            select(Message).where(
                or_(
                    Message.content.contains("WorkflowManagerTool"),
                    Message.content.contains("workflow_manager"),
                    Message.content.contains("cannot access local variable"),
                    Message.content.contains("UnboundLocal"),
                )
            )
        )
        error_msgs = error_result.scalars().all()
        print(f"Found {len(error_msgs)} messages with workflow error content")
        
        # Show them
        conv_ids = set()
        for m in error_msgs:
            preview = m.content[:100] if m.content else ""
            print(f"  [{m.role}] conv={m.conversation_id[:12]}... : {preview}")
            conv_ids.add(m.conversation_id)
        
        print(f"\nAffected conversations: {len(conv_ids)}")
        
        # Delete ALL messages from those conversations
        for conv_id in conv_ids:
            count = await session.execute(
                select(func.count()).where(Message.conversation_id == conv_id)
            )
            msg_count = count.scalar()
            print(f"\nDeleting {msg_count} messages from conv {conv_id[:12]}...")
            await session.execute(
                delete(Message).where(Message.conversation_id == conv_id)
            )
            await session.execute(
                delete(Conversation).where(Conversation.id == conv_id)
            )
        
        await session.commit()
        print(f"\nDone! Cleared {len(conv_ids)} conversation(s).")

asyncio.run(find_and_clean())
