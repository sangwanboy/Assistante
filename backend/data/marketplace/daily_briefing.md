---
name: daily_briefing
description: Generates a morning briefing with news, tasks, and priorities
version: "1.0"
author: Assitance Team
tags: [productivity, scheduling, news]
---

# Daily Briefing Skill

## Instructions

When triggered (manually or via heartbeat schedule), generate a daily briefing:

1. Get the current date/time using `get_datetime`.
2. Search for top news headlines using `web_search` with query "top news today [date]".
3. Search for any relevant domain-specific news the user has configured (check memory_context).
4. Structure the briefing as:

```
# Good morning! Daily Briefing for [DATE]

## Top Headlines
- [headline 1]
- [headline 2]
- [headline 3]

## Key Priorities for Today
[Based on any standing instructions in memory]

## Weather & Calendar
[If calendar integration is available in workspace files]
```

5. Keep the briefing concise and actionable. No fluff.
