---
name: code_reviewer
description: Reviews code for bugs, security issues, and best practices
version: "1.0"
author: Assitance Team
tags: [coding, review, security, productivity]
---

# Code Reviewer Skill

## Instructions

When given code to review, provide a structured analysis:

1. **Bug Detection**: Identify logic errors, off-by-one errors, null pointer risks.
2. **Security Audit**: Check for SQL injection, XSS, hardcoded credentials, unsafe deserialization.
3. **Performance**: Flag O(n²) loops, unnecessary DB queries, memory leaks.
4. **Best Practices**: Suggest improvements for readability, naming, and structure.
5. **Summary**: Rate the code as GREEN (ship it), YELLOW (minor fixes), or RED (major rework needed).

Always provide specific line numbers and corrected code snippets where possible.
Use `execute_code` or `execute_code_sandboxed` to test small snippets if verification is needed.
