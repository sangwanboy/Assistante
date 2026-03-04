"""Mention parser for @AgentName detection in chat messages.

Centralizes the parsing and validation logic for @mentions used in
the unified group chat system.
"""

import re
from dataclasses import dataclass, field


# Matches @AgentName — supports multi-word names, stops at punctuation or line boundary
MENTION_PATTERN = re.compile(r'@([\w][\w ]*?)(?=\s*[:,;.!?\n]|\s*@|\s*$)')


@dataclass
class ParsedMention:
    """A single @mention found in a message."""
    agent_name: str
    start: int
    end: int


@dataclass
class ResolvedMention:
    """A validated mention linked to an actual agent in the channel."""
    agent_id: str
    agent_name: str
    original_text: str


@dataclass
class MentionResult:
    """Complete parsing result for a message."""
    raw_mentions: list[ParsedMention] = field(default_factory=list)
    resolved: list[ResolvedMention] = field(default_factory=list)
    unresolved: list[str] = field(default_factory=list)  # Names not found in channel


def parse_mentions(text: str) -> list[ParsedMention]:
    """Extract all @mentions from a message.

    Returns list of ParsedMention with agent name and character positions.
    """
    mentions = []
    for match in MENTION_PATTERN.finditer(text):
        name = match.group(1).strip()
        if name:
            mentions.append(ParsedMention(
                agent_name=name,
                start=match.start(),
                end=match.end(),
            ))
    return mentions


async def resolve_mentions(
    session,
    mentions: list[ParsedMention],
    channel_id: str,
    include_announcement_agents: bool = False,
) -> MentionResult:
    """Validate mentions against channel membership.

    For each @mention, look up the agent by case-insensitive name match
    and verify they are a member of the channel.

    Args:
        session: SQLAlchemy async session
        mentions: parsed mentions from parse_mentions()
        channel_id: the channel to validate membership against
        include_announcement_agents: if True and channel is announcement, match all active agents

    Returns:
        MentionResult with resolved agents and unresolved names
    """
    from sqlalchemy import select, func
    from app.models.agent import Agent
    from app.models.channel import Channel
    from app.models.channel_agent import ChannelAgent

    result = MentionResult(raw_mentions=mentions)

    if not mentions:
        return result

    # Check if this is an announcements channel
    channel = await session.get(Channel, channel_id)
    is_announcement = channel.is_announcement if channel else False

    seen_names = set()
    for mention in mentions:
        lower_name = mention.agent_name.lower()
        if lower_name in seen_names:
            continue  # Deduplicate
        seen_names.add(lower_name)

        if is_announcement or include_announcement_agents:
            # Announcements channel: match any active agent
            stmt = (
                select(Agent)
                .where(
                    func.lower(Agent.name) == lower_name,
                    Agent.is_active == True,
                )
            )
        else:
            # Regular channel: agent must be a member
            stmt = (
                select(Agent)
                .join(ChannelAgent, Agent.id == ChannelAgent.agent_id)
                .where(
                    ChannelAgent.channel_id == channel_id,
                    func.lower(Agent.name) == lower_name,
                    Agent.is_active == True,
                )
            )

        db_result = await session.execute(stmt)
        agent = db_result.scalar_one_or_none()

        if agent:
            result.resolved.append(ResolvedMention(
                agent_id=agent.id,
                agent_name=agent.name,
                original_text=mention.agent_name,
            ))
        else:
            result.unresolved.append(mention.agent_name)

    return result
