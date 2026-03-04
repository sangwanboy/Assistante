---
name: smart_summarizer
description: Summarizes documents, articles, and conversations intelligently
version: "1.0"
author: Assitance Team
tags: [productivity, documents, reading]
---

# Smart Summarizer Skill

## Instructions

When asked to summarize content:

1. **Identify the content type**: article, PDF, conversation transcript, code, report.
2. **Adapt the summary style**:
   - Articles/Reports: Executive summary (3-5 bullets) + detailed paragraphs
   - Conversations: Key decisions + action items + unresolved questions
   - Code: What it does, how it works, edge cases handled
   - PDFs: Use `search_knowledge_base` if the document was uploaded to the Knowledge Base
3. **Always include**:
   - TL;DR (1 sentence)
   - Key Points (3-7 bullets)
   - Action Items (if applicable)
4. If the document is too long for context, ask the user to upload it to the Knowledge Base first.
5. Offer to save the summary to a file using `file_manager`.
