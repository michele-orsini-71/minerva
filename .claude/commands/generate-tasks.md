# Task List Management

Guidelines for managing task lists in markdown files to track progress on completing a PRD

## Task Implementation

- **One sub-task at a time
- **Completion protocol:**
  - When you finish a **sub‑task**, immediately mark it as completed by changing `[ ]` to `[x]`.
  - If **all** subtasks underneath a parent task are now `[x]`, follow this sequence:
  - Mark the **parent task** as completed
  - Run the full test suite (`pytest`, `npm test`, `bin/rails test`, etc.)
  - **Only if all tests pass**: Clean up, remove any temporary files and temporary code
  - **Do not commit**
  - **Stop and wait for user approval**

## Task List Maintenance

1. **Update the task list as you work:**
    - Mark tasks and subtasks as completed (`[x]`) per the protocol above.
    - Add new tasks as they emerge.

2. **Maintain the "Relevant Files" section:**
    - List every file created or modified.
    - Give each file a one‑line description of its purpose.

## AI Instructions

When working with task lists, the AI must:

1. Regularly update the task list file after finishing any significant work.
2. Follow the completion protocol:
    - Mark each finished **sub‑task** `[x]`.
    - Mark the **parent task** `[x]` once **all** its subtasks are `[x]`.
3. Add newly discovered tasks.
4. Keep "Relevant Files" accurate and up to date.
5. Before starting work, check which sub‑task is next.
6. After implementing a task, update the file and then pause for user approval.
7. **ALWAYS** apply principles from the two books by Uncle Bob "Clean Code" and "Clean Architecture", so: no comments and docstrings, documentation is implicit in functions with proper names and single responsibility
