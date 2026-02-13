---
name: autonomous-project
description: Coordinate a team of specialized AI agents to build projects autonomously with minimal user intervention
---

# Autonomous Project Agent Harness

This skill initializes and manages a coordinated team of specialized subagents capable of executing a project from initialization through completion with minimal user intervention.

## Overview

The Autonomous Project Agent Harness creates a master coordinator that spawns and manages role-based specialist agents including:
- **Planner/Architect** - Analyzes requirements, creates task breakdowns, designs architecture
- **Builder/Implementer** - Implements features, writes code, creates files
- **Quality Checker** - Reviews code quality, enforces standards, validates implementations
- **Tester/Validator** - Writes tests, validates functionality, ensures correctness
- **Documenter** - Creates documentation, comments code, maintains README

## Usage

When the user requests autonomous project execution, use:

```bash
python3 $SKILL_DIR/autonomous_project.py "Project description here"
```

## Core Features

### 1. Master Coordinator
- Owns global context and project goals
- Creates, assigns, and manages subagents
- Resolves conflicts between agents
- Prioritizes and sequences work
- Controls task state transitions
- Minimizes user interruptions

### 2. Local SQLite Database
- Persistent task and state management
- Session tracking and resumability
- Agent activity logging
- Progress reporting
- **No cloud dependencies** - everything stored locally

### 3. Shared Task System
- Structured task breakdown
- Task ownership and dependencies
- Status tracking (pending → in_progress → completed)
- Priority management

### 4. Quality Control Loop
- All work passes through validation
- Failed validation returns tasks with feedback
- Ensures output matches project goals

### 5. Progress Reporting
- End-of-session summaries
- Completed tasks tracking
- Active blockers identification
- Next priority recommendations

## Command Line Options

### Start New Project
```bash
python3 $SKILL_DIR/autonomous_project.py "Build a task management app"
```

### Resume Session
```bash
python3 $SKILL_DIR/autonomous_project.py --resume 20260212_143000
```

### Custom Directory
```bash
python3 $SKILL_DIR/autonomous_project.py "Build API server" --dir /path/to/project
```

### Launch Web Dashboard
```bash
python3 $SKILL_DIR/autonomous_project_web.py --web --dir /path/to/project
```

## Examples

### Example 1: Web Application
```bash
python3 $SKILL_DIR/autonomous_project.py "Build a blog platform with user authentication and markdown support"
```

**What happens:**
1. Planner analyzes requirements and creates task breakdown
2. Builder implements components incrementally
3. Quality Checker reviews each completion
4. Tester validates functionality
5. Documenter creates user guides and API docs

### Example 2: CLI Tool
```bash
python3 $SKILL_DIR/autonomous_project.py "Create a CLI tool for managing environment variables across projects"
```

### Example 3: API Service
```bash
python3 $SKILL_DIR/autonomous_project.py "Build a REST API for managing todos with SQLite backend"
```

## Database Schema

All state is stored in `.autonomous_project.db`:

**Sessions Table:**
- session_id (unique identifier)
- created_at (timestamp)
- project_goal (description)
- current_phase (planning, implementation, testing, etc.)

**Agents Table:**
- role (planner, builder, quality_checker, etc.)
- agent_id (unique agent identifier)
- started_at (timestamp)
- status (active, retired)

**Tasks Table:**
- task_id (unique identifier)
- agent_role (assigned agent)
- description (task details)
- status (pending, in_progress, completed)
- created_at, completed_at (timestamps)

**Reports Table:**
- timestamp
- phase
- completed_tasks (count)
- data (JSON report)

## Project Phases

The system progresses through these phases:

1. **Planning** - Requirements analysis, task breakdown, architecture design
2. **Implementation** - Code writing, component creation, feature building
3. **Quality Check** - Code review, standards enforcement, validation
4. **Testing** - Test creation, functionality validation, correctness verification
5. **Documentation** - README creation, code comments, user guides

## User Interaction Model

The system **minimizes interruptions** and only asks for user input when:
- Required information is missing and cannot be inferred
- Critical decisions need executive authority
- Multiple valid approaches exist with significant tradeoffs

Otherwise, agents work autonomously and provide progress reports.

## State Management

All project state is persisted locally in SQLite:
- **Session recovery** - Resume from any point
- **Agent coordination** - Track active agents and assignments
- **Task tracking** - Monitor progress and dependencies
- **Report history** - Review past progress reports

Database location: `<project_dir>/.autonomous_project.db`

## When to Use This Skill

Use when the user requests:
- "Build a new project autonomously"
- "Create [project] with minimal supervision"
- "Coordinate agents to build [project]"
- "I want an autonomous team to handle this"
- "Set up an agentic system for this project"

## Example User Requests

**User:** "Build me a todo app with React, let the agents handle it"
**You:** Start autonomous project harness with that goal

**User:** "Create a blog platform autonomously"
**You:** Initialize agent team with planning phase

**User:** "I need an API server built with minimal input from me"
**You:** Spawn coordinator and specialized agents

## Output

The script generates:
- Real-time progress updates as agents work
- Phase transition announcements
- End-of-session progress reports including:
  - Completed tasks count
  - Current blockers
  - Next priorities
  - Recommendations
  - Active agents

## Requirements

- Python 3.7+
- SQLite3 (built into Python)
- Flask (for web GUI): `pip install flask`
- No external API keys required
- No cloud dependencies

## Resume Capability

Sessions can be paused and resumed:

```bash
# Start session
python3 $SKILL_DIR/autonomous_project.py "Build notification system"

# Session creates ID: 20260212_143000
# Work happens...
# User presses Ctrl+C

# Later, resume:
python3 $SKILL_DIR/autonomous_project.py --resume 20260212_143000
```

## Constraints

- Avoids redundant agents (spawns only what's needed)
- Maintains clear task ownership
- Preserves long-term context without bloat
- Prefers incremental progress over large speculative actions
- All data stored locally (no cloud services)

## Integration with Task System

The harness integrates with the AI assistant's built-in task management:
- Creates tasks using TaskCreate/TodoWrite
- Updates status with TaskUpdate/TodoWrite
- Tracks dependencies between tasks
- Provides visibility into agent progress

### Agent and Task Synchronization to Web GUI

**IMPORTANT:** To ensure agents and tasks appear in the web GUI, you must sync them to the SQLite database.

#### Syncing Agents

When spawning agents using the Task tool, immediately sync them to the database:

```python
import subprocess
from pathlib import Path

def sync_agent_to_db(project_dir: str, role: str, agent_id: str, session_id: str = None):
    """Sync an agent to the SQLite database for web GUI visibility"""
    skill_dir = Path(__file__).parent
    subprocess.run([
        "python3",
        str(skill_dir / "sync_agent_to_db.py"),
        str(project_dir),
        role,
        agent_id,
        session_id or ""
    ])

# Example: After spawning a builder agent
sync_agent_to_db("/path/to/project", "builder", "builder_001")
```

**When to Sync Agents:**
- Immediately after spawning any agent via Task tool
- When agent status changes (active → retired)
- When reassigning tasks between agents

#### Syncing Tasks

When spawning agents that create tasks (especially the Planner agent), follow this workflow:

1. **After Planner creates tasks**, get all current tasks
2. **Export tasks to JSON** format
3. **Sync to SQLite** using the sync script:

```bash
python3 $SKILL_DIR/sync_tasks_to_db.py <project_dir> '<tasks_json>'
```

**Automated Sync Example:**

```python
import subprocess
import json
from pathlib import Path

# Get current tasks
tasks = [
    {"id": "1", "subject": "Setup project structure", "description": "...", "status": "pending", "owner": "builder"},
    # ... more tasks
]

# Sync to SQLite
skill_dir = Path(__file__).parent
subprocess.run([
    "python3",
    str(skill_dir / "sync_tasks_to_db.py"),
    str(project_dir),
    json.dumps(tasks)
])
```

**When to Sync Tasks:**
- After Planner creates initial task breakdown
- When Builder completes tasks (update status)
- When new tasks are added during execution
- Periodically during long-running sessions

This ensures the web GUI shows real-time agent and task status.

---

**Note:** This is a meta-skill that orchestrates other agents and tools to achieve project goals with maximum autonomy and minimum user intervention.
