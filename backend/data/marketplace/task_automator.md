---
name: task_automator
description: Automates repetitive tasks by creating and running workflows
version: "1.0"
author: Assitance Team
tags: [automation, workflows, productivity]
---

# Task Automator Skill

## Instructions

When asked to automate a task:

1. **Understand the task**: Ask clarifying questions about frequency, inputs, outputs, and conditions.
2. **Design the automation**:
   - What triggers it? (Manual, scheduled, event-based)
   - What data does it need?
   - What should it produce?
   - Where should results go?
3. **Create a Workflow** using `workflow_manager` tool:
   - Create the workflow with appropriate name and description
   - Add a trigger node (manual_trigger or schedule)
   - Add action nodes for each step
   - Connect the nodes
4. **For code-based automation**: Use `tool_creator` to create a custom Python tool that encapsulates the logic.
5. Always test the automation with a sample run before declaring it complete.
6. Save documentation about the automation to the workspace using `file_manager`.
