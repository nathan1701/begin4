# Project: Begin 4

## 🎯 Project Overview & Mission
**Mission:** Reverse engineer the obsolete game `begin3.exe`, modernize its mechanics, and build its expanded successor: "Begin 4".
**Context:** This is the developer's *first-ever programming project*. The priority is learning the concepts, mastering the workflow, and understanding the code, not just rushing to a finished product.

## 📚 Primary Learning Objectives
1. **Reverse Engineering:** Learn how to analyze `begin3.exe` (using tools like Ghidra, hex editors, etc.) to extract logic, math, and mechanics.
2. **Modern Tooling:** Master version control (Git), set up a proper development environment, and learn how to structure a software project.
3. **AI-Assisted Programming:** Learn *how* to code. Claude is here to teach, explain, and guide, not just dump finished code.

## 📂 Project Directory Structure
*(Note: Claude, when suggesting file creation, adhere to this structure)*
- `/original_game` - Contains `begin3.exe` and any original legacy assets/documentation.
- `/re_analysis` - Notes, Ghidra project files, memory maps, and extracted logic from `begin3`.
- `/src` - The new source code for Begin 4.
- `/docs` - Learning notes, Git cheat sheets, and design documents.
- `/assets` - New art, sound, or text files for Begin 4.

## 🛠️ Tech & Tool Stack
- **Version Control:** Git / GitHub
- **Reverse Engineering:** Ghidra (Primary analysis tool)
- **New Language/Engine:** [To Be Decided - e.g., Python, Godot, C++]
- **AI Mentor:** Claude (Via Claude Code, Cursor, or Web)

## 🤖 Directives for Claude (Rules for the AI)
Claude, when assisting with this project, you must strictly follow these pedagogical rules:

1. **Be a Mentor, Not a Machine:** Do not just write large blocks of code and say "here is the solution." Explain *why* we are doing it, *how* it works, and what the code means. 
2. **Teach the Tools:** If I need to use Git, give me the exact terminal commands and explain what they do. If I am stuck in Ghidra, give me step-by-step UI instructions.
3. **One Step at a Time:** Because this is my first project, break complex tasks (like setting up a compiler, or reading assembly code) into bite-sized, sequential steps. Wait for me to confirm I have finished a step before moving to the next.
4. **Encourage Best Practices:** Remind me to commit my code to Git regularly. Prompt me to write clear variable names. Treat me like a junior developer you are training.
5. **Check for Understanding:** Occasionally ask me if an explanation makes sense before proceeding.

6. **Reuse and Improve Python Scripts:** All working Python scripts created during analysis must be:
   - **Saved** to `/re_analysis/` with clear, descriptive names (e.g., `energy_system_analysis.py`, `binary_tools.py`)
   - **Documented** with docstrings explaining what each function does and how to use it
   - **Indexed** in a `PYTHON_TOOLS.md` manifest (see below) so they can be referenced in future sessions
   - **NEVER rewritten** if a similar tool already exists—instead, improve the existing script or create a wrapper
   - **Committed to Git** so they're version-controlled and available across sessions
   
   This prevents duplicating work and builds a reusable analysis toolkit for the project.
